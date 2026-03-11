"""Integration tests for Claude Code headless execution fixture.

Tests verify that the claude_headless pytest fixture correctly:
- Executes Claude Code in headless mode
- Returns properly structured JSON output

Consolidated from 8 tests to 1 essential smoke test.
"""

import json

import pytest


@pytest.mark.slow
@pytest.mark.integration
def test_claude_headless_simple_prompt(claude_headless) -> None:
    """Smoke test: headless fixture executes and returns structured JSON."""
    result = claude_headless("What is 2+2?")

    assert isinstance(result, dict), "Result should be a dictionary"
    assert result["success"], f"Execution failed: {result.get('error')}"
    assert "output" in result, "Result should have 'output' key"
    assert "result" in result, "Result should have 'result' key"

    output_data = json.loads(result["output"])
    assert isinstance(output_data, dict | list), "Output should be parseable as JSON"
