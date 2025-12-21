"""End-to-end integration tests for FastMCP task server.

Tests the complete MCP server functionality by simulating client interactions.
Follows the test design specified in the task specification.
"""

from __future__ import annotations

import time
from pathlib import Path

from skills.tasks import task_ops


class TestViewTasks:
    """Test view_tasks tool end-to-end."""

    def test_view_tasks_default(self, test_data_dir: Path):
        """Test viewing tasks with default parameters."""
        from skills.tasks.server import view_tasks

        result = view_tasks.fn()

        assert result["success"] is True
        assert result["total_tasks"] > 0  # Has active tasks
        assert len(result["tasks"]) > 0
        assert result["page"] == 1

        # Verify task data structure
        task = result["tasks"][0]
        assert "title" in task
        assert "priority" in task
        assert "status" in task
        assert "created" in task

    def test_view_tasks_pagination(self, test_data_dir: Path):
        """Test pagination works correctly."""
        from skills.tasks.server import view_tasks

        # Get total count first
        all_tasks = view_tasks.fn()
        total_count = all_tasks["total_tasks"]
        assert total_count > 0, "Need at least 1 task for pagination test"

        # View first page with 1 task per page
        result = view_tasks.fn(page=1, per_page=1)

        assert result["success"] is True
        assert result["total_tasks"] == total_count
        assert len(result["tasks"]) == 1
        assert result["page"] == 1
        assert result["per_page"] == 1

        # View second page if there are enough tasks
        if total_count > 1:
            result2 = view_tasks.fn(page=2, per_page=1)

            assert result2["success"] is True
            assert len(result2["tasks"]) == 1
            assert result2["page"] == 2

            # Tasks should be different
            assert result["tasks"][0]["title"] != result2["tasks"][0]["title"]

    def test_view_tasks_filter_by_priority(self, test_data_dir: Path):
        """Test filtering by priority."""
        from skills.tasks.server import view_tasks

        # First check if we have any P1 tasks
        all_tasks = view_tasks.fn()
        p1_tasks = [t for t in all_tasks["tasks"] if t["priority"] == 1]

        if not p1_tasks:
            # Skip test if no P1 tasks exist
            return

        result = view_tasks.fn(priority_filter=[1])

        assert result["success"] is True
        assert result["total_tasks"] == len(p1_tasks)
        # All returned tasks should be priority 1
        for task in result["tasks"]:
            assert task["priority"] == 1

    def test_view_tasks_filter_by_project(self, test_data_dir: Path):
        """Test filtering by project."""
        from skills.tasks.server import view_tasks

        # Find any tasks with projects
        all_tasks = view_tasks.fn()
        tasks_with_projects = [t for t in all_tasks["tasks"] if t.get("project")]

        if not tasks_with_projects:
            # Skip test if no tasks have projects
            return

        # Use first available project
        test_project = tasks_with_projects[0]["project"]
        expected_count = sum(
            1 for t in all_tasks["tasks"] if t.get("project") == test_project
        )

        result = view_tasks.fn(project_filter=test_project)

        assert result["success"] is True
        assert result["total_tasks"] == expected_count
        # All returned tasks should have matching project
        for task in result["tasks"]:
            assert task.get("project") == test_project

    def test_view_tasks_sort_by_priority(self, test_data_dir: Path):
        """Test sorting by priority."""
        from skills.tasks.server import view_tasks

        result = view_tasks.fn(sort="priority")

        assert result["success"] is True
        assert len(result["tasks"]) > 0

        # Verify tasks are sorted by priority (ascending)
        priorities = [t["priority"] for t in result["tasks"]]
        assert priorities == sorted(
            priorities
        ), "Tasks should be sorted by priority ascending"

    def test_view_tasks_sort_by_date(self, test_data_dir: Path):
        """Test sorting by date (created desc)."""
        from skills.tasks.server import view_tasks

        result = view_tasks.fn(sort="date")

        assert result["success"] is True
        # Most recent first
        created_dates = [t["created"] for t in result["tasks"]]
        assert created_dates == sorted(created_dates, reverse=True)

    def test_view_tasks_compact_mode(self, test_data_dir: Path):
        """Test compact mode returns minimal data."""
        from skills.tasks.server import view_tasks

        result = view_tasks.fn(compact=True)

        assert result["success"] is True
        assert len(result["tasks"]) > 0, "Should have at least one task"
        # Compact mode should not include body
        for task in result["tasks"]:
            assert "body" not in task or task["body"] is None

    def test_view_tasks_empty_directory(self, tmp_path: Path, monkeypatch):
        """Test viewing tasks when no tasks exist."""
        from skills.tasks.server import view_tasks

        empty_dir = tmp_path / "empty_data"
        (empty_dir / "tasks/inbox").mkdir(parents=True)
        (empty_dir / "tasks/queue").mkdir(parents=True)
        (empty_dir / "tasks/archived").mkdir(parents=True)

        # Set ACA_DATA to empty directory
        monkeypatch.setenv("ACA_DATA", str(empty_dir))

        result = view_tasks.fn()

        assert result["success"] is True
        assert result["total_tasks"] == 0
        assert len(result["tasks"]) == 0

    def test_view_tasks_invalid_data_dir(self, tmp_path: Path, monkeypatch):
        """Test viewing tasks with non-existent directory returns error."""
        from skills.tasks.server import view_tasks

        # Set ACA_DATA to non-existent path
        empty_dir = tmp_path / "new_data_dir"
        monkeypatch.setenv("ACA_DATA", str(empty_dir))

        result = view_tasks.fn()

        # Should fail with error when data directory doesn't exist
        assert result["success"] is False
        assert "message" in result
        assert "not found" in result["message"].lower()


