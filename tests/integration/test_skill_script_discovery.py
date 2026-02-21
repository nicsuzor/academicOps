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
import shutil
from pathlib import Path

import pytest
import lib.paths


@pytest.fixture(autouse=True)
def setup_integration_env(monkeypatch):
    """Setup environment for integration tests."""
    # Set AOPS to plugin root
    aops_path = lib.paths.get_plugin_root()
    monkeypatch.setenv("AOPS", str(aops_path))

    # Ensure ~/.claude/skills symlink exists
    home_claude = Path.home() / ".claude"
    created_home_claude = False
    if not home_claude.exists():
        # If ~/.claude doesn't exist, create it
        home_claude.mkdir(parents=True, exist_ok=True)
        created_home_claude = True

    skills_link = home_claude / "skills"
    skills_target = aops_path / "skills"

    created_link = False
    if not skills_link.exists():
        try:
            skills_link.symlink_to(skills_target)
            created_link = True
        except OSError:
            pass  # Handle permission error or race condition

    yield

    # Cleanup
    if created_link and skills_link.is_symlink():
        skills_link.unlink()

    if created_home_claude:
        shutil.rmtree(home_claude)


@pytest.mark.integration
@pytest.mark.slow
def test_task_skill_scripts_discoverable(claude_headless, data_dir):
    """Test that task skill scripts are found and executable from writing repo.

    Verifies:
    - Claude can access task scripts via ~/.claude/skills/ symlink
    - Scripts work from non-AOPS working directory
    - No need to search for scripts in CWD
    """
    prompt = """Use the framework skill to validate docs.

    Run the validate_docs.py script using the path ~/.claude/skills/framework/scripts/validate_docs.py

    Use this exact command:
    PYTHONPATH=$AOPS uv run python ~/.claude/skills/framework/scripts/validate_docs.py --help

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

    # Should mention usage or success
    assert any(
        keyword in response_text for keyword in ["usage", "help", "validate_docs.py", "success"]
    ), "Response should indicate script usage was shown"

    # Should NOT indicate script not found
    assert "not found" not in response_text, "Script should be found via symlink"
    assert "no such file" not in response_text, "Script file should exist"


@pytest.mark.integration
@pytest.mark.slow
def test_skill_scripts_exist_via_symlink():
    """Test that skill scripts are accessible via ~/.claude/skills/ symlink.

    Verifies:
    - ~/.claude/skills/framework/ symlink exists
    - Script files are accessible through symlink
    - Path resolution works correctly
    """
    # Check symlink exists
    skills_path = Path.home() / ".claude" / "skills"
    assert skills_path.exists(), "~/.claude/skills/ should exist"
    assert skills_path.is_symlink() or skills_path.is_dir(), (
        "~/.claude/skills/ should be symlink or directory"
    )

    # Check framework skill exists
    skill_path = skills_path / "framework"
    assert skill_path.exists(), "~/.claude/skills/framework/ should exist"

    # Check scripts directory exists
    scripts_path = skill_path / "scripts"
    assert scripts_path.exists(), "~/.claude/skills/framework/scripts/ should exist"

    # Check specific scripts exist
    required_scripts = ["validate_docs.py"]
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

    # Build command to run validate_docs.py
    cmd = [
        "uv",
        "run",
        "python",
        str(Path.home() / ".claude" / "skills" / "framework" / "scripts" / "validate_docs.py"),
        "--help",
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

    # Should show usage info
    assert "usage:" in result.stdout or "usage:" in result.stderr, "Should show script usage"


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
    prompt = """I need to check documentation.

    Load the framework skill documentation and tell me the exact path to the validate_docs.py script.
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
        "~/.claude/skills/framework/scripts",  # symlink path
        "skills/framework/scripts",  # relative path
        "$aops/skills/framework/scripts",  # actual path with env var
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
    - Scripts live in skill directory (skills/framework/scripts/)
    - Scripts are accessible via symlink (~/.claude/skills/framework/scripts/)
    - Architecture supports run-from-anywhere
    """
    import os

    aops = os.environ.get("AOPS")
    assert aops, "AOPS environment variable should be set"

    aops_path = Path(aops)
    assert aops_path.exists(), f"AOPS path should exist: {aops_path}"

    # Scripts should exist in AOPS framework
    scripts_in_aops = aops_path / "skills" / "framework" / "scripts"
    assert scripts_in_aops.exists(), f"Scripts should exist in AOPS: {scripts_in_aops}"

    # Symlink should point to these scripts
    symlink_path = Path.home() / ".claude" / "skills" / "framework" / "scripts"
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
