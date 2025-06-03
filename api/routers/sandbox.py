import os
import json
import asyncio
import time
import httpx
import uuid
import traceback
import base64
from io import BytesIO

from dotenv import load_dotenv
from contextlib import asynccontextmanager

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from jupyter_client.manager import AsyncKernelManager

from kubernetes import client, config
import kubernetes.client.exceptions as k8s_exceptions
from kubernetes.stream import stream

load_dotenv(".env.local")

# Configuration
IMAGE_NAME = os.environ.get(
    "SANDBOX_IMAGE", 
    "us-central1-docker.pkg.dev/exalted-crane-459000-g5/backend/backend-api:17"
)
SANDBOX_PREFIX = "sandbox-"
SANDBOX_PORT = 8000
IDLE_TIMEOUT = 3600
CHECK_INTERVAL = 3600

# k8s client init
k8s_v1 = None
k8s_apps = None

print(f"Sandbox chekc: {os.environ.get('IS_SANDBOX')}")
print(f"Not sandbox check: {not os.environ.get('IS_SANDBOX')}")

# if not os.environ.get("IS_SANDBOX"):
if os.environ.get("IS_SANDBOX") != "1":
    print(f"IS_SANDBOX = {os.environ.get('IS_SANDBOX')}")

    config_loaded = False
    try:
        config.load_incluster_config()
        config_loaded = True
        print("Loaded cluster config")
    except config.ConfigException:
        try:
            config.load_kube_config()
            config_loaded = True
            print("Loaded kube config")
        except config.ConfigException:
            print("NO config")
    
    if config_loaded:
        k8s_v1 = client.CoreV1Api()
        k8s_apps = client.AppsV1Api()
        print("k8s cluster initialized")
    else:
        print("k8s config not laoded")

hx = httpx.AsyncClient(timeout=10000.0)
last_active = {}

async def terminate_idle_sandboxes():
    if k8s_v1 is None:
        return

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        now = time.time()

        for pod in list_sandboxes():
            sandbox_id = pod.metadata.name
            last_time = last_active.get(sandbox_id, None)

            if last_time is None:
                print(f"Terminating sandbox {sandbox_id}")
                try:
                    await cleanup_sandbox_resources(sandbox_id)
                except k8s_exceptions.ApiException:
                    pass
                continue

            if now - last_time > IDLE_TIMEOUT:
                print(f"Terminating sandbox {sandbox_id}")
                try:
                    await cleanup_sandbox_resources(sandbox_id)
                    last_active.pop(sandbox_id, None)
                except k8s_exceptions.ApiException:
                    last_active.pop(sandbox_id, None)

def get_namespace():
    return os.environ.get("KUBERNETES_NAMESPACE", "app")

async def cleanup_sandbox_resources(sandbox_id: str):
    namespace = get_namespace()
    
    try:
        k8s_v1.delete_namespaced_service(
            name=f"{sandbox_id}-service",
            namespace=namespace
        )
    except k8s_exceptions.ApiException:
        pass

    try:
        k8s_v1.delete_namespaced_pod(
            name=sandbox_id,
            namespace=namespace
        )
    except k8s_exceptions.ApiException:
        pass

async def wait_for_pod_ready(pod_name: str, namespace: str, timeout: int = 300):
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            pod = k8s_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            if pod.status.phase == "Running":

                if pod.status.container_statuses:
                    all_ready = all(
                        container.ready for container in pod.status.container_statuses
                    )
                    if all_ready and pod.status.pod_ip:
                        return pod
            
            await asyncio.sleep(2)
            
        except k8s_exceptions.ApiException:
            await asyncio.sleep(2)
    
    raise HTTPException(status_code=504, detail="Pod startup timeout")

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

    if k8s_v1 is None:
        return []
    
    try:
        pods = k8s_v1.list_namespaced_pod(
            namespace=get_namespace(),
            label_selector="app=sandbox,sbx=1"
        )
        return pods.items
    except Exception:
        return []

@router.get("/sandboxes")
async def get_sandboxes():
    sandboxes = [
        {
            "id": pod.metadata.name, 
            "name": pod.metadata.name, 
            "status": pod.status.phase,
            "ready": pod.status.container_statuses[0].ready if pod.status.container_statuses else False
        }
        for pod in list_sandboxes()
    ]
    return {"sandboxes": sandboxes}

