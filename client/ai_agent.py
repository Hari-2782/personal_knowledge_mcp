
import asyncio
import json
import os

from dotenv import load_dotenv
from groq import AsyncGroq
from mcp import Client

from client.mcp_client import create_server_parameters
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

MAX_TOOL_ROUNDS = 5

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found in .env")


SYSTEM_PROMPT = """
You are a personal knowledge-base assistant.

You have access to a local Markdown knowledge base through MCP tools.

Rules:
1. Use search_notes to find documents matching a topic.
2. Use read_note when the user requests the contents of a specific note.
3. Use write_note when the user explicitly asks to save or create information.
4. Never claim that a note was read, searched, or saved unless the tool
   returned a successful result.
5. Use paths relative to the knowledge-base root.
6. Never invent document contents.
7. Do not overwrite an existing note unless the user explicitly requests it.
8. Answer clearly using the actual information returned by the tools.
"""


def convert_mcp_tools_to_groq(mcp_tools) -> list[dict]:
    """Convert MCP tool definitions into Groq function schemas."""

    groq_tools = []

    for tool in mcp_tools:
        groq_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        })

    return groq_tools

def serialize_mcp_result(result) -> str:
    """Convert MCP tool results into text for the LLM."""

    output = []

    for item in result.content:
        if hasattr(item, "text"):
            output.append(item.text)
        else:
            output.append(
                json.dumps(item.model_dump(mode="json"))
            )

    if result.is_error:
        return "MCP tool execution failed: " + "\n".join(output)

    if not output:
        return "The MCP tool returned no content."

    return "\n".join(output)


async def execute_mcp_tool(
    mcp_client: Client,
    tool_name: str,
    arguments: dict,
    allowed_tools: set[str],
) -> str:
    """Execute a model-requested tool through the MCP client."""

    if tool_name not in allowed_tools:
        return f"Error: Unknown or unauthorized tool: {tool_name}"

    if not isinstance(arguments, dict):
        return "Error: Tool arguments must be a JSON object."

    print(f"\n[MCP TOOL CALL] {tool_name}")
    print(json.dumps(arguments, indent=2))

    try:
        result = await mcp_client.call_tool(
            tool_name,
            arguments,
        )

        tool_output = serialize_mcp_result(result)

        print("\n[MCP TOOL RESULT]")
        print(tool_output)

        return tool_output

    except Exception as error:
        error_message = (
            f"Tool execution failed: {type(error).__name__}: {error}"
        )
        print(error_message)
        return error_message


async def process_user_message(
    user_message: str,
    conversation: list[dict],
    groq_client: AsyncGroq,
    mcp_client: Client,
    groq_tools: list[dict],
    allowed_tools: set[str],
) -> str:
    """Run the LLM and MCP tool-calling loop."""

    conversation.append({
        "role": "user",
        "content": user_message,
    })

    for round_number in range(MAX_TOOL_ROUNDS):

        response = await groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=conversation,
            tools=groq_tools,
            tool_choice="auto",
            parallel_tool_calls=False,
            temperature=0.2,
            max_completion_tokens=2048,
            include_reasoning=False,
        )

        assistant_message = response.choices[0].message

        # No tool call: the model has generated its final answer.
        if not assistant_message.tool_calls:

            answer = assistant_message.content or (
                "The model returned no text response."
            )

            conversation.append({
                "role": "assistant",
                "content": answer,
            })

            return answer

        # Preserve the assistant's tool-call request in conversation history.
        conversation.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in assistant_message.tool_calls
            ],
        })

        print(
            f"\n[AGENT] Tool-calling round "
            f"{round_number + 1}/{MAX_TOOL_ROUNDS}"
        )

        for tool_call in assistant_message.tool_calls:

            tool_name = tool_call.function.name

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )
            except (json.JSONDecodeError, TypeError):
                tool_result = "Error: Invalid JSON tool arguments."
            else:
                tool_result = await execute_mcp_tool(
                    mcp_client=mcp_client,
                    tool_name=tool_name,
                    arguments=arguments,
                    allowed_tools=allowed_tools,
                )

            conversation.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

    # Prevent an unlimited agent/tool loop.
    conversation.append({
        "role": "assistant",
        "content": (
            "I reached the maximum number of tool-calling rounds. "
            "Please narrow your request."
        ),
    })

    return conversation[-1]["content"]


async def main():
    groq_client = AsyncGroq(api_key=GROQ_API_KEY)

    server_parameters = create_server_parameters()

    print("=" * 55)
    print("PERSONAL KNOWLEDGE BASE AI AGENT")
    print("=" * 55)
    print("Model:", GROQ_MODEL)
    print("Connecting to MCP server...")

    try:
        async with Client(server_parameters) as mcp_client:

            print("MCP connection established.")

            # Discover tools from the MCP server.
            response = await mcp_client.list_tools()

            mcp_tools = response.tools

            # Convert MCP schemas to Groq function definitions.
            groq_tools = convert_mcp_tools_to_groq(mcp_tools)

            allowed_tools = {
                tool.name for tool in mcp_tools
            }

            print("\nDiscovered tools:")
            for tool in mcp_tools:
                print("-", tool.name)

            conversation = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                }
            ]

            print("\nAgent is ready.")
            print("Type 'exit' to stop.\n")

            while True:

                user_message = input("You: ").strip()

                if user_message.lower() in {"exit", "quit"}:
                    print("Shutting down agent.")
                    break

                if not user_message:
                    continue

                try:
                    answer = await process_user_message(
                        user_message=user_message,
                        conversation=conversation,
                        groq_client=groq_client,
                        mcp_client=mcp_client,
                        groq_tools=groq_tools,
                        allowed_tools=allowed_tools,
                    )

                    print("\nAssistant:", answer)
                    print()

                except Exception as error:
                    print(
                        "\nAgent error:",
                        type(error).__name__,
                        str(error),
                    )

    finally:
        await groq_client.close()


if __name__ == "__main__":
    asyncio.run(main())
