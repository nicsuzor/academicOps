"""Integration tests for deny rules blocking .claude directory access.

Consolidated from 2 tests to 1 (the other was already skipped due to design flaw).
"""

import re

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

    # --- Robust "did not silently succeed" check ---
    #
    # `assert not file_exists` below is the load-bearing security assertion.
    # This second check only guards against Claude silently succeeding (writing
    # the file via some side channel while reporting nothing). The old version
    # matched an ever-growing list of exact phrases ("denied", "blocked", ...),
    # which broke on every new Claude phrasing — a per-phrasing treadmill.
    #
    # Two correct mechanisms both block the write, and they surface DIFFERENTLY,
    # so neither alone is reliable (observed empirically across runs):
    #   1. autoMode soft_deny  -> the CLI records the blocked tool call in the
    #      structured `permission_denials` array (tool_name="Write", the
    #      .claude file_path). Prose phrasing varies. This is the cleanest
    #      signal WHEN it fires.
    #   2. real/OS-level failure (e.g. ~/.claude resolves to an unwritable
    #      path) -> `permission_denials` is EMPTY; Claude reports a
    #      "permission denied" error in prose instead.
    # Note `is_error` is False and `stop_reason` is "end_turn" in BOTH cases
    # (Claude ends its turn normally after the block), so those are NOT usable.
    #
    # Robust signal = structured denial OR a permission-family prose response.
    # A blocked Write deterministically produces a permission-related response
    # (soft_deny -> prompt family) or a deny/blocked/refused acknowledgement;
    # "permission" is the stable anchor that appeared in every observed
    # phrasing. Combined with `assert not file_exists` guarding real success,
    # this stops the treadmill while still verifying Claude acknowledged it
    # could not write.
    permission_denials = output.get("permission_denials", []) if isinstance(output, dict) else []
    write_to_claude_denied = any(
        d.get("tool_name") == "Write"
        and ".claude" in str((d.get("tool_input") or {}).get("file_path", ""))
        for d in permission_denials
    )

    deny_indicators = (
        "permission",  # soft_deny -> permission prompt/request family (stable anchor)
        "denied",
        "blocked",
        "refused",
        "not allowed",
        "not permitted",
        "cannot write",
        "cannot create",
        "cannot access",
        "restricted",
        "protected",
    )
    _deny_pattern = re.compile("|".join(r"\b" + re.escape(ind) + r"\b" for ind in deny_indicators))
    prose_indicates_denial = bool(_deny_pattern.search(response_text))

    found_denial = write_to_claude_denied or prose_indicates_denial

    from pathlib import Path

    test_file = Path.home() / ".claude" / "test-deny-rules.txt"
    file_exists = test_file.exists()

    if file_exists:
        test_file.unlink()

    assert not file_exists, f"Deny rule failed: file was created at {test_file}. Got: {output}"
    # Confirm Claude did not silently succeed: either the structured envelope
    # recorded the Write to ~/.claude as denied, or Claude's response
    # acknowledged it could not write (permission/deny family).
    assert found_denial, (
        "Expected the write to ~/.claude to be reported as blocked "
        "(via permission_denials or a permission/deny prose response). "
        f"permission_denials={permission_denials!r}; result_text={result_text!r}"
    )
