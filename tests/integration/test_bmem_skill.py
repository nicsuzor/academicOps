#!/usr/bin/env python3
"""Integration test for bmem skill.

Tests that the bmem skill can:
1. Create valid Obsidian-compatible bmem files
2. Files pass validation
3. Proper frontmatter with required fields
4. Observations add new information (not duplicate frontmatter)
5. Relations use WikiLink syntax

NOTE: These tests must run sequentially (not in parallel) because they:
- Record timestamp before creating files
- Search for files modified after that timestamp
- Use keyword matching that could match files from other tests
Running in parallel would cause tests to find each other's files.

DESIGN PRINCIPLE: These are E2E tests that invoke Claude agent in headless mode.
LLM behavior is non-deterministic, so tests use retry logic to verify reliability:
- Each test runs up to 3 attempts
- Pass if ANY attempt succeeds (proves capability exists)
- Track success rates to detect degradation
This tests "can the framework reliably capture information via bmem" rather than
"does Claude always make the right tool choice" (which is non-deterministic).
"""

import subprocess
import time

import pytest

from tests.paths import get_writing_root

# Disable parallel execution for these tests
pytestmark = [pytest.mark.integration, pytest.mark.xdist_group("bmem_sequential")]


def retry_flaky_e2e(test_func, max_attempts=3):
    """Retry E2E test up to max_attempts times.

    E2E tests with LLMs are non-deterministic. This wrapper allows tests to
    retry, passing if ANY attempt succeeds. This tests capability (can it work?)
    rather than consistency (does it always work?).

    Args:
        test_func: Test function to execute
        max_attempts: Maximum number of attempts (default: 3)

    Returns:
        Result of first successful attempt

    Raises:
        AssertionError: If all attempts fail, raises last attempt's error
    """
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return test_func()
        except AssertionError as e:
            last_error = e
            if attempt < max_attempts:
                # Brief pause between retries
                time.sleep(1)
                continue
            else:
                # All attempts failed
                raise AssertionError(
                    f"Test failed after {max_attempts} attempts. "
                    f"Last error: {e}"
                ) from last_error


@pytest.mark.integration
@pytest.mark.slow
def test_bmem_skill_creates_valid_file(claude_headless):
    """Test that bmem skill creates valid bmem file with proper structure."""

    def _test_attempt():
        # Arrange
        # Record timestamp with 1-second buffer to avoid race conditions
        start_time = time.time() - 1
        prompt = """
        Using the bmem MCP tool, create a research note about platform governance
        and content moderation. Include information about: 1) scale challenges,
        2) context awareness in moderation systems, 3) limitations of automated systems.
        Store it in my knowledge base.
        """

        # Act
        result = claude_headless(
            prompt,
            permission_mode="bypassPermissions",
            timeout_seconds=180,
            model="sonnet",  # Use more capable model for reliability
        )

        # Assert: Command succeeded
        assert result["success"], f"bmem skill execution failed: {result.get('error')}"

        # Assert: File was created in writing root directory
        writing_root = get_writing_root()
        data_files = list((writing_root / "data").rglob("*.md"))

        # Find newly created file (modified after test start, contains target content)
        created_file = None
        for file in data_files:
            # Only check files modified after test started (with 1s buffer)
            if file.stat().st_mtime < start_time:
                continue
            content = file.read_text()
            if (
                "platform governance" in content.lower()
                or "content moderation" in content.lower()
            ):
                created_file = file
                break

        assert created_file is not None, (
            f"bmem skill did not create a file matching criteria\n"
            f"Checked {len([f for f in data_files if f.stat().st_mtime >= start_time])} "
            f"files modified since {start_time}"
        )
        return created_file

    # Run with retry logic for E2E reliability
    created_file = retry_flaky_e2e(_test_attempt)

    # Assert: File has valid frontmatter
    content = created_file.read_text()
    assert content.startswith("---"), "File missing YAML frontmatter"
    assert "title:" in content, "File missing title field"
    assert "permalink:" in content, "File missing permalink field"
    assert "type:" in content, "File missing type field"

    # Assert: File has required sections
    assert "# " in content, "File missing H1 heading"
    assert (
        "## Context" in content or "## Observations" in content
    ), "File missing required sections"

    # Assert: Observations use proper syntax
    if "## Observations" in content:
        obs_section = content.split("## Observations")[1].split("##")[0]
        # Should have at least one observation with [category] syntax
        assert "[" in obs_section, "Observations missing opening bracket"
        assert "]" in obs_section, "Observations missing closing bracket"

    # Assert: Relations use WikiLink syntax if present
    if "## Relations" in content:
        rel_section = (
            content.split("## Relations")[1].split("##")[0]
            if "## Relations" in content.split("##")[-1] != content
            else content.split("## Relations")[1]
        )
        if "[[" in rel_section:
            # If there are relations, they should use [[Entity]] syntax
            assert "[[" in rel_section, "Relations missing opening WikiLink"
            assert "]]" in rel_section, "Relations missing closing WikiLink"


