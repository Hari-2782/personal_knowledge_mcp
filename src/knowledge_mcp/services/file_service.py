from pathlib import Path

from knowledge_mcp.config import (
    KNOWLEDGE_BASE_PATH,
    MAX_FILE_SIZE,
    MAX_QUERY_LENGTH,
)
from knowledge_mcp.validators.input_validator import (
    validate_content,
    validate_note_path,
    validate_query,
)


class KnowledgeBaseService:
    """Provides safe access to the local Markdown knowledge base."""

    def __init__(self, root: Path = KNOWLEDGE_BASE_PATH):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_note_path(self, note_path: str) -> Path:
        """Resolve a note path and prevent escaping the knowledge base."""

        relative_path = validate_note_path(note_path)
        resolved_path = (self.root / relative_path).resolve()

        if not resolved_path.is_relative_to(self.root):
            raise ValueError("Access outside the knowledge base is forbidden.")

        return resolved_path

    def read_note(self, note_path: str) -> str:
        """Read the complete content of a Markdown note."""

        path = self._resolve_note_path(note_path)

        if not path.is_file():
            raise FileNotFoundError(f"Note not found: {note_path}")

        if path.stat().st_size > MAX_FILE_SIZE:
            raise ValueError("Note exceeds the maximum allowed file size.")

        return path.read_text(encoding="utf-8")

    def search_notes(self, query: str) -> list[dict]:
        """Search Markdown files by case-insensitive keyword matching."""

        query = validate_query(query, MAX_QUERY_LENGTH)
        query_lower = query.casefold()

        matches = []

        for path in self.root.rglob("*.md"):
            # Resolve again to prevent following symlinks outside the root.
            resolved_path = path.resolve()

            if not resolved_path.is_relative_to(self.root):
                continue

            if not resolved_path.is_file():
                continue

            if resolved_path.stat().st_size > MAX_FILE_SIZE:
                continue

            try:
                content = resolved_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            if query_lower not in content.casefold():
                continue

            matching_lines = [
                line.strip()
                for line in content.splitlines()
                if query_lower in line.casefold()
            ]

            matches.append({
                "filename": resolved_path.relative_to(self.root).as_posix(),
                "snippets": matching_lines[:5],
            })

        return matches

    def write_note(
        self,
        note_path: str,
        content: str,
        overwrite: bool = False,
    ) -> str:
        """Create or update a Markdown note."""

        path = self._resolve_note_path(note_path)
        content = validate_content(content, MAX_FILE_SIZE)

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Note already exists: {note_path}. "
                "Set overwrite=True to replace it."
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        return f"Note successfully saved: {note_path}"