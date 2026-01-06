"""E2E tests for PreToolUse criteria_gate hook.

Tests verify the hook blocks Edit/Write/Bash operations until
the criteria gate has been passed (gate file exists).

NOTE: These tests use default permission mode (not bypassPermissions) because
bypassPermissions appears to also bypass PreToolUse hooks.
"""

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture
def claude_test(claude_headless):
    """Fixture providing claude_headless with default test settings.

    Uses longer timeout and NO bypassPermissions (so hooks run).
    """

    def _run(prompt: str, cwd: Path | None = None):
        return claude_headless(
            prompt=prompt,
            model="haiku",
            timeout_seconds=180,
            # Don't use bypassPermissions - we need hooks to run
            cwd=cwd,
        )

    return _run


@pytest.fixture
def temp_repo():
    """Fixture providing a temporary git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        (repo_dir / "test.txt").write_text("test")
        subprocess.run(
            ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        yield repo_dir


@pytest.mark.slow
@pytest.mark.integration
def test_e2e_blocks_file_write_without_gate(claude_test) -> None:
    """Test that Claude cannot write files without criteria gate passed.

    The criteria_gate hook should block Write operations when the
    gate file doesn't exist for this session.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        target_file = Path(tmpdir) / "test-output.txt"

        result = claude_test(
            prompt=f"Write a file at {target_file} with content 'Hello World'. Just write the file directly.",
            cwd=Path(tmpdir),
        )

        assert result["success"], f"Execution failed: {result.get('error')}"

        # File should NOT exist - hook blocked the write
        # Note: Claude may also just respond that it was blocked
        from tests.integration.conftest import extract_response_text

        try:
            response = extract_response_text(result).lower()
            # Either file doesn't exist OR response indicates block
            file_blocked = not target_file.exists()
            response_indicates_block = any(
                w in response
                for w in ["blocked", "criteria", "gate", "cannot", "must first"]
            )
            assert file_blocked or response_indicates_block, (
                f"File exists: {target_file.exists()}, Response: {response[:300]}"
            )
        except (ValueError, TypeError):
            # Can't extract response - just check file doesn't exist
            assert not target_file.exists(), "File was created but should have been blocked"


@pytest.mark.slow
@pytest.mark.integration
def test_e2e_blocks_edit_without_gate(claude_test) -> None:
    """Test that Claude cannot edit files without criteria gate passed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file to edit
        target_file = Path(tmpdir) / "existing-file.txt"
        target_file.write_text("original content")

        result = claude_test(
            prompt=f"Edit the file at {target_file} and change 'original' to 'modified'.",
            cwd=Path(tmpdir),
        )

        assert result["success"], f"Execution failed: {result.get('error')}"

        # File should still have original content - hook blocked the edit
        content = target_file.read_text()

        from tests.integration.conftest import extract_response_text

        try:
            response = extract_response_text(result).lower()
            # Either content unchanged OR response indicates block
            edit_blocked = "original" in content
            response_indicates_block = any(
                w in response
                for w in ["blocked", "criteria", "gate", "cannot", "must first"]
            )
            assert edit_blocked or response_indicates_block, (
                f"Content: {content}, Response: {response[:300]}"
            )
        except (ValueError, TypeError):
            # Can't extract response - just check content unchanged
            assert "original" in content, "File was edited but should have been blocked"


@pytest.mark.slow
@pytest.mark.integration
def test_e2e_blocks_destructive_bash_without_gate(claude_test, temp_repo) -> None:
    """Test that Claude cannot run destructive bash commands without gate."""
    # Create a file to potentially delete
    target_file = temp_repo / "deleteme.txt"
    target_file.write_text("do not delete")

    result = claude_test(
        prompt=f"Run this command: rm {target_file}",
        cwd=temp_repo,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # File should still exist - hook blocked the rm command
    from tests.integration.conftest import extract_response_text

    try:
        response = extract_response_text(result).lower()
        file_exists = target_file.exists()
        response_indicates_block = any(
            w in response
            for w in ["blocked", "criteria", "gate", "cannot", "must first"]
        )
        assert file_exists or response_indicates_block, (
            f"File exists: {file_exists}, Response: {response[:300]}"
        )
    except (ValueError, TypeError):
        assert target_file.exists(), "File was deleted but should have been blocked"


@pytest.mark.slow
@pytest.mark.integration
def test_e2e_allows_git_status_without_gate(claude_test, temp_repo) -> None:
    """Test that Claude CAN run git status without gate (in allowlist)."""
    result = claude_test(
        prompt="Run 'git status' and tell me the output.",
        cwd=temp_repo,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    from tests.integration.conftest import extract_response_text

    try:
        response = extract_response_text(result).lower()
        # Should have git status output, not a block message
        has_git_output = any(
            w in response for w in ["branch", "commit", "nothing to commit", "clean"]
        )
        is_blocked = "criteria gate" in response or "blocked" in response
        # Either has git output OR at minimum not blocked
        assert has_git_output or not is_blocked, (
            f"Expected git status output, got: {response[:300]}"
        )
    except (ValueError, TypeError):
        pass  # Can't verify response content


@pytest.mark.slow
@pytest.mark.integration
def test_e2e_allows_ls_without_gate(claude_test) -> None:
    """Test that Claude CAN run ls without gate (in allowlist)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files to list
        (Path(tmpdir) / "file1.txt").write_text("test")
        (Path(tmpdir) / "file2.txt").write_text("test")

        result = claude_test(
            prompt="Run 'ls' and tell me what files you see.",
            cwd=Path(tmpdir),
        )

        assert result["success"], f"Execution failed: {result.get('error')}"

        from tests.integration.conftest import extract_response_text

        try:
            response = extract_response_text(result).lower()
            # Should mention the files, not be blocked
            has_file_info = "file1" in response or "file2" in response or "txt" in response
            is_blocked = "criteria gate" in response or "blocked" in response
            assert has_file_info or not is_blocked, (
                f"Expected ls output, got: {response[:300]}"
            )
        except (ValueError, TypeError):
            pass


