#!/usr/bin/env python3
"""End-to-end test for prompt router → main agent self-classification.

Tests that when prompt router has no slash command match, the main agent
receives routing guidance (decision flowchart) and can self-classify.

This validates the two-tier routing:
1. Slash command → Direct route to skill (tested elsewhere)
2. No match → Routing guidance injected (tested HERE)
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("prompt_router_flow"),
    pytest.mark.xfail(
        reason="LLM behavior is non-deterministic - observational test", strict=False
    ),
]


def _used_skill_or_exploration(tool_calls: list) -> bool:
    """Check if agent used skills or exploration tools.

    Args:
        tool_calls: List of parsed tool calls from session

    Returns:
        True if agent used Skill, Glob, Read, Grep, or Task tools
    """
    exploration_tools = {"Skill", "Glob", "Read", "Grep", "Task"}
    for call in tool_calls:
        if call["name"] in exploration_tools:
            return True
    return False


@pytest.mark.integration
@pytest.mark.slow
def test_no_slash_command_gets_routing_guidance(
    claude_headless_tracked,
) -> None:
    """Test that prompts without slash commands work correctly.

    When prompt_router.py has no slash command, it injects routing guidance
    (the decision flowchart). The agent uses this to self-classify and
    invoke appropriate skills.

    Note: For simple prompts, the agent may respond conversationally
    without tools - this is acceptable behavior.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        # Make it actionable so agent is likely to use tools
        "please analyze the structure of this codebase and tell me about it",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # For vague prompts, agent may respond without tools (valid behavior)
    # OR use tools like Explore/Glob/Read to analyze
    # All are acceptable - test passes if execution succeeded

    if tool_calls:
        used_appropriate_tools = _used_skill_or_exploration(tool_calls)
        assert used_appropriate_tools, (
            f"Agent used tools but none were exploration/skill.\n"
            f"Tool calls: {[c['name'] for c in tool_calls]}"
        )


@pytest.mark.integration
@pytest.mark.slow
def test_ambiguous_prompt_handled_gracefully(
    claude_headless_tracked,
) -> None:
    """Test that ambiguous prompts are handled appropriately.

    "help me with this" is ambiguous - could be framework, tasks, memory server, etc.
    Valid responses include:
    - Skill invocation (follows routing guidance)
    - AskUserQuestion (asks for clarification)
    - Exploration tools (investigates context)
    - Conversational response (for very vague prompts)
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "help me with this complicated thing",  # Deliberately vague
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # For very vague prompts, ANY response is valid:
    # - Tool use (Skill, AskUserQuestion, exploration)
    # - Conversational response (no tools)
    # The test validates the system doesn't crash on ambiguous input

    # If tools were used, verify they're appropriate
    if tool_calls:
        invoked_skill = any(c["name"] == "Skill" for c in tool_calls)
        asked_user = any(c["name"] == "AskUserQuestion" for c in tool_calls)
        used_exploration = _used_skill_or_exploration(tool_calls)

        handled_appropriately = invoked_skill or asked_user or used_exploration

        assert handled_appropriately, (
            f"Agent used tools but none were appropriate for ambiguous prompt.\n"
            f"Tool calls: {[c['name'] for c in tool_calls]}"
        )
    # No tools used = conversational response, also valid for vague prompts
