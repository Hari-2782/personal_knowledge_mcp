from knowledge_mcp.services.file_service import KnowledgeBaseService

from mcp.server.mcpserver.exceptions import ToolError

knowledge_base = KnowledgeBaseService()


def write_note(
    note_path: str,
    content: str,
    overwrite: bool = False,
) -> str:
    """Create or update a Markdown note."""

    try:
        return knowledge_base.write_note(
            note_path=note_path,
            content=content,
            overwrite=overwrite,
        )
    except (ValueError, FileExistsError) as error:
        raise ToolError(str(error)) from error