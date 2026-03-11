"""Tests for iOS note capture GitHub Actions workflow.

Validates the workflow YAML structure and configuration for capturing
notes from iOS via repository_dispatch webhooks.
"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workflow_path(repo_root: Path) -> Path:
    """Path to iOS note capture workflow file.

    Args:
        repo_root: Path to repository root from fixture.

    Returns:
        Path to workflow YAML file.
    """
    return repo_root / ".github/workflows/ios-note-capture.yml"


@pytest.fixture
def workflow_yaml(workflow_path: Path) -> dict:
    """Loaded workflow YAML as dictionary.

    Args:
        workflow_path: Path to workflow file from fixture.

    Returns:
        Parsed workflow YAML.

    Raises:
        AssertionError: If YAML parsing fails.
    """
    content = workflow_path.read_text()
    try:
        workflow = yaml.safe_load(content)
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML: {e}")

    assert isinstance(workflow, dict), "Workflow must be a dictionary"
    return workflow


def test_ios_note_capture_workflow_exists(workflow_path: Path) -> None:
    """Workflow file exists at expected location.

    Args:
        workflow_path: Path to workflow file from fixture.

    Raises:
        AssertionError: If workflow file not found.
    """
    assert workflow_path.exists(), f"Workflow not found at {workflow_path}"


def test_ios_note_capture_workflow_valid_yaml(workflow_yaml: dict) -> None:
    """Workflow file is valid YAML.

    Args:
        workflow_yaml: Parsed workflow YAML from fixture.

    Raises:
        AssertionError: If YAML not a dict (validated in fixture).
    """
    # Validation happens in fixture - this just confirms it loaded
    assert workflow_yaml is not None


def test_ios_note_capture_workflow_triggers(workflow_yaml: dict) -> None:
    """Workflow has required trigger configuration.

    Args:
        workflow_yaml: Parsed workflow YAML from fixture.

    Raises:
        AssertionError: If required triggers missing.
    """
    # Must have 'on' trigger configuration
    # Note: YAML 1.1 interprets 'on' as boolean True, so check for both
    trigger_key = "on" if "on" in workflow_yaml else True
    assert trigger_key in workflow_yaml, "Workflow must have 'on' trigger"

    triggers = workflow_yaml[trigger_key]

    # Must support repository_dispatch for iOS webhook
    assert "repository_dispatch" in triggers, "Must have repository_dispatch trigger"
    assert "types" in triggers["repository_dispatch"], "repository_dispatch must specify types"
    assert "capture-note" in triggers["repository_dispatch"]["types"], (
        "Must handle 'capture-note' event type"
    )

    # Should also support manual trigger for testing
    assert "workflow_dispatch" in triggers, "Should have workflow_dispatch for manual testing"


def test_ios_note_capture_workflow_uses_claude_code_action(workflow_yaml: dict) -> None:
    """Workflow uses Claude Code action for processing.

    Args:
        workflow_yaml: Parsed workflow YAML from fixture.

    Raises:
        AssertionError: If Claude Code action not configured.
    """
    assert "jobs" in workflow_yaml, "Workflow must have jobs"

    # Find the process-note job
    jobs = workflow_yaml["jobs"]
    assert "process-note" in jobs, "Must have 'process-note' job"

    steps = jobs["process-note"]["steps"]

    # Look for Claude Code action
    claude_action_found = False
    for step in steps:
        if "uses" in step and "anthropics/claude-code-action" in step["uses"]:
            claude_action_found = True

            # Verify required configuration
            assert "with" in step, "Claude Code action must have 'with' configuration"
            with_config = step["with"]

            assert "anthropic_api_key" in with_config, "Must specify anthropic_api_key"
            assert "prompt" in with_config, "Must specify prompt for note processing"

            break

    assert claude_action_found, "Workflow must use anthropics/claude-code-action"


def test_ios_note_capture_workflow_persists_data(workflow_yaml: dict) -> None:
    """Workflow persists captured data (to memory server or git).

    Args:
        workflow_yaml: Parsed workflow YAML from fixture.

    Raises:
        AssertionError: If no persistence mechanism found.
    """
    steps = workflow_yaml["jobs"]["process-note"]["steps"]

    # Look for persistence mechanism: either git commit/push OR memory server
    persistence_found = False
    for step in steps:
        # Check for git-based persistence
        if "run" in step:
            run_content = step["run"]
            if "git commit" in run_content and "git push" in run_content:
                persistence_found = True
                break
            # Check for memory server reference (current implementation)
            if "memory server" in run_content.lower() or "memory" in run_content.lower():
                persistence_found = True
                break

        # Check for Claude Code action with memory store prompt
        if "uses" in step and "claude-code-action" in step.get("uses", ""):
            prompt = step.get("with", {}).get("prompt", "")
            if "memory" in prompt.lower() or "store" in prompt.lower():
                persistence_found = True
                break

    assert persistence_found, "Workflow must persist data (git commit/push or memory server)"


def test_ios_note_capture_workflow_has_reasonable_timeout(workflow_yaml: dict) -> None:
    """Workflow has reasonable timeout to prevent runaway costs.

    Args:
        workflow_yaml: Parsed workflow YAML from fixture.

    Raises:
        AssertionError: If timeout missing or too long.
    """
    job = workflow_yaml["jobs"]["process-note"]

    assert "timeout-minutes" in job, "Job must have timeout-minutes"

    timeout = job["timeout-minutes"]
    assert timeout <= 10, f"Timeout should be <= 10 minutes, got {timeout}"
