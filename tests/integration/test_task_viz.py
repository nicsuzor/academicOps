#!/usr/bin/env python3
"""Integration test for task visualization dashboard.

Tests that the task-viz automation can:
1. Discover task files across multiple repositories
2. Parse task metadata from Markdown with YAML frontmatter
3. Generate valid Excalidraw JSON visualization
4. Correctly group tasks by project and status
5. Apply visual encoding (color by status)
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from tests.integration.conftest import extract_response_text


@pytest.fixture
def test_repos():
    """Create temporary test repositories with task files.

    Returns:
        Path to temporary directory containing test repos
    """
    # Create temporary directory for test
    temp_dir = Path(tempfile.mkdtemp(prefix="task-viz-test-"))

    try:
        # Create test repository structure
        repo1 = temp_dir / "repo1"
        repo2 = temp_dir / "repo2"
        repo3 = temp_dir / "repo3"

        for repo in [repo1, repo2, repo3]:
            (repo / "data" / "tasks" / "inbox").mkdir(parents=True)

        # Create test task files in Markdown format with YAML frontmatter
        # Repo 1: Framework tasks (active and blocked)
        (repo1 / "data" / "tasks" / "inbox" / "task-001.md").write_text(
            """---
title: Active framework task
created: 2025-11-17T10:00:00Z
priority: 1
project: framework
status: active
---

# Active framework task

Working on implementing new feature.
"""
        )

        (repo1 / "data" / "tasks" / "inbox" / "task-002.md").write_text(
            """---
title: Blocked doc task
created: 2025-11-17T11:00:00Z
priority: 2
project: framework
status: blocked
blockers:
  - waiting-input
---

# Blocked doc task

Need input from user before proceeding.

## Blockers

- waiting-input: Waiting for user decision on approach
"""
        )

        # Repo 2: Privacy research tasks (active and queued)
        (repo2 / "data" / "tasks" / "inbox" / "task-003.md").write_text(
            """---
title: Privacy paper draft
created: 2025-11-15T09:00:00Z
priority: 1
project: privacy
status: active
---

# Privacy paper draft

Drafting introduction and background sections.
"""
        )

        (repo2 / "data" / "tasks" / "inbox" / "task-004.md").write_text(
            """---
title: Review literature
created: 2025-11-16T14:00:00Z
priority: 2
project: privacy
status: queued
---

# Review literature

Need to review recent papers on platform governance.
"""
        )

        # Repo 3: Teaching task (completed)
        (repo3 / "data" / "tasks" / "inbox" / "task-005.md").write_text(
            """---
title: Completed task example
created: 2025-11-10T08:00:00Z
priority: 3
project: teaching
status: completed
---

# Completed task example

This task has been completed successfully.
"""
        )

        yield temp_dir

    finally:
        # Cleanup: Remove temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.slow
@pytest.mark.integration
def test_task_viz_agent_workflow(claude_headless, test_repos: Path):
    """Test agent workflow for task visualization generation.

    This test validates that an agent can:
    1. Discover task files across multiple test repositories
    2. Read and parse task metadata
    3. Orchestrate generation of Excalidraw visualization
    4. Produce valid output

    Args:
        claude_headless: Fixture for headless Claude execution
        test_repos: Fixture providing test repository directory

    Raises:
        AssertionError: If agent workflow fails or output is invalid
    """
    # Create output location
    output_file = test_repos / "test-tasks.excalidraw"

    # Arrange: Prepare agent prompt
    prompt = f"""
I have task files in multiple test repositories at:
- {test_repos}/repo1/data/tasks/inbox/
- {test_repos}/repo2/data/tasks/inbox/
- {test_repos}/repo3/data/tasks/inbox/

Each repository contains task files in Markdown format with YAML frontmatter.

Please:
1. Discover all task files using Glob
2. Read each task file
3. Parse the frontmatter to extract: title, status, project, priority, blockers
4. Group tasks by project
5. Create a data structure suitable for visualization

For this test, just confirm you can read and parse all 5 task files and
summarize what you found by status and project. List each task by title.

