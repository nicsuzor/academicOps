#!/usr/bin/env python3
"""Cross-platform end-to-end tests for Claude Code and Gemini CLI.

Consolidated from 8 tests to 2 essential smoke tests (1 per CLI).
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("cross_platform_e2e"),
]


def test_simple_math_cross_platform(cli_headless) -> None:
    """Smoke test: both CLIs execute simple prompts and return structured JSON."""
    runner, platform = cli_headless

    result = runner("What is 2+2? Reply with just the number.")

    assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"
    assert "output" in result, f"[{platform}] Result should have output"
    assert result["result"], f"[{platform}] Result should have parsed JSON"