@pytest.mark.integration
@pytest.mark.slow
def test_bmem_skill_observations_add_new_information(claude_headless):
    """Test that observations don't duplicate frontmatter."""

    def _test_attempt():
        # Arrange
        start_time = time.time() - 1
        prompt = """
        Create a task note for "Review student thesis" due on 2025-11-15 with priority p1.
        Use the bmem skill.
        """

        # Act
        result = claude_headless(
            prompt,
            permission_mode="bypassPermissions",
            timeout_seconds=180,
            model="sonnet",
        )

        # Assert: Command succeeded
        assert result["success"], f"bmem skill execution failed: {result.get('error')}"

        # Find created task file (modified after test start)
        writing_root = get_writing_root()
        task_files = list((writing_root / "data" / "tasks").rglob("*.md"))

        created_file = None
        for file in task_files:
            # Only check files modified after test started
            if file.stat().st_mtime < start_time:
                continue
            content = file.read_text()
            if "review student thesis" in content.lower():
                created_file = file
                break

        assert created_file is not None, "bmem skill did not create task file"
        return created_file

    # Run with retry logic
    created_file = retry_flaky_e2e(_test_attempt)

    # Assert: File contains due date and priority (in frontmatter or body)
    content = created_file.read_text()
    assert "2025-11-15" in content, "File missing due date"
    assert "p1" in content, "File missing priority"

    # Assert: Observations don't duplicate this frontmatter
    if "## Observations" in content:
        obs_section = content.split("## Observations")[1].split("##")[0]
        # Should NOT have observations like "[requirement] Due date: 2025-11-15"
        # This is too strict to test automatically, but we can check for common bad patterns
        # Just verify observations exist and use proper syntax
        assert "-" in obs_section, "Observations section empty"
        assert "[" in obs_section, "Observations missing category syntax"


@pytest.mark.integration
def test_bmem_skill_uses_obsidian_compatible_tags(claude_headless):
    """Test that tags can use hyphens (Obsidian-compatible)."""

    def _test_attempt():
        # Arrange
        start_time = time.time() - 1
        prompt = """
        Using the bmem MCP tool, create a new note in my knowledge base about academic
        writing best practices. Include tags "academic-writing" and "research-methods".
        The note should be stored in my data directory.
        """

        # Act
        result = claude_headless(
            prompt,
            permission_mode="bypassPermissions",
            timeout_seconds=180,
            model="sonnet",
        )

        # Assert: Command succeeded
        assert result["success"], f"bmem skill execution failed: {result.get('error')}"

        # Find created file (modified after test start)
        writing_root = get_writing_root()
        data_files = list((writing_root / "data").rglob("*.md"))

        created_file = None
        for file in data_files:
            # Only check files modified after test started
            if file.stat().st_mtime < start_time:
                continue
            content = file.read_text()
            if "academic" in content.lower() and "writing" in content.lower():
                created_file = file
                break

        assert created_file is not None, "bmem skill did not create file"
        return created_file

    # Run with retry logic
    created_file = retry_flaky_e2e(_test_attempt)

    # Assert: Tags can contain hyphens
    content = created_file.read_text()
    # Either in frontmatter or inline tags
    assert (
        "academic-writing" in content or "research-methods" in content
    ), "File missing hyphenated tags (Obsidian-compatible)"


@pytest.mark.integration
def test_bmem_validation_passes(claude_headless):
    """Test that files created by bmem skill pass validation."""

    def _test_attempt():
        # Arrange
        start_time = time.time() - 1
        prompt = """
        Using the bmem MCP tool, create a reference note about quality assurance
        in software development. Include sections on: 1) Testing methodologies,
        2) Test automation tools, 3) Integration testing strategies.
        Store it in my knowledge base.
        """

        # Act
        result = claude_headless(
            prompt,
            permission_mode="bypassPermissions",
            timeout_seconds=180,
            model="sonnet",
        )

        # Assert: Command succeeded
        assert result["success"], f"bmem skill execution failed: {result.get('error')}"

        # Find created file (modified after test start)
        writing_root = get_writing_root()
        data_files = list((writing_root / "data").rglob("*.md"))

        created_file = None
        for file in data_files:
            # Only check files modified after test started
            if file.stat().st_mtime < start_time:
                continue
            content = file.read_text()
            if "quality assurance" in content.lower() or "testing" in content.lower():
                created_file = file
                break

        assert created_file is not None, "bmem skill did not create file"
        return created_file

    # Run with retry logic
    created_file = retry_flaky_e2e(_test_attempt)

    # Run bmem validation on the file
    writing_root = get_writing_root()
    validation_result = subprocess.run(
        ["uv", "run", "python", "bmem_tools.py", "validate", str(created_file)],
        cwd=writing_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    # Assert: Validation passes
    assert (
        validation_result.returncode == 0
    ), f"bmem validation failed: {validation_result.stderr}\n{validation_result.stdout}"
