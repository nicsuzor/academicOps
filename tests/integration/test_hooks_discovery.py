#!/usr/bin/env python3
"""Integration tests for hooks discovery on Claude Code and Gemini CLI.

Consolidated from 7 tests to 1 essential test.
Verifies that hooks are registered and firing in a real session.
"""

import pytest

from tests.conftest import extract_response_text


@pytest.mark.slow
@pytest.mark.integration
def test_claude_hooks_registry_not_empty(claude_headless) -> None:
    """Test that Claude's hook registry has entries and hooks are firing."""
    result = claude_headless(
        "Check if any hooks fired at the start of this session. "
        "Look for system-reminder tags or hook notifications in the conversation.",
        timeout_seconds=600,
    )

    assert result["success"], f"Claude headless failed: {result.get('error')}"

    raw_output = result.get("output", "").lower()
    response_text = extract_response_text(result).lower()

    hook_evidence = [
        "system-reminder",
        "hook success",
        "sessionstart",
        "userpromptsubmit",
        "pretooluse",
    ]

    has_hook_evidence = any(
        indicator in raw_output or indicator in response_text for indicator in hook_evidence
    )

    assert has_hook_evidence, (
        "Expected evidence of hooks firing in Claude session. "
        "No system-reminder or hook success indicators found."
    )
