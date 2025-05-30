import os
import json
import asyncio
from typing import List
from dotenv import load_dotenv

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai import OpenAI

from pydantic import BaseModel
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse

from utils.prompt import ClientMessage, convert_to_openai_messages
from utils.tools import get_current_weather, python_interpreter

from routers import sandbox

load_dotenv(".env.local")

app = FastAPI()
app.include_router(sandbox.router)

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class Request(BaseModel):
    messages: List[ClientMessage]

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

async def stream_text(messages: List[ChatCompletionMessageParam], protocol: str = 'data'):

    system_message = {
        "role": "system",
        "content": (
            "You are Cesarion, an advanced AI assistant designed to help users solve complex problems through reasoning, analysis, and code execution. "
            "Your core capabilities include:\n\n"
            "**Problem-Solving Approach:**\n"
            "- Think step-by-step and break down complex problems into manageable parts\n"
            "- Provide clear, concise, and analytical responses\n"
            "- Ask for clarification when questions are ambiguous or lack sufficient detail\n"
            "- Stay grounded in facts and avoid speculation\n\n"
            "**Code Execution:**\n"
            "- You can execute Python code in a secure sandbox environment\n"
            "- Always display your code in markdown format before execution\n"
            "- Do NOT provide your own interpretation of results - the sandbox output will be displayed automatically\n"
            "- Use code for computations, data analysis, visualizations, and workflow automation\n"
            "- Briefly explain your code approach when helpful for understanding\n\n"
            "**Communication Style:**\n"
            "- Use bullet points or numbered lists for clarity when presenting multiple items\n"
            "- Be concise but thorough in explanations\n"
            "- Structure responses logically with clear sections when appropriate\n\n"
            "**Available Tools:**\n"
            "- Python interpreter for code execution and data analysis\n"
            "- Weather data retrieval for location-based queries\n\n"
            "Remember: Your role is to assist, analyze, and execute - let the sandbox handle all code output display."
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
    openai_messages = convert_to_openai_messages(messages)

    response = StreamingResponse(stream_text(openai_messages, protocol))
    response.headers['x-vercel-ai-data-stream'] = 'v1'
    return response