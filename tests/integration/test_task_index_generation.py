"""Integration tests for task index generation.

Tests regenerate_task_index.py with real filesystem and subprocess.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


class TestTaskIndexGeneration:
    """Test regenerate_task_index.py with temp data."""

    @pytest.fixture
    def aops_root(self) -> Path:
        """Get the academicOps root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def test_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        tasks_dir = data_dir / "tasks" / "inbox"
        tasks_dir.mkdir(parents=True)
        return data_dir

    def test_script_runs_successfully(
        self, aops_root: Path, test_data_dir: Path
    ) -> None:
        """Verify script completes without error."""
        # Create test task with type: task
        inbox_dir = test_data_dir / "tasks" / "inbox"
        task_file = inbox_dir / "test-task.md"
        task_file.write_text(
            """---
title: Test Task
type: task
priority: 1
status: inbox
project: test-project
---

# Test Task

A test task for integration testing.
"""
        )

        # Run script
        result = subprocess.run(
            ["uv", "run", "python", "scripts/regenerate_task_index.py"],
            cwd=str(aops_root),
            env={**os.environ, "ACA_DATA": str(test_data_dir)},
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify outputs exist
        assert (test_data_dir / "tasks" / "index.json").exists()
        assert (test_data_dir / "tasks" / "INDEX.md").exists()

    def test_filters_by_type_task(
        self, aops_root: Path, test_data_dir: Path
    ) -> None:
        """Verify only type: task files are included."""
        inbox_dir = test_data_dir / "tasks" / "inbox"
        notes_dir = test_data_dir / "notes"
        notes_dir.mkdir(parents=True)

        # Task file in tasks/ (should be included)
        (inbox_dir / "task.md").write_text(
            """---
title: Included Task
type: task
project: test-project
---
"""
        )

        # Note file (should be excluded - wrong type)
        (notes_dir / "note.md").write_text(
            """---
title: Note
type: note
---
"""
        )

        # Task in notes dir (should be included - has type: task)
        (notes_dir / "task-in-notes.md").write_text(
            """---
title: Task in Notes
type: task
project: notes-project
---
"""
        )

        result = subprocess.run(
            ["uv", "run", "python", "scripts/regenerate_task_index.py"],
            cwd=str(aops_root),
            env={**os.environ, "ACA_DATA": str(test_data_dir)},
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify correct files included via JSON (more precise than string matching)
        with open(test_data_dir / "tasks" / "index.json") as f:
            index_data = json.load(f)

        assert index_data["total_tasks"] == 2
        titles = [t["title"] for t in index_data["tasks"]]
        assert "Included Task" in titles
        assert "Task in Notes" in titles
        # "Note" (the note file) should NOT be in titles
        assert "Note" not in titles

        # Also verify INDEX.md has the right tasks
        index_md = (test_data_dir / "tasks" / "INDEX.md").read_text()
        assert "Included Task" in index_md
        assert "Task in Notes" in index_md

    def test_groups_by_project(
        self, aops_root: Path, test_data_dir: Path
    ) -> None:
        """Verify INDEX.md groups tasks by project."""
        inbox_dir = test_data_dir / "tasks" / "inbox"

        # Create tasks in different projects
        (inbox_dir / "task1.md").write_text(
            """---
title: Alpha Task
type: task
project: alpha-project
priority: 1
---
"""
        )

        (inbox_dir / "task2.md").write_text(
            """---
title: Beta Task
type: task
project: beta-project
priority: 2
---
"""
        )

        (inbox_dir / "task3.md").write_text(
            """---
title: Another Alpha
type: task
project: alpha-project
priority: 0
---
"""
        )

        result = subprocess.run(
            ["uv", "run", "python", "scripts/regenerate_task_index.py"],
            cwd=str(aops_root),
            env={**os.environ, "ACA_DATA": str(test_data_dir)},
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        index_md = (test_data_dir / "tasks" / "INDEX.md").read_text()

        # Verify project headers exist
        assert "## alpha-project (2)" in index_md
        assert "## beta-project (1)" in index_md

        # Verify alphabetical order (alpha before beta)
        alpha_pos = index_md.find("## alpha-project")
        beta_pos = index_md.find("## beta-project")
        assert alpha_pos < beta_pos

    def test_excludes_sessions_directory(
        self, aops_root: Path, test_data_dir: Path
    ) -> None:
        """Verify session transcripts are excluded even if they contain type: task."""
        inbox_dir = test_data_dir / "tasks" / "inbox"
        sessions_dir = test_data_dir / "sessions" / "claude"
        sessions_dir.mkdir(parents=True)

        # Real task (should be included)
        (inbox_dir / "real-task.md").write_text(
            """---
title: Real Task
type: task
---
"""
        )

        # Session transcript with quoted task frontmatter (should be excluded)
        (sessions_dir / "session.md").write_text(
            """---
title: Session Transcript
type: session
---

User created a task:
```
---
title: Quoted Task
type: task
---
```
"""
        )

        result = subprocess.run(
            ["uv", "run", "python", "scripts/regenerate_task_index.py"],
            cwd=str(aops_root),
            env={**os.environ, "ACA_DATA": str(test_data_dir)},
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        with open(test_data_dir / "tasks" / "index.json") as f:
            index_data = json.load(f)

        assert index_data["total_tasks"] == 1
        assert index_data["tasks"][0]["title"] == "Real Task"