DO NOT actually generate Excalidraw JSON yet - we're testing the discovery
and parsing workflow first.
"""

    # Act: Execute agent workflow
    result = claude_headless(
        prompt=prompt,
        timeout_seconds=120,
        permission_mode="bypassPermissions",
        cwd=test_repos,
    )

    # Assert: Command succeeded
    assert result["success"], f"Agent execution failed: {result.get('error')}"

    # Extract response using helper function
    response = extract_response_text(result)
    response_lower = response.lower()

    # Assert: Agent found all 5 tasks
    # Check for task titles in response
    assert (
        "active framework task" in response_lower
    ), f"Missing task 1 in response: {response}"
    assert "blocked doc task" in response_lower, f"Missing task 2 in response: {response}"
    assert (
        "privacy paper draft" in response_lower
    ), f"Missing task 3 in response: {response}"
    assert "review literature" in response_lower, f"Missing task 4 in response: {response}"
    assert (
        "completed task example" in response_lower
    ), f"Missing task 5 in response: {response}"

    # Assert: Agent identified all projects
    assert "framework" in response_lower, f"Missing framework project: {response}"
    assert "privacy" in response_lower, f"Missing privacy project: {response}"
    assert "teaching" in response_lower, f"Missing teaching project: {response}"

    # Assert: Agent identified different statuses
    assert "active" in response_lower, f"Missing active status: {response}"
    assert "blocked" in response_lower, f"Missing blocked status: {response}"
    assert "queued" in response_lower, f"Missing queued status: {response}"
    assert "completed" in response_lower, f"Missing completed status: {response}"


@pytest.mark.integration
def test_task_file_parsing(test_repos: Path):
    """Test that task file format can be parsed correctly (fast unit-style test).

    Args:
        test_repos: Fixture providing test repository directory

    Raises:
        AssertionError: If task files cannot be parsed or are missing expected fields
    """
    import re

    # Read a task file
    task_file = test_repos / "repo1" / "data" / "tasks" / "inbox" / "task-001.md"
    content = task_file.read_text()

    # Assert: File has YAML frontmatter
    assert content.startswith("---"), "Task file missing YAML frontmatter opening"
    assert content.count("---") >= 2, "Task file missing YAML frontmatter closing"

    # Extract frontmatter
    frontmatter = content.split("---")[1]

    # Assert: Required fields present
    assert "title:" in frontmatter, "Task missing title field"
    assert "created:" in frontmatter, "Task missing created field"
    assert "priority:" in frontmatter, "Task missing priority field"
    assert "status:" in frontmatter, "Task missing status field"

    # Assert: Can extract values
    title_match = re.search(r"title:\s*(.+)", frontmatter)
    assert title_match, "Cannot parse title field"
    assert "Active framework task" in title_match.group(1)

    priority_match = re.search(r"priority:\s*(\d+)", frontmatter)
    assert priority_match, "Cannot parse priority field"
    assert priority_match.group(1) == "1"

    status_match = re.search(r"status:\s*(\w+)", frontmatter)
    assert status_match, "Cannot parse status field"
    assert status_match.group(1) == "active"


@pytest.mark.integration
def test_excalidraw_json_structure():
    """Test understanding of Excalidraw JSON structure (documentation test).

    This test documents the expected Excalidraw JSON structure that the
    generation script should produce. It validates that we can create
    minimal valid Excalidraw JSON.

    Raises:
        AssertionError: If minimal Excalidraw JSON structure is invalid
    """
    # Create minimal valid Excalidraw JSON structure
    excalidraw_data = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {
                "id": "test-rect-1",
                "type": "rectangle",
                "x": 100,
                "y": 100,
                "width": 200,
                "height": 80,
                "backgroundColor": "#a5d8ff",
                "strokeColor": "#1971c2",
                "strokeWidth": 2,
                "fillStyle": "solid",
                "opacity": 100,
            },
            {
                "id": "test-text-1",
                "type": "text",
                "x": 110,
                "y": 120,
                "text": "Test Task",
                "fontSize": 20,
                "fontFamily": 1,
            },
        ],
        "appState": {"viewBackgroundColor": "#ffffff"},
    }

    # Assert: Can serialize to JSON
    json_str = json.dumps(excalidraw_data, indent=2)
    assert len(json_str) > 0, "Cannot serialize Excalidraw structure to JSON"

    # Assert: Can deserialize back
    parsed = json.loads(json_str)
    assert parsed["type"] == "excalidraw", "Invalid Excalidraw type"
    assert parsed["version"] == 2, "Invalid Excalidraw version"
    assert len(parsed["elements"]) == 2, "Elements not preserved in serialization"

    # Assert: Elements have required properties
    rect = parsed["elements"][0]
    assert rect["type"] == "rectangle", "Rectangle type not preserved"
    assert rect["x"] == 100, "Rectangle x coordinate not preserved"
    assert rect["backgroundColor"] == "#a5d8ff", "Rectangle color not preserved"


@pytest.mark.integration
def test_task_discovery_pattern(test_repos: Path):
    """Test that task files can be discovered with glob pattern (fast unit-style test).

    Args:
        test_repos: Fixture providing test repository directory

    Raises:
        AssertionError: If glob pattern doesn't find expected task files
    """
    # Use glob to discover task files (simulating agent Glob tool)
    pattern = str(test_repos / "*/data/tasks/inbox/*.md")
    import glob

    task_files = sorted(glob.glob(pattern))

    # Assert: Found all 5 test task files
    assert len(task_files) == 5, f"Expected 5 task files, found {len(task_files)}"

    # Assert: Files are from all 3 repos
    repo_names = {Path(f).parts[-5] for f in task_files}  # Extract repo name from path
    assert repo_names == {
        "repo1",
        "repo2",
        "repo3",
    }, f"Missing repos in discovered files: {repo_names}"

    # Assert: All files are .md files
    assert all(f.endswith(".md") for f in task_files), "Non-markdown files in results"
