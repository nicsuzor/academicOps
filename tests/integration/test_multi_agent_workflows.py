#!/usr/bin/env python3
"""End-to-end tests for multi-agent workflows.

Consolidated from 5 tests to 1 essential test.
Tests that the Task tool correctly spawns subagents.
"""

import pytest

from tests.conftest import extract_task_calls

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.integration,
    pytest.mark.xdist_group("multi_agent"),
]


@pytest.mark.integration
@pytest.mark.slow
def test_explore_agent_spawns_successfully(claude_headless_tracked) -> None:
    """Test that Explore agent can be spawned via Task tool."""
    result, session_id, tool_calls = claude_headless_tracked(
        "Use the Explore agent to find all Python files in the hooks directory",
        timeout_seconds=180,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert tool_calls, f"No tool calls recorded for session {session_id}"

    task_calls = extract_task_calls(tool_calls)
    assert len(task_calls) > 0, (
        f"Task tool NOT used for Explore agent.\n"
        f"Actual tool calls: {[c['name'] for c in tool_calls]}"
    )
