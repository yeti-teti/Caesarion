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

from routers.sandbox import create_sandbox, execute_code, CreateSandboxRequest, ExecuteRequest

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

async def python_interpreter(code):
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create Container
            sandbox_response = await client.post(
                "http://localhost:8000/sandboxes",
                json={"lang": "python"},
                headers={'Content-Type': 'application/json'}
            )
            sandbox_response.raise_for_status()

            # Get container ID
            sandbox_data = sandbox_response.json()
            sandbox_id = sandbox_data.get('id')

            if not sandbox_id:
                return {"error": "Failed to create sandbox - no ID returned"}

            # Wait a moment for the container to be ready
            await asyncio.sleep(2)

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
                
                # res = re.findall('t": .*\n', result_text)
                # return[2:]

                if result_text.startswith('data: '):

                    json_str = result_text[6:].strip()
                    try:
                        # Parse the JSON
                        data = json.loads(json_str)
                        print(data['content'])
                        return data['content']
                            
                    except json.JSONDecodeError as e:
                        return {"error": f"Failed to parse response: {str(e)}"}
                else:
                    return {"error": "Unexpected response format"}
            else:
                # Handle JSON response
                return execute_response.json()
    except Exception as e:
        return {f"Error: {str(e)}"}