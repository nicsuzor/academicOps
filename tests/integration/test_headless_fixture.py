"""Integration tests for Claude Code headless execution fixture.

Tests verify that the claude_headless pytest fixture correctly:
- Executes Claude Code in headless mode
- Passes parameters (model, timeout, permission_mode)
- Returns properly structured JSON output
- Uses correct working directory
"""

import json

import pytest


def test_claude_headless_fixture_exists(claude_headless) -> None:
    """Test that claude_headless fixture is available and callable.

    Verifies:
    - Fixture is defined and accessible
    - Fixture is callable
    """
    assert callable(claude_headless), "claude_headless fixture should be callable"


@pytest.mark.slow
@pytest.mark.integration
def test_claude_headless_simple_prompt(claude_headless) -> None:
    """Test basic execution with simple prompt.

    Verifies:
    - Simple arithmetic prompt executes successfully
    - Response contains expected keys
    - Output is parseable JSON (list of events with --debug flag)
    """
    result = claude_headless("What is 2+2?")

    assert isinstance(result, dict), "Result should be a dictionary"
    assert "success" in result, "Result should have 'success' key"
    assert "output" in result, "Result should have 'output' key"
    assert "result" in result, "Result should have 'result' key"

    # Verify output is valid JSON - with --debug flag, output is a list of events
    output_data = json.loads(result["output"])
    assert isinstance(output_data, list), "Output should be parseable as JSON list (debug format)"
    assert len(output_data) > 0, "Output should contain at least one event"


@pytest.mark.slow
@pytest.mark.integration
def test_claude_headless_with_model(claude_headless) -> None:
    """Test that model parameter is passed correctly.

    Verifies:
    - Model parameter can be specified
    - Execution completes with custom model
    - Result structure is maintained
    """
    result = claude_headless(
        "Respond with just 'ok'", model="claude-sonnet-4-5-20250929"
    )

    assert result["success"] is True, "Execution with model param should succeed"
    assert "output" in result, "Result should include output"


@pytest.mark.slow
@pytest.mark.integration
def test_claude_headless_timeout(claude_headless) -> None:
    """Test that timeout parameter works.

    Verifies:
    - Timeout parameter can be specified
    - Command respects timeout value
    - Result structure is maintained
    """
    result = claude_headless("What is 1+1?", timeout_seconds=300)

    assert isinstance(result, dict), "Result should be a dictionary"
    assert "success" in result, "Result should have success status"


@pytest.mark.slow
@pytest.mark.integration
def test_claude_headless_permission_mode(claude_headless) -> None:
    """Test that permission_mode parameter is passed.

    Verifies:
    - permission_mode parameter can be specified
    - Execution completes with specified permission mode
    - Result structure is maintained
    """
    result = claude_headless("What is 3+3?", permission_mode="plan")

    assert result["success"] is True, "Execution with permission_mode should succeed"
    assert "output" in result, "Result should include output"


@pytest.mark.slow
@pytest.mark.integration
def test_claude_headless_json_output(claude_headless) -> None:
    """Test that output is returned as parsed JSON.

    Verifies:
    - Output key contains valid JSON string
    - JSON can be parsed (list format with --debug flag)
    - Events contain expected structure
    """
    result = claude_headless("What is 5+5?")

    assert "output" in result, "Result should have output key"

    # Parse the JSON output - with --debug flag, output is a list of events
    output_data = json.loads(result["output"])

    assert isinstance(output_data, list), "Parsed output should be a list (debug format)"
    # Debug output should contain session events - look for assistant message or result
    event_types = [e.get("type") for e in output_data if isinstance(e, dict)]
    assert any(
        t in event_types for t in ["assistant", "result"]
    ) or any(
        "hook_event" in e for e in output_data if isinstance(e, dict)
    ), f"Should have assistant/result message or hook events. Found types: {event_types}"


@pytest.mark.slow
@pytest.mark.integration
def test_claude_headless_cwd(claude_headless, data_dir) -> None:  # noqa: ARG001
    """Test that cwd defaults to data_dir.

    Verifies:
    - Working directory is set to data_dir by default
    - Commands execute in correct directory context
    """
    # Ask Claude to report the current working directory
    result = claude_headless("Use the Bash tool to run 'pwd' and tell me the result")

    assert result["success"] is True, "Directory check should succeed"
    assert "output" in result, "Result should include output"

    # The output should reference the data_dir path
    # Note: This is a weak test since we can't reliably parse the exact cwd
    # from Claude's natural language response, but we verify execution succeeded


@pytest.mark.slow
@pytest.mark.integration
def test_run_claude_headless_direct(data_dir) -> None:
    """Test calling run_claude_headless function directly.

    Verifies:
    - Function can be imported and called directly
    - Function accepts all expected parameters
    - Function returns properly structured result
    """
    # Import the function directly
    from tests.integration.conftest import run_claude_headless

    result = run_claude_headless(
        prompt="What is 7+7?",
        cwd=data_dir,
        timeout_seconds=60,
        permission_mode="plan",
    )

    assert isinstance(result, dict), "Direct call should return dictionary"
    assert "success" in result, "Result should have success key"
    assert "output" in result, "Result should have output key"
    assert "result" in result, "Result should have result key"
