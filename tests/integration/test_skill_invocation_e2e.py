#!/usr/bin/env python3
"""End-to-end tests for skill invocation via prompt router.

Tests that prompts matching keywords result in actual Skill tool invocation.
Uses session ID tracking to parse JSONL tool traces for DIRECT verification.

Pain points from learning logs:
1. "show me my tasks" → tasks skill not invoked
2. Framework file editing → framework skill not invoked
3. bmem queries → bmem skill bypassed
"""

import pytest

# Disable parallel execution for these tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("skill_invocation_e2e"),
]


def _used_task_tools(tool_calls: list) -> bool:
    """Check if task-related tools were used (Skill or MCP)."""
    for call in tool_calls:
        name = call.get("name", "")
        # Accept either Skill("tasks") or direct MCP task tools
        if name == "Skill" and "task" in str(call.get("input", {})).lower():
            return True
        if name.startswith("mcp__task_manager__"):
            return True
    return False


def _used_bmem_tools(tool_calls: list) -> bool:
    """Check if bmem-related tools were used (Skill or MCP)."""
    for call in tool_calls:
        name = call.get("name", "")
        # Accept either Skill("bmem") or direct MCP bmem tools
        if name == "Skill" and "bmem" in str(call.get("input", {})).lower():
            return True
        if name.startswith("mcp__bmem__"):
            return True
    return False


@pytest.mark.integration
@pytest.mark.slow
def test_tasks_prompt_invokes_skill(claude_headless_tracked, skill_was_invoked) -> None:
    """Test that 'show me my tasks' uses task management tools.

    Agent can either invoke the tasks skill OR use MCP task tools directly.
    Both are valid approaches for task management.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "show me my tasks",
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"Session file not found for {session_id}"

    # Accept Skill invocation OR direct MCP tool usage
    task_tools_used = _used_task_tools(tool_calls) or skill_was_invoked(tool_calls, "task")

    assert task_tools_used, (
        f"No task tools used. Tool calls: {[c['name'] for c in tool_calls]}"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_framework_prompt_invokes_skill(claude_headless_tracked, skill_was_invoked) -> None:
    """Test that framework-related prompts invoke the framework skill.

    Pain point: Users ask about hooks/skills but agent doesn't invoke framework skill.
    Expected: Prompt router keyword 'hook' triggers framework skill suggestion.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "explain how the prompt router hook works",
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"Session file not found for {session_id}"

    framework_invoked = skill_was_invoked(tool_calls, "framework")

    assert framework_invoked, (
        f"Framework skill NOT invoked. Tool calls: {[c['name'] for c in tool_calls]}"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_bmem_prompt_invokes_skill(claude_headless_tracked, skill_was_invoked) -> None:
    """Test that bmem-related prompts use bmem tools.

    Agent can either invoke the bmem skill OR use MCP bmem tools directly.
    Both are valid approaches for knowledge base queries.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "search my knowledge base for information about prompt routing",
        timeout_seconds=120,  # bmem semantic search needs more time than keyword matching
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"Session file not found for {session_id}"

    # Accept Skill invocation OR direct MCP tool usage
    bmem_tools_used = _used_bmem_tools(tool_calls) or skill_was_invoked(tool_calls, "bmem")

    assert bmem_tools_used, (
        f"No bmem tools used. Tool calls: {[c['name'] for c in tool_calls]}"
    )
