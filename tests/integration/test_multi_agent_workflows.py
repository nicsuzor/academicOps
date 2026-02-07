#!/usr/bin/env python3
"""End-to-end tests for multi-agent workflows.

Tests that the Task tool correctly spawns subagents and that orchestration
patterns work as expected. This validates the core multi-agent infrastructure.

Key patterns tested:
1. Task tool successfully spawns subagent
2. Subagent returns results to parent agent
3. Multiple parallel subagents work
"""

import pytest

from tests.conftest import count_task_calls, extract_task_calls

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("multi_agent"),
]


def _task_tool_used(tool_calls: list) -> bool:
    """Check if Task tool was used to spawn a subagent."""
    return len(extract_task_calls(tool_calls)) > 0


@pytest.mark.integration
@pytest.mark.slow
def test_explore_agent_spawns_successfully(claude_headless_tracked) -> None:
    """Test that Explore agent can be spawned via Task tool.

    The Explore agent is commonly used for codebase exploration.
    This tests the basic multi-agent infrastructure works.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "Use the Explore agent to find all Python files in the hooks directory",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Verify Task tool was used with Explore subagent
    task_used = _task_tool_used(tool_calls)

    if not task_used:
        tool_names = [c["name"] for c in tool_calls]
        pytest.fail(
            f"Task tool NOT used for Explore agent.\n"
            f"Expected: Task(subagent_type='Explore')\n"
            f"Actual tool calls: {tool_names}\n"
            f"This indicates multi-agent spawn is broken."
        )


@pytest.mark.integration
@pytest.mark.slow
def test_general_purpose_agent_spawns(claude_headless_tracked) -> None:
    """Test that general-purpose agent can be spawned.

    The general-purpose agent type is used for various tasks.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "Use the Task tool to spawn a general-purpose agent that searches for "
        "'def main' in the hooks directory",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Verify Task tool was used
    task_used = _task_tool_used(tool_calls)

    if not task_used:
        tool_names = [c["name"] for c in tool_calls]
        pytest.fail(
            f"Task tool NOT used for general-purpose agent.\n"
            f"Expected: Task(subagent_type='general-purpose')\n"
            f"Actual tool calls: {tool_names}"
        )


@pytest.mark.integration
@pytest.mark.slow
def test_python_dev_skill_invoked_for_code_task(claude_headless_tracked) -> None:
    """Test that python-dev skill is invoked for code-related tasks.

    For Python development, we use general-purpose subagent with python-dev skill.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "Use the Task tool with subagent_type='general-purpose' to analyze the code "
        "structure of hooks/prompt_router.py. The subagent should invoke "
        "Skill(skill='python-dev') first.",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Verify Task tool was used (with general-purpose agent)
    task_used = _task_tool_used(tool_calls)

    if not task_used:
        tool_names = [c["name"] for c in tool_calls]
        pytest.fail(
            f"Task tool NOT used for code task.\n"
            f"Expected: Task(subagent_type='general-purpose')\n"
            f"Actual tool calls: {tool_names}"
        )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skip(reason="Plan agent is heavy - times out frequently, test separately")
def test_plan_agent_spawns(claude_headless_tracked) -> None:
    """Test that Plan agent can be spawned for planning tasks.

    The Plan agent is used for designing implementation plans.
    Note: Plan agent often times out due to complexity - marked skip.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "Use the Task tool to spawn a Plan agent to design how we would "
        "add a new hook for logging",
        timeout_seconds=300,  # Plan agent needs more time
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Verify Task tool was used
    task_used = _task_tool_used(tool_calls)

    if not task_used:
        tool_names = [c["name"] for c in tool_calls]
        pytest.fail(
            f"Task tool NOT used for Plan agent.\n"
            f"Expected: Task(subagent_type='Plan')\n"
            f"Actual tool calls: {tool_names}"
        )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skip(reason="Parallel agent spawn is advanced - test separately")
def test_parallel_agent_spawn(claude_headless_tracked) -> None:
    """Test that multiple agents can be spawned in parallel.

    When multiple independent tasks are requested, the parent agent should
    spawn multiple subagents in a single message.

    Note: This is a more advanced pattern that may not always work.
    Marking as skip for now - enable when investigating parallel issues.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "Spawn TWO agents in parallel using the Task tool: "
        "1. An Explore agent to find all .py files in hooks/ "
        "2. An Explore agent to find all .md files in skills/",
        timeout_seconds=240,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Count Task tool calls - should be at least 2 for parallel
    task_count = count_task_calls(tool_calls)

    if task_count < 2:
        tool_names = [c["name"] for c in tool_calls]
        pytest.fail(
            f"Expected at least 2 Task tool calls for parallel spawn.\n"
            f"Actual Task calls: {task_count}\n"
            f"All tool calls: {tool_names}"
        )
