#!/usr/bin/env python3
"""Tests for polecat sanctioned mechanism SSoT checks.

Verifies that the pre-dispatch checks correctly refuse or flag worker-class
and method substitutions when a sanctioned mechanism is recorded.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from polecat.cli import _verify_sanctioned_mechanism


def _mock_agent_response(mechanism_name: str, verdict: str) -> MagicMock:
    """Build a mock subprocess.CompletedProcess for a claude -p judgment response."""
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.stdout = f"MECHANISM: {mechanism_name}\nVERDICT: {verdict}"
    mock.returncode = 0
    return mock


def test_verify_sanctioned_mechanism_no_mechanism():
    """Tasks without a sanctioned mechanism specified should pass validation."""
    task = MagicMock()
    task.body = "This is a normal task description."
    task.tags = []
    task.parent = None
    manager = MagicMock()

    with patch("polecat.cli.subprocess.run", return_value=_mock_agent_response("none", "valid")):
        _verify_sanctioned_mechanism(task, manager, "claude", False, False)


def test_verify_sanctioned_mechanism_valid_matching():
    """Tasks with a matching client for the sanctioned mechanism should pass.

    Uses natural-language body text to demonstrate that agent judgment covers
    descriptions the old regex could not detect.
    """
    task = MagicMock()
    task.body = "This loop uses the agy WSL dashboard QA harness as the canonical test method."
    task.tags = []
    task.parent = None
    manager = MagicMock()

    with patch(
        "polecat.cli.subprocess.run",
        return_value=_mock_agent_response("feedback_agy_wsl_dashboard_qa_loop", "valid"),
    ):
        _verify_sanctioned_mechanism(task, manager, "antigravity", False, False)

    with patch(
        "polecat.cli.subprocess.run",
        return_value=_mock_agent_response("feedback_agy_wsl_dashboard_qa_loop", "valid"),
    ):
        _verify_sanctioned_mechanism(task, manager, "gemini", False, False)


def test_verify_sanctioned_mechanism_prohibited_substitution():
    """Tasks with a mismatched client should be rejected with exit code 3."""
    task = MagicMock()
    task.id = "task-123"
    task.body = "This loop uses the agy WSL dashboard QA harness as the canonical test method."
    task.tags = []
    task.parent = None
    manager = MagicMock()

    with patch(
        "polecat.cli.subprocess.run",
        return_value=_mock_agent_response(
            "feedback_agy_wsl_dashboard_qa_loop",
            "VIOLATION: mechanism requires an agy/antigravity worker, not claude",
        ),
    ):
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
    parent_task.body = "The sanctioned harness for this loop is the agy WSL dashboard QA loop."
    parent_task.tags = []

    manager = MagicMock()
    manager.get_task.return_value = parent_task

    with patch(
        "polecat.cli.subprocess.run",
        return_value=_mock_agent_response(
            "feedback_agy_wsl_dashboard_qa_loop",
            "VIOLATION: mechanism requires an agy/antigravity worker, not claude",
        ),
    ):
        with pytest.raises(SystemExit) as exc_info:
            _verify_sanctioned_mechanism(task, manager, "claude", False, False)
    assert exc_info.value.code == 3
