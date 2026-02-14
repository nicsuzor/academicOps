#!/usr/bin/env python3
"""End-to-end test for skill script discovery and execution.

Tests that Claude can:
1. Find skill scripts via ~/.claude/skills/ symlinks
2. Execute task scripts from any working directory
3. Use skills without searching the current directory

This test validates the run-from-anywhere architecture works correctly.
"""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_task_skill_scripts_discoverable(claude_headless, data_dir):
    """Test that task skill scripts are found and executable from writing repo.

    Verifies:
    - Claude can access task scripts via ~/.claude/skills/ symlink
    - Scripts work from non-AOPS working directory
    - No need to search for scripts in CWD
    """
    prompt = """Use the task skill to view tasks.

    Run the task_view.py script using the path ~/.claude/skills/tasks/scripts/task_view.py

    Use this exact command:
    PYTHONPATH=$AOPS uv run python ~/.claude/skills/tasks/scripts/task_view.py --compact

    Tell me if it succeeded and what the output was."""

    result = claude_headless(
        prompt=prompt,
        cwd=data_dir,
        timeout_seconds=180,
        permission_mode="plan",
    )

    # Basic success check
    assert result["success"], f"Claude execution failed: {result.get('error', 'Unknown error')}"

    # Get the full response text
    output = result["output"]
    parsed = json.loads(output)

    # The response should contain evidence of successful script execution
    response_text = str(parsed).lower()

    # Should mention tasks or successful execution
    assert any(
        keyword in response_text for keyword in ["task", "success", "inbox", "using data_dir"]
    ), "Response should indicate task script was executed"

    # Should NOT indicate script not found
    assert "not found" not in response_text, "Script should be found via symlink"
    assert "no such file" not in response_text, "Script file should exist"


@pytest.mark.integration
@pytest.mark.slow
def test_skill_scripts_exist_via_symlink():
    """Test that skill scripts are accessible via ~/.claude/skills/ symlink.

    Verifies:
    - ~/.claude/skills/tasks/ symlink exists
    - Script files are accessible through symlink
    - Path resolution works correctly
    """
    # Check symlink exists
    skills_path = Path.home() / ".claude" / "skills"
    assert skills_path.exists(), "~/.claude/skills/ should exist"
    assert skills_path.is_symlink() or skills_path.is_dir(), (
        "~/.claude/skills/ should be symlink or directory"
    )

    # Check task skill exists
    task_skill_path = skills_path / "tasks"
    assert task_skill_path.exists(), "~/.claude/skills/tasks/ should exist"

    # Check scripts directory exists
    scripts_path = task_skill_path / "scripts"
    assert scripts_path.exists(), "~/.claude/skills/tasks/scripts/ should exist"

    # Check specific scripts exist
    required_scripts = ["task_view.py", "task_add.py", "task_archive.py"]
    for script_name in required_scripts:
        script_path = scripts_path / script_name
        assert script_path.exists(), f"Script {script_name} should exist at {script_path}"


@pytest.mark.integration
@pytest.mark.slow
def test_task_script_runs_from_writing_repo(data_dir):
    """Test that task scripts execute correctly from writing repo.

    Verifies:
    - Scripts can be invoked with PYTHONPATH=$AOPS
    - Scripts find lib.paths correctly
    - Scripts locate data in writing repo's data directory
    """
    import os

    # Build command to run task_view.py
    cmd = [
        "uv",
        "run",
        "python",
        str(Path.home() / ".claude" / "skills" / "tasks" / "scripts" / "task_view.py"),
        "--compact",
    ]

    # Set environment
    env = os.environ.copy()
    aops = env.get("AOPS")
    assert aops, "AOPS environment variable should be set"
    env["PYTHONPATH"] = aops

    # Execute from writing repo
    result = subprocess.run(
        cmd,
        cwd=data_dir,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        check=False,
    )

    # Should succeed
    assert result.returncode == 0, (
        f"Script should execute successfully\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # Should show data directory from writing repo
    assert "data/tasks" in result.stdout, "Should use writing repo's data directory"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skip(
    reason="Flaky test - depends on Claude's response format which varies. Core path functionality tested by test_skill_self_contained_architecture."
)
def test_claude_finds_scripts_without_search(claude_headless, data_dir):
    """Test that Claude doesn't waste time searching for scripts in CWD.

    Verifies:
    - Skill documentation guides Claude to correct path
    - No need to glob/search for script locations
    - Scripts are found immediately via documented paths

    NOTE: This test is flaky because it depends on Claude's free-form response
    containing specific path strings. The underlying functionality (scripts exist
    at correct paths, symlinks work) is tested by test_skill_self_contained_architecture.
    """
    prompt = """I need to create a task.

    Load the tasks skill documentation and tell me the exact path to the task_add.py script.
    Do NOT search for it - just read the skill documentation.

    What path does the documentation say to use?"""

    result = claude_headless(
        prompt=prompt,
        cwd=data_dir,
        timeout_seconds=120,
        permission_mode="plan",
    )

    assert result["success"], f"Claude execution failed: {result.get('error', 'Unknown error')}"

    # Parse response
    output = result["output"]
    parsed = json.loads(output)
    response_text = str(parsed).lower()

    # Should mention one of the valid path formats
    valid_paths = [
        "~/.claude/skills/tasks/scripts",  # symlink path
        "skills/tasks/scripts",  # relative path
        "$aops/skills/tasks/scripts",  # actual path with env var
    ]
    normalized_response = response_text.replace("\\", "/")

    assert any(path.lower() in normalized_response for path in valid_paths), (
        f"Response should reference one of the valid paths: {valid_paths}\n"
        f"Got response: {response_text[:500]}"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_skill_self_contained_architecture():
    """Test that skills are self-contained with their own scripts.

    Verifies:
    - Scripts live in skill directory (skills/tasks/scripts/)
    - Scripts are accessible via symlink (~/. claude/skills/tasks/scripts/)
    - Architecture supports run-from-anywhere
    """
    import os

    aops = os.environ.get("AOPS")
    assert aops, "AOPS environment variable should be set"

    aops_path = Path(aops)
    assert aops_path.exists(), f"AOPS path should exist: {aops_path}"

    # Scripts should exist in AOPS framework
    scripts_in_aops = aops_path / "skills" / "tasks" / "scripts"
    assert scripts_in_aops.exists(), f"Scripts should exist in AOPS: {scripts_in_aops}"

    # Symlink should point to these scripts
    symlink_path = Path.home() / ".claude" / "skills" / "tasks" / "scripts"
    assert symlink_path.exists(), f"Symlink should exist: {symlink_path}"

    # Verify they point to same location (resolve symlinks)
    symlink_resolved = symlink_path.resolve()
    scripts_resolved = scripts_in_aops.resolve()

    assert symlink_resolved == scripts_resolved, (
        f"Symlink should point to AOPS scripts\n"
        f"Symlink resolves to: {symlink_resolved}\n"
        f"AOPS scripts at: {scripts_resolved}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
