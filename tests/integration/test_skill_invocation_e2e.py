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


@pytest.mark.integration
@pytest.mark.slow
def test_tasks_prompt_invokes_skill(claude_headless_tracked, skill_was_invoked) -> None:
    """Test that 'show me my tasks' invokes the tasks skill.

    Pain point: Users ask about tasks but agent doesn't invoke skill.
    Expected: Prompt router keyword 'tasks' triggers skill suggestion,
    and agent invokes Skill("tasks") or similar.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "show me my tasks",
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"Session file not found for {session_id}"

    # Check if any task-related skill/tool was invoked
    # Accept: Skill("task"), mcp__task_manager__*, or Bash with task scripts
    task_invoked = (
        skill_was_invoked(tool_calls, "task")
        or any(c["name"].startswith("mcp__task") for c in tool_calls)
        or any(
            c["name"] == "Bash" and "task" in str(c["input"]).lower()
            for c in tool_calls
        )
    )

    assert task_invoked, (
        f"Tasks skill NOT invoked. Tool calls: {[c['name'] for c in tool_calls]}"
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
    """Test that bmem-related prompts invoke the bmem skill.

    Pain point: Users ask to save knowledge but agent calls MCP tools directly
    without loading skill formatting guidance first.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "search my knowledge base for information about prompt routing",
        timeout_seconds=120,  # bmem semantic search needs more time than keyword matching
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"Session file not found for {session_id}"

    # For bmem, check either skill invocation OR direct MCP tool usage
    # (MCP tools are acceptable for read operations)
    bmem_used = (
        skill_was_invoked(tool_calls, "bmem")
        or any(c["name"].startswith("mcp__bmem__") for c in tool_calls)
    )

    assert bmem_used, (
        f"bmem skill/tools NOT invoked. Tool calls: {[c['name'] for c in tool_calls]}"
    )
