#!/usr/bin/env python3
"""Tests for custodiet hook output format.

Verifies that the custodiet hook uses the correct output format:
- Threshold reached: hookSpecificOutput.additionalContext (NOT decision/reason)
- additionalContext contains custodiet instruction wrapped in system-reminder tags
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary state directory for tests."""
    state_dir = tmp_path / "claude-compliance"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def mock_templates():
    """Mock template files with minimal content."""
    context_template = "Audit context. Session: {session_context}. Tool: {tool_name}"
    instruction_template = "Read {temp_path} and check compliance."
    return context_template, instruction_template


def test_threshold_reached_uses_hookspecificoutput_format(temp_state_dir, mock_templates):
    """Test that threshold trigger uses hookSpecificOutput.additionalContext format.

    When tool_count reaches TOOL_CALL_THRESHOLD, the hook should output:
    {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "<system-reminder>\n{instruction}\n</system-reminder>"
        }
    }

    NOT the decision/reason format used for errors.
    """
    # Import after patching TEMP_DIR to avoid state file conflicts
    import sys
    from io import StringIO

    # Patch TEMP_DIR and template files
    with patch("hooks.custodiet.TEMP_DIR", temp_state_dir), \
         patch("hooks.custodiet.load_template") as mock_load_template, \
         patch("hooks.custodiet.extract_router_context", return_value="Test session context"):

        mock_load_template.side_effect = mock_templates

        # Import main after patching
        from hooks.custodiet import main, TOOL_CALL_THRESHOLD

        # Setup: Create state with tool_count = TOOL_CALL_THRESHOLD - 1
        # So next tool call will reach threshold
        cwd = "/test/project"
        from hooks.custodiet import get_state_file
        state_file = get_state_file(cwd)
        state_file.parent.mkdir(parents=True, exist_ok=True)

        initial_state = {
            "cwd": cwd,
            "tool_count": TOOL_CALL_THRESHOLD - 1,  # One away from threshold
            "last_check_ts": 0.0,
        }
        state_file.write_text(json.dumps(initial_state))

        # Prepare input: Bash tool (counts toward threshold)
        input_data = {
            "cwd": cwd,
            "transcript_path": "/tmp/test-session.jsonl",
            "tool_name": "Bash",
        }

        # Mock stdin with input_data
        mock_stdin = StringIO(json.dumps(input_data))

        # Capture stdout
        mock_stdout = StringIO()

        with patch("sys.stdin", mock_stdin), \
             patch("sys.stdout", mock_stdout):

            # Run hook
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify exit code is 0 (success)
            assert exc_info.value.code == 0

            # Parse output
            output_json = mock_stdout.getvalue()
            output = json.loads(output_json)

            # Verify output structure
            assert "hookSpecificOutput" in output, \
                "Output should use hookSpecificOutput format, not decision/reason"

            hook_output = output["hookSpecificOutput"]
            assert hook_output["hookEventName"] == "PostToolUse"
            assert "additionalContext" in hook_output

            # Verify additionalContext contains system-reminder tags
            additional_context = hook_output["additionalContext"]
            assert additional_context.startswith("<system-reminder>\n")
            assert additional_context.endswith("\n</system-reminder>")

            # Verify it contains the instruction (not just the tags)
            assert "Read" in additional_context  # From instruction template
            assert "check compliance" in additional_context

            # Verify state was reset
            updated_state = json.loads(state_file.read_text())
            assert updated_state["tool_count"] == 0, \
                "tool_count should be reset to 0 after threshold reached"


def test_skip_tools_dont_count_toward_threshold(temp_state_dir):
    """Test that Read, Glob, Grep tools don't increment tool_count."""
    from io import StringIO

    with patch("hooks.custodiet.TEMP_DIR", temp_state_dir):
        from hooks.custodiet import main, get_state_file

        cwd = "/test/project"
        state_file = get_state_file(cwd)
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Start with fresh state
        initial_state = {
            "cwd": cwd,
            "tool_count": 0,
            "last_check_ts": 0.0,
        }
        state_file.write_text(json.dumps(initial_state))

        # Test skip tools
        skip_tools = ["Read", "Glob", "Grep", "mcp__memory__retrieve_memory"]

        for tool in skip_tools:
            input_data = {
                "cwd": cwd,
                "tool_name": tool,
            }

            mock_stdin = StringIO(json.dumps(input_data))
            mock_stdout = StringIO()

            with patch("sys.stdin", mock_stdin), \
                 patch("sys.stdout", mock_stdout):

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0

                # Verify output is empty dict
                output = json.loads(mock_stdout.getvalue())
                assert output == {}

                # Verify tool_count unchanged
                state = json.loads(state_file.read_text())
                assert state["tool_count"] == 0, \
                    f"{tool} should not increment tool_count"


