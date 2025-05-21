import requests
from fastapi.responses import StreamingResponse
from jupyter_client.manager import AsyncKernelManager
import asyncio
import json 
from io import BytesIO

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

async def execute_code(code: str):
    km = AsyncKernelManager()
    await km.start_kernel()
    kc = km.client()
    kc.start_channels()
    await kc.wait_for_ready()

    msg_id = kc.execute(code)

    async def stream_results():
        try:
            while True:
                reply = await kc.get_iopub_msg()
                msg_type = reply["msg_type"]
                if msg_type == 'stream':
                    yield json.dumps({"text": reply['content']['text']}) + "\n"
                elif msg_type == 'display_data':
                    data = reply['content']['data']
                    if "image/png" in data:
                        yield json.dumps({"image": data["image/png"]}) + "\n"
                elif msg_type == "error":
                    traceback = "\n".join(reply['content']['traceback'])
                    yield json.dumps({"error": traceback}) + "\n"
                    break
                elif msg_type == "status" and reply["content"]["execution_state"] == "idle":
                    break
        except asyncio.CancelledError:
            pass
        finally:
            kc.stop_channels()
            await km.shutdown_kernel()

    return StreamingResponse(stream_results(), media_type="application/x-ndjson")
