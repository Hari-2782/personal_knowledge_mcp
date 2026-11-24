import os
import asyncio
import json
import sys


from mcp import Client
from mcp.client.stdio import StdioServerParameters

from knowledge_mcp.config import PROJECT_ROOT



def create_server_parameters(
    env: dict[str, str] | None = None,
) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "knowledge_mcp.server"],
        cwd=str(PROJECT_ROOT),
        env=env,
    )

async def discover_tools(client: Client):
    """Discover tools dynamically from the MCP server."""

    response = await client.list_tools()

    print("\n========== DISCOVERED MCP TOOLS ==========")

    for tool in response.tools:
        print(f"\nTool name: {tool.name}")
        print(f"Description: {tool.description}")
        print("Input schema:")
        print(json.dumps(tool.input_schema, indent=4))

    print("\nTotal tools discovered:", len(response.tools))

    return response.tools


async def execute_tool(client: Client, name: str, arguments: dict):
    """Execute a discovered MCP tool."""

    print(f"\n========== EXECUTING: {name} ==========")
    print("Arguments:", json.dumps(arguments, indent=4))

    result = await client.call_tool(name, arguments)

    print("\nTool result:")

    for item in result.content:
        if hasattr(item, "text"):
            print(item.text)

    if result.is_error:
        print("\nTool execution returned an error.")

    return result


async def main():
    server_parameters = create_server_parameters()

    print("Starting MCP client...")
    print("Server module: knowledge_mcp.server")
    print("Project root:", PROJECT_ROOT)

    async with Client(server_parameters) as client:

        print("\nMCP connection established.")

        # Step 1: Discover tools
        tools = await discover_tools(client)

        # Step 2: Verify the expected tools exist
        expected_tools = {
            "read_note",
            "search_notes",
            "write_note",
        }

        discovered_names = {tool.name for tool in tools}

        if not expected_tools.issubset(discovered_names):
            raise RuntimeError(
                f"Missing MCP tools: {expected_tools - discovered_names}"
            )

        # Step 3: Execute a read operation
        await execute_tool(
            client,
            "read_note",
            {
                "note_path": "projects/pothole_detection.md"
            },
        )

    print("\nMCP client session closed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
