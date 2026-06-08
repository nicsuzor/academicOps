#!/usr/bin/env python3
"""Tests for polecat sanctioned mechanism SSoT checks.

Verifies that the pre-dispatch checks correctly refuse or flag worker-class
and method substitutions when a sanctioned mechanism is recorded.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from polecat.cli import _verify_sanctioned_mechanism


def test_verify_sanctioned_mechanism_no_mechanism():
    """Tasks without a sanctioned mechanism specified should pass validation."""
    task = MagicMock()
    task.body = "This is a normal task description."
    task.tags = []
    task.parent = None
    manager = MagicMock()

    # Should not raise or exit
    _verify_sanctioned_mechanism(task, manager, "claude", False, False)


def test_verify_sanctioned_mechanism_valid_matching():
    """Tasks with a matching client for the sanctioned mechanism should pass."""
    task = MagicMock()
    task.body = "Sanctioned Mechanism: feedback_agy_wsl_dashboard_qa_loop"
    task.tags = []
    task.parent = None
    manager = MagicMock()

    # Matching client "antigravity" or "gemini" should succeed without exiting
    _verify_sanctioned_mechanism(task, manager, "antigravity", False, False)
    _verify_sanctioned_mechanism(task, manager, "gemini", False, False)


def test_verify_sanctioned_mechanism_prohibited_substitution():
    """Tasks with a mismatched client should be rejected with exit code 3."""
    task = MagicMock()
    task.id = "task-123"
    task.body = "Sanctioned Mechanism: feedback_agy_wsl_dashboard_qa_loop"
    task.tags = []
    task.parent = None
    manager = MagicMock()

    # Selecting "claude" is a prohibited substitution. It should print error and exit(3).
    with pytest.raises(SystemExit) as exc_info:
        _verify_sanctioned_mechanism(task, manager, "claude", False, False)
    assert exc_info.value.code == 3


def test_verify_sanctioned_mechanism_parent_inherits():
    """Tasks should inherit the sanctioned mechanism check from their parent task."""
    task = MagicMock()
    task.id = "task-123"
    task.body = "Do the work."
    task.tags = []
    task.parent = "parent-123"

    parent_task = MagicMock()
    parent_task.body = "This loop requires feedback_agy_wsl_dashboard_qa_loop"
    parent_task.tags = []

    manager = MagicMock()
    manager.get_task.return_value = parent_task

    # Selecting "claude" is a prohibited substitution, inherited from parent.
    with pytest.raises(SystemExit) as exc_info:
        _verify_sanctioned_mechanism(task, manager, "claude", False, False)
    assert exc_info.value.code == 3
