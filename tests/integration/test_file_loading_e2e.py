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

from tests.conftest import extract_response_text


@pytest.mark.slow
@pytest.mark.integration
def test_axioms_content_actually_loaded(claude_headless: Any) -> None:
    """Verify AXIOMS.md content is actually loaded, not just referenced.

    This test runs from /tmp to verify that AXIOMS.md is loaded via
    SessionStart hook regardless of working directory.

    Args:
        claude_headless: Fixture for headless Claude execution

    Raises:
        AssertionError: If Claude doesn't know AXIOMS.md content
    """
    result = claude_headless(
        prompt=(
            "Without reading any files, tell me: What is AXIOM #1 about? "
            "Quote the exact principle if you know it."
        ),
        timeout_seconds=120,
        cwd=Path("/tmp"),
    )

    assert result["success"], f"Claude execution failed: {result.get('error')}"

    # Extract response
    response = extract_response_text(result)

    # Check if response contains AXIOM #1 concepts
    # AXIOM #1 is "categorical-imperative" - universal rule, justifiable
    axiom_concepts = [
        "categorical" in response.lower(),
        "universal rule" in response.lower(),
        "justifiable" in response.lower(),
    ]

    assert any(axiom_concepts), (
        f"Agent doesn't know AXIOM #1 content. "
        f"This suggests AXIOMS.md was NOT loaded at session start, only referenced. "
        f"Response: {response}"
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
        timeout_seconds=120,
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
def test_agent_knows_axioms_without_reading(claude_headless: Any) -> None:
    """Verify Claude answers AXIOM questions from loaded context.

    This test checks that Claude can answer AXIOM questions in a single
    prompt that explicitly forbids using the Read tool, proving the
    content was loaded at session start.

    Args:
        claude_headless: Fixture for headless Claude execution

    Raises:
        AssertionError: If Claude can't answer without reading files
    """
    from lib.paths import get_aops_root

    aops_root = get_aops_root()

    # Ask about axioms with explicit instruction not to read files
    result = claude_headless(
        prompt=(
            "WITHOUT using the Read tool or any file reading, "
            "what does AXIOM #1 say? "
            "If you don't already know this from your loaded context, "
            "just say 'I don't know'."
        ),
        timeout_seconds=120,
        cwd=aops_root,
    )

    assert result["success"], f"Query failed: {result.get('error')}"

    response = extract_response_text(result).lower()

    # Claude should know AXIOM #1 content if it was loaded at session start
    # AXIOM #1 is "categorical-imperative" - universal rule, justifiable
    knows_axiom = (
        "categorical" in response
        or "universal rule" in response
        or "justifiable" in response
    )
    didnt_know = "i don't know" in response or "don't have" in response

    assert knows_axiom and not didnt_know, (
        f"Agent doesn't know AXIOM #1 content from loaded context. "
        f"Session start file loading may not be working. Response: {response}"
    )
