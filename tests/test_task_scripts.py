#!/usr/bin/env python3
"""
Tests for task management scripts using Basic Memory MCP integration.

These tests validate:
- Task creation via mcp__bm__write_note
- Task search via mcp__bm__search_notes
- Task modification via mcp__bm__edit_note
- Task viewing via mcp__bm__build_context
- Task archival via mcp__bm__move_note
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

# Import task scripts (will create these next)
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    import task_create
    import task_search
    import task_modify
    import task_view
    import task_archive
except ImportError:
    # Scripts don't exist yet - that's expected in TDD
    pass


class TestTaskCreate:
    """Test task creation via BM MCP."""

    def test_create_basic_task(self):
        """Test creating a simple task with minimal fields."""
        task_data = {
            "title": "Test Task",
            "description": "This is a test task",
            "priority": 2,
            "type": "todo",
        }

        # Use test mode (no MCP)
        result = task_create.create_task(task_data, use_mcp=False)

        # Verify result structure
        assert result["success"] is True
        assert "id" in result
        assert result["id"].startswith("20251106")  # Today's date

        # Check content structure
        content = result["content"]
        assert "priority: 2" in content
        assert "type: todo" in content
        assert "This is a test task" in content
        assert "# Test Task" in content

    def test_create_task_with_all_fields(self):
        """Test creating a task with all optional fields."""
        task_data = {
            "title": "Complex Task",
            "description": "Detailed description",
            "priority": 1,
            "type": "email_reply",
            "classification": "Action",
            "due": "2025-12-31T00:00:00Z",
            "project": "writing",
            "metadata": {"email_id": "abc123", "sender": "test@example.com"},
        }

        result = task_create.create_task(task_data, use_mcp=False)

        assert result["success"] is True
        content = result["content"]

        # Verify all fields present
        assert "priority: 1" in content
        assert "classification: Action" in content
        assert "due: '2025-12-31T00:00:00Z'" in content
        assert "project: writing" in content
        assert "email_id: abc123" in content

    def test_create_task_generates_id(self):
        """Test that task creation generates a unique ID."""
        task_data = {
            "title": "ID Test",
            "description": "Test ID generation",
            "priority": 2,
            "type": "todo",
        }

        result = task_create.create_task(task_data, use_mcp=False)

        # Check that an ID was generated
        assert "id" in result
        # ID should be YYYYMMDD-HASH format
        assert len(result["id"].split("-")) == 2
        assert result["id"].split("-")[0].startswith("2025")

    def test_create_task_sets_timestamps(self):
        """Test that created and modified timestamps are set."""
        task_data = {
            "title": "Timestamp Test",
            "description": "Test timestamps",
            "priority": 2,
            "type": "todo",
        }

        result = task_create.create_task(task_data, use_mcp=False)

        content = result["content"]

        # Verify timestamps present
        assert "created:" in content
        assert "modified:" in content

        # Parse frontmatter to check format
        parts = content.split("---")
        frontmatter = yaml.safe_load(parts[1])

        # Check ISO 8601 format with timezone
        assert "T" in frontmatter["created"]
        assert "+" in frontmatter["created"] or "Z" in frontmatter["created"]


class TestTaskSearch:
    """Test task search via BM MCP."""

    def test_search_by_query(self):
        """Test basic semantic search."""
        with patch("task_search.mcp__bm__search_notes") as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "identifier": "20251106-test",
                        "title": "Test Task",
                        "relevance": 0.9,
                    }
                ]
            }

            results = task_search.search_tasks("test query")

            assert len(results) == 1
            assert results[0]["identifier"] == "20251106-test"
            assert mock_search.called

    def test_search_with_filters(self):
        """Test search with priority/status filters."""
        with patch("task_search.mcp__bm__search_notes") as mock_search:
            mock_search.return_value = {"results": []}

            task_search.search_tasks("test query", priority=1, status="inbox")

            # Verify filter parameters passed to MCP
            call_args = mock_search.call_args
            query = call_args.args[0]

            # Filters should be in query or params
            assert "priority" in str(call_args) or "priority: 1" in query

    def test_search_returns_empty_on_no_results(self):
        """Test search returns empty list when no matches."""
        with patch("task_search.mcp__bm__search_notes") as mock_search:
            mock_search.return_value = {"results": []}

            results = task_search.search_tasks("nonexistent")

            assert results == []


class TestTaskModify:
    """Test task modification via BM MCP."""

    def test_modify_priority(self):
        """Test changing task priority."""
        with patch("task_modify.mcp__bm__edit_note") as mock_edit:
            mock_edit.return_value = {"success": True}

            task_modify.modify_task("20251106-test", priority=1)

            assert mock_edit.called
            call_args = mock_edit.call_args

            # Check identifier
            assert call_args.kwargs["identifier"] == "20251106-test"

            # Check operation is find_replace or replace_section
            assert call_args.kwargs["operation"] in ["find_replace", "replace_section"]

    def test_modify_status(self):
        """Test changing task status."""
        with patch("task_modify.mcp__bm__edit_note") as mock_edit:
            mock_edit.return_value = {"success": True}

            task_modify.modify_task("20251106-test", status="active")

            assert mock_edit.called
            # Status change should update frontmatter and modified timestamp
            mock_edit.call_args.kwargs.get("content", "")
            assert "status:" in str(mock_edit.call_args)

    def test_modify_updates_modified_timestamp(self):
        """Test that modified timestamp is updated."""
        with patch("task_modify.mcp__bm__edit_note") as mock_edit:
            with patch("task_modify.mcp__bm__read_note") as mock_read:
                mock_read.return_value = {
                    "content": "---\nid: test\npriority: 2\nmodified: '2025-01-01T00:00:00Z'\n---\n\nContent"
                }
                mock_edit.return_value = {"success": True}

                task_modify.modify_task("20251106-test", priority=1)

                # Modified timestamp should be updated
                call_args = mock_edit.call_args
                content = call_args.kwargs.get("content", "")

                # New modified time should be present and different from 2025-01-01
                assert "modified:" in content or "modified:" in str(call_args)


class TestTaskView:
    """Test task viewing with context via BM MCP."""

    def test_view_task_basic(self):
        """Test viewing a single task."""
        with patch("task_view.mcp__bm__read_note") as mock_read:
            mock_read.return_value = {
                "content": "---\nid: test\ntitle: Test\n---\n\n# Test\n\nContent",
                "metadata": {"id": "test", "title": "Test"},
            }

            result = task_view.view_task("20251106-test")

            assert result["id"] == "test"
            assert result["title"] == "Test"
            assert mock_read.called

    def test_view_task_with_context(self):
        """Test viewing task with related context."""
        with patch("task_view.mcp__bm__build_context") as mock_context:
            mock_context.return_value = {
                "main": {"content": "Main task content"},
                "related": [{"title": "Related 1"}, {"title": "Related 2"}],
            }

            result = task_view.view_task("20251106-test", include_context=True)

            assert "related" in result
            assert len(result["related"]) == 2

    def test_view_formats_output(self):
        """Test that view output is human-readable."""
        with patch("task_view.mcp__bm__read_note") as mock_read:
            mock_read.return_value = {
                "content": "---\nid: test\npriority: 1\n---\n\nContent",
                "metadata": {"id": "test", "priority": 1},
            }

            result = task_view.view_task("20251106-test", format="human")

            # Should have formatted priority
            assert "P1" in result["formatted"] or result["priority"] == 1


class TestTaskArchive:
    """Test task archival via BM MCP."""

    def test_archive_task(self):
        """Test moving task to archived folder."""
        with patch("task_archive.mcp__bm__move_note") as mock_move:
            with patch("task_archive.mcp__bm__edit_note") as mock_edit:
                mock_move.return_value = {"success": True}
                mock_edit.return_value = {"success": True}

                task_archive.archive_task("20251106-test")

                # Verify move to archived folder
                assert mock_move.called
                call_args = mock_move.call_args

                destination = call_args.kwargs["destination_path"]
                assert "archived" in destination

    def test_archive_updates_status_and_timestamp(self):
        """Test that archival updates status and adds archived_at."""
        with patch("task_archive.mcp__bm__move_note") as mock_move:
            with patch("task_archive.mcp__bm__edit_note") as mock_edit:
                mock_move.return_value = {"success": True}
                mock_edit.return_value = {"success": True}

                task_archive.archive_task("20251106-test")

                # Verify status updated to archived
                assert mock_edit.called
                edit_args = mock_edit.call_args

                # Should update status and add archived_at timestamp
                content = edit_args.kwargs.get("content", "")
                assert "status:" in str(edit_args) or "archived" in content

    def test_unarchive_task(self):
        """Test moving task back to inbox."""
        with patch("task_archive.mcp__bm__move_note") as mock_move:
            with patch("task_archive.mcp__bm__edit_note") as mock_edit:
                mock_move.return_value = {"success": True}
                mock_edit.return_value = {"success": True}

                task_archive.unarchive_task("20251106-test")

                # Verify move to inbox folder
                assert mock_move.called
                call_args = mock_move.call_args

                destination = call_args.kwargs["destination_path"]
                assert "inbox" in destination


class TestIntegration:
    """Integration tests for complete task workflows."""

    def test_create_search_modify_archive_workflow(self):
        """Test complete task lifecycle."""
        # This will be implemented in Phase 6 with real BM backend
        pytest.skip("Integration test - requires Phase 6")

    def test_task_persistence(self):
        """Test that tasks persist correctly in BM."""
        # This will be implemented in Phase 6 with real BM backend
        pytest.skip("Integration test - requires Phase 6")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
