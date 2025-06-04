import os
import json
import asyncio
from typing import List, Optional
from dotenv import load_dotenv

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai import OpenAI

from pydantic import BaseModel
from fastapi import FastAPI, Query, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from utils.prompt import ClientMessage, convert_to_openai_messages
from utils.tools import get_current_weather, python_interpreter, session_containers, session_pod

from routers import sandbox
from routers.sandbox import upload_file_to_sandbox

load_dotenv(".env.local")

app = FastAPI()
app.include_router(sandbox.router)

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class Request(BaseModel):
    messages: List[ClientMessage]
    session_id: Optional[str] = None

available_tools = {
    "get_current_weather": get_current_weather,
    "python_interpreter": python_interpreter
}

def do_stream(messages: List[ChatCompletionMessageParam]):
    try:
        stream = client.chat.completions.create(
            messages=messages,
            model="gpt-4.1",
            stream=True,
            tools=[
                {
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
            },
            {
                "type": "function",
                "function":{
                    "name": "python_interpreter",
                    "description": "Execute the python code",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                # "type": "object",
                                "type": "string",
                                "description": "Code to execute. Write it in a format which can be sent in the header in json.",
                            }
                        }
                    }
                }
            }
            ]
        )

        return stream
    except Exception as e:
        print(f"API Called failed {e}")
        raise HTTPException(status_code=500, detail=f"API Error {str(e)}")

async def stream_text(session_id: str, messages: List[ChatCompletionMessageParam], protocol: str = 'data'):

    system_message = {
        "role": "system",
        "content": (
            "You are Cesarion, an AI assistant for Python code execution in secure Kubernetes sandbox environments.\n\n"
            
            "**Core Rules:**\n"
            "1. Execute Python code using the python_interpreter tool\n"
            "2. Always use print() statements for all outputs - never return silent results\n"
            "3. For file operations: First check `import os; print(os.listdir('/uploaded_files/'))` before processing\n"
            "4. Install missing packages: `!pip install package_name` (try standard, then --upgrade if failed)\n"
            "5. Display visualizations directly - don't save them\n"
            "6. Never access /app/ directory\n\n"
            
            "**Available Tools:**\n"
            "- python_interpreter(code): Execute Python code in sandbox\n" 
            "- get_current_weather(latitude, longitude): Get weather data\n\n"
            
            "**File Workflow:**\n"
            "When users mention files: List → Inspect → Preview → Process\n\n"
            
            "**Error Handling:**\n"
            "- Auto-retry network errors once\n"
            "- Try package installation strategies if ImportError\n"
            "- Show raw outputs first, explain only if asked\n\n"
            
            "Be direct and factual. Always produce visible confirmation of operations."
        )
    }
    
    full_messages = [system_message] + messages
    draft_tool_calls = []
    draft_tool_calls_index = -1
    stream = do_stream(full_messages)
    
    try:
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
                        tool_function = available_tools[tool_call["name"]]
                        
                        try:
                            if tool_call["name"] == "python_interpreter":
                                yield '0:{text}\n'.format(text=json.dumps("Executing code..."))

                            # Execute with timeout protection
                            if asyncio.iscoroutinefunction(tool_function):
                                if tool_call["name"] == "python_interpreter":
                                    
                                    tool_result = await asyncio.wait_for(
                                        tool_function(
                                            session_id=session_id,
                                            **json.loads(tool_call["arguments"])
                                        ),
                                        timeout=300.0 
                                    )
                                else:
                                    tool_result = await asyncio.wait_for(
                                        tool_function(**json.loads(tool_call["arguments"])),
                                        timeout=60.0 
                                    )
                            else:
                                tool_result = tool_function(**json.loads(tool_call["arguments"]))

                        except asyncio.TimeoutError:
                            print(f"Tool execution timeout: {tool_call['name']}")

                            yield '0:{text}\n'.format(text=json.dumps("Execution timed out"))

                            tool_result = {
                                "code": json.loads(tool_call["arguments"]).get("code", ""),
                                "outputs": [{
                                    "output_type": "error",
                                    "ename": "TimeoutError",
                                    "evalue": "Execution timed out after 5 minutes",
                                    "traceback": ["Tool execution exceeded maximum time limit"]
                                }],
                                "success": False
                            }
                        except Exception as e:
                            print(f"Tool execution error: {tool_call['name']} - {str(e)}")

                            yield '0:{text}\n'.format(text=json.dumps("Execution Failed"))

                            tool_result = {
                                "code": json.loads(tool_call["arguments"]).get("code", ""),
                                "outputs": [{
                                    "output_type": "error",
                                    "ename": "ExecutionError",
                                    "evalue": str(e),
                                    "traceback": [f"Tool execution failed: {str(e)}"]
                                }],
                                "success": False
                            }

                        # Always send result
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
                    reason="tool-calls" if len(draft_tool_calls) > 0 else "stop",
                    prompt=prompt_tokens,
                    completion=completion_tokens
                )
                
    except Exception as e:
        print(f"Streaming error: {str(e)}")
        # Send error completion
        yield 'e:{{"finishReason":"error","error":"{error}","isContinued":false}}\n'.format(
            error=json.dumps(str(e))
        )

@app.post("/api/sessions/{session_id}/initialize")
async def initialize_session(session_id: str):
    """Initialize a session and create the sandbox pod proactively"""
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    try:
       
        if session_id in session_containers:
            return {
                "status": "exists", 
                "session_id": session_id,
                "sandbox_id": session_containers[session_id]
            }
        
    
        sandbox_id = await session_pod(session_id)
        
        return {
            "status": "created",
            "session_id": session_id, 
            "sandbox_id": sandbox_id,
            "message": "Sandbox environment initialized successfully"
        }
        
    except Exception as e:
        print(f"Session initialization failed: {e}")
        return {
            "status": "failed",
            "session_id": session_id,
            "error": str(e),
            "message": "Sandbox initialization failed, will create on first code execution"
        }

@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query('data')):

    messages = request.messages
    session_id = request.session_id

    if not session_id:
        raise HTTPException(status_code=400, detail="No session ID")
    
    # try:
    #     await session_pod(session_id)
    # except Exception as e:
    #     print(f"Initial Pod creation failed: {e}")
    
    openai_messages = convert_to_openai_messages(messages)

    response = StreamingResponse(stream_text(session_id, openai_messages, protocol))
    response.headers['x-vercel-ai-data-stream'] = 'v1'
    return response

@app.post("/api/sandboxes/upload")
async def upload_file_by_session(
    file: UploadFile = File(...),
    session_id: str = Query(...)
):
    
    print(f"Session id: {session_id}")
    print(f"session_containers: {session_containers}")
    print(f"File name:{file.filename}")

    if session_id not in session_containers:
        raise HTTPException(status_code=404, detail="No active sandbox for this session")
    
    sandbox_id = session_containers[session_id]
    
    return await upload_file_to_sandbox(sandbox_id, file)

@app.get("/")
@app.post("/")
async def root_health_check():
    return {"status": "healthy", "service": "api"}