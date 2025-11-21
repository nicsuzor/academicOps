"""Integration tests for deny rules blocking .claude directory access.

Tests verify that deny rules in settings.json correctly:
- Block Read tool access to ~/.claude/ directories
- Prevent agents from reading/modifying framework settings
- Force use of $AOPS paths for framework configuration

The deny rules tested:
- Read(**/.claude/**)
- Write(**/.claude/**)
- Edit(**/.claude/**)
"""

import pytest

pytestmark = [pytest.mark.integration]


def test_deny_rules_block_claude_dir_read(claude_headless):
    """Verify deny rules prevent reading from .claude directories.

    The framework settings at $AOPS/config/claude/settings.json contain:
    - Read(**/.claude/**)
    - Write(**/.claude/**)
    - Edit(**/.claude/**)

    These rules should block access to ~/.claude/ forcing use of $AOPS paths.
    """
    # Ask Claude to read from ~/.claude/ - should be denied
    prompt = (
        "Use the Read tool to read the file at ~/.claude/settings.json "
        "and tell me what permissions are configured. "
        "Do NOT use any other approach - you MUST use the Read tool on that exact path."
    )

    result = claude_headless(prompt, timeout_seconds=90)

    # The command should succeed (Claude responded)
    assert result["success"], f"Headless execution failed: {result.get('error')}"

    # Get the response text
    output = result.get("result", {})

    # The response should indicate the read was blocked/denied
    # Claude's response when a tool is blocked by deny rules typically includes
    # phrases like "denied", "blocked", "not allowed", "permission", or "cannot access"
    response_text = str(output).lower()

    # Check for indicators that the read was blocked
    deny_indicators = [
        "denied",
        "blocked",
        "not allowed",
        "permission denied",
        "cannot access",
        "cannot read",
        "not permitted",
        "access denied",
        "deny rule",
        "restricted",
    ]

    found_denial = any(indicator in response_text for indicator in deny_indicators)

    # Also check that the response does NOT contain actual settings content
    # (which would indicate the read succeeded when it shouldn't have)
    settings_content_indicators = [
        "allowedtools",
        "denytools",
        "permissions",
        '"read"',
        '"write"',
        '"edit"',
    ]

    contains_settings_content = any(
        indicator in response_text for indicator in settings_content_indicators
    )

    assert found_denial or not contains_settings_content, (
        f"Deny rule may not be working. Response should indicate read was blocked "
        f"or should NOT contain settings file content. Got: {output}"
    )


def test_deny_rules_block_claude_dir_write(claude_headless):
    """Verify deny rules prevent writing to .claude directories.

    Tests that Write tool access to ~/.claude/ is blocked by deny rules.
    """
    # Ask Claude to write to ~/.claude/ - should be denied
    prompt = (
        "Use the Write tool to create a file at ~/.claude/test-deny-rules.txt "
        "with the content 'test'. Do NOT use any other approach - "
        "you MUST use the Write tool on that exact path."
    )

    result = claude_headless(prompt, timeout_seconds=90)

    # The command should succeed (Claude responded)
    assert result["success"], f"Headless execution failed: {result.get('error')}"

    # Get the response text
    output = result.get("result", {})
    response_text = str(output).lower()

    # Check for indicators that the write was blocked
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

    # Also check the file was NOT created
    from pathlib import Path

    test_file = Path.home() / ".claude" / "test-deny-rules.txt"
    file_exists = test_file.exists()

    # Clean up if file was somehow created
    if file_exists:
        test_file.unlink()

    assert found_denial or not file_exists, (
        f"Deny rule may not be working. Response should indicate write was blocked "
        f"or file should NOT exist. Got: {output}"
    )
