from pathlib import Path


def validate_note_path(note_path: str) -> Path:
    """Validate a relative Markdown note path."""

    if not isinstance(note_path, str) or not note_path.strip():
        raise ValueError("Note path must be a non-empty string.")

    note_path = note_path.strip()

    if "\x00" in note_path:
        raise ValueError("Null bytes are not allowed in note paths.")

    path = Path(note_path)

    if path.is_absolute() or path.drive:
        raise ValueError("Absolute paths are not allowed.")

    if ".." in path.parts:
        raise ValueError("Path traversal is not allowed.")

    if path.suffix.lower() != ".md":
        raise ValueError("Only Markdown (.md) files are supported.")

    return path


def validate_query(query: str, max_length: int) -> str:
    """Validate a search query."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query must not be empty.")

    query = query.strip()

    if len(query) > max_length:
        raise ValueError(
            f"Search query exceeds the {max_length}-character limit."
        )

    return query


def validate_content(content: str, max_size: int) -> str:
    """Validate Markdown content and its UTF-8 size."""

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Note content must not be empty.")

    if len(content.encode("utf-8")) > max_size:
        raise ValueError(
            f"Note content exceeds the {max_size}-byte limit."
        )

    return content