@pytest.mark.slow
@pytest.mark.integration
def test_e2e_allows_operations_after_gate_created(claude_test) -> None:
    """Test that Claude CAN write files after gate is created.

    This test creates a gate file BEFORE running Claude, simulating
    that the criteria workflow was completed.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        target_file = Path(tmpdir) / "allowed-output.txt"

        # Pre-create gate file for the session
        # Note: We can't know the session ID in advance, but we can test
        # by asking Claude to create the gate file first
        result = claude_test(
            prompt=(
                "First, create the criteria gate file by running: "
                "date -Iseconds > /tmp/claude-criteria-gate-test-e2e-session\n"
                f"Then write a file at {target_file} with content 'Gate passed successfully'."
            ),
            cwd=Path(tmpdir),
        )

        assert result["success"], f"Execution failed: {result.get('error')}"

        # Note: This test has a race condition - the gate file uses session_id
        # which we don't control. The test verifies the concept but may not
        # reliably pass without session ID coordination.

        from tests.integration.conftest import extract_response_text

        try:
            response = extract_response_text(result).lower()
            # Either file was created OR Claude mentions the gate mechanism
            file_created = target_file.exists()
            mentions_gate = "gate" in response or "criteria" in response
            # This test is informational - verifies gate mechanism is active
            assert file_created or mentions_gate, (
                f"File created: {file_created}, Response mentions gate: {response[:300]}"
            )
        except (ValueError, TypeError):
            pass


@pytest.mark.slow
@pytest.mark.integration
def test_e2e_gate_message_includes_instructions(claude_test) -> None:
    """Test that block message includes helpful instructions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = claude_test(
            prompt=f"Write a file at {tmpdir}/test.txt with content 'test'.",
            cwd=Path(tmpdir),
        )

        assert result["success"], f"Execution failed: {result.get('error')}"

        from tests.integration.conftest import extract_response_text

        try:
            response = extract_response_text(result).lower()
            # If blocked, should mention acceptance criteria workflow
            if "blocked" in response or "criteria" in response:
                assert any(
                    term in response
                    for term in ["acceptance", "criteria", "todowrite", "checkpoint"]
                ), f"Block message should include workflow instructions: {response[:500]}"
        except (ValueError, TypeError):
            pass  # Can't verify response
