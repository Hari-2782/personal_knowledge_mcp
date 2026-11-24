
import pytest

import knowledge_mcp.services.file_service as file_service_module


class TestReadNote:

    def test_reads_existing_note(self, knowledge_base):
        path = knowledge_base.root / "python" / "memory.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Python Memory", encoding="utf-8")

        result = knowledge_base.read_note("python/memory.md")

        assert result == "# Python Memory"

    def test_rejects_missing_note(self, knowledge_base):
        with pytest.raises(FileNotFoundError):
            knowledge_base.read_note("missing.md")

    def test_rejects_invalid_path(self, knowledge_base):
        with pytest.raises(ValueError):
            knowledge_base.read_note("../outside.md")

    def test_rejects_oversized_file(
        self, knowledge_base, monkeypatch
    ):
        monkeypatch.setattr(
            file_service_module, "MAX_FILE_SIZE", 5
        )

        path = knowledge_base.root / "large.md"
        path.write_text("123456", encoding="utf-8")

        with pytest.raises(ValueError, match="maximum allowed"):
            knowledge_base.read_note("large.md")


class TestSearchNotes:

    def test_finds_matching_note(self, knowledge_base):
        path = knowledge_base.root / "python.md"
        path.write_text(
            "# Python\nYOLOv8 is a detection model.",
            encoding="utf-8",
        )

        results = knowledge_base.search_notes("YOLOv8")

        assert len(results) == 1
        assert results[0]["filename"] == "python.md"
        assert "YOLOv8" in results[0]["snippets"][0]

    def test_search_is_case_insensitive(self, knowledge_base):
        path = knowledge_base.root / "python.md"
        path.write_text("Learning PYTHON", encoding="utf-8")

        results = knowledge_base.search_notes("python")

        assert len(results) == 1

    def test_returns_empty_list_when_no_match(self, knowledge_base):
        path = knowledge_base.root / "python.md"
        path.write_text("Python notes", encoding="utf-8")

        results = knowledge_base.search_notes("Azure")

        assert results == []

    def test_searches_nested_directories(self, knowledge_base):
        path = knowledge_base.root / "projects" / "ai.md"
        path.parent.mkdir(parents=True)
        path.write_text("MCP and AI agents", encoding="utf-8")

        results = knowledge_base.search_notes("MCP")

        assert len(results) == 1
        assert results[0]["filename"] == "projects/ai.md"

    def test_returns_at_most_five_matching_lines(self, knowledge_base):
        path = knowledge_base.root / "many_matches.md"
        path.write_text(
            "\n".join(["Python"] * 10),
            encoding="utf-8",
        )

        results = knowledge_base.search_notes("Python")

        assert len(results[0]["snippets"]) == 5

    def test_skips_oversized_files(
        self, knowledge_base, monkeypatch
    ):
        monkeypatch.setattr(
            file_service_module, "MAX_FILE_SIZE", 5
        )

        path = knowledge_base.root / "large.md"
        path.write_text("Python is great", encoding="utf-8")

        results = knowledge_base.search_notes("Python")

        assert results == []

    def test_rejects_empty_query(self, knowledge_base):
        with pytest.raises(ValueError):
            knowledge_base.search_notes("")


class TestWriteNote:

    def test_creates_new_note(self, knowledge_base):
        result = knowledge_base.write_note(
            "python/notes.md",
            "# Python Notes",
        )

        assert result == "Note successfully saved: python/notes.md"
        assert (
            knowledge_base.root / "python" / "notes.md"
        ).read_text(encoding="utf-8") == "# Python Notes"

    def test_creates_nested_directories(self, knowledge_base):
        knowledge_base.write_note(
            "a/b/c/notes.md",
            "# Nested Note",
        )

        assert (
            knowledge_base.root / "a" / "b" / "c" / "notes.md"
        ).is_file()

    def test_rejects_existing_file_without_overwrite(
        self, knowledge_base
    ):
        knowledge_base.write_note("notes.md", "# Original")

        with pytest.raises(FileExistsError):
            knowledge_base.write_note("notes.md", "# Updated")

        assert knowledge_base.read_note("notes.md") == "# Original"

    def test_allows_explicit_service_level_overwrite(
        self, knowledge_base
    ):
        knowledge_base.write_note("notes.md", "# Original")

        knowledge_base.write_note(
            "notes.md",
            "# Updated",
            overwrite=True,
        )

        assert knowledge_base.read_note("notes.md") == "# Updated"

    def test_rejects_empty_content(self, knowledge_base):
        with pytest.raises(ValueError):
            knowledge_base.write_note("empty.md", "")

    def test_rejects_oversized_content(
        self, knowledge_base, monkeypatch
    ):
        monkeypatch.setattr(
            file_service_module, "MAX_FILE_SIZE", 5
        )

        with pytest.raises(ValueError, match="byte limit"):
            knowledge_base.write_note("large.md", "123456")

    def test_rejects_path_traversal(self, knowledge_base):
        with pytest.raises(ValueError):
            knowledge_base.write_note(
                "../outside.md",
                "# Outside",
            )

    def test_rejects_symlink_escape_on_read(self, knowledge_base, tmp_path):
        outside = tmp_path.parent / "outside_secret.md"
        outside.write_text("Secret", encoding="utf-8")

        link = knowledge_base.root / "escape.md"

        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation is not permitted on this system")

        with pytest.raises(ValueError, match="outside"):
            knowledge_base.read_note("escape.md")

    def test_rejects_symlink_escape_on_write(self, knowledge_base, tmp_path):
        outside = tmp_path.parent / "outside_write.md"
        link = knowledge_base.root / "escape.md"

        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation is not permitted on this system")

        with pytest.raises(ValueError, match="outside"):
            knowledge_base.write_note("escape.md", "# Attack")

        assert not outside.exists()
