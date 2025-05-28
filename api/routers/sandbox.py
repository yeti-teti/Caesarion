import os
import json
import asyncio
import time
import docker
import httpx
import uuid
import sys
import traceback
from io import StringIO
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai import OpenAI

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import StreamingResponse

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
hx = httpx.AsyncClient()
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

@router.post("/execute")
async def execute_code_in_sandbox(request: ExecuteRequest):
    """Execute Python code in this sandbox container"""
    async def stream_execution():
        try:
            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()
            
            # Execute the code
            exec(request.code)
            
            # Get the output
            output = captured_output.getvalue()
            sys.stdout = old_stdout
            
            # Stream the result
            result = {
                "type": "stdout",
                "content": output,
                "error": None
            }
            yield f"data: {json.dumps(result)}\n\n"
            
        except Exception as e:
            sys.stdout = old_stdout
            error_result = {
                "type": "error", 
                "content": str(e),
                "traceback": traceback.format_exc()
            }
            yield f"data: {json.dumps(error_result)}\n\n"
    
    return StreamingResponse(stream_execution(), media_type="text/plain")

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