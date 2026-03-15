import pytest

from tests.conftest import check_blocked


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

    result = runner(instruction, model=model)

    assert result["success"], f"CLI execution failed: {result.get('error')}"

    if expected_behavior == "blocked":
        is_blocked = check_blocked(result)

        assert is_blocked, (
            f"Expected {gate} gate to block, but no block message found. Platform: {platform}"
        )


@pytest.mark.integration
@pytest.mark.slow
def test_gate_lifecycle_e2e(cli_headless):
    """Full gate lifecycle: blocked before hydration, allowed after.

    Verifies the hydration gate enforces the full cycle:
    1. Gate CLOSED — shell tool calls are blocked/warned before hydration.
    2. Gate OPEN — shell tool calls succeed once hydration is bypassed.

    The '.' prefix is the user-ignore shortcut that signals no hydration is
    needed (post-hydration follow-up), keeping the gate in its initial OPEN
    state so the agent's Bash call is not intercepted.
    """
    runner, platform = cli_headless
    model = "gemini-2.0-flash" if platform == "gemini" else "haiku"

    # Step 1: Unhyrated prompt — gate closes, shell call is blocked/warned.
    result_blocked = runner("Run shell command: ls /etc/hosts", model=model)
    assert result_blocked["success"], f"CLI execution failed: {result_blocked.get('error')}"
    assert check_blocked(result_blocked), (
        f"Expected hydration gate to block before hydration. Platform: {platform}"
    )

    # Step 2: Post-hydration prompt — '.' prefix skips the hydration trigger so
    # the gate stays OPEN and the Bash call proceeds without any gate message.
    result_allowed = runner(". Run shell command: ls /etc/hosts", model=model)
    assert result_allowed["success"], f"CLI execution failed: {result_allowed.get('error')}"
    assert not check_blocked(result_allowed), (
        f"Expected gate to allow shell calls after hydration. Platform: {platform}"
    )
