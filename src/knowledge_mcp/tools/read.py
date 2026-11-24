from knowledge_mcp.services.file_service import KnowledgeBaseService

from mcp.server.mcpserver.exceptions import ToolError

knowledge_base = KnowledgeBaseService()


def read_note(note_path: str) -> str:
    """Read the complete contents of a Markdown note."""

    try:
        return knowledge_base.read_note(note_path)
    except (ValueError, FileNotFoundError) as error:
        raise ToolError(str(error)) from error