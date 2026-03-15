#!/usr/bin/env python3
"""E2E test for Gemini MCP tool.

Consolidated from 2 tests to 1 essential test.
Verifies that mcp__gemini__ask-gemini works correctly when invoked
via Claude Code.
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.requires_local_env,
    pytest.mark.xdist_group("gemini_mcp"),
]


def _gemini_mcp_was_called(tool_calls: list) -> bool:
    """Check if Gemini MCP tool was invoked."""
    return any(call["name"] == "mcp__gemini__ask-gemini" for call in tool_calls)


@pytest.mark.integration
@pytest.mark.slow
def test_gemini_mcp_simple_query(claude_headless_tracked) -> None:
    """Test that Gemini MCP can answer a simple factual question."""
    result, session_id, tool_calls = claude_headless_tracked(
        'Use the mcp__gemini__ask-gemini tool to answer: "What is the largest planet in our solar system?"',
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    assert _gemini_mcp_was_called(tool_calls), (
        f"Expected mcp__gemini__ask-gemini to be invoked. "
        f"Tool calls: {[c['name'] for c in tool_calls]}"
    )
