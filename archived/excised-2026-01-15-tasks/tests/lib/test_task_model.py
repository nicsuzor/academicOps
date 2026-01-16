"""Unit tests for Task Model v2.

Tests the hierarchical task model per specs/tasks-v2.md.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from lib.task_model import Task, TaskStatus, TaskType


class TestTaskCreation:
    """Test Task object creation and validation."""

    def test_create_minimal_task(self):
        """Create task with only required fields."""
        task = Task(id="20260112-test-task", title="Test Task")

        assert task.id == "20260112-test-task"
        assert task.title == "Test Task"
        assert task.type == TaskType.TASK
        assert task.status == TaskStatus.INBOX
        assert task.priority == 2
        assert task.order == 0
        assert task.parent is None
        assert task.depends_on == []
        assert task.depth == 0
        assert task.leaf is True

    def test_create_full_task(self):
        """Create task with all fields populated."""
        now = datetime.now(UTC)
        task = Task(
            id="20260112-write-book",
            title="Write a new book",
            type=TaskType.GOAL,
            status=TaskStatus.ACTIVE,
            priority=1,
            order=0,
            created=now,
            modified=now,
            parent=None,
            depends_on=["20260110-research-topic"],
            depth=0,
            leaf=False,
            due=datetime(2026, 12, 31, tzinfo=UTC),
            project="book",
            tags=["writing", "long-term"],
            effort="6 months",
            context="@home",
        )

        assert task.type == TaskType.GOAL
        assert task.status == TaskStatus.ACTIVE
        assert task.priority == 1
        assert task.depends_on == ["20260110-research-topic"]
        assert task.project == "book"
        assert task.tags == ["writing", "long-term"]

    def test_invalid_id_format_raises(self):
        """Task ID must be date-slug format."""
        with pytest.raises(ValueError, match="date-slug format"):
            Task(id="invalid-id", title="Test")

    def test_missing_id_raises(self):
        """Task ID is required."""
        with pytest.raises(ValueError, match="id is required"):
            Task(id="", title="Test")

    def test_missing_title_raises(self):
        """Task title is required."""
        with pytest.raises(ValueError, match="title is required"):
            Task(id="20260112-test", title="")

    def test_invalid_priority_raises(self):
        """Priority must be 0-4."""
        with pytest.raises(ValueError, match="Priority must be 0-4"):
            Task(id="20260112-test", title="Test", priority=5)

        with pytest.raises(ValueError, match="Priority must be 0-4"):
            Task(id="20260112-test", title="Test", priority=-1)

    def test_negative_depth_raises(self):
        """Depth must be non-negative."""
        with pytest.raises(ValueError, match="non-negative"):
            Task(id="20260112-test", title="Test", depth=-1)


class TestTaskIdGeneration:
    """Test automatic task ID generation."""

    def test_generate_id_basic(self):
        """Generate ID from simple title."""
        task_id = Task.generate_id("Test Task", datetime(2026, 1, 12, tzinfo=UTC))
        assert task_id == "20260112-test-task"

    def test_generate_id_special_chars(self):
        """Generate ID with special characters removed."""
        task_id = Task.generate_id(
            "Write Chapter 1: Introduction!", datetime(2026, 1, 12, tzinfo=UTC)
        )
        assert task_id == "20260112-write-chapter-1-introduction"

    def test_generate_id_truncates_long_titles(self):
        """Long titles are truncated in slug."""
        long_title = "This is a very long title that should be truncated to keep the ID reasonable"
        task_id = Task.generate_id(long_title, datetime(2026, 1, 12, tzinfo=UTC))
        # 8 digits + dash + max 50 chars = 59 max
        assert len(task_id) <= 59

    def test_generate_id_uses_current_date(self):
        """ID uses current date when none provided."""
        task_id = Task.generate_id("Test")
        today = datetime.now(UTC).strftime("%Y%m%d")
        assert task_id.startswith(today)


class TestTaskSerialization:
    """Test Task serialization to/from frontmatter and markdown."""

    def test_to_frontmatter(self):
        """Convert task to frontmatter dictionary."""
        task = Task(
            id="20260112-test-task",
            title="Test Task",
            type=TaskType.TASK,
            status=TaskStatus.ACTIVE,
            priority=1,
            project="test-project",
        )

        fm = task.to_frontmatter()

        assert fm["id"] == "20260112-test-task"
        assert fm["title"] == "Test Task"
        assert fm["type"] == "task"
        assert fm["status"] == "active"
        assert fm["priority"] == 1
        assert fm["project"] == "test-project"
        assert fm["leaf"] is True
        assert fm["depth"] == 0

    def test_from_frontmatter(self):
        """Create task from frontmatter dictionary."""
        fm = {
            "id": "20260112-test-task",
            "title": "Test Task",
            "type": "goal",
            "status": "active",
            "priority": 0,
            "order": 1,
            "parent": "20260101-parent-task",
            "depends_on": ["20260110-dep1", "20260111-dep2"],
            "depth": 2,
            "leaf": False,
            "project": "test",
            "created": "2026-01-12T10:00:00+00:00",
            "modified": "2026-01-12T11:00:00+00:00",
        }

        task = Task.from_frontmatter(fm)

        assert task.id == "20260112-test-task"
        assert task.type == TaskType.GOAL
        assert task.status == TaskStatus.ACTIVE
        assert task.priority == 0
        assert task.parent == "20260101-parent-task"
        assert task.depends_on == ["20260110-dep1", "20260111-dep2"]
        assert task.depth == 2
        assert task.leaf is False

    def test_to_markdown(self):
        """Convert task to full markdown with frontmatter."""
        task = Task(
            id="20260112-test-task",
            title="Test Task",
            body="## Context\n\nThis is the task body.",
        )

        md = task.to_markdown()

        assert md.startswith("---")
        assert "id: 20260112-test-task" in md
        assert "title: Test Task" in md
        assert "# Test Task" in md
        assert "## Context" in md
        assert "This is the task body." in md

    def test_from_markdown(self):
        """Parse task from markdown with frontmatter."""
        content = """---
