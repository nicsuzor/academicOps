#!/usr/bin/env python3
"""Tests for task CLI (TDD - written before implementation)."""

import os
import subprocess
import sys
from pathlib import Path

# CLI is invoked via subprocess to test actual entry point behavior
CLI_CMD = [sys.executable, "-m", "scripts.task_cli"]


def run_cli(
    *args: str, cwd: Path | None = None, env: dict | None = None
) -> subprocess.CompletedProcess:
    """Run the task CLI with given arguments."""
    cmd = CLI_CMD + list(args)
    # Merge with current env if custom env provided
    run_env = None
    if env:
        run_env = os.environ.copy()
        run_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or Path(__file__).parent.parent,
        env=run_env,
    )


class TestCliHelp:
    """Tests for CLI help and basic invocation."""

    def test_help_flag_shows_usage(self):
        """--help displays usage information."""
        result = run_cli("--help")
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()

    def test_help_shows_available_commands(self):
        """--help lists available commands."""
        result = run_cli("--help")
        assert result.returncode == 0
        # Should show main commands
        assert "list" in result.stdout.lower()
        assert "create" in result.stdout.lower()


class TestCliList:
    """Tests for 'task list' command."""

    def test_list_returns_success(self, tmp_path):
        """'task list' returns exit code 0."""
        result = run_cli("list", env={"ACA_DATA": str(tmp_path)})
        assert result.returncode == 0

    def test_list_with_status_filter(self, tmp_path):
        """'task list --status active' filters by status."""
        result = run_cli("list", "--status", "active", env={"ACA_DATA": str(tmp_path)})
        assert result.returncode == 0

    def test_list_with_project_filter(self, tmp_path):
        """'task list --project book' filters by project."""
        result = run_cli("list", "--project", "book", env={"ACA_DATA": str(tmp_path)})
        assert result.returncode == 0


class TestCliCreate:
    """Tests for 'task create' command."""

    def test_create_requires_title(self, tmp_path):
        """'task create' without title shows error."""
        result = run_cli("create", env={"ACA_DATA": str(tmp_path)})
        # Should fail without required title argument
        assert result.returncode != 0

    def test_create_with_title(self, tmp_path):
        """'task create "My Task"' creates a task."""
        result = run_cli("create", "My Test Task", env={"ACA_DATA": str(tmp_path)})
        assert result.returncode == 0
        # Should output the created task ID
        assert "ID:" in result.stdout

    def test_create_with_project(self, tmp_path):
        """'task create --project book "My Task"' assigns to project."""
        result = run_cli(
            "create",
            "--project",
            "book",
            "My Book Task",
            env={"ACA_DATA": str(tmp_path)},
        )
        assert result.returncode == 0


class TestCliComplete:
    """Tests for 'task complete' command."""

    def test_complete_requires_task_id(self, tmp_path):
        """'task complete' without ID shows error."""
        result = run_cli("complete", env={"ACA_DATA": str(tmp_path)})
        assert result.returncode != 0

    def test_complete_nonexistent_task(self, tmp_path):
        """'task complete nonexistent-id' shows error."""
        result = run_cli(
            "complete", "nonexistent-task-id", env={"ACA_DATA": str(tmp_path)}
        )
        assert result.returncode != 0
        assert (
            "not found" in result.stdout.lower() or "not found" in result.stderr.lower()
        )

    def test_complete_existing_task(self, tmp_path):
        """'task complete <id>' marks task as done."""
        env = {"ACA_DATA": str(tmp_path)}
        # First create a task
        create_result = run_cli("create", "Task to complete", env=env)
        assert create_result.returncode == 0
        # Extract task ID from output
        task_id = None
        for line in create_result.stdout.splitlines():
            if "ID:" in line:
                task_id = line.split("ID:")[-1].strip()
                break

        # Fallback to searching for date-like ID if ID: line not found (legacy)
        if not task_id:
            for word in create_result.stdout.split():
                if word.startswith("20") and len(word) >= 8:
                    task_id = word.strip()
                    break

        assert task_id is not None, f"Could not find task ID in: {create_result.stdout}"

        # Now complete it
        result = run_cli("complete", task_id, env=env)
        assert result.returncode == 0


class TestCliShow:
    """Tests for 'task show' command."""

    def test_show_requires_task_id(self, tmp_path):
        """'task show' without ID shows error."""
        result = run_cli("show", env={"ACA_DATA": str(tmp_path)})
        assert result.returncode != 0

    def test_show_nonexistent_task(self, tmp_path):
        """'task show nonexistent-id' shows error."""
        result = run_cli("show", "nonexistent-task-id", env={"ACA_DATA": str(tmp_path)})
        assert result.returncode != 0

    def test_show_existing_task(self, tmp_path):
        """'task show <id>' displays task details."""
        env = {"ACA_DATA": str(tmp_path)}
        # First create a task
        create_result = run_cli("create", "Task to show", env=env)
        assert create_result.returncode == 0

        task_id = None
        for line in create_result.stdout.splitlines():
            if "ID:" in line:
                task_id = line.split("ID:")[-1].strip()
                break

        if not task_id:
            for word in create_result.stdout.split():
                if word.startswith("20") and len(word) >= 8:
                    task_id = word.strip()
                    break

        assert task_id is not None, f"Could not find task ID in: {create_result.stdout}"

        # Now show it
        result = run_cli("show", task_id, env=env)
        assert result.returncode == 0
        assert "Task to show" in result.stdout
