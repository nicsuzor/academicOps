#!/usr/bin/env python3
"""Unit tests for Task CLI v2.

Tests CLI commands per specs/tasks-v2.md Section 7.1.
Uses click.testing.CliRunner for isolated CLI testing.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from lib.task_index import TaskIndex
from lib.task_model import TaskStatus, TaskType
from lib.task_storage import TaskStorage
from scripts.task_cli import cli


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create temp data directory for CLI tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "tasks" / "inbox").mkdir(parents=True)
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


@pytest.fixture
def storage(data_dir: Path) -> TaskStorage:
    """Create TaskStorage with temp directory."""
    return TaskStorage(data_dir)


@pytest.fixture
def index(data_dir: Path) -> TaskIndex:
    """Create TaskIndex with temp directory."""
    return TaskIndex(data_dir)


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


class TestAddCommand:
    """Test task add command."""

    def test_add_minimal(self, runner: CliRunner, data_dir: Path) -> None:
        """Add task with just title."""
        result = runner.invoke(cli, ["add", "Test Task"])

        assert result.exit_code == 0
        assert "Created:" in result.output
        assert "Test Task" in result.output

    def test_add_with_project(self, runner: CliRunner, data_dir: Path) -> None:
        """Add task with project assignment."""
        result = runner.invoke(cli, ["add", "Project Task", "--project", "book"])

        assert result.exit_code == 0
        assert "Project: book" in result.output

    def test_add_with_type(self, runner: CliRunner, data_dir: Path) -> None:
        """Add task with specific type."""
        result = runner.invoke(cli, ["add", "Big Goal", "--type", "goal"])

        assert result.exit_code == 0
        assert "Type:    goal" in result.output

    def test_add_with_parent(
        self, runner: CliRunner, storage: TaskStorage, data_dir: Path
    ) -> None:
        """Add task with parent reference."""
        # Create parent first
        parent = storage.create_task("Parent Task", project="test")
        storage.save_task(parent)

        result = runner.invoke(
            cli, ["add", "Child Task", "--parent", parent.id, "--project", "test"]
        )

        assert result.exit_code == 0
        assert "Created:" in result.output

    def test_add_with_dependencies(self, runner: CliRunner, data_dir: Path) -> None:
        """Add task with dependencies."""
        # Create dependency first
        result1 = runner.invoke(cli, ["add", "Dependency Task", "--project", "test"])
        assert result1.exit_code == 0

        # Extract task ID from output
        dep_id = result1.output.split("Created: ")[1].split("\n")[0].strip()

        result2 = runner.invoke(
            cli, ["add", "Dependent Task", "-d", dep_id, "--project", "test"]
        )

        assert result2.exit_code == 0

    def test_add_with_tags(self, runner: CliRunner, data_dir: Path) -> None:
        """Add task with tags."""
        result = runner.invoke(cli, ["add", "Tagged Task", "-t", "urgent", "-t", "work"])

        assert result.exit_code == 0


class TestShowCommand:
    """Test task show command."""

    def test_show_basic(
        self, runner: CliRunner, storage: TaskStorage, data_dir: Path
    ) -> None:
        """Show basic task info."""
        task = storage.create_task("Show Test Task", project="test")
        storage.save_task(task)

        result = runner.invoke(cli, ["show", task.id])

        assert result.exit_code == 0
        assert "Show Test Task" in result.output
        assert task.id in result.output

    def test_show_with_children(
        self, runner: CliRunner, storage: TaskStorage, index: TaskIndex, data_dir: Path
    ) -> None:
        """Show task with children tree."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        child1 = storage.create_task("Child 1", project="test", parent=parent.id)
        storage.save_task(child1)

        child2 = storage.create_task("Child 2", project="test", parent=parent.id)
        storage.save_task(child2)

        # Rebuild index for children lookup
        index.rebuild()

        result = runner.invoke(cli, ["show", parent.id])

        assert result.exit_code == 0
        assert "Children:" in result.output
        assert "Child 1" in result.output
        assert "Child 2" in result.output

    def test_show_not_found(self, runner: CliRunner, data_dir: Path) -> None:
        """Show error for missing task."""
        result = runner.invoke(cli, ["show", "20260112-nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output


class TestDoneCommand:
    """Test task done command."""

    def test_done_single(
        self, runner: CliRunner, storage: TaskStorage, data_dir: Path
    ) -> None:
        """Complete single task."""
        task = storage.create_task("Complete Me", project="test")
        storage.save_task(task)

        result = runner.invoke(cli, ["done", task.id])

        assert result.exit_code == 0
        assert "Completed:" in result.output

        # Verify task is done
        reloaded = storage.get_task(task.id)
        assert reloaded is not None
        assert reloaded.status == TaskStatus.DONE

    def test_done_multiple(
        self, runner: CliRunner, storage: TaskStorage, data_dir: Path
    ) -> None:
        """Complete multiple tasks."""
        task1 = storage.create_task("Task 1", project="test")
        storage.save_task(task1)

        task2 = storage.create_task("Task 2", project="test")
        storage.save_task(task2)

        result = runner.invoke(cli, ["done", task1.id, task2.id])

        assert result.exit_code == 0
        assert task1.id in result.output
        assert task2.id in result.output

    def test_done_not_found(self, runner: CliRunner, data_dir: Path) -> None:
        """Done with missing task shows error but continues."""
        result = runner.invoke(cli, ["done", "20260112-nonexistent"])

        # Should still exit 0 (processes what it can)
        assert "not found" in result.output


class TestReadyCommand:
    """Test task ready command."""

    def test_ready_lists_actionable(
        self, runner: CliRunner, storage: TaskStorage, index: TaskIndex, data_dir: Path
    ) -> None:
        """List actionable tasks."""
        task = storage.create_task("Ready Task", project="test")
        task.status = TaskStatus.ACTIVE
        storage.save_task(task)

        index.rebuild()

        result = runner.invoke(cli, ["ready"])

        assert result.exit_code == 0
        assert "Ready Task" in result.output

    def test_ready_filter_by_project(
        self, runner: CliRunner, storage: TaskStorage, index: TaskIndex, data_dir: Path
    ) -> None:
        """Filter ready tasks by project."""
        t1 = storage.create_task("Task A", project="proj-a")
        t1.status = TaskStatus.ACTIVE
        storage.save_task(t1)

        t2 = storage.create_task("Task B", project="proj-b")
        t2.status = TaskStatus.ACTIVE
        storage.save_task(t2)

        index.rebuild()

        result = runner.invoke(cli, ["ready", "--project", "proj-a"])

        assert result.exit_code == 0
        assert "Task A" in result.output
        assert "Task B" not in result.output

    def test_ready_empty(
        self, runner: CliRunner, index: TaskIndex, data_dir: Path
    ) -> None:
        """Show message when no ready tasks."""
        index.rebuild()

        result = runner.invoke(cli, ["ready"])

        assert result.exit_code == 0
        assert "No ready tasks" in result.output


class TestBlockedCommand:
    """Test task blocked command."""

    def test_blocked_lists_blocked(
        self, runner: CliRunner, storage: TaskStorage, index: TaskIndex, data_dir: Path
    ) -> None:
        """List blocked tasks."""
        dep = storage.create_task("Dependency", project="test")
        storage.save_task(dep)

        blocked = storage.create_task("Blocked Task", project="test", depends_on=[dep.id])
        storage.save_task(blocked)

        index.rebuild()

        result = runner.invoke(cli, ["blocked"])

        assert result.exit_code == 0
        assert "Blocked Task" in result.output


class TestTreeCommand:
    """Test task tree command."""

    def test_tree_shows_hierarchy(
        self, runner: CliRunner, storage: TaskStorage, index: TaskIndex, data_dir: Path
    ) -> None:
        """Show task decomposition tree."""
        root = storage.create_task("Root", project="test", type=TaskType.GOAL)
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        grandchild = storage.create_task("Grandchild", project="test", parent=child.id)
        storage.save_task(grandchild)

        index.rebuild()

        result = runner.invoke(cli, ["tree", root.id])

        assert result.exit_code == 0
        assert "Root" in result.output
        assert "Child" in result.output
        assert "Grandchild" in result.output

    def test_tree_not_found(self, runner: CliRunner, data_dir: Path) -> None:
        """Tree error for missing task."""
        result = runner.invoke(cli, ["tree", "20260112-nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output


class TestDepsCommand:
    """Test task deps command."""

    def test_deps_shows_dependencies(
        self, runner: CliRunner, storage: TaskStorage, index: TaskIndex, data_dir: Path
    ) -> None:
        """Show dependency graph."""
        dep = storage.create_task("Dependency", project="test")
        storage.save_task(dep)

        task = storage.create_task("Task", project="test", depends_on=[dep.id])
        storage.save_task(task)

        dependent = storage.create_task("Dependent", project="test", depends_on=[task.id])
        storage.save_task(dependent)

        index.rebuild()

        result = runner.invoke(cli, ["deps", task.id])

        assert result.exit_code == 0
        assert "Depends on:" in result.output
        assert "Dependency" in result.output
        assert "Blocks:" in result.output
        assert "Dependent" in result.output


class TestDecomposeCommand:
    """Test task decompose command."""

    def test_decompose_creates_children(
        self, runner: CliRunner, storage: TaskStorage, data_dir: Path
    ) -> None:
        """Decompose task into children."""
        parent = storage.create_task("Chapter 1", project="book", type=TaskType.PROJECT)
        storage.save_task(parent)

        result = runner.invoke(
            cli,
            [
                "decompose",
                parent.id,
                "-t",
                "Outline",
                "-t",
                "Draft",
                "-t",
                "Revise",
            ],
        )

        assert result.exit_code == 0
        assert "Decomposed:" in result.output
        assert "Outline" in result.output
        assert "Draft" in result.output
        assert "Revise" in result.output

    def test_decompose_sequential(
        self, runner: CliRunner, storage: TaskStorage, data_dir: Path
    ) -> None:
        """Decompose with sequential dependencies."""
        parent = storage.create_task("Chapter 1", project="book")
        storage.save_task(parent)

        result = runner.invoke(
            cli,
            [
                "decompose",
                parent.id,
                "-t",
                "Outline",
                "-t",
                "Draft",
                "--sequential",
            ],
        )

        assert result.exit_code == 0
        assert "depends on:" in result.output

    def test_decompose_no_children_error(
        self, runner: CliRunner, storage: TaskStorage, data_dir: Path
    ) -> None:
        """Decompose without children shows error."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        result = runner.invoke(cli, ["decompose", parent.id])

        assert result.exit_code == 1
        assert "No child titles" in result.output


class TestReorderCommand:
    """Test task reorder command."""

    def test_reorder_children(
        self, runner: CliRunner, storage: TaskStorage, index: TaskIndex, data_dir: Path
    ) -> None:
        """Reorder children of a task."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        c1 = storage.create_task("Child 1", project="test", parent=parent.id)
        c1.order = 0
        storage.save_task(c1)

        c2 = storage.create_task("Child 2", project="test", parent=parent.id)
        c2.order = 1
        storage.save_task(c2)

        index.rebuild()

        # Reorder: c2 before c1
        result = runner.invoke(cli, ["reorder", parent.id, c2.id, c1.id])

        assert result.exit_code == 0
        assert "Reordered" in result.output

        # Verify new order
        reloaded_c1 = storage.get_task(c1.id)
        reloaded_c2 = storage.get_task(c2.id)
        assert reloaded_c2 is not None
        assert reloaded_c1 is not None
        assert reloaded_c2.order < reloaded_c1.order


class TestIndexCommands:
    """Test index subcommands."""

    def test_index_rebuild(
        self, runner: CliRunner, storage: TaskStorage, data_dir: Path
    ) -> None:
        """Rebuild task index."""
        storage.save_task(storage.create_task("Task 1", project="test"))
        storage.save_task(storage.create_task("Task 2", project="test"))

        result = runner.invoke(cli, ["index", "rebuild"])

        assert result.exit_code == 0
        assert "Index rebuilt" in result.output
        assert "Total tasks:  2" in result.output

    def test_index_stats(
        self, runner: CliRunner, storage: TaskStorage, index: TaskIndex, data_dir: Path
    ) -> None:
        """Show index statistics."""
        storage.save_task(storage.create_task("Task 1", project="test"))
        storage.save_task(storage.create_task("Task 2", project="test"))
        index.rebuild()

        result = runner.invoke(cli, ["index", "stats"])

        assert result.exit_code == 0
        assert "Task Index Statistics" in result.output
        assert "Total:" in result.output


class TestVersionOption:
    """Test CLI version option."""

    def test_version(self, runner: CliRunner) -> None:
        """Show version."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "2.0.0" in result.output


class TestHelpOption:
    """Test CLI help option."""

    def test_help(self, runner: CliRunner) -> None:
        """Show help."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Task v2" in result.output
        assert "add" in result.output
        assert "show" in result.output
        assert "done" in result.output

    def test_command_help(self, runner: CliRunner) -> None:
        """Show command-specific help."""
        result = runner.invoke(cli, ["add", "--help"])

        assert result.exit_code == 0
        assert "Add a new task" in result.output
        assert "--type" in result.output
        assert "--project" in result.output
