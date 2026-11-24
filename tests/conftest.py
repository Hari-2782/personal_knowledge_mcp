
import pytest

from knowledge_mcp.services.file_service import KnowledgeBaseService


@pytest.fixture
def knowledge_base(tmp_path):
    """Provide an isolated knowledge base for each test."""
    return KnowledgeBaseService(root=tmp_path)