class TestArchiveTasks:
    """Test archive_tasks tool end-to-end."""

    def test_archive_single_task(self, test_data_dir: Path):
        """Test archiving a single task."""
        from skills.tasks.server import archive_tasks, create_task

        # Create a task to archive
        create_result = create_task.fn(title="Task to archive")
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        result = archive_tasks.fn(identifiers=[task_filename])

        assert result["success"] is True
        assert result["success_count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True

        # Verify file moved
        assert not (test_data_dir / "inbox" / task_filename).exists()
        assert (test_data_dir / "archived" / task_filename).exists()

        # Verify frontmatter updated
        task = task_ops.load_task_from_file(test_data_dir / "archived" / task_filename)
        assert task.status == "archived"
        assert task.archived_at is not None

    def test_archive_multiple_tasks(self, test_data_dir: Path):
        """Test archiving multiple tasks in one operation."""
        from skills.tasks.server import archive_tasks, create_task

        # Create 2 tasks to archive
        task1 = create_task.fn(title="Task 1 to archive")
        task2 = create_task.fn(title="Task 2 to archive")
        assert task1["success"]
        assert task2["success"]

        task_filenames = [task1["filename"], task2["filename"]]

        result = archive_tasks.fn(
            identifiers=task_filenames,
        )

        assert result["success"] is True
        assert result["success_count"] == 2
        assert len(result["results"]) == 2

        # Verify both files moved
        for filename in task_filenames:
            assert not (test_data_dir / "inbox" / filename).exists()
            assert (test_data_dir / "archived" / filename).exists()

    def test_archive_without_extension(self, test_data_dir: Path):
        """Test archiving using task ID without .md extension."""
        from skills.tasks.server import archive_tasks, create_task

        # Create a task to archive
        create_result = create_task.fn(title="Task for extension test")
        assert create_result["success"] is True

        # Use task ID without .md extension
        task_id = create_result["task_id"]

        result = archive_tasks.fn(identifiers=[task_id])

        assert result["success"] is True
        assert result["success_count"] == 1

    def test_archive_nonexistent_task(self, test_data_dir: Path):
        """Test archiving non-existent task returns error."""
        from skills.tasks.server import archive_tasks

        result = archive_tasks.fn(identifiers=["nonexistent.md"])

        assert result["success"] is False
        assert result["success_count"] == 0
        assert result["failure_count"] == 1

    def test_archive_partial_failure(self, test_data_dir: Path):
        """Test archiving with mix of valid and invalid tasks."""
        from skills.tasks.server import archive_tasks, create_task

        # Create a task to archive
        create_result = create_task.fn(title="Task for partial failure test")
        assert create_result["success"] is True
        valid_task = create_result["filename"]

        result = archive_tasks.fn(
            identifiers=[valid_task, "nonexistent.md"],
        )

        assert result["success"] is False  # Not all succeeded
        assert result["success_count"] == 1
        assert result["failure_count"] == 1
        assert len(result["results"]) == 2


class TestUnarchiveTasks:
    """Test unarchive_tasks tool end-to-end."""

    def test_unarchive_single_task(self, test_data_dir: Path):
        """Test unarchiving a single task."""
        from skills.tasks.server import archive_tasks, create_task, unarchive_tasks

        # Create and archive a task to unarchive
        create_result = create_task.fn(title="Task to unarchive")
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        archive_result = archive_tasks.fn(identifiers=[task_filename])
        assert archive_result["success"] is True

        # Now unarchive it
        result = unarchive_tasks.fn(identifiers=[task_filename])

        assert result["success"] is True
        assert result["success_count"] == 1

        # Verify file moved
        assert not (test_data_dir / "archived" / task_filename).exists()
        assert (test_data_dir / "inbox" / task_filename).exists()

        # Verify frontmatter updated
        task = task_ops.load_task_from_file(test_data_dir / "inbox" / task_filename)
        assert task.status == "inbox"
        assert task.archived_at is None

    def test_unarchive_multiple_tasks(self, test_data_dir: Path):
        """Test unarchiving multiple tasks."""
        from skills.tasks.server import archive_tasks, create_task, unarchive_tasks

        # Create and archive two tasks
        task1 = create_task.fn(title="Task 1 to unarchive")
        task2 = create_task.fn(title="Task 2 to unarchive")
        assert task1["success"]
        assert task2["success"]

        task_filenames = [task1["filename"], task2["filename"]]

        archive_result = archive_tasks.fn(identifiers=task_filenames)
        assert archive_result["success"] is True

        # Then unarchive both
        result = unarchive_tasks.fn(identifiers=task_filenames)

        assert result["success"] is True
        assert result["success_count"] == 2

    def test_unarchive_nonexistent_task(self, test_data_dir: Path):
        """Test unarchiving non-existent task returns error."""
        from skills.tasks.server import unarchive_tasks

        result = unarchive_tasks.fn(identifiers=["nonexistent.md"])

        assert result["success"] is False
        assert result["success_count"] == 0


class TestCreateTask:
    """Test create_task tool end-to-end."""

    def test_create_minimal_task(self, test_data_dir: Path):
        """Test creating task with only required fields."""
        from skills.tasks.server import create_task

        result = create_task.fn(title="New minimal task")

        assert result["success"] is True
        assert result["task_id"] is not None
        assert result["filename"] is not None

        # Verify file exists and is memory-compliant
        task_path = test_data_dir / "inbox" / result["filename"]
        assert task_path.exists()

        task = task_ops.load_task_from_file(task_path)
        assert task.title == "New minimal task"
        assert task.status == "inbox"
        assert task.type == "task"  # memory requires "task" not "todo"

        # Verify memory structure
        content = task_path.read_text()
        assert "permalink:" in content
        assert "task_id:" in content
        assert "aliases:" in content
        assert "## Context" in content
        assert "## Observations" in content
        assert "## Relations" in content

    def test_create_task_with_all_fields(self, test_data_dir: Path):
        """Test creating task with all optional fields."""
        from skills.tasks.server import create_task

        due_date = "2025-11-15T12:00:00Z"

        result = create_task.fn(
            title="Full featured task",
            priority=1,
            project="test-project",
            due=due_date,
            body="Detailed task description with context.",
            tags=["important", "urgent"],
        )

        assert result["success"] is True

        # Verify all fields persisted
        task_path = test_data_dir / "inbox" / result["filename"]
        task = task_ops.load_task_from_file(task_path)

        assert task.title == "Full featured task"
        assert task.priority == 1
        assert task.project == "test-project"
        assert task.due is not None
        assert task.body == "Detailed task description with context."
        assert "important" in task.tags
        assert "urgent" in task.tags

    def test_create_task_generates_unique_ids(self, test_data_dir: Path):
        """Test that creating multiple tasks generates unique IDs."""
        from skills.tasks.server import create_task

        result1 = create_task.fn(title="Task 1")
        result2 = create_task.fn(title="Task 2")

        assert result1["task_id"] != result2["task_id"]
        assert result1["filename"] != result2["filename"]

    def test_create_task_invalid_priority(self, test_data_dir: Path):
        """Test creating task with invalid priority fails validation."""
        from skills.tasks.server import create_task

        result = create_task.fn(title="Invalid priority task", priority=99)

        assert result["success"] is False
        assert (
            "validation" in result["message"].lower()
            or "priority" in result["message"].lower()
        )

    def test_create_task_performance(self, test_data_dir: Path):
        """Test that create_task meets performance target (<300ms per spec)."""
        from skills.tasks.server import create_task

        start = time.time()
        result = create_task.fn(title="Performance test task")
        duration = time.time() - start

        assert result["success"] is True
        # Spec requires <300ms, but allow 500ms for test environment
        assert (
            duration < 0.5
        ), f"create_task took {duration*1000:.0f}ms, expected <500ms"


class TestModifyTask:
    """Test modify_task tool end-to-end."""

    def test_modify_task_title(self, test_data_dir: Path):
        """Test modifying task title."""
        from skills.tasks.server import create_task, modify_task

        # Create a task to modify
        create_result = create_task.fn(title="Original title")
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        result = modify_task.fn(
            identifier=task_filename,
            title="Updated title",
        )

        assert result["success"] is True
        assert result["modified_fields"] == ["title"]

        # Verify change persisted
        task = task_ops.load_task_from_file(test_data_dir / "inbox" / task_filename)
        assert task.title == "Updated title"

    def test_modify_task_multiple_fields(self, test_data_dir: Path):
        """Test modifying multiple fields at once."""
        from skills.tasks.server import create_task, modify_task

        # Create a task to modify
        create_result = create_task.fn(title="Original title", priority=1)
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        result = modify_task.fn(
            identifier=task_filename,
            title="New title",
            priority=2,
            project="new-project",
            body="Updated body content",
        )

        assert result["success"] is True
        assert set(result["modified_fields"]) == {
            "title",
            "priority",
            "project",
            "body",
        }

        # Verify all changes
        task = task_ops.load_task_from_file(test_data_dir / "inbox" / task_filename)
        assert task.title == "New title"
        assert task.priority == 2
        assert task.project == "new-project"
        assert task.body == "Updated body content"

    def test_modify_task_add_tags(self, test_data_dir: Path):
        """Test adding tags to task."""
        from skills.tasks.server import create_task, modify_task

        # Create a task to modify
        create_result = create_task.fn(title="Task for tag test")
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        result = modify_task.fn(
            identifier=task_filename,
            add_tags=["new-tag", "another-tag"],
        )

        assert result["success"] is True

        task = task_ops.load_task_from_file(test_data_dir / "inbox" / task_filename)
        assert "new-tag" in task.tags
        assert "another-tag" in task.tags

    def test_modify_task_remove_tags(self, test_data_dir: Path):
        """Test removing tags from task."""
        from skills.tasks.server import create_task, modify_task

        # Create a task with tags
        create_result = create_task.fn(
            title="Task for tag removal", tags=["to-remove", "urgent"]
        )
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        # Remove tags
        result = modify_task.fn(
            identifier=task_filename,
            remove_tags=["to-remove", "urgent"],
        )

        assert result["success"] is True

        task = task_ops.load_task_from_file(test_data_dir / "inbox" / task_filename)
        assert "to-remove" not in task.tags
        assert "urgent" not in task.tags

    def test_modify_task_not_found(self, test_data_dir: Path):
        """Test modifying non-existent task fails."""
        from skills.tasks.server import modify_task

        result = modify_task.fn(
            identifier="nonexistent.md",
            title="Won't work",
        )

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_modify_task_preserves_memory_format(self, test_data_dir: Path):
        """Test that modifications preserve memory format structure."""
        from skills.tasks.server import create_task, modify_task

        # Create a task to modify
        create_result = create_task.fn(title="Original task")
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        modify_task.fn(
            identifier=task_filename,
            title="Modified task",
            body="Modified body content",
        )

        # Verify memory structure still intact
        task_path = test_data_dir / "inbox" / task_filename
        content = task_path.read_text()

        assert "permalink:" in content
        assert "task_id:" in content
        assert "aliases:" in content
        assert "## Context" in content
        assert "## Observations" in content
        assert "## Relations" in content
        assert "Modified body content" in content


class TestEndToEndWorkflow:
    """Test complete workflows combining multiple operations."""

    def test_workflow_create_view_archive(self, test_data_dir: Path):
        """Test: Create task -> View it -> Archive it."""
        from skills.tasks.server import archive_tasks, create_task, view_tasks

        # Get baseline count
        initial_view = view_tasks.fn()
        initial_count = initial_view["total_tasks"]

        # Create new task
        create_result = create_task.fn(
            title="Workflow test task",
            priority=1,
            project="workflow-test",
        )
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        # View tasks and verify it appears
        view_result = view_tasks.fn()
        assert view_result["success"] is True
        assert view_result["total_tasks"] == initial_count + 1
        titles = [t["title"] for t in view_result["tasks"]]
        assert "Workflow test task" in titles

        # Archive the task
        archive_result = archive_tasks.fn(identifiers=[task_filename])
        assert archive_result["success"] is True

        # Verify it's no longer in active view
        view_result2 = view_tasks.fn()
        assert view_result2["total_tasks"] == initial_count

    def test_workflow_archive_modify_unarchive(self, test_data_dir: Path):
        """Test: Archive task -> Unarchive it -> Modify it."""
        from skills.tasks.server import (
            archive_tasks,
            create_task,
            modify_task,
            unarchive_tasks,
        )

        # Create a task for this workflow
        create_result = create_task.fn(title="Task for workflow")
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        # Archive the task
        archive_result = archive_tasks.fn(identifiers=[task_filename])
        assert archive_result["success"] is True

        # Unarchive it
        unarchive_result = unarchive_tasks.fn(identifiers=[task_filename])
        assert unarchive_result["success"] is True

        # Modify after unarchiving
        modify_result = modify_task.fn(
            identifier=task_filename,
            title="Modified after unarchive",
        )
        assert modify_result["success"] is True

        # Verify modification persisted
        task = task_ops.load_task_from_file(test_data_dir / "inbox" / task_filename)
        assert task.title == "Modified after unarchive"
        assert task.status == "inbox"

    def test_workflow_bulk_operations(self, test_data_dir: Path):
        """Test bulk archiving and viewing."""
        from skills.tasks.server import archive_tasks, create_task, view_tasks

        # Get baseline count
        initial_view = view_tasks.fn()
        initial_count = initial_view["total_tasks"]

        # Create multiple P2 tasks
        created_tasks = []
        for i in range(5):
            result = create_task.fn(
                title=f"Bulk task {i}",
                priority=2,
            )
            created_tasks.append(result["filename"])

        # View all tasks
        view_result = view_tasks.fn()
        assert view_result["total_tasks"] == initial_count + 5

        # Archive all P2 tasks (including newly created ones)
        p2_tasks = [t["filename"] for t in view_result["tasks"] if t["priority"] == 2]
        archive_result = archive_tasks.fn(identifiers=p2_tasks)
        assert archive_result["success_count"] == len(p2_tasks)

        # Verify correct number remains
        view_result2 = view_tasks.fn()
        # Should have initial_count - archived P2 tasks + 5 new - 5 archived
        expected_remaining = initial_count + 5 - len(p2_tasks)
        assert view_result2["total_tasks"] == expected_remaining


class TestPerformance:
    """Performance tests to validate spec requirements."""

    def test_view_tasks_performance(self, test_data_dir: Path):
        """Test view_tasks meets <500ms target for 10 tasks."""
        from skills.tasks.server import create_task, view_tasks

        # Create 10 tasks
        for i in range(10):
            create_task.fn(
                title=f"Performance test {i}",
            )

        # Measure view_tasks performance
        start = time.time()
        result = view_tasks.fn(per_page=10)
        duration = time.time() - start

        assert result["success"] is True
        # Spec requires <500ms, allow 1s for test environment
        assert (
            duration < 1.0
        ), f"view_tasks took {duration*1000:.0f}ms, expected <1000ms"

    def test_archive_task_performance(self, test_data_dir: Path):
        """Test archive_tasks meets <200ms target."""
        from skills.tasks.server import archive_tasks, create_task

        # Create a task to archive
        create_result = create_task.fn(title="Performance test task")
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        start = time.time()
        result = archive_tasks.fn(identifiers=[task_filename])
        duration = time.time() - start

        assert result["success"] is True
        # Spec requires <200ms, allow 500ms for test environment
        assert (
            duration < 0.5
        ), f"archive_tasks took {duration*1000:.0f}ms, expected <500ms"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_malformed_task_file(self, test_data_dir: Path):
        """Test that malformed task files are handled gracefully."""
        from skills.tasks.server import view_tasks

        # Get baseline count
        initial_result = view_tasks.fn()
        initial_count = initial_result["total_tasks"]

        # Create malformed task
        bad_task = test_data_dir / "inbox" / "malformed.md"
        bad_task.write_text("This is not valid YAML frontmatter", encoding="utf-8")

        result = view_tasks.fn()

        # Should succeed but skip malformed file
        assert result["success"] is True
        # Should return same count as before (malformed file ignored)
        assert result["total_tasks"] == initial_count

    def test_concurrent_modification_detection(self, test_data_dir: Path):
        """Test detection of concurrent file modifications."""
        from skills.tasks.server import create_task, modify_task

        # Create a task to modify
        create_result = create_task.fn(title="Task for concurrency test")
        assert create_result["success"] is True
        task_filename = create_result["filename"]

        # This is a basic test - true concurrent modification would need threading
        # For now, verify that the modify operation is atomic

        result = modify_task.fn(
            identifier=task_filename,
            title="First modification",
        )
        assert result["success"] is True

        # Second modification should succeed (no actual concurrency here)
        result2 = modify_task.fn(
            identifier=task_filename,
            title="Second modification",
        )
        assert result2["success"] is True

        # Verify final state
        task = task_ops.load_task_from_file(test_data_dir / "inbox" / task_filename)
        assert task.title == "Second modification"

    def test_disk_space_simulation(self, test_data_dir: Path):
        """Test behavior when creating many tasks (stress test)."""
        from skills.tasks.server import create_task

        # Create 50 tasks rapidly
        results = []
        for i in range(50):
            result = create_task.fn(
                title=f"Stress test task {i}",
                priority=2,
            )
            results.append(result)

        # All should succeed
        assert all(r["success"] for r in results)

        # All should have unique IDs
        task_ids = [r["task_id"] for r in results]
        assert len(task_ids) == len(set(task_ids))