def test_counting_tools_increment_toward_threshold(temp_state_dir):
    """Test that normal tools (Bash, Edit, etc.) increment tool_count."""
    from io import StringIO

    with patch("hooks.custodiet.TEMP_DIR", temp_state_dir):
        from hooks.custodiet import main, get_state_file

        cwd = "/test/project"
        state_file = get_state_file(cwd)
        state_file.parent.mkdir(parents=True, exist_ok=True)

        initial_state = {
            "cwd": cwd,
            "tool_count": 0,
            "last_check_ts": 0.0,
        }
        state_file.write_text(json.dumps(initial_state))

        # Call with Bash tool (should count)
        input_data = {
            "cwd": cwd,
            "tool_name": "Bash",
        }

        mock_stdin = StringIO(json.dumps(input_data))
        mock_stdout = StringIO()

        with patch("sys.stdin", mock_stdin), \
             patch("sys.stdout", mock_stdout):

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

            # Verify tool_count incremented
            state = json.loads(state_file.read_text())
            assert state["tool_count"] == 1, \
                "Bash tool should increment tool_count"


def test_infrastructure_error_returns_decision_reason_format(temp_state_dir):
    """Test that infrastructure errors use decision/reason format and exit 1.

    This is the ONLY case where decision/reason should be used - for fail-fast errors.
    """
    from io import StringIO

    with patch("hooks.custodiet.TEMP_DIR", temp_state_dir), \
         patch("hooks.custodiet.load_template") as mock_load_template:

        # Make template loading fail (infrastructure error)
        mock_load_template.side_effect = FileNotFoundError("Template missing")

        from hooks.custodiet import main, TOOL_CALL_THRESHOLD, get_state_file

        cwd = "/test/project"
        state_file = get_state_file(cwd)
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Set state to trigger threshold
        initial_state = {
            "cwd": cwd,
            "tool_count": TOOL_CALL_THRESHOLD - 1,
            "last_check_ts": 0.0,
        }
        state_file.write_text(json.dumps(initial_state))

        input_data = {
            "cwd": cwd,
            "tool_name": "Bash",
        }

        mock_stdin = StringIO(json.dumps(input_data))
        mock_stdout = StringIO()

        with patch("sys.stdin", mock_stdin), \
             patch("sys.stdout", mock_stdout):

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify exit code is 1 (failure)
            assert exc_info.value.code == 1

            # Verify output uses decision/reason format for errors
            output = json.loads(mock_stdout.getvalue())
            assert "decision" in output
            assert output["decision"] == "block"
            assert "reason" in output
            assert "infrastructure error" in output["reason"].lower()


def test_random_reminder_uses_hookspecificoutput_format(temp_state_dir, mock_templates):
    """Test that random reminders also use hookSpecificOutput.additionalContext format."""
    from io import StringIO

    with patch("hooks.custodiet.TEMP_DIR", temp_state_dir), \
         patch("hooks.custodiet.get_random_reminder", return_value="Test reminder message"):

        from hooks.custodiet import main, get_state_file

        cwd = "/test/project"
        state_file = get_state_file(cwd)
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # State below threshold
        initial_state = {
            "cwd": cwd,
            "tool_count": 0,
            "last_check_ts": 0.0,
        }
        state_file.write_text(json.dumps(initial_state))

        input_data = {
            "cwd": cwd,
            "tool_name": "Bash",
        }

        mock_stdin = StringIO(json.dumps(input_data))
        mock_stdout = StringIO()

        with patch("sys.stdin", mock_stdin), \
             patch("sys.stdout", mock_stdout):

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

            output = json.loads(mock_stdout.getvalue())

            # Should use hookSpecificOutput format for reminders too
            assert "hookSpecificOutput" in output
            hook_output = output["hookSpecificOutput"]
            assert hook_output["hookEventName"] == "PostToolUse"
            assert "additionalContext" in hook_output

            additional_context = hook_output["additionalContext"]
            assert additional_context.startswith("<system-reminder>\n")
            assert "Test reminder message" in additional_context
            assert additional_context.endswith("\n</system-reminder>")
