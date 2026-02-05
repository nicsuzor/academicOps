"""Tests for task_model.py - Task model with graph relationships."""

import pytest

from lib.task_model import Task, TaskStatus, TaskType


class TestTaskStatusInbox:
    """Tests for inbox status support."""

    def test_create_task_with_inbox_status(self):
        """Task can be created with INBOX status."""
        task = Task(
            id="test-123",
            title="Test task",
            status=TaskStatus.INBOX,
        )
        assert task.status == TaskStatus.INBOX
        assert task.status.value == "inbox"

    def test_from_frontmatter_parses_inbox_status(self):
        """from_frontmatter correctly parses inbox status."""
        fm = {"id": "test-456", "title": "Test", "type": "task", "status": "inbox"}
        task = Task.from_frontmatter(fm)
        assert task.status == TaskStatus.INBOX

    def test_to_frontmatter_serializes_inbox_status(self):
        """to_frontmatter correctly serializes inbox status."""
        task = Task(
            id="test-789",
            title="Test task",
            status=TaskStatus.INBOX,
        )
        fm = task.to_frontmatter()
        assert fm["status"] == "inbox"


class TestTaskTypeValidation:
    """Tests for task type validation - invalid types should be rejected."""

    def test_invalid_type_raises_valueerror(self):
        """from_frontmatter raises ValueError for invalid type values."""
        fm = {"id": "note-123", "title": "A Note", "type": "note"}
        with pytest.raises(ValueError) as exc_info:
            Task.from_frontmatter(fm)
        assert "not a task" in str(exc_info.value).lower()
        assert "note" in str(exc_info.value)

    def test_invalid_type_reference_raises_valueerror(self):
        """from_frontmatter raises ValueError for 'reference' type."""
        fm = {"id": "ref-456", "title": "A Reference", "type": "reference"}
        with pytest.raises(ValueError) as exc_info:
            Task.from_frontmatter(fm)
        assert "not a task" in str(exc_info.value).lower()

    def test_valid_types_are_accepted(self):
        """from_frontmatter accepts all valid TaskType values."""
        valid_types = ["goal", "project", "epic", "task", "action", "bug", "feature", "learn"]
        for task_type in valid_types:
            fm = {"id": f"test-{task_type}", "title": "Test", "type": task_type}
            task = Task.from_frontmatter(fm)
            assert task.type.value == task_type

    def test_missing_type_raises_valueerror(self):
        """from_frontmatter raises ValueError when type field is missing."""
        fm = {"id": "test-default", "title": "Test"}
        with pytest.raises(ValueError) as exc_info:
            Task.from_frontmatter(fm)
        assert "missing 'type' field" in str(exc_info.value).lower()
        assert "not a task file" in str(exc_info.value).lower()
