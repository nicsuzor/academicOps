#!/usr/bin/env python3
"""Cross-platform end-to-end tests for Claude Code and Gemini CLI.

Tests that run on both platforms using the parameterized cli_headless fixture.
Verifies basic functionality works across both AI coding assistants.
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group("cross_platform_e2e"),
]


@pytest.mark.integration
@pytest.mark.slow
def test_simple_math_cross_platform(cli_headless) -> None:
    """Test basic math question works on both platforms.

    Verifies:
    - Both CLIs can execute simple prompts
    - JSON output is parseable
    - Response is successful
    """
    runner, platform = cli_headless

    result = runner("What is 2+2? Reply with just the number.")

    assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"
    assert "output" in result, f"[{platform}] Result should have output"
    assert result["result"], f"[{platform}] Result should have parsed JSON"


@pytest.mark.integration
@pytest.mark.slow
def test_file_read_cross_platform(cli_headless) -> None:
    """Test that both platforms can read files.

    Verifies:
    - File reading works on both platforms
    - Response indicates success
    """
    runner, platform = cli_headless

    result = runner(
        "Read the file /etc/hostname and tell me what it contains. "
        "Just report the contents briefly.",
        timeout_seconds=60,
    )

    assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"


@pytest.mark.integration
@pytest.mark.slow
def test_bash_command_cross_platform(cli_headless) -> None:
    """Test that both platforms can execute bash commands.

    Verifies:
    - Bash/shell execution works on both platforms
    - Output contains expected result
    """
    runner, platform = cli_headless

    # Map permission mode per platform (Claude: bypassPermissions, Gemini: yolo)
    perm_mode = "bypassPermissions" if platform == "claude" else "yolo"

    result = runner(
        "Run the command 'echo hello' and tell me the output.",
        timeout_seconds=60,
        permission_mode=perm_mode,
    )

    assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"
    # Check that hello appears in the output
    output_lower = result.get("output", "").lower()
    assert "hello" in output_lower, f"[{platform}] Expected 'hello' in output"


@pytest.mark.integration
@pytest.mark.slow
def test_json_output_structure_cross_platform(cli_headless) -> None:
    """Test that JSON output is properly structured on both platforms.

    Verifies:
    - Both platforms return valid JSON
    - Result structure contains expected keys
    """
    runner, platform = cli_headless

    result = runner("Say 'test complete'")

    assert isinstance(result, dict), f"[{platform}] Result should be a dictionary"
    assert "success" in result, f"[{platform}] Result should have 'success' key"
    assert "output" in result, f"[{platform}] Result should have 'output' key"
    assert "result" in result, f"[{platform}] Result should have 'result' key"


# --- Platform-specific Gemini tests ---


@pytest.mark.integration
@pytest.mark.slow
def test_gemini_headless_fixture_exists(gemini_headless) -> None:
    """Test that gemini_headless fixture is available and callable."""
    assert callable(gemini_headless), "gemini_headless fixture should be callable"


@pytest.mark.integration
@pytest.mark.slow
def test_gemini_headless_simple_prompt(gemini_headless) -> None:
    """Test basic execution with simple prompt on Gemini."""
    result = gemini_headless("What is 3+3? Reply with just the number.")

    assert isinstance(result, dict), "Result should be a dictionary"
    assert "success" in result, "Result should have 'success' key"
    assert "output" in result, "Result should have 'output' key"


@pytest.mark.integration
@pytest.mark.slow
def test_gemini_headless_yolo_mode(gemini_headless) -> None:
    """Test that yolo mode works on Gemini CLI."""
    result = gemini_headless(
        "Run 'pwd' and tell me the directory",
        permission_mode="yolo",
        timeout_seconds=60,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"


@pytest.mark.integration
@pytest.mark.slow
def test_gemini_headless_with_model(gemini_headless) -> None:
    """Test that model parameter is passed correctly to Gemini."""
    result = gemini_headless(
        "Respond with just 'ok'",
        model="gemini-2.0-flash",
        timeout_seconds=60,
    )

    # May fail if model not available, but should not crash
    assert "success" in result, "Result should have success status"
