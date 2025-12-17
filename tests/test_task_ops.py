"""Unit tests for task operations library."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from skills.tasks import task_ops
from skills.tasks.models import Task


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    (data_dir / "tasks/inbox").mkdir(parents=True)
    (data_dir / "tasks/queue").mkdir(parents=True)
    (data_dir / "tasks/archived").mkdir(parents=True)
    return data_dir


@pytest.fixture
def sample_task_file(test_data_dir: Path) -> Path:
    """Create a sample task file."""
    task_file = test_data_dir / "tasks/inbox/20251110-test001.md"
    content = """---
title: "Test task 1"
priority: 1
type: "todo"
created: "2025-11-10T10:00:00Z"
status: "inbox"
tags: []
---
This is a test task body.
"""
    task_file.write_text(content, encoding="utf-8")
    return task_file


def test_get_data_dir_with_override(tmp_path: Path):
    """Test get_data_dir with explicit override."""
    data_dir = tmp_path / "custom_data"
    data_dir.mkdir()

    result = task_ops.get_data_dir(data_dir)

    assert result == data_dir


def test_get_data_dir_not_found():
    """Test get_data_dir fails when directory doesn't exist."""
    with pytest.raises(
        task_ops.TaskDirectoryNotFoundError, match="Data directory not found"
    ):
        task_ops.get_data_dir(Path("/nonexistent/path"))


def test_load_task_from_file(sample_task_file: Path):
    """Test loading task from valid markdown file."""
    task = task_ops.load_task_from_file(sample_task_file)

    assert task.title == "Test task 1"
    assert task.priority == 1
    assert task.type == "todo"
    assert task.status == "inbox"
    assert task.body == "This is a test task body."
    assert task.filename == "20251110-test001.md"


def test_load_task_from_file_not_found():
    """Test loading task from non-existent file fails."""
    with pytest.raises(task_ops.TaskNotFoundError, match="Task file not found"):
        task_ops.load_task_from_file(Path("/nonexistent/file.md"))


def test_load_task_from_file_no_frontmatter(test_data_dir: Path):
    """Test loading task without frontmatter fails."""
    bad_file = test_data_dir / "tasks/inbox/bad.md"
    bad_file.write_text("No frontmatter here", encoding="utf-8")

    with pytest.raises(
        task_ops.InvalidTaskFormatError, match="No frontmatter in bad.md"
    ):
        task_ops.load_task_from_file(bad_file)


def test_load_task_from_file_invalid_yaml(test_data_dir: Path):
    """Test loading task with invalid YAML fails."""
    bad_file = test_data_dir / "tasks/inbox/invalid.md"
    content = """---
title: "Test"
invalid: {this is not valid yaml
---
Body
"""
    bad_file.write_text(content, encoding="utf-8")

    with pytest.raises(task_ops.InvalidTaskFormatError, match="YAML parse error"):
        task_ops.load_task_from_file(bad_file)


def test_load_task_extracts_priority_from_tags(test_data_dir: Path):
    """Test priority extraction from tags when not in frontmatter."""
    task_file = test_data_dir / "tasks/inbox/priority-tag.md"
    content = """---
title: "Test with priority tag"
type: "todo"
created: "2025-11-10T10:00:00Z"
tags: ["priority-p2", "other-tag"]
---
Body
"""
    task_file.write_text(content, encoding="utf-8")

    task = task_ops.load_task_from_file(task_file)

    assert task.priority == 2


def test_save_task_to_file(test_data_dir: Path):
    """Test saving task to file."""
    task = Task(
        title="New task",
        priority=2,
        type="todo",
        project="test-project",
        created=datetime(2025, 11, 10, 12, 0, 0, tzinfo=UTC),
        status="inbox",
        tags=["test", "sample"],
        body="Task body content",
    )

    save_path = test_data_dir / "tasks/inbox/new-task.md"
    task_ops.save_task_to_file(task, save_path)

    assert save_path.exists()

    # Verify can reload
    loaded = task_ops.load_task_from_file(save_path)
    assert loaded.title == task.title
    assert loaded.priority == task.priority
    assert loaded.body == task.body


