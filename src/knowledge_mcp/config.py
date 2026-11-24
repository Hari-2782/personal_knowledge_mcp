import os
from pathlib import Path

from dotenv import load_dotenv

# Project root: personal-knowledge-mcp/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load the project's .env file explicitly.
load_dotenv(PROJECT_ROOT / ".env")

# Resolve relative knowledge-base paths from the project root.
_configured_path = Path(
    os.getenv("KNOWLEDGE_BASE_PATH", "knowledge_base")
)

KNOWLEDGE_BASE_PATH = (
    _configured_path
    if _configured_path.is_absolute()
    else PROJECT_ROOT / _configured_path
).resolve()

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "1048576"))
MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "500"))