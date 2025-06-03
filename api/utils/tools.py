import requests
import re
import ast

from fastapi.responses import StreamingResponse
from jupyter_client.manager import AsyncKernelManager

import json 
from io import BytesIO, StringIO

import sys
import traceback

import httpx
import json
import asyncio
import os


def get_current_weather(latitude, longitude):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m&hourly=temperature_2m&daily=sunrise,sunset&timezone=auto"

    try:
        response = requests.get(url)

        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:

        print(f"Error fetching weather data: {e}")
        return None

session_containers = {}


def get_sandbox_base_url():

    if os.environ.get("IS_SANDBOX"):
        return "http://localhost:8000"
    
    # k8s - Use service DNS name for inter-pod communication
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        namespace = os.environ.get("KUBERNETES_NAMESPACE", "app")
        return f"http://api.{namespace}.svc.cluster.local:8000"
    
    # Local Docker development
    if os.environ.get("DOCKER_ENV"):
        return "http://host.docker.internal:8000"
    
    return "http://localhost:8000"


async def python_interpreter(code, session_id=None):
    
    if not session_id:
        return {
            "code": code,
            "outputs": [{
                "output_type": "error", 
                "ename": "SessionError",
                "evalue": "No session ID provided",
                "traceback": ["Error: Session ID required for code execution"]
            }],
            "success": False
        }

    try:
        base_url = get_sandbox_base_url()
        async with httpx.AsyncClient(timeout=10000.0) as client:
            
            # Checking container for this session
            if session_id not in session_containers:

                # Create Container
                sandbox_response = await client.post(
                    f"{base_url}/sandboxes",
                    json={"lang": "python"},
                    headers={'Content-Type': 'application/json'}
                )
                sandbox_response.raise_for_status()

                # Get container ID
                sandbox_data = sandbox_response.json()
                session_containers[session_id] = sandbox_data.get('id')

                await asyncio.sleep(2)

            sandbox_id = session_containers[session_id]

            if not sandbox_id:
                return {"error": "Failed to create sandbox"}

            # Execute the code
            execute_response = await client.post(
                f"{base_url}/sandboxes/{sandbox_id}/execute",
                json={"code": code},
                headers={'Content-Type': 'application/json'}
            )
            execute_response.raise_for_status()

            content_type = execute_response.headers.get('content-type', '')
            
            if 'application/x-ndjson' in content_type or 'text/plain' in content_type:
                # Handle streaming response
                result_text = execute_response.text
                
                # print(result_text)

                outputs = []
                for line in result_text.strip().split('\n'):
                    if line.strip():
                        try:
                            output = json.loads(line)
                            outputs.append(output)
                        except json.JSONDecodeError as e:
                            print(f"Error: {e}")
                            continue
                
                return {
                    "code": code, 
                    "outputs": outputs,
                    "success": True
                }
            else:
                return execute_response.json()
    except Exception as e:
        return {
            "code": code,
            "outputs": [{
                "output_type": "error",
                "ename": "ExecutionError",
                "evalue": str(e),
                "traceback": [f"Error: {str(e)}"]
            }],
            "success": False
        }