@router.post("/sandboxes")
async def create_sandbox(request: CreateSandboxRequest):

    print(f"Starting sandbox: {request.lang}")

    if request.lang.lower() != "python":
        raise HTTPException(status_code=400, detail="Only Python sandboxes are supported.")

    if k8s_v1 is None:
        print("k8s client None")
        raise HTTPException(status_code=500, detail="Kubernetes client not available")

    pod_name = f"{SANDBOX_PREFIX}{str(uuid.uuid4())[:8]}"
    namespace = get_namespace()
    print(f"Creating sandbox with name: {pod_name} in namespace: {namespace}")
    
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": pod_name,
            "namespace": namespace,
            "labels": {
                "app": "sandbox",
                "sbx": "1",
                "sbx_lang": request.lang.lower(),
                "pod-name": pod_name
            }
        },
        "spec": {
            "containers": [{
                "name": "jupyter-sandbox",
                "image": IMAGE_NAME,
                "ports": [{"containerPort": SANDBOX_PORT}],
                "env": [
                    {"name": "IS_SANDBOX", "value": "1"},
                    {"name": "PORT", "value": str(SANDBOX_PORT)},
                    {"name": "OPENAI_API_KEY", "value": os.environ.get("OPENAI_API_KEY", "")}
                ],
                "resources": {
                    "limits": {"memory": "5Gi", "cpu": "500m"},
                    "requests": {"memory": "1024Mi", "cpu": "100m"}
                },
                "readinessProbe": {
                    "httpGet": {
                        "path": "/health",
                        "port": SANDBOX_PORT
                    },
                    "initialDelaySeconds": 5,
                    "periodSeconds": 3,
                    "timeoutSeconds": 5
                },
                "livenessProbe": {
                    "httpGet": {
                        "path": "/health", 
                        "port": SANDBOX_PORT
                    },
                    "initialDelaySeconds": 15,
                    "periodSeconds": 10,
                    "timeoutSeconds": 5
                }
            }],
            "restartPolicy": "Never"
        }
    }
    
    service_manifest = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": f"{pod_name}-service",
            "namespace": namespace,
            "labels": {
                "app": "sandbox",
                "sbx": "1"
            }
        },
        "spec": {
            "selector": {
                "app": "sandbox",
                "sbx": "1",
                "pod-name": pod_name
            },
            "ports": [{
                "port": SANDBOX_PORT,
                "targetPort": SANDBOX_PORT,
                "protocol": "TCP"
            }],
            "type": "ClusterIP"
        }
    }

    print(f"Image: {IMAGE_NAME}")
    print(f"Pod: {pod_name}")
    
    try:
        print("Creating pod")
        # Create pod
        pod = k8s_v1.create_namespaced_pod(
            namespace=namespace, 
            body=pod_manifest
        )
        print(f"Pod created: {pod.metadata.name}")
        
        print("Creating service")
        # Create service  
        service = k8s_v1.create_namespaced_service(
            namespace=namespace,
            body=service_manifest
        )
        print(f"Service created: {service.metadata.name}")
        
        last_active[pod.metadata.name] = time.time()
        print("Sandbox creation completed successfully")
        
        return {
            "id": pod.metadata.name, 
            "name": pod.metadata.name, 
            "status": "creating"
        }
    except Exception as e:
        print(f"Sandbox cration error: {str(e)}")
        print(f"Error: {type(e)}")

        if hasattr(e, 'body'):
            print(f"ERROR: API response body: {e.body}")
        if hasattr(e, 'status'):
            print(f"ERROR: HTTP status: {e.status}")
        if hasattr(e, 'reason'):
            print(f"ERROR: Reason: {e.reason}")

        import traceback
        print("Full traceback")
        traceback.print_exc()

        try:
            await cleanup_sandbox_resources(pod_name)
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandboxes/{sandbox_id}")
async def get_sandbox(sandbox_id: str):
    if k8s_v1 is None:
        raise HTTPException(status_code=500, detail="Kubernetes client not available")
        
    try:
        pod = k8s_v1.read_namespaced_pod(
            name=sandbox_id, 
            namespace=get_namespace()
        )
        
        if "sbx" not in pod.metadata.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        return {
            "id": pod.metadata.name,
            "name": pod.metadata.name,
            "status": pod.status.phase,
            "ip": pod.status.pod_ip,
            "ready": pod.status.container_statuses[0].ready if pod.status.container_statuses else False
        }
    except k8s_exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sandboxes/{sandbox_id}/execute")
