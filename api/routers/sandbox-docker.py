import os
import json
import asyncio
import time
import docker
import httpx
import uuid
import tarfile
import tempfile

from dotenv import load_dotenv
from contextlib import asynccontextmanager

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from jupyter_client.manager import AsyncKernelManager

load_dotenv(".env.local")

# Configuration
IMAGE_NAME = "fastapi-jupyter-server:latest"
CONTAINER_PREFIX = "sandbox_"
SANDBOX_PORT = 8000
IDLE_TIMEOUT = 3600
CHECK_INTERVAL = 3600

# client_container = docker.from_env()
client_container = None
if not os.environ.get("IS_SANDBOX"):
    client_container = docker.from_env()
hx = httpx.AsyncClient(timeout=10000.0)
last_active = {}

async def terminate_idle_sandboxes():

    if client_container is None:
        return []

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        now = time.time()

        for container in await asyncio.to_thread(list_sandboxes):
            sandbox_id = container.id
            last_time = last_active.get(sandbox_id, None)

            if last_time is None:
                print(f"Terminating untracked sandbox {sandbox_id} (server restarted?)")
                try:
                    container.stop()
                    container.remove()
                except docker.errors.NotFound:
                    pass
                continue

            if now - last_time > IDLE_TIMEOUT:
                print(f"Terminating idle sandbox {sandbox_id} (idle for {now - last_time:.1f} seconds)")
                try:
                    container.stop()
                    container.remove()
                    last_active.pop(sandbox_id, None)
                except docker.errors.NotFound:
                    last_active.pop(sandbox_id, None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(terminate_idle_sandboxes())
    yield

router = APIRouter(lifespan=lifespan)

class CreateSandboxRequest(BaseModel):
    lang: str

class ExecuteRequest(BaseModel):
    code: str

def list_sandboxes():
    if client_container is None:
        return []
    return client_container.containers.list(filters={"label": "sbx=1"})

@router.get("/sandboxes")
async def get_sandboxes():
    sandboxes = [
        {"id": container.id, "name": container.name, "status": container.status}
        for container in list_sandboxes()
    ]
    return {"sandboxes": sandboxes}

@router.post("/sandboxes")
async def create_sandbox(request: CreateSandboxRequest):
    if request.lang.lower() != "python":
        raise HTTPException(status_code=400, detail="Only Python sandboxes are supported.")

    container_name = CONTAINER_PREFIX + str(uuid.uuid4())[:8]
    
    try:
        container = client_container.containers.run(
            IMAGE_NAME,
            name=container_name,
            labels={
                "sbx": "1",
                "sbx_lang": request.lang.lower()
            },
            detach=True,
            stdin_open=False,
            tty=False,
            ports={f"{SANDBOX_PORT}/tcp": 0},  # Auto-assign a port
            # volumes={
            #     '/path/to/host/data': {'bind': '/app/data', 'mode': 'rw'}
            # }, 
            # network="sandbox-network"
            environment={"IS_SANDBOX": "1"}
        )
        last_active[container.id] = time.time()
        return {"id": container.id, "name": container.name, "status": container.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandboxes/{sandbox_id}")
async def get_sandbox(sandbox_id: str):
    try:
        container = client_container.containers.get(sandbox_id)
        if "sbx" not in container.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")
 
        ports = container.attrs["NetworkSettings"]["Ports"]
        port_mapping = ports.get(f"{SANDBOX_PORT}/tcp", [])
        if not port_mapping:
            raise HTTPException(status_code=500, detail="No exposed port found")

        host_port = port_mapping[0]["HostPort"]

        return {
            "id": container.id,
            "name": container.name,
            "status": container.status,
            "port": host_port,
        }
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sandbox not found")

@router.post("/sandboxes/{sandbox_id}/execute")
async def execute_code(sandbox_id: str, request: ExecuteRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    try:
        container = client_container.containers.get(sandbox_id)
        if "sbx" not in container.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        ports = container.attrs["NetworkSettings"]["Ports"]
        port_mapping = ports.get(f"{SANDBOX_PORT}/tcp", [])
        if not port_mapping:
            raise HTTPException(status_code=500, detail="No exposed port found")

        host_port = port_mapping[0]["HostPort"]
        # sandbox_url = f"http://localhost:{host_port}/execute"
        sandbox_url = f"http://host.docker.internal:{host_port}/execute"
        
        # With Docker Network  
        # sandbox_container_name = container.name
        # sandbox_url = f"http://{sandbox_container_name}:{SANDBOX_PORT}/execute"
        
        print(f"Attempting to connect to sandbox: {sandbox_url}")  # Debug logging
        
        async def stream_response():
            try:
                async with hx.stream("POST", sandbox_url, json=request.dict()) as response:
                    if not response.is_success:
                        raise HTTPException(status_code=response.status_code, detail=f"Execution failed with status {response.status_code}")
                    async for chunk in response.aiter_bytes():
                        yield chunk
                        last_active[sandbox_id] = time.time()
            except httpx.ConnectError as e:
                print(f"Connection error to sandbox {sandbox_id}: {e}")
                raise HTTPException(status_code=503, detail=f"Cannot connect to sandbox - container may not be ready: {str(e)}")
            except httpx.TimeoutException as e:
                print(f"Timeout error to sandbox {sandbox_id}: {e}")
                raise HTTPException(status_code=504, detail="Sandbox request timed out")
            except httpx.RemoteProtocolError as e:
                print(f"Protocol error to sandbox {sandbox_id}: {e}")
                raise HTTPException(status_code=502, detail="Sandbox disconnected unexpectedly")
            except Exception as e:
                print(f"Unexpected error with sandbox {sandbox_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Sandbox execution error: {str(e)}")
        
        return StreamingResponse(stream_response(), media_type="application/x-ndjson")
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    except Exception as e:
        raise e


async def execute_code_inside(code: str):
    km = AsyncKernelManager()
    await km.start_kernel()
    kc = km.client()
    kc.start_channels()
    await kc.wait_for_ready()

    msg_id = kc.execute(code)

    async def stream_results():
        outputs = []
        try:
            while True:
                reply = await kc.get_iopub_msg()
                msg_type = reply["msg_type"]
                
                if msg_type == 'stream':
                    outputs.append({
                        "output_type": "stream",
                        "name": reply['content']['name'],  # stdout or stderr
                        "text": reply['content']['text']
                    })
                    yield json.dumps(outputs[-1]) + "\n"
                    
                elif msg_type == 'display_data':
                    data = reply['content']['data']
                    output = {
                        "output_type": "display_data",
                        "data": data,
                        "metadata": reply['content'].get('metadata', {})
                    }
                    outputs.append(output)
                    yield json.dumps(output) + "\n"
                    
                elif msg_type == 'execute_result':
                    data = reply['content']['data']
                    output = {
                        "output_type": "execute_result",
                        "execution_count": reply['content']['execution_count'],
                        "data": data,
                        "metadata": reply['content'].get('metadata', {})
                    }
                    outputs.append(output)
                    yield json.dumps(output) + "\n"
                    
                elif msg_type == "error":
                    output = {
                        "output_type": "error",
                        "ename": reply['content']['ename'],
                        "evalue": reply['content']['evalue'],
                        "traceback": reply['content']['traceback']
                    }
                    outputs.append(output)
                    yield json.dumps(output) + "\n"
                    break
                    
                elif msg_type == "status" and reply["content"]["execution_state"] == "idle":
                    break
        except asyncio.CancelledError:
            pass
        finally:
            kc.stop_channels()
            await km.shutdown_kernel()

    return StreamingResponse(stream_results(), media_type="application/x-ndjson")

@router.post("/execute")
async def execute_code_in_sandbox(request: ExecuteRequest):
    """Execute Python code in this sandbox container"""
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Missing 'code' field")
    
    return await execute_code_inside(request.code)


@router.delete("/sandboxes/{sandbox_id}")
async def delete_sandbox(sandbox_id: str):
    try:
        container = client_container.containers.get(sandbox_id)
        if "sbx" not in container.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        container.stop()
        container.remove()
        last_active.pop(sandbox_id, None)
        return {"message": f"Sandbox {sandbox_id} deleted"}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sandbox not found")

@router.post("/sandboxes/{sandbox_id}/upload")
async def upload_file_to_sandbox(sandbox_id: str, file: UploadFile = File(...)):

    try: 
        container = client_container.containers.get(sandbox_id)
        if "sbx" not in container.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        file_content = await file.read()

        # Temp Tar file
        with tempfile.NamedTemporaryFile(suffix='.tar') as tar_file:
            with tarfile.open(tar_file.name, 'w') as tar:

                tarinfo = tarfile.TarInfo(name=file.filename)
                tarinfo.size = len(file_content)

                import io
                tar.addfile(tarinfo, io.BytesIO(file_content))
            
            with open(tar_file.name, 'rb') as tar_data:
                container.put_archive('/app', tar_data)
        
        last_active[sandbox_id] = time.time()
        
        return {
            "message": f"File '{file.filename}' uploaded to sandbox",
            "filename": file.filename,
            "size": len(file_content),
            "path": f"/app/{file.filename}"
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/sandboxes/{sandbox_id}/files")
async def list_sandbox_files(sandbox_id: str):
    """List files in the sandbox container"""
    try:
        container = client_container.containers.get(sandbox_id)
        if "sbx" not in container.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        result = container.exec_run("ls -la /app", user="jovyan")
        if result.exit_code == 0:
            files_output = result.output.decode('utf-8')
            return {"files": files_output}
        else:
            raise HTTPException(status_code=500, detail="Failed to list files")
            
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sandbox not found")