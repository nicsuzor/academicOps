"""Pytest fixtures for aOps framework tests.

Provides fixtures for common paths and test setup.
All paths resolve using AOPS and ACA_DATA environment variables.
"""

from pathlib import Path

import pytest

from .paths import get_bots_dir, get_data_dir, get_hooks_dir, get_writing_root


@pytest.fixture
def bots_dir() -> Path:
    """Return Path to framework root (AOPS).

    Legacy alias - framework root is the old "bots" directory.

    Returns:
        Path: Absolute path to framework root ($AOPS)
    """
    return get_bots_dir()


@pytest.fixture
def data_dir() -> Path:
    """Return Path to data directory (ACA_DATA).

    Returns:
        Path: Absolute path to data directory ($ACA_DATA)
    """
    return get_data_dir()


@pytest.fixture
def hooks_dir() -> Path:
    """Return Path to hooks directory.

    Returns:
        Path: Absolute path to hooks/ directory ($AOPS/hooks)
    """
    return get_hooks_dir()


@pytest.fixture
def writing_root() -> Path:
    """Return Path to writing root (framework root).

    Returns:
        Path: Absolute path to framework root ($AOPS)
    """
    return get_writing_root()


@pytest.fixture
def test_data_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create temporary data directory structure for task tests.

    Creates the standard task directory structure in a temp location
    and sets the ACA_DATA environment variable to point to it.
    Also creates sample task files for tests that need them.

    Args:
        tmp_path: pytest's temporary directory fixture
        monkeypatch: pytest monkeypatch fixture for environment variables

    Returns:
        Path: Path to the temporary tasks directory (where inbox, archived, queue live)
    """
    data_dir = tmp_path / "data"
    tasks_dir = data_dir / "tasks"
    inbox_dir = tasks_dir / "inbox"
    (inbox_dir).mkdir(parents=True)
    (tasks_dir / "queue").mkdir(parents=True)
    (tasks_dir / "archived").mkdir(parents=True)

    # Create sample task files for tests
    _create_sample_task(
        inbox_dir, "sample-task-1", "High Priority Task", 1, "project-a"
    )
    _create_sample_task(
        inbox_dir, "sample-task-2", "Medium Priority Task", 2, "project-b"
    )
    _create_sample_task(inbox_dir, "sample-task-3", "Low Priority Task", 3, "project-a")

    # Set ACA_DATA - server reads this directly via task_ops.get_data_dir()
    monkeypatch.setenv("ACA_DATA", str(data_dir))

    return tasks_dir


def _create_sample_task(
    directory: Path, task_id: str, title: str, priority: int, project: str
) -> None:
    """Create a sample task file in markdown format.

    Args:
        directory: Directory to create task file in
        task_id: Task ID for the file
        title: Task title
        priority: Priority level (0-3)
        project: Project name
    """
    from datetime import datetime, timezone

    filename = f"{task_id}.md"
    filepath = directory / filename

    # Generate properly formatted content
    now = datetime.now(timezone.utc).isoformat()
    created = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()

    content = f"""---
title: {title}
permalink: tasks/{task_id}
type: task
task_id: {task_id}
aliases: []
status: inbox
priority: {priority}
project: {project}
tags: [test, sample]
created: {created}
updated: {now}
---

# {title}

## Context
Test task for integration testing with priority {priority}.

## Observations
This is a sample task created by the test fixture.

## Relations
- Project: {project}
- Status: inbox
"""
    filepath.write_text(content, encoding="utf-8")