async def execute_code(sandbox_id: str, request: ExecuteRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    
    if k8s_v1 is None:
        raise HTTPException(status_code=500, detail="Kubernetes client not available")
    
    try:
        pod = k8s_v1.read_namespaced_pod(
            name=sandbox_id, 
            namespace=get_namespace()
        )
        
        if "sbx" not in pod.metadata.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        if pod.status.phase != "Running":
            pod = await wait_for_pod_ready(sandbox_id, get_namespace())

        # Use service DNS name for networking
        namespace = get_namespace()
        service_url = f"http://{sandbox_id}-service.{namespace}.svc.cluster.local:{SANDBOX_PORT}/execute"
        
        print(f"Executing code in sandbox: {service_url}")
        
        async def stream_response():
            try:
                async with hx.stream("POST", service_url, json=request.dict()) as response:
                    if not response.is_success:
                        raise HTTPException(status_code=response.status_code, detail=f"Execution failed with status {response.status_code}")
                    async for chunk in response.aiter_bytes():
                        yield chunk
                        last_active[sandbox_id] = time.time()
            except httpx.ConnectError as e:
                print(f"Connection error to sandbox {sandbox_id}: {e}")
                raise HTTPException(status_code=503, detail=f"Cannot connect to sandbox: {str(e)}")
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
    
    except k8s_exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.post("/health")
@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@router.delete("/sandboxes/{sandbox_id}")
async def delete_sandbox(sandbox_id: str):
    if k8s_v1 is None:
        raise HTTPException(status_code=500, detail="Kubernetes client not available")
        
    try:
        pod = k8s_v1.read_namespaced_pod(
            name=sandbox_id, 
            namespace=get_namespace()
        )
        if "sbx" not in pod.metadata.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        await cleanup_sandbox_resources(sandbox_id)
        last_active.pop(sandbox_id, None)
        return {"message": f"Sandbox {sandbox_id} deleted"}
    except k8s_exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sandboxes/{sandbox_id}/upload")
async def upload_file_to_sandbox(sandbox_id: str, file: UploadFile = File(...)):

    print(f"Uploading to {sandbox_id}, file={file.filename}")

    if k8s_v1 is None:
        raise HTTPException(status_code=500, detail="Kubernetes client not available")

    try: 
        print(f"Pod info readign: {sandbox_id}")
        pod = k8s_v1.read_namespaced_pod(
            name=sandbox_id, 
            namespace=get_namespace()
        )
        print(f"Pod found, labels={pod.metadata.labels}")
        
        if "sbx" not in pod.metadata.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")
    
        print(f"Pod phase={pod.status.phase}")
        
        if pod.status.phase != "Running":
            print(f"Pod not running")
            raise HTTPException(status_code=503, detail="Sandbox not ready")
        
        print(f"Reading file content")
        file_content = await file.read()
        print(f'File size={len(file_content)} bytes')
        
        # base64 encoded content for kubectl exec
        print(f"Encoding file")
        encoded_content = base64.b64encode(file_content).decode('utf-8')
        print("Encoded")
        
        # kubectl exec to write file
        exec_command = [
            'sh', '-c', 
            f'echo "{encoded_content}" | base64 -d > /app/{file.filename}'
        ]
        print(f"Executing command")
        
        try:
            print("Starting kubectl exec")
            resp = stream(
                k8s_v1.connect_get_namespaced_pod_exec,
                sandbox_id,
                get_namespace(),
                command=exec_command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False
            )
            print("Kubectl exec finish")
            print(f"Response: {resp}")
            
            last_active[sandbox_id] = time.time()
            
            return {
                "message": f"File '{file.filename}' uploaded to sandbox",
                "filename": file.filename,
                "size": len(file_content),
                "path": f"/app/{file.filename}"
            }
        except Exception as exec_error:
            print("Traceback")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(exec_error)}")
        
    except k8s_exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandboxes/{sandbox_id}/files")
async def list_sandbox_files(sandbox_id: str):
    if k8s_v1 is None:
        raise HTTPException(status_code=500, detail="Kubernetes client not available")
        
    try:
        pod = k8s_v1.read_namespaced_pod(
            name=sandbox_id, 
            namespace=get_namespace()
        )
        if "sbx" not in pod.metadata.labels:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        if pod.status.phase != "Running":
            raise HTTPException(status_code=503, detail="Sandbox not ready")
        
        exec_command = ['ls', '-la', '/app']
        
        try:
            resp = stream(
                k8s_v1.connect_get_namespaced_pod_exec,
                sandbox_id,
                get_namespace(),
                command=exec_command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False
            )
            
            return {"files": resp}
        except Exception as exec_error:
            raise HTTPException(status_code=500, detail=f"Failed to list files: {str(exec_error)}")
            
    except k8s_exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        raise HTTPException(status_code=500, detail=str(e))