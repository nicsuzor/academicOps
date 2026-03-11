import json

import pytest


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize(
    "gate, instruction, expected_behavior",
    [
        ("hydration", "Run shell command: ls /etc/hosts", "blocked"),
    ],
)
def test_gate_enforcement_e2e(cli_headless, gate, instruction, expected_behavior):
    """E2E test for gate enforcement using real CLI agents."""
    runner, platform = cli_headless

    model = "gemini-2.0-flash" if platform == "gemini" else "haiku"

    if platform == "gemini" and expected_behavior == "blocked":
        pytest.xfail(
            "Gemini CLI hooks (PreToolUse) not triggering for native tools in headless mode (known gap)"
        )

    result = runner(instruction, model=model)

    assert result["success"], f"CLI execution failed: {result.get('error')}"

    output_text = json.dumps(result["result"])

    if expected_behavior == "blocked":
        block_indicators = [
            "Hydration Required",
            "This session is not hydrated",
            "Access Denied",
            "Gate Blocked",
            "BLOCKED",
        ]

        is_blocked = any(indicator in output_text for indicator in block_indicators)

        if not is_blocked:
            is_blocked = "block" in output_text.lower() or "denied" in output_text.lower()

        assert is_blocked, (
            f"Expected {gate} gate to block, but no block message found. Platform: {platform}"
        )
