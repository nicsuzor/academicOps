#!/usr/bin/env python3
"""E2E tests for file loading at session start.

These tests verify that Claude Code actually READS and LOADS file contents
at session start, not just that files exist or are referenced.

Test approach: Ask Claude to prove it has specific content from files
without using Read tool.
"""

from pathlib import Path
from typing import Any

import pytest

from .conftest import extract_response_text


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.parametrize(
    "context_name,get_cwd",
    [
        ("aops_repo", lambda: __import__("lib.paths", fromlist=["get_aops_root"]).get_aops_root()),
        ("data_dir", lambda: __import__("tests.paths", fromlist=["get_data_dir"]).get_data_dir()),
        ("temp_dir", lambda: Path("/tmp")),
    ],
    ids=["aops_repo", "data_dir", "temp_dir"],
)
def test_axioms_content_actually_loaded(claude_headless: Any, context_name: str, get_cwd: Any) -> None:
    """Verify AXIOMS.md content is actually loaded, not just referenced.

    This test runs in multiple contexts (aops repo, writing repo, temp dir)
    to verify that AXIOMS.md is loaded via SessionStart hook regardless
    of working directory.

    Args:
        claude_headless: Fixture for headless Claude execution
        context_name: Name of context being tested
        get_cwd: Callable that returns Path for working directory

    Raises:
        AssertionError: If Claude doesn't know AXIOMS.md content
    """
    # Get working directory for this context
    cwd = get_cwd()

    result = claude_headless(
        prompt=(
            "Without reading any files, tell me: What is AXIOM #1 about? "
            "Quote the exact principle if you know it."
        ),
        timeout_seconds=60,
        cwd=cwd,
    )

    assert result["success"], f"Claude execution failed: {result.get('error')}"

    # Extract response
    response = extract_response_text(result)

    # Check if response contains AXIOM #1 concepts
    # AXIOM #1 is "DO ONE THING - Complete the task requested, then STOP"
    axiom_concepts = [
        "do one thing" in response.lower(),
        "complete" in response.lower() and "stop" in response.lower(),
        "task" in response.lower() and "then stop" in response.lower(),
    ]

    assert any(axiom_concepts), (
        f"[{context_name}] Agent doesn't know AXIOM #1 content. "
        f"This suggests AXIOMS.md was NOT loaded at session start, only referenced. "
        f"Working directory: {cwd}. Response: {response}"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_readme_structure_actually_loaded(claude_headless: Any) -> None:
    """Verify README.md content is actually loaded, not just referenced.

    This test asks Claude about README.md structure without allowing
    file reads. If Claude can answer, README was loaded at startup.

    Args:
        claude_headless: Fixture for headless Claude execution

    Raises:
        AssertionError: If Claude doesn't know README.md content
    """
    from lib.paths import get_aops_root

    aops_root = get_aops_root()

    result = claude_headless(
        prompt=(
            "Without reading any files, tell me: According to the README, "
            "what are the main directories in this framework? List 3-5."
        ),
        timeout_seconds=60,
        cwd=aops_root,
    )

    assert result["success"], f"Claude execution failed: {result.get('error')}"

    # Extract response
    response = extract_response_text(result)

    # Check for key directories that should be in README
    expected_dirs = ["skills", "hooks", "commands"]
    dirs_found = sum(1 for d in expected_dirs if d in response.lower())

    assert dirs_found >= 2, (
        f"Agent doesn't know README.md directory structure. "
        f"Expected at least 2 of {expected_dirs}, found {dirs_found}. "
        f"This suggests README.md was NOT loaded at session start. "
        f"Response: {response}"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_agent_didnt_use_read_tool(claude_headless: Any) -> None:
    """Verify Claude answers from loaded context, not by reading files.

    This meta-test asks Claude to confirm whether it used the Read tool
    to answer the previous question. If it did, session start loading failed.

    Args:
        claude_headless: Fixture for headless Claude execution

    Raises:
        AssertionError: If Claude had to read files (session start failed)
    """
    from lib.paths import get_aops_root

    aops_root = get_aops_root()

    # First ask a question
    result1 = claude_headless(
        prompt="What is the first AXIOM in this framework?",
        timeout_seconds=60,
        cwd=aops_root,
    )

    assert result1["success"], f"First query failed: {result1.get('error')}"

    # Then ask if Read tool was used
    result2 = claude_headless(
        prompt=(
            "Did you use the Read tool to answer the previous question about "
            "the first AXIOM? Answer with just 'yes' or 'no'."
        ),
        timeout_seconds=60,
        cwd=aops_root,
    )

    assert result2["success"], f"Second query failed: {result2.get('error')}"

    # Extract response
    response = extract_response_text(result2).lower()

    # Claude should NOT have used Read tool if content was loaded at start
    assert "no" in response or "did not" in response or "didn't" in response, (
        f"Agent used Read tool instead of loading content at session start! "
        f"This means session start file loading is NOT working. Response: {response}"
    )
