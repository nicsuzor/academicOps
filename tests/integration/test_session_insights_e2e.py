"""
E2E integration test for session-insights skill.

Tests that the full skill execution completes successfully and produces expected output.
Requires Claude CLI and is marked as slow.
"""

import pytest


@pytest.mark.slow
@pytest.mark.integration
def test_session_insights_skill_e2e(claude_headless) -> None:
    """Test that session-insights skill executes successfully end-to-end.

    Invokes the skill via Claude CLI and verifies:
    - Skill completes without error
    - Output mentions transcript generation
    - Output mentions daily summary
    """
    result = claude_headless(
        prompt='Skill(skill="session-insights")',
        timeout_seconds=300,  # 5 minutes - skill runs parallel agents
    )

    assert result["success"], f"Skill execution failed: {result.get('error')}"

    output = result.get("output", "")

    # Verify output mentions key artifacts
    # The skill should report on transcripts generated
    has_transcript_mention = (
        "transcript" in output.lower()
        or "generated" in output.lower()
        or "sessions/claude" in output.lower()
    )
    assert has_transcript_mention, "Output doesn't mention transcript generation"

    # The skill should mention daily summary
    has_daily_mention = (
        "daily" in output.lower() or "summary" in output.lower() or "-daily.md" in output.lower()
    )
    assert has_daily_mention, "Output doesn't mention daily summary"
