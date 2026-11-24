
import pytest

from mcp import Client

from client.mcp_client import create_server_parameters
import  os


@pytest.mark.asyncio
async def test_mcp_server_tools(monkeypatch, tmp_path):
    # Set the temporary knowledge-base directory.
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", str(tmp_path))

    # Explicitly forward the environment to the MCP subprocess.
    server_env = os.environ.copy()
    server_env.pop("GROQ_API_KEY", None)

    async with Client(
        create_server_parameters(env=server_env)
    ) as client:
        # 1. Discover tools.
        response = await client.list_tools()

        tools = {tool.name: tool for tool in response.tools}

        assert set(tools) == {
            "read_note",
            "search_notes",
            "write_note",
        }

        # 2. Verify overwrite is not exposed in the schema.
        write_schema = tools["write_note"].input_schema
        properties = write_schema["properties"]

        assert set(properties) == {"note_path", "content"}
        assert "overwrite" not in properties

        # 3. Create a note.
        create_result = await client.call_tool(
            "write_note",
            {
                "note_path": "learning/integration_test.md",
                "content": "# MCP Integration Test\n\nTesting MCP.",
            },
        )

        assert not create_result.is_error

        # 4. Read the note.
        read_result = await client.call_tool(
            "read_note",
            {"note_path": "learning/integration_test.md"},
        )

        assert not read_result.is_error

        read_text = "\n".join(
            block.text
            for block in read_result.content
            if hasattr(block, "text")
        )

        assert "# MCP Integration Test" in read_text

        # 5. Search for the note's content.
        search_result = await client.call_tool(
            "search_notes",
            {"query": "Integration Test"},
        )

        assert not search_result.is_error

        search_text = "\n".join(
            block.text
            for block in search_result.content
            if hasattr(block, "text")
        )

        assert "integration_test.md" in search_text

        # 6. Attempt to create the same note again.
        duplicate_result = await client.call_tool(
            "write_note",
            {
                "note_path": "learning/integration_test.md",
                "content": "# Updated Content",
            },
        )

        assert duplicate_result.is_error

        # 7. Verify that the original content remains unchanged.
        final_read = await client.call_tool(
            "read_note",
            {"note_path": "learning/integration_test.md"},
        )

        assert not final_read.is_error

        final_text = "\n".join(
            block.text
            for block in final_read.content
            if hasattr(block, "text")
        )

        assert "# MCP Integration Test" in final_text
        assert "# Updated Content" not in final_text
