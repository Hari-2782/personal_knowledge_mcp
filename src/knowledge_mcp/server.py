from mcp.server import MCPServer

from knowledge_mcp.tools.read import read_note as read_note_impl
from knowledge_mcp.tools.search import search_notes as search_notes_impl
from knowledge_mcp.tools.write import write_note as write_note_impl


mcp = MCPServer(
    "Personal Knowledge Base",
    instructions=(
        "A local Markdown knowledge-base server. "
        "Use search_notes to find relevant documents, "
        "read_note to retrieve their contents, and "
        "write_note to save new information."
    ),
)


@mcp.tool()
def read_note(note_path: str) -> str:
    """Read the complete contents of a Markdown note.

    Args:
        note_path: Relative path to a Markdown file inside the knowledge base.
    """
    return read_note_impl(note_path)


@mcp.tool()
def search_notes(query: str) -> list[dict]:
    """Search all Markdown notes using a keyword or phrase.

    Args:
        query: Keyword or phrase to search for.
    """
    return search_notes_impl(query)


@mcp.tool()
def write_note(
    note_path: str,
    content: str,
    overwrite: bool = False,
) -> str:
    """Create or update a Markdown note.

    Args:
        note_path: Relative destination path ending in .md.
        content: Markdown content to save.
        overwrite: Set true only when intentionally replacing an existing note.
    """
    return write_note_impl(note_path, content, overwrite)


if __name__ == "__main__":
    mcp.run()