def test_load_all_tasks(test_data_dir: Path):
    """Test loading all tasks from inbox and queue."""
    # Create multiple tasks
    inbox1 = test_data_dir / "tasks/inbox/task1.md"
    inbox1.write_text(
        """---
title: "Inbox task 1"
created: "2025-11-10T10:00:00Z"
---
""",
        encoding="utf-8",
    )

    inbox2 = test_data_dir / "tasks/inbox/task2.md"
    inbox2.write_text(
        """---
title: "Inbox task 2"
created: "2025-11-10T11:00:00Z"
---
""",
        encoding="utf-8",
    )

    queue1 = test_data_dir / "tasks/queue/task3.md"
    queue1.write_text(
        """---
title: "Queue task 1"
created: "2025-11-10T12:00:00Z"
---
""",
        encoding="utf-8",
    )

    tasks = task_ops.load_all_tasks(test_data_dir)

    assert len(tasks) == 3
    titles = [t.title for t in tasks]
    assert "Inbox task 1" in titles
    assert "Inbox task 2" in titles
    assert "Queue task 1" in titles


def test_load_all_tasks_excludes_archived(test_data_dir: Path):
    """Test that load_all_tasks excludes archived tasks by default."""
    # Create task with archived_at set
    archived_task = test_data_dir / "tasks/inbox/archived.md"
    archived_task.write_text(
        """---
title: "Archived task"
created: "2025-11-10T10:00:00Z"
archived_at: "2025-11-10T12:00:00Z"
---
""",
        encoding="utf-8",
    )

    active_task = test_data_dir / "tasks/inbox/active.md"
    active_task.write_text(
        """---
title: "Active task"
created: "2025-11-10T11:00:00Z"
---
""",
        encoding="utf-8",
    )

    tasks = task_ops.load_all_tasks(test_data_dir, include_archived=False)

    assert len(tasks) == 1
    assert tasks[0].title == "Active task"


def test_find_task_file(test_data_dir: Path, sample_task_file: Path):
    """Test finding task file in inbox/queue."""
    # With .md extension
    found = task_ops.find_task_file("20251110-test001.md", test_data_dir)
    assert found == sample_task_file

    # Without .md extension
    found = task_ops.find_task_file("20251110-test001", test_data_dir)
    assert found == sample_task_file


def test_find_task_file_not_found(test_data_dir: Path):
    """Test finding non-existent task returns None."""
    found = task_ops.find_task_file("nonexistent.md", test_data_dir)
    assert found is None


def test_archive_task(test_data_dir: Path, sample_task_file: Path):
    """Test archiving a task."""
    result = task_ops.archive_task("20251110-test001.md", test_data_dir)

    assert result["success"] is True
    assert "Archived" in result["message"]

    # Verify file moved
    assert not sample_task_file.exists()
    archived_path = test_data_dir / "tasks/archived/20251110-test001.md"
    assert archived_path.exists()

    # Verify frontmatter updated
    task = task_ops.load_task_from_file(archived_path)
    assert task.status == "archived"
    assert task.archived_at is not None


def test_archive_task_not_found(test_data_dir: Path):
    """Test archiving non-existent task fails gracefully."""
    result = task_ops.archive_task("nonexistent.md", test_data_dir)

    assert result["success"] is False
    assert "not found" in result["message"]


def test_unarchive_task(test_data_dir: Path):
    """Test unarchiving a task."""
    # Create archived task
    archived_file = test_data_dir / "tasks/archived/20251110-archived.md"
    content = """---
title: "Archived task"
priority: 2
created: "2025-11-10T10:00:00Z"
status: "archived"
archived_at: "2025-11-10T12:00:00Z"
---
Body
"""
    archived_file.write_text(content, encoding="utf-8")

    result = task_ops.unarchive_task("20251110-archived.md", test_data_dir)

    assert result["success"] is True
    assert "Unarchived" in result["message"]

    # Verify file moved
    assert not archived_file.exists()
    inbox_path = test_data_dir / "tasks/inbox/20251110-archived.md"
    assert inbox_path.exists()

    # Verify frontmatter updated
    task = task_ops.load_task_from_file(inbox_path)
    assert task.status == "inbox"
    assert task.archived_at is None


def test_create_task(test_data_dir: Path):
    """Test creating a new task."""
    result = task_ops.create_task(
        title="New test task",
        data_dir=test_data_dir,
        priority=1,
        task_type="todo",
        project="test-project",
        body="Task description",
        tags=["test", "new"],
    )

    assert result["success"] is True
    assert result["task_id"] is not None
    assert result["filename"] is not None

    # Verify file created
    task_path = test_data_dir / result["path"]
    assert task_path.exists()

    # Verify content
    task = task_ops.load_task_from_file(task_path)
    assert task.title == "New test task"
    assert task.priority == 1
    assert task.project == "test-project"
    assert task.body == "Task description"
    assert "test" in task.tags


