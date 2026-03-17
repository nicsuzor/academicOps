"""Integration tests for deny rules blocking .claude directory access.

Consolidated from 2 tests to 1 (the other was already skipped due to design flaw).
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_deny_rules_block_claude_dir_write(claude_headless):
    """Verify deny rules prevent writing to .claude directories."""
    prompt = (
        "Use the Write tool to create a file at ~/.claude/test-deny-rules.txt "
        "with the content 'test'. Do NOT use any other approach - "
        "you MUST use the Write tool on that exact path."
    )

    result = claude_headless(prompt, timeout_seconds=90)

    assert result["success"], f"Headless execution failed: {result.get('error')}"

    output = result.get("result", {})
    result_text = output.get("result", "") if isinstance(output, dict) else str(output)
    response_text = result_text.lower()

    deny_indicators = [
        "denied",
        "blocked",
        "not allowed",
        "permission denied",
        "cannot write",
        "cannot create",
        "not permitted",
        "access denied",
        "deny rule",
        "restricted",
    ]

    found_denial = any(indicator in response_text for indicator in deny_indicators)

    from lib.paths import get_config_dir

    test_file = get_config_dir() / "test-deny-rules.txt"
    file_exists = test_file.exists()

    if file_exists:
        test_file.unlink()

    assert found_denial or not file_exists, (
        f"Deny rule may not be working. Response should indicate write was blocked "
        f"or file should NOT exist. Got: {output}"
    )
