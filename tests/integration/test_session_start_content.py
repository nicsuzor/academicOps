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

from .conftest import extract_response_text


def test_claude_md_exists(aops_root: Path) -> None:
    """Test 1: Verify CLAUDE.md exists and is readable.

    Args:
        aops_root: Path to repository root (from fixture)

    Raises:
        AssertionError: If CLAUDE.md does not exist or is not readable
    """
    claude_md = aops_root / "CLAUDE.md"

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
    # Match lines like "- @README.md" or "- @skills/README.md"
    # Pattern: line starts with "- @" followed by non-whitespace characters
    pattern = r"^- @(\S+)"
    return re.findall(pattern, markdown_content, re.MULTILINE)


# Removed test_all_referenced_files_exist - CLAUDE.md structure is project-specific
# Per user decision: "CLAUDE.md structure varies by project, so framework should only
# test that the _information_ was loaded properly, not CLAUDE.md structure"
# This test was checking @-reference syntax, not information loading behavior


def test_readme_contains_directory_structure(aops_root: Path) -> None:
    """Test 3: Verify README.md contains directory structure documentation.

    Args:
        aops_root: Path to framework root (from fixture)

    Raises:
        AssertionError: If README.md is missing expected directory structure content
    """
    readme = aops_root / "README.md"
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


def test_no_conflicting_path_references(aops_root: Path, data_dir: Path) -> None:
    """Test 5: Verify session start files have consistent path references.

    Checks that session start files don't contain conflicting path references
    that could confuse agents.

    Args:
        aops_root: Path to framework root (from fixture)
        data_dir: Path to user data directory (from fixture)

    Raises:
        AssertionError: If conflicting path references are found
    """
    session_files = [
        aops_root / "CLAUDE.md",
        aops_root / "README.md",
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
@pytest.mark.parametrize("test_location", ["aops_repo", "temp_dir"])
def test_session_start_content_loaded(
    claude_headless: Any, aops_root: Path, tmp_path: Path, test_location: str
) -> None:
    """Test 7: Use claude_headless to verify SessionStart hooks inject AXIOMS.

    This integration test verifies that SessionStart hooks work from any directory
    by asking Claude about AXIOMS content that should be injected via hooks.

    Tests two scenarios:
    1. Claude runs from $AOPS (framework repo)
    2. Claude runs from /tmp (arbitrary directory)

    Args:
        claude_headless: Fixture for headless Claude execution
        aops_root: Path to framework root (from fixture)
        tmp_path: Temporary directory (pytest fixture)
        test_location: Parametrized test location (aops_repo or temp_dir)

    Raises:
        AssertionError: If Claude doesn't know AXIOMS content loaded via hooks
    """
    # Select working directory based on test parameter
    cwd = aops_root if test_location == "aops_repo" else tmp_path

    result = claude_headless(
        prompt="What is AXIOM #1? Answer concisely.",
        timeout_seconds=60,
        cwd=cwd,
    )

    assert result["success"], f"Claude execution failed: {result.get('error')}"

    # Extract response text from result
    response_content = extract_response_text(result)

    # Look for AXIOM #1 content: "DO ONE THING"
    axiom_found = (
        "DO ONE THING" in response_content
        or "Complete the task requested" in response_content
        or "then STOP" in response_content
    )

    assert axiom_found, (
        f"Agent doesn't know AXIOM #1 content. "
        f"SessionStart hooks may not be executing from {cwd}. "
        f"Response: {response_content}"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_session_knows_work_style(claude_headless: Any, aops_root: Path) -> None:
    """Test 8: Use claude_headless to verify agent knows AXIOMS principles.

    This integration test verifies that SessionStart hooks inject AXIOMS
    by asking Claude about core principles.

    Args:
        claude_headless: Fixture for headless Claude execution
        aops_root: Path to framework root (from fixture)

    Raises:
        AssertionError: If Claude doesn't know AXIOMS principles
    """
    result = claude_headless(
        prompt="What are the core AXIOMS principles? Answer concisely.",
        timeout_seconds=60,
        cwd=aops_root,
    )

    assert result["success"], f"Claude execution failed: {result.get('error')}"

    # Extract response text
    response_content = extract_response_text(result)

    # Look for expected AXIOMS principles
    principles_found = (
        "fail-fast" in response_content.lower()
        or "fail fast" in response_content.lower()
        or "DO ONE THING" in response_content
        or "no defaults" in response_content.lower()
        or "DRY" in response_content
    )

    assert (
        principles_found
    ), f"Agent doesn't know AXIOMS principles. Response: {response_content}"
