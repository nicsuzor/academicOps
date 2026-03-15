import pytest


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_local_env
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
        from tests.conftest import check_blocked

        is_blocked = check_blocked(result)

        assert is_blocked, (
            f"Expected {gate} gate to block, but no block message found. Platform: {platform}"
        )