id: 20260112-test-task
title: Test Task
type: task
status: inbox
priority: 2
order: 0
created: '2026-01-12T10:00:00+00:00'
modified: '2026-01-12T10:00:00+00:00'
parent: null
depends_on: []
depth: 0
leaf: true
---

# Test Task

This is the body content.
"""

        task = Task.from_markdown(content)

        assert task.id == "20260112-test-task"
        assert task.title == "Test Task"
        assert task.body == "# Test Task\n\nThis is the body content."

    def test_from_markdown_missing_frontmatter_raises(self):
        """Missing frontmatter raises ValueError."""
        content = "# Just a heading\n\nNo frontmatter here."

        with pytest.raises(ValueError, match="must start with YAML frontmatter"):
            Task.from_markdown(content)

    def test_from_markdown_missing_id_raises(self):
        """Missing id in frontmatter raises ValueError."""
        content = """---
title: Test Task
---

Body content.
"""
        with pytest.raises(ValueError, match="missing required field: id"):
            Task.from_markdown(content)

    def test_roundtrip_serialization(self):
        """Task survives roundtrip through markdown."""
        original = Task(
            id="20260112-roundtrip-test",
            title="Roundtrip Test",
            type=TaskType.PROJECT,
            status=TaskStatus.ACTIVE,
            priority=1,
            parent="20260101-parent",
            depends_on=["20260110-dep1"],
            depth=1,
            leaf=False,
            project="test",
            tags=["a", "b"],
            body="## Notes\n\nSome content here.",
        )

        md = original.to_markdown()
        restored = Task.from_markdown(md)

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.type == original.type
        assert restored.status == original.status
        assert restored.priority == original.priority
        assert restored.parent == original.parent
        assert restored.depends_on == original.depends_on
        assert restored.depth == original.depth
        assert restored.leaf == original.leaf
        assert restored.project == original.project
        assert restored.tags == original.tags


class TestTaskFileOperations:
    """Test Task file read/write operations."""

    def test_to_file_creates_file(self, tmp_path: Path):
        """Write task creates file with correct content."""
        task = Task(id="20260112-file-test", title="File Test", project="test")
        filepath = tmp_path / "tasks" / "20260112-file-test.md"

        task.to_file(filepath)

        assert filepath.exists()
        content = filepath.read_text()
        assert "id: 20260112-file-test" in content
        assert "title: File Test" in content

    def test_to_file_creates_parent_dirs(self, tmp_path: Path):
        """Write task creates parent directories."""
        task = Task(id="20260112-nested-test", title="Nested Test")
        filepath = tmp_path / "deep" / "nested" / "path" / "task.md"

        task.to_file(filepath)

        assert filepath.exists()

    def test_from_file_loads_task(self, tmp_path: Path):
        """Load task from file."""
        task = Task(
            id="20260112-load-test",
            title="Load Test",
            type=TaskType.ACTION,
            status=TaskStatus.ACTIVE,
        )
        filepath = tmp_path / "task.md"
        task.to_file(filepath)

        loaded = Task.from_file(filepath)

        assert loaded.id == "20260112-load-test"
        assert loaded.title == "Load Test"
        assert loaded.type == TaskType.ACTION
        assert loaded.status == TaskStatus.ACTIVE


class TestTaskGraphOperations:
    """Test Task graph relationship operations."""

    def test_is_ready_leaf_no_deps(self):
        """Leaf task with no deps is ready."""
        task = Task(
            id="20260112-ready-test",
            title="Ready Test",
            status=TaskStatus.ACTIVE,
            leaf=True,
            depends_on=[],
        )

        assert task.is_ready() is True

    def test_is_ready_non_leaf_not_ready(self):
        """Non-leaf task is not ready (has children)."""
        task = Task(
            id="20260112-parent-test",
            title="Parent Test",
            status=TaskStatus.ACTIVE,
            leaf=False,
        )

        assert task.is_ready() is False

    def test_is_ready_with_deps_not_ready(self):
        """Task with dependencies is not ready."""
        task = Task(
            id="20260112-blocked-test",
            title="Blocked Test",
            status=TaskStatus.ACTIVE,
            leaf=True,
            depends_on=["20260111-dependency"],
        )

        assert task.is_ready() is False

    def test_is_blocked_with_deps(self):
        """Task with dependencies is blocked."""
        task = Task(
            id="20260112-blocked-test",
            title="Blocked Test",
            depends_on=["20260111-dependency"],
        )

        assert task.is_blocked() is True

    def test_is_blocked_status(self):
        """Task with blocked status is blocked."""
        task = Task(
            id="20260112-blocked-test",
            title="Blocked Test",
            status=TaskStatus.BLOCKED,
        )

        assert task.is_blocked() is True

    def test_add_child_updates_leaf(self):
        """Adding a child makes task non-leaf."""
        task = Task(id="20260112-parent-test", title="Parent Test", leaf=True)
        assert task.leaf is True

        task.add_child("20260112-child-task")

        assert task.leaf is False
        assert "20260112-child-task" in task.children

    def test_add_child_idempotent(self):
        """Adding same child twice doesn't duplicate."""
        task = Task(id="20260112-parent-test", title="Parent Test")

        task.add_child("20260112-child-task")
        task.add_child("20260112-child-task")

        assert task.children.count("20260112-child-task") == 1

    def test_complete_sets_done(self):
        """Complete marks task as done."""
        task = Task(
            id="20260112-complete-test",
            title="Complete Test",
            status=TaskStatus.ACTIVE,
        )

        task.complete()

        assert task.status == TaskStatus.DONE


class TestTaskTypes:
    """Test task type semantics."""

    def test_all_types_valid(self):
        """All TaskType values are valid."""
        for task_type in TaskType:
            task = Task(id="20260112-type-test", title="Type Test", type=task_type)
            assert task.type == task_type

    def test_type_serialization(self):
        """Task types serialize to string values."""
        assert TaskType.GOAL.value == "goal"
        assert TaskType.PROJECT.value == "project"
        assert TaskType.TASK.value == "task"
        assert TaskType.ACTION.value == "action"


class TestTaskStatuses:
    """Test task status semantics."""

    def test_all_statuses_valid(self):
        """All TaskStatus values are valid."""
        for status in TaskStatus:
            task = Task(id="20260112-status-test", title="Status Test", status=status)
            assert task.status == status

    def test_status_serialization(self):
        """Task statuses serialize to string values."""
        assert TaskStatus.INBOX.value == "inbox"
        assert TaskStatus.ACTIVE.value == "active"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.WAITING.value == "waiting"
        assert TaskStatus.DONE.value == "done"
        assert TaskStatus.CANCELLED.value == "cancelled"
