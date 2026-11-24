from knowledge_mcp.services.file_service import KnowledgeBaseService

knowledge_base = KnowledgeBaseService()


def search_notes(query: str) -> list[dict]:
    """Search Markdown notes using a case-insensitive keyword."""

    return knowledge_base.search_notes(query)