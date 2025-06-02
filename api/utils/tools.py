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


def get_current_weather(latitude, longitude):
    # Format the URL with proper parameter substitution
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m&hourly=temperature_2m&daily=sunrise,sunset&timezone=auto"

    try:
        # Make the API call
        response = requests.get(url)

        # Raise an exception for bad status codes
        response.raise_for_status()

        # Return the JSON response
        return response.json()

    except requests.RequestException as e:
        # Handle any errors that occur during the request
        print(f"Error fetching weather data: {e}")
        return None

session_containers = {}

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
        async with httpx.AsyncClient(timeout=10000.0) as client:
            
            # Checking container for this session
            if session_id not in session_containers:

                # Create Container
                sandbox_response = await client.post(
                    "http://localhost:8000/sandboxes",
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
                f"http://localhost:8000/sandboxes/{sandbox_id}/execute",
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