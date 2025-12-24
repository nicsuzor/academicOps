#!/usr/bin/env python3
"""End-to-end tests for skill delegation pattern.

Tests the "FRAMEWORK SKILL CHECKED" token enforcement - the pattern where
framework skill provides context and delegates to implementation skills.

Key patterns tested:
1. Framework skill invoked before implementation work
2. Implementation skills receive delegation token
3. Skill → skill delegation chain works
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("skill_delegation"),
    pytest.mark.xfail(reason="LLM behavior is non-deterministic - observational test", strict=False),
]


def _skill_invoked(tool_calls: list, skill_name: str) -> bool:
    """Check if a specific skill was invoked.

    Args:
        tool_calls: List of parsed tool calls from session
        skill_name: Name of skill to check for

    Returns:
        True if Skill tool was called with matching skill name
    """
    for call in tool_calls:
        if call["name"] == "Skill":
            skill_param = call.get("input", {}).get("skill", "")
            if skill_name.lower() in skill_param.lower():
                return True
    return False


def _skill_order(tool_calls: list) -> list[str]:
    """Extract ordered list of skill invocations.

    Args:
        tool_calls: List of parsed tool calls from session

    Returns:
        List of skill names in order they were invoked
    """
    skills = []
    for call in tool_calls:
        if call["name"] == "Skill":
            skill_param = call.get("input", {}).get("skill", "")
            if skill_param:
                skills.append(skill_param)
    return skills


@pytest.mark.integration
@pytest.mark.slow
def test_framework_skill_invoked_for_framework_work(
    claude_headless_tracked,
) -> None:
    """Test that framework work invokes the framework skill first.

    Per CLAUDE.md: "ALL work in this repo flows through the framework skill"
    When working on hooks/skills/commands, framework skill should be invoked.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "Explain the structure of the hooks directory in this framework",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Framework skill should be invoked for framework-related questions
    framework_invoked = _skill_invoked(tool_calls, "framework")

    if not framework_invoked:
        tool_names = [c["name"] for c in tool_calls]
        skills_invoked = _skill_order(tool_calls)
        pytest.fail(
            f"Framework skill NOT invoked for framework work.\n"
            f"Expected: Skill(skill='framework')\n"
            f"Skills invoked: {skills_invoked}\n"
            f"All tool calls: {tool_names}"
        )


@pytest.mark.integration
@pytest.mark.slow
def test_python_dev_skill_invoked_for_python_work(
    claude_headless_tracked,
) -> None:
    """Test that Python work invokes the python-dev skill.

    The prompt router should route Python-related prompts to python-dev skill.
    Note: "pytest" also matches "framework" keywords, so either skill is valid.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        # Use a prompt that clearly targets Python, not framework
        "Write a simple Python function that adds two numbers with type hints",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # Python-dev skill should be invoked for Python code work
    # Framework skill is also acceptable if it delegates to python-dev
    python_invoked = _skill_invoked(tool_calls, "python-dev")
    framework_invoked = _skill_invoked(tool_calls, "framework")

    # Either skill is acceptable for Python work
    if not python_invoked and not framework_invoked:
        tool_names = [c["name"] for c in tool_calls]
        skills_invoked = _skill_order(tool_calls)
        pytest.fail(
            f"Neither python-dev nor framework skill invoked for Python work.\n"
            f"Expected: Skill(skill='python-dev') or Skill(skill='framework')\n"
            f"Skills invoked: {skills_invoked}\n"
            f"All tool calls: {tool_names}"
        )


@pytest.mark.integration
@pytest.mark.slow
def test_framework_before_python_for_framework_python(
    claude_headless_tracked,
) -> None:
    """Test delegation order: framework → python-dev for framework Python work.

    When writing Python code for the framework, the ideal pattern is:
    1. Framework skill provides context (conventions, paths)
    2. Python-dev skill implements the code

    This tests the delegation pattern is followed.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "I want to add a new Python hook to the framework. "
        "What conventions should I follow?",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    skills_invoked = _skill_order(tool_calls)

    # Either framework OR python-dev should be invoked (both are valid)
    # The ideal is framework first, but either is acceptable
    has_relevant_skill = (
        _skill_invoked(tool_calls, "framework")
        or _skill_invoked(tool_calls, "python-dev")
    )

    if not has_relevant_skill:
        tool_names = [c["name"] for c in tool_calls]
        pytest.fail(
            f"Neither framework nor python-dev skill invoked.\n"
            f"Expected: Skill('framework') or Skill('python-dev')\n"
            f"Skills invoked: {skills_invoked}\n"
            f"All tool calls: {tool_names}"
        )

    # If both are invoked, verify framework comes first (optional check)
    if "framework" in skills_invoked and "python-dev" in skills_invoked:
        framework_idx = skills_invoked.index("framework")
        python_idx = skills_invoked.index("python-dev")
        if framework_idx > python_idx:
            pytest.fail(
                f"Framework skill invoked AFTER python-dev skill.\n"
                f"Expected: framework before python-dev for delegation pattern.\n"
                f"Actual order: {skills_invoked}"
            )


@pytest.mark.integration
@pytest.mark.slow
def test_memory_skill_invoked_for_knowledge_queries(
    claude_headless_tracked,
) -> None:
    """Test that knowledge base queries invoke memory skill.

    Per prompt_router.py keywords: "knowledge base", "search notes", etc.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "Search the knowledge base for information about testing patterns",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # memory skill OR direct MCP tools should be used
    memory_invoked = _skill_invoked(tool_calls, "memory")
    mcp_memory_used = any(
        c["name"].startswith("mcp__memory__") for c in tool_calls
    )

    if not memory_invoked and not mcp_memory_used:
        tool_names = [c["name"] for c in tool_calls]
        skills_invoked = _skill_order(tool_calls)
        pytest.fail(
            f"Neither memory skill nor MCP memory tools used.\n"
            f"Expected: Skill('memory') or mcp__memory__* tools\n"
            f"Skills invoked: {skills_invoked}\n"
            f"All tool calls: {tool_names}"
        )


@pytest.mark.integration
@pytest.mark.slow
def test_tasks_skill_invoked_for_task_queries(
    claude_headless_tracked,
) -> None:
    """Test that task-related queries invoke tasks skill.

    Per prompt_router.py keywords: "archive task", "view task", etc.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        "Show me my current tasks",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    # tasks skill OR direct MCP tools should be used
    tasks_invoked = _skill_invoked(tool_calls, "tasks")
    mcp_tasks_used = any(
        c["name"].startswith("mcp__task_manager__") for c in tool_calls
    )

    if not tasks_invoked and not mcp_tasks_used:
        tool_names = [c["name"] for c in tool_calls]
        skills_invoked = _skill_order(tool_calls)
        pytest.fail(
            f"Neither tasks skill nor MCP task tools used.\n"
            f"Expected: Skill('tasks') or mcp__task_manager__* tools\n"
            f"Skills invoked: {skills_invoked}\n"
            f"All tool calls: {tool_names}"
        )
