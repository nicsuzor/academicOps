#!/usr/bin/env python3
"""Session start content validation tests.

Validates that session start files (CLAUDE.md + @-referenced files) exist,
are properly structured, and load correctly in Claude headless mode.

Test categories:
- Tests 1-6: Unit-style tests (fast, no Claude execution)
- Tests 7-8: Integration tests (slow, require Claude execution)

Running tests:
- Unit tests only: pytest tests/integration/test_session_start_content.py -m "integration and not slow"
- All tests (including slow): pytest tests/integration/test_session_start_content.py -m "integration"
- Slow integration tests only: pytest tests/integration/test_session_start_content.py -m "slow"

Note: Tests in integration/ directory are auto-marked as 'integration' by conftest.py.
The default pytest configuration excludes both 'integration' and 'slow' markers.
"""

import re
from pathlib import Path
from typing import Any

import pytest


def test_claude_md_exists(writing_root: Path) -> None:
    """Test 1: Verify CLAUDE.md exists and is readable.

    Args:
        writing_root: Path to repository root (from fixture)

    Raises:
        AssertionError: If CLAUDE.md does not exist or is not readable
    """
    claude_md = writing_root / "CLAUDE.md"

    assert claude_md.exists(), f"CLAUDE.md not found at {claude_md}"
    assert claude_md.is_file(), f"CLAUDE.md is not a file: {claude_md}"

    # Verify file is readable by attempting to read it
    try:
        content = claude_md.read_text(encoding="utf-8")
        assert len(content) > 0, "CLAUDE.md is empty"
    except Exception as e:
        msg = f"CLAUDE.md is not readable: {e}"
        raise AssertionError(msg) from e


def _extract_at_references(markdown_content: str) -> list[str]:
    """Extract @-references from markdown content.

    Looks for lines starting with "- @" followed by a path.

    Args:
        markdown_content: Markdown file content

    Returns:
        List of referenced file paths (relative paths as written)
    """
    # Match lines like "- @README.md" or "- @bots/CORE.md"
    # Pattern: line starts with "- @" followed by non-whitespace characters
    pattern = r"^- @(\S+)"
    return re.findall(pattern, markdown_content, re.MULTILINE)


# Removed test_all_referenced_files_exist - CLAUDE.md structure is project-specific
# Per user decision: "CLAUDE.md structure varies by project, so framework should only
# test that the _information_ was loaded properly, not CLAUDE.md structure"
# This test was checking @-reference syntax, not information loading behavior


def test_readme_contains_directory_structure(writing_root: Path) -> None:
    """Test 3: Verify README.md contains directory structure documentation.

    Args:
        writing_root: Path to framework root (from fixture)

    Raises:
        AssertionError: If README.md is missing expected directory structure content
    """
    readme = writing_root / "README.md"
    content = readme.read_text(encoding="utf-8")

    # Check for key framework directories (not heading - tree content matters)
    required_dirs = ["skills/", "hooks/", "commands/"]
    missing_dirs = []
    for dir_name in required_dirs:
        if dir_name not in content:
            missing_dirs.append(dir_name)

    if missing_dirs:
        error_msg = f"README.md missing directory references: {', '.join(missing_dirs)}"
        raise AssertionError(error_msg)


def test_bots_directory_structure_exists(bots_dir: Path) -> None:
    """Test 4: Verify framework directory structure exists.

    Args:
        bots_dir: Path to framework root (from fixture - legacy alias)

    Raises:
        AssertionError: If expected framework subdirectories do not exist
    """
    required_subdirs = ["hooks", "commands", "skills", "config", "lib"]
    missing_dirs = []

    for subdir_name in required_subdirs:
        subdir = bots_dir / subdir_name
        if not subdir.exists():
            missing_dirs.append(str(subdir))

    if missing_dirs:
        error_msg = "Missing framework subdirectories:\n" + "\n".join(
            f"  - {d}" for d in missing_dirs
        )
        raise AssertionError(error_msg)


