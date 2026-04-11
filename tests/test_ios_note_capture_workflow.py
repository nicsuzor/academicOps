"""Tests for iOS note capture GitHub Actions workflow.

Only tests properties that GitHub Actions YAML validation cannot catch.
Structural YAML validity is validated by GitHub itself on push.
"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workflow_yaml(repo_root: Path) -> dict:
    """Loaded workflow YAML as dictionary."""
    workflow_path = repo_root / ".github/workflows/ios-note-capture.yml"
    assert workflow_path.exists(), f"Workflow not found at {workflow_path}"
    content = workflow_path.read_text()
    try:
        workflow = yaml.safe_load(content)
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML: {e}")

    assert isinstance(workflow, dict), "Workflow must be a dictionary"
    return workflow


def test_ios_note_capture_workflow_has_reasonable_timeout(workflow_yaml: dict) -> None:
    """Workflow has reasonable timeout to prevent runaway costs."""
    job = workflow_yaml["jobs"]["process-note"]

    assert "timeout-minutes" in job, "Job must have timeout-minutes"

    timeout = job["timeout-minutes"]
    assert timeout <= 10, f"Timeout should be <= 10 minutes, got {timeout}"
