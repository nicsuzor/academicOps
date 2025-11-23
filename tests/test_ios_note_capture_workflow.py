"""Tests for iOS note capture GitHub Actions workflow.

Validates the workflow YAML structure and configuration for capturing
notes from iOS via repository_dispatch webhooks.
"""

from pathlib import Path

import pytest
import yaml


def test_ios_note_capture_workflow_exists(bots_dir: Path) -> None:
    """Workflow file exists at expected location.

    Args:
        bots_dir: Path to framework root from fixture.

    Raises:
        AssertionError: If workflow file not found.
    """
    # Staged in config/workflows/ - move to .github/workflows/ after merge
    workflow_path = bots_dir / "config/workflows/ios-note-capture.yml"
    assert workflow_path.exists(), f"Workflow not found at {workflow_path}"


def test_ios_note_capture_workflow_valid_yaml(bots_dir: Path) -> None:
    """Workflow file is valid YAML.

    Args:
        bots_dir: Path to framework root from fixture.

    Raises:
        AssertionError: If YAML parsing fails.
    """
    # Staged in config/workflows/ - move to .github/workflows/ after merge
    workflow_path = bots_dir / "config/workflows/ios-note-capture.yml"
    content = workflow_path.read_text()

    try:
        workflow = yaml.safe_load(content)
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML: {e}")

    assert isinstance(workflow, dict), "Workflow must be a dictionary"


def test_ios_note_capture_workflow_triggers(bots_dir: Path) -> None:
    """Workflow has required trigger configuration.

    Args:
        bots_dir: Path to framework root from fixture.

    Raises:
        AssertionError: If required triggers missing.
    """
    # Staged in config/workflows/ - move to .github/workflows/ after merge
    workflow_path = bots_dir / "config/workflows/ios-note-capture.yml"
    workflow = yaml.safe_load(workflow_path.read_text())

    # Must have 'on' trigger configuration
    # Note: YAML 1.1 interprets 'on' as boolean True, so check for both
    trigger_key = "on" if "on" in workflow else True
    assert trigger_key in workflow, "Workflow must have 'on' trigger"

    triggers = workflow[trigger_key]

    # Must support repository_dispatch for iOS webhook
    assert "repository_dispatch" in triggers, "Must have repository_dispatch trigger"
    assert "types" in triggers["repository_dispatch"], "repository_dispatch must specify types"
    assert "capture-note" in triggers["repository_dispatch"]["types"], (
        "Must handle 'capture-note' event type"
    )

    # Should also support manual trigger for testing
    assert "workflow_dispatch" in triggers, "Should have workflow_dispatch for manual testing"


def test_ios_note_capture_workflow_uses_claude_code_action(bots_dir: Path) -> None:
    """Workflow uses Claude Code action for processing.

    Args:
        bots_dir: Path to framework root from fixture.

    Raises:
        AssertionError: If Claude Code action not configured.
    """
    # Staged in config/workflows/ - move to .github/workflows/ after merge
    workflow_path = bots_dir / "config/workflows/ios-note-capture.yml"
    workflow = yaml.safe_load(workflow_path.read_text())

    assert "jobs" in workflow, "Workflow must have jobs"

    # Find the process-note job
    jobs = workflow["jobs"]
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


def test_ios_note_capture_workflow_commits_changes(bots_dir: Path) -> None:
    """Workflow commits changes after processing.

    Args:
        bots_dir: Path to framework root from fixture.

    Raises:
        AssertionError: If commit step missing.
    """
    # Staged in config/workflows/ - move to .github/workflows/ after merge
    workflow_path = bots_dir / "config/workflows/ios-note-capture.yml"
    workflow = yaml.safe_load(workflow_path.read_text())

    steps = workflow["jobs"]["process-note"]["steps"]

    # Look for commit step
    commit_step_found = False
    for step in steps:
        if "run" in step:
            run_content = step["run"]
            if "git commit" in run_content and "git push" in run_content:
                commit_step_found = True
                break

    assert commit_step_found, "Workflow must have a step that commits and pushes changes"


def test_ios_note_capture_workflow_has_reasonable_timeout(bots_dir: Path) -> None:
    """Workflow has reasonable timeout to prevent runaway costs.

    Args:
        bots_dir: Path to framework root from fixture.

    Raises:
        AssertionError: If timeout missing or too long.
    """
    # Staged in config/workflows/ - move to .github/workflows/ after merge
    workflow_path = bots_dir / "config/workflows/ios-note-capture.yml"
    workflow = yaml.safe_load(workflow_path.read_text())

    job = workflow["jobs"]["process-note"]

    assert "timeout-minutes" in job, "Job must have timeout-minutes"

    timeout = job["timeout-minutes"]
    assert timeout <= 10, f"Timeout should be <= 10 minutes, got {timeout}"