def test_no_conflicting_path_references(writing_root: Path, data_dir: Path) -> None:
    """Test 5: Verify session start files have consistent path references.

    Checks that session start files don't contain conflicting path references
    that could confuse agents.

    Args:
        writing_root: Path to framework root (from fixture)
        data_dir: Path to user data directory (from fixture)

    Raises:
        AssertionError: If conflicting path references are found
    """
    session_files = [
        writing_root / "CLAUDE.md",
        writing_root / "README.md",
        data_dir / "CORE.md",
        data_dir / "ACCOMMODATIONS.md",
    ]

    # Check each file exists before processing
    for file_path in session_files:
        if not file_path.exists():
            msg = f"Session start file missing: {file_path}"
            raise AssertionError(msg)

    # Look for potential conflicting task location references
    # This is a basic check - can be expanded based on specific concerns
    issues = []
    for file_path in session_files:
        content = file_path.read_text(encoding="utf-8")

        # Check for references to task storage/location that don't point to data/tasks/
        if "task" in content.lower():
            # Look for patterns like "task location", "task storage", "task file"
            task_location_pattern = re.compile(
                r"task\s+(location|storage|file)", re.IGNORECASE
            )
            matches = task_location_pattern.findall(content)

            if matches and "data/tasks/" not in content:
                issues.append(
                    f"{file_path.name}: Contains task location references but doesn't mention data/tasks/"
                )

    if issues:
        error_msg = "Potential conflicting path references:\n" + "\n".join(
            f"  - {i}" for i in issues
        )
        raise AssertionError(error_msg)


@pytest.mark.slow
@pytest.mark.integration
def test_session_start_content_loaded(claude_headless: Any, writing_root: Path) -> None:
    """Test 7: Use claude_headless to verify agent knows user info without file reading.

    This integration test verifies that session start content is properly loaded
    by asking Claude about user information that should be available from CLAUDE.md
    and its @-referenced files.

    Args:
        claude_headless: Fixture for headless Claude execution
        writing_root: Path to repository root (from fixture)

    Raises:
        AssertionError: If Claude doesn't know expected user information
    """
    result = claude_headless(
        prompt="What is my name and email address? Answer concisely.",
        timeout_seconds=60,
        cwd=writing_root,
    )

    assert result["success"], f"Claude execution failed: {result.get('error')}"

    # Extract response text from result
    # Claude Code returns nested dict with actual response in result["result"]
    result_data = result.get("result", {})
    if isinstance(result_data, dict):
        response_content = result_data.get("result", "")
    else:
        response_content = result_data

    # Look for expected user information
    # Should mention Nic/Nicolas Suzor and at least one email
    name_found = (
        "Nic" in response_content
        or "Nicolas" in response_content
        or "Suzor" in response_content
    )
    email_found = (
        "n.suzor@qut.edu.au" in response_content
        or "nic@suzor.net" in response_content
        or "@qut.edu.au" in response_content
        or "@suzor.net" in response_content
    )

    assert name_found, f"Agent doesn't know user's name. Response: {response_content}"
    assert email_found, f"Agent doesn't know user's email. Response: {response_content}"


@pytest.mark.slow
@pytest.mark.integration
def test_session_knows_work_style(claude_headless: Any, writing_root: Path) -> None:
    """Test 8: Use claude_headless to verify agent knows work principles without file reading.

    This integration test verifies that session start content includes work
    principles by asking Claude about core axioms that should be loaded from
    session start files.

    Args:
        claude_headless: Fixture for headless Claude execution
        writing_root: Path to repository root (from fixture)

    Raises:
        AssertionError: If Claude doesn't know expected work principles
    """
    result = claude_headless(
        prompt="What are my core work principles or axioms? Answer concisely.",
        timeout_seconds=60,
        cwd=writing_root,
    )

    assert result["success"], f"Claude execution failed: {result.get('error')}"

    # Extract response text
    # Claude Code returns nested dict with actual response in result["result"]
    result_data = result.get("result", {})
    if isinstance(result_data, dict):
        response_content = result_data.get("result", "")
    else:
        response_content = result_data

    # Look for expected principles - should mention fail-fast or AXIOMS concepts
    principles_found = (
        "fail-fast" in response_content.lower()
        or "fail fast" in response_content.lower()
        or "axiom" in response_content.lower()
        or "no defaults" in response_content.lower()
        or "explicit" in response_content.lower()
    )

    assert (
        principles_found
    ), f"Agent doesn't know work principles. Response: {response_content}"
