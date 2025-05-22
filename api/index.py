import os
import json
import asyncio
import time
import docker
import httpx
import uuid
from typing import List
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai import OpenAI

from pydantic import BaseModel
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse

from utils.prompt import ClientMessage, convert_to_openai_messages
from utils.tools import get_current_weather
from utils.tools import execute_code


load_dotenv(".env.local")

# Configuration
IMAGE_NAME = "fastapi-jupyter-server"
CONTAINER_PREFIX = "sandbox_"
SANDBOX_PORT = 8000
IDLE_TIMEOUT = 3600
CHECK_INTERVAL = 3600

client_container = docker.from_env()
hx = httpx.AsyncClient()
last_active = {}

async def terminate_idle_sandboxes():
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

app = FastAPI(lifespan=lifespan)

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


class Request(BaseModel):
    messages: List[ClientMessage]


available_tools = {
    "get_current_weather": get_current_weather,
}

def do_stream(messages: List[ChatCompletionMessageParam]):
    stream = client.chat.completions.create(
        messages=messages,
        model="gpt-4o",
        stream=True,
        tools=[{
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather at a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "The latitude of the location",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "The longitude of the location",
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
            },
        }]
    )

    return stream

def stream_text(messages: List[ChatCompletionMessageParam], protocol: str = 'data'):
    draft_tool_calls = []
    draft_tool_calls_index = -1

    stream = client.chat.completions.create(
        messages=messages,
        model="gpt-4o",
        stream=True,
        tools=[{
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather at a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "The latitude of the location",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "The longitude of the location",
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
            },
        }]
    )

    for chunk in stream:
        for choice in chunk.choices:
            if choice.finish_reason == "stop":
                continue

            elif choice.finish_reason == "tool_calls":
                for tool_call in draft_tool_calls:
                    yield '9:{{"toolCallId":"{id}","toolName":"{name}","args":{args}}}\n'.format(
                        id=tool_call["id"],
                        name=tool_call["name"],
                        args=tool_call["arguments"])

                for tool_call in draft_tool_calls:
                    tool_result = available_tools[tool_call["name"]](
                        **json.loads(tool_call["arguments"]))

                    yield 'a:{{"toolCallId":"{id}","toolName":"{name}","args":{args},"result":{result}}}\n'.format(
                        id=tool_call["id"],
                        name=tool_call["name"],
                        args=tool_call["arguments"],
                        result=json.dumps(tool_result))

            elif choice.delta.tool_calls:
                for tool_call in choice.delta.tool_calls:
                    id = tool_call.id
                    name = tool_call.function.name
                    arguments = tool_call.function.arguments

                    if (id is not None):
                        draft_tool_calls_index += 1
                        draft_tool_calls.append(
                            {"id": id, "name": name, "arguments": ""})

                    else:
                        draft_tool_calls[draft_tool_calls_index]["arguments"] += arguments

            else:
                yield '0:{text}\n'.format(text=json.dumps(choice.delta.content))

        if chunk.choices == []:
            usage = chunk.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens

            yield 'e:{{"finishReason":"{reason}","usage":{{"promptTokens":{prompt},"completionTokens":{completion}}},"isContinued":false}}\n'.format(
                reason="tool-calls" if len(
                    draft_tool_calls) > 0 else "stop",
                prompt=prompt_tokens,
                completion=completion_tokens
            )

@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query('data')):
    messages = request.messages
    openai_messages = convert_to_openai_messages(messages)

    response = StreamingResponse(stream_text(openai_messages, protocol))
    response.headers['x-vercel-ai-data-stream'] = 'v1'
    return response


class CreateSandboxRequest(BaseModel):
    lang: str

class ExecuteRequest(BaseModel):
    code: str

def list_sandboxes():
    return client_container.containers.list(filters={"label": "sbx=1"})

@app.get("/sandboxes")
async def get_sandboxes():
    sandboxes = [
        {"id": container.id, "name": container.name, "status": container.status}
        for container in list_sandboxes()
    ]
    return {"sandboxes": sandboxes}

@app.post("/sandboxes")
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
        )
        last_active[container.id] = time.time()
        return {"id": container.id, "name": container.name, "status": container.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sandboxes/{sandbox_id}")
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

@app.post("/sandboxes/{sandbox_id}/execute")
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

        async def stream_response():
            async with hx.stream("POST", sandbox_url, json=request.dict()) as response:
                if not response.is_success:
                    raise HTTPException(status_code=response.status_code, detail=f"Execution failed")
                async for chunk in response.aiter_bytes():
                    yield chunk
                    last_active[sandbox_id] = time.time()

        return StreamingResponse(stream_response(), media_type="application/x-ndjson")
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sandbox not found")

@app.delete("/sandboxes/{sandbox_id}")
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