def test_create_task_with_due_date(test_data_dir: Path):
    """Test creating task with due date."""
    due_date = datetime(2025, 11, 15, 12, 0, 0, tzinfo=UTC)

    result = task_ops.create_task(
        title="Task with due date",
        data_dir=test_data_dir,
        due=due_date,
    )

    assert result["success"] is True

    task_path = test_data_dir / result["path"]
    task = task_ops.load_task_from_file(task_path)
    assert task.due == due_date


@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("Hello World", "hello-world"),
        ("My Cool Task!", "my-cool-task"),
        ("  --multiple---spaces  ", "multiple-spaces"),
        ("a" * 100, "a" * 50),
    ],
)
def test_sanitize_slug(input_str: str, expected: str):
    """Test slug sanitization functionality.

    Args:
        input_str: Raw input string to sanitize
        expected: Expected sanitized slug
    """
    result = task_ops.sanitize_slug(input_str)
    assert result == expected


def test_sanitize_slug_empty_raises():
    """Test that sanitize_slug raises ValueError for strings that become empty."""
    with pytest.raises(ValueError, match="empty"):
        task_ops.sanitize_slug("@#$%")


def test_create_task_with_slug(test_data_dir: Path):
    """Test creating a task with custom slug instead of UUID.

    When slug parameter is provided, filename should be YYYYMMDD-slug.md
    instead of YYYYMMDD-XXXXXXXX.md (UUID format).
    """
    result = task_ops.create_task(
        title="Task with Custom Slug",
        data_dir=test_data_dir,
        slug="my-test-task",
        priority=1,
    )

    assert result["success"] is True

    # Verify task_id uses slug instead of UUID
    task_id = result["task_id"]
    timestamp_part = datetime.now(UTC).strftime("%Y%m%d")
    expected_task_id = f"{timestamp_part}-my-test-task"
    assert task_id == expected_task_id

    # Verify filename matches
    expected_filename = f"{expected_task_id}.md"
    assert result["filename"] == expected_filename

    # Verify file actually created with slug-based name
    task_path = test_data_dir / result["path"]
    assert task_path.exists()
    assert task_path.name == expected_filename


def test_task_add_cli_with_slug(test_data_dir: Path):
    """Test task_add.py CLI accepts --slug argument and creates slug-based file.

    Verifies that:
    1. CLI script accepts --slug argument without error
    2. Output mentions the slug-based task_id
    3. File is created with slug-based filename (YYYYMMDD-slug.md)
    """
    import subprocess

    script_path = Path(__file__).parent.parent / "skills/tasks/scripts/task_add.py"

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(script_path),
            "--title",
            "CLI Test Task",
            "--slug",
            "test-slug",
            "--data-dir",
            str(test_data_dir),
        ],
        capture_output=True,
        text=True,
    )

    # Should succeed
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Output should mention slug-based task_id
    timestamp_part = datetime.now(UTC).strftime("%Y%m%d")
    expected_task_id = f"{timestamp_part}-test-slug"
    assert expected_task_id in result.stdout, f"Expected '{expected_task_id}' in output: {result.stdout}"

    # File should exist with slug-based name
    expected_filename = f"{expected_task_id}.md"
    task_file = test_data_dir / "tasks/inbox" / expected_filename
    assert task_file.exists(), f"Expected file not created: {task_file}"


def test_mcp_create_task_request_accepts_slug():
    """Test CreateTaskRequest model accepts optional slug field.

    Verifies that:
    1. CreateTaskRequest validates with slug parameter
    2. slug field defaults to None
    3. slug field is accessible on validated model
    """
    from skills.tasks.models import CreateTaskRequest

    # Test with slug provided
    request_with_slug = CreateTaskRequest(
        title="Test Task",
        slug="my-custom-slug",
    )

    assert request_with_slug.slug == "my-custom-slug"

    # Test without slug (should default to None)
    request_without_slug = CreateTaskRequest(
        title="Test Task Without Slug",
    )

    assert request_without_slug.slug is None
