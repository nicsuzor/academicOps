#!/usr/bin/env python3
"""E2E test for Gemini MCP tool.

Verifies that mcp__gemini__ask-gemini works correctly when invoked
via Claude Code, matching how the framework uses it in session-insights.
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("gemini_mcp"),
]


def _gemini_mcp_was_called(tool_calls: list) -> bool:
    """Check if Gemini MCP tool was invoked.

    Args:
        tool_calls: List of parsed tool calls from session

    Returns:
        True if mcp__gemini__ask-gemini was called
    """
    for call in tool_calls:
        if call["name"] == "mcp__gemini__ask-gemini":
            return True
    return False


@pytest.mark.integration
@pytest.mark.slow
def test_gemini_mcp_simple_query(claude_headless_tracked) -> None:
    """Test that Gemini MCP can answer a simple factual question.

    This matches how the framework invokes Gemini via mcp__gemini__ask-gemini
    in the session-insights skill for transcript analysis.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        'Use the mcp__gemini__ask-gemini tool to answer: "What is the largest planet in our solar system?"',
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Verify Gemini MCP was called
    assert _gemini_mcp_was_called(tool_calls), (
        f"Expected mcp__gemini__ask-gemini to be invoked. "
        f"Tool calls: {[c['name'] for c in tool_calls]}"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_gemini_mcp_returns_response(claude_headless_tracked) -> None:
    """Test that Gemini MCP returns a meaningful response.

    Verifies end-to-end that the response contains expected content.
    """
    result, session_id, tool_calls = claude_headless_tracked(
        'Use the mcp__gemini__ask-gemini tool with prompt "What element has atomic number 79?" and tell me the answer.',
        timeout_seconds=120,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"

    # Verify Gemini was called
    assert _gemini_mcp_was_called(
        tool_calls
    ), f"Gemini MCP not invoked. Tools used: {[c['name'] for c in tool_calls]}"

    # Check response contains expected answer (gold) in raw output
    output_lower = result.get("output", "").lower()
    assert (
        "gold" in output_lower or "au" in output_lower
    ), f"Expected response to mention 'gold' or 'Au'. Output: {result.get('output', '')[:500]}"
