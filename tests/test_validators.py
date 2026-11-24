
import pytest

from knowledge_mcp.validators.input_validator import (
    validate_content,
    validate_note_path,
    validate_query,
)


class TestValidateNotePath:

    def test_accepts_valid_markdown_path(self):
        result = validate_note_path("projects/pothole_detection.md")
        assert result.as_posix() == "projects/pothole_detection.md"

    def test_rejects_empty_path(self):
        with pytest.raises(ValueError):
            validate_note_path("")

    def test_rejects_non_string_path(self):
        with pytest.raises(ValueError):
            validate_note_path(None)

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="traversal"):
            validate_note_path("../outside.md")

    def test_rejects_absolute_path(self, tmp_path):
        with pytest.raises(ValueError, match="Absolute"):
            validate_note_path(str(tmp_path / "outside.md"))

    def test_rejects_non_markdown_extension(self):
        with pytest.raises(ValueError, match="Markdown"):
            validate_note_path("notes.txt")

    def test_accepts_uppercase_markdown_extension(self):
        result = validate_note_path("notes.MD")
        assert result.suffix == ".MD"

    def test_rejects_null_byte(self):
        with pytest.raises(ValueError, match="Null bytes"):
            validate_note_path("notes\x00.md")


class TestValidateQuery:

    def test_accepts_valid_query(self):
        assert validate_query("  YOLOv8  ", 100) == "YOLOv8"

    def test_rejects_empty_query(self):
        with pytest.raises(ValueError):
            validate_query("", 100)

    def test_rejects_non_string_query(self):
        with pytest.raises(ValueError):
            validate_query(None, 100)

    def test_rejects_query_exceeding_limit(self):
        with pytest.raises(ValueError, match="character limit"):
            validate_query("A" * 101, 100)


class TestValidateContent:

    def test_accepts_valid_content(self):
        content = "# Python Notes"
        assert validate_content(content, 100) == content

    def test_rejects_empty_content(self):
        with pytest.raises(ValueError):
            validate_content("", 100)

    def test_rejects_whitespace_only_content(self):
        with pytest.raises(ValueError):
            validate_content("   ", 100)

    def test_rejects_non_string_content(self):
        with pytest.raises(ValueError):
            validate_content(None, 100)

    def test_enforces_utf8_byte_limit(self):
        # Each emoji occupies multiple bytes in UTF-8.
        with pytest.raises(ValueError, match="byte limit"):
            validate_content("😀" * 10, 10)
