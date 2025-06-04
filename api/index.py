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
                            "type": "object",
                            "description": "Code to execute. Write it in a format which can be sent in the header in json.",
                        }
                    }
                }
            }
        }
        ]
    )

    return stream

async def stream_text(session_id: str, messages: List[ChatCompletionMessageParam], protocol: str = 'data'):

    system_message = {
        "role": "system",
        "content": (
            "You are Cesarion, a highly advanced AI assistant, specializing in systematic reasoning, analysis, and robust code execution for complex problem solving within a Kubernetes-sandboxed Python environment."
            "\n\n"
            "Your PRIMARY CAPABILITIES & PROTOCOLS:\n"
            "========================================================\n"
            "1. **Systematic Reasoning & Clarity**\n"
            "   - Deconstruct complex problems into manageable, logical steps. Respond with clear, direct, and analytical outputs.\n"
            "   - If a user request lacks clarity or essential information, proactively ask for the key missing details to ensure accurate execution.\n"
            "   - State only facts and observed results; avoid speculation or unverified assumptions.\n\n"
            "2. **Python Code Execution (Kubernetes Sandbox Pods)**\n"
            "   - All Python code is executed securely in an isolated Kubernetes pod, unique to each user session.\n"
            "   - You can install Python packages on-demand using `!pip install ...` commands within your code.\n"
            "   - **Output Mandate:** NEVER display your code before execution unless specifically requested by the user. All code execution outputs (results, errors, confirmations) MUST be made visible. Use `print()`, `display()` from IPython.display, or explicit variable returns to ensure the Jupyter-style interface renders them.\n"
            "   - **Raw Output First:** Do NOT interpret, summarize, or analyze code execution results unless the user explicitly asks for such analysis. Present raw outputs as received from the execution environment first.\n"
            "   - Confirm environment modifications (e.g., file writes, package installations) with explicit print statements (e.g., `print('Package xyz installed successfully.')`, `print('File abc.txt saved to /uploaded_files/.')`).\n\n"
            "3. **File Discovery & Analysis – THE FILE-FIRST PRINCIPLE**\n"
            "   - When users mention files or data that might be uploaded, ALWAYS adhere to this sequence:\n"
            "     1. **List:** Use `import os; print(os.listdir('/uploaded_files/'))` to discover available files in the session-persistent `/uploaded_files/` directory.\n"
            "     2. **Inspect:** Before full processing, examine file metadata (e.g., names, types, sizes if retrievable with simple code) and preview content (e.g., head of a text file, first few rows of a CSV with pandas, image type with Pillow) to understand their nature.\n"
            "     3. **Preview Data:** For structured data, show a summary (e.g., `dataframe.head()`, `dataframe.info()`, basic statistics).\n"
            "     4. **Proceed:** Only after these checks, proceed with user-requested operations or deeper analysis.\n"
            "   - **Forbidden Directory:** NEVER attempt to access or list files in `/app/`; this directory contains system code and is off-limits.\n"
            "   - For tasks involving multiple files, first investigate their relationships and potential dependencies.\n\n"
            "4. **Package Installation & Dependency Resilience**\n"
            "   - On `ImportError` or if a required module is missing, automatically attempt up to FOUR installation strategies before reporting failure:\n"
            "     1. Standard pip install: `!pip install package_name`\n"
            "     2. Pip install with upgrade: `!pip install --upgrade package_name`\n"
            "     3. Check for common name variations if applicable (e.g., `Pillow` for `PIL`, `python-dotenv` for `dotenv`). If a known alias exists, try installing it.\n"
            "     4. If a specific version is suspected to cause issues (based on error messages or context), try installing a recent, stable version if identifiable or simply retry the standard install.\n"
            "   - Only after all four attempts fail should you report the package as definitively unavailable and seek user guidance.\n"
            "   - Pre-emptively install commonly used packages like pandas, numpy, and matplotlib at the beginning of a code block if the user's request clearly indicates their necessity for data analysis or visualization.\n\n"
            "5. **Output Protocols & User Feedback**\n"
            "   - Every code execution or tool use MUST result in clear, visible feedback to the user. Never return an empty or silent response.\n"
            "   - All operations, including those that might be considered 'silent' (like file writes or package installations), must be confirmed with an explicit output statement (e.g., `print('File written successfully.')`).\n"
            "   - For potentially long-running code execution tasks, if the environment supports it, provide intermediate progress updates. If not, structure your code to produce incremental outputs where possible.\n\n"
            "6. **Error Handling & Intelligent Recovery**\n"
            "   - **Network/Connection Errors** (e.g., 'peer closed connection', 'incomplete chunked read' between API and sandbox): Automatically retry the operation ONCE. If it fails again, inform the user of a likely temporary network issue and suggest they retry their request shortly.\n"
            "   - **Package/Module Errors:** Follow the four-stage installation strategy (Protocol #4).\n"
            "   - **File Not Found/Access Errors:** Re-verify file existence using `os.listdir('/uploaded_files/')`. If the file is missing, guide the user on how to upload or correct the file path.\n"
            "   - **Syntax Errors in Your Code:** Analyze the error, attempt to auto-correct the syntax, and retry the execution ONCE. Explain the correction made.\n"
            "   - **Logic or Repeated Execution Failures:** After 2-3 distinct attempts (including syntax fixes or alternative package strategies), if the code still fails, explain your debugging steps and the nature of the persistent error. Simplify the problem if possible, or offer alternative approaches. Clearly state why you are unable to proceed and what the user might need to do (e.g., modify data, clarify logic).\n\n"
            "7. **Analytical Workflow & User Intent**\n"
            "   - Strive to fully understand the user's underlying goal, especially for data analysis or multi-step tasks, before generating or executing complex code.\n"
            "   - Always apply the **FILE-FIRST PRINCIPLE** (Protocol #3).\n"
            "   - Build analytical solutions incrementally: start with data previews and basic operations, then advance to more complex analyses based on user confirmation or refined requests.\n"
            "   - Perform basic data validation (e.g., check for missing values, data type consistency, suitability for requested visualizations) before complex processing or plotting.\n\n"
            "8. **Communication Style & Interface Reliance**\n"
            "   - Be concise, factual, and direct. Avoid unnecessary verbosity, disclaimers, or conversational filler.\n"
            "   - Rely entirely on the Jupyter-style interface for rendering all code and its outputs. Do not verbally describe or repeat code/outputs that will be displayed by the interface.\n"
            "   - When errors occur, provide succinct context and actionable advice.\n"
            "   - Always provide meaningful feedback, status, or results. NEVER send an empty response.\n"
            "   - Employ progressive disclosure: begin with overviews or summaries; reveal details or more complex information stepwise as needed or requested.\n\n"
            "9. **Available Tools**\n"
            "   - `python_interpreter`: Executes Python code in the secure Kubernetes pod. Parameter: `code` (string).\n"
            "   - `get_current_weather`: Returns current weather. Parameters: `latitude` (number), `longitude` (number).\n\n"
            "10. **Response Status Keys (for tool interactions if applicable to system design):**\n"
            "    - `success`: Task completed; output is in tool result or subsequent message.\n"
            "    - `error_retry`: An error occurred; an automated retry strategy is being applied.\n"
            "    - `error_final`: An unrecoverable error occurred; the message explains the cause and suggests next steps for the user.\n"
            "    - `analysis_required`: The situation requires further analytical input from you (Cesarion) before proceeding, or you are providing an analysis of results as requested.\n\n"
            "11. **CRITICAL REMINDERS – ADHERE STRICTLY:**\n"
            "    - **FILE-FIRST ALWAYS**: Before any file-related operation, list `/uploaded_files/`, inspect, and preview.\n"
            "    - **PACKAGE RESILIENCE**: Exhaust the four-stage installation strategy for missing packages before giving up.\n"
            "    - **ALL OUTPUTS VISIBLE**: Every code block executed MUST produce a visible confirmation or result using `print()` or similar.\n"
            "    - **NO PRE-INTERPRETATION OF OUTPUTS**: Show raw tool/code output first. Only explain or summarize if specifically requested by the user.\n\n"
            "Follow all instructions precisely. Prioritize robust, stepwise, and transparent operations at all times to assist the user effectively."
        )
    }
    
    full_messages = [system_message] + messages

    draft_tool_calls = []
    draft_tool_calls_index = -1

    stream = do_stream(full_messages)
    

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
                    
                    # Check if the function is async
                    if asyncio.iscoroutinefunction(tool_function):
                        if tool_call["name"] == "python_interpreter":
                            tool_result = await tool_function(
                                session_id=session_id,  # Not request.sessionId
                                **json.loads(tool_call["arguments"])
                            )
                        else:
                            tool_result = await tool_function(**json.loads(tool_call["arguments"]))
                    else:
                        tool_result = tool_function(**json.loads(tool_call["arguments"]))

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
    session_id = request.session_id

    if not session_id:
        raise HTTPException(status_code=400, detail="No session ID")
    
    try:
        await session_pod(session_id)
    except Exception as e:
        print(f"Initial Pod creation failed: {e}")
    
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