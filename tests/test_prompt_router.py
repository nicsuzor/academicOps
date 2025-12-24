"""Tests for prompt router hook.

Tests the analyze_prompt() function that routes to capabilities.
v4: LLM-first - only slash commands get direct routing, everything else → LLM classifier.
"""

import json
import subprocess
import sys

import pytest

from hooks.prompt_router import (
    FRAMING_VERSION,
    analyze_prompt,
    detect_diagnostic_prompt,
    get_command_names,
    load_capabilities_text,
)


class TestAnalyzePrompt:
    """Tests for analyze_prompt function."""

    def test_slash_command_direct_route(self) -> None:
        """Test that explicit slash commands get direct routing."""
        result, matched = analyze_prompt("/meta show status")

        assert "meta" in result
        assert 'Skill(skill="meta")' in result
        assert matched == ["/meta"]

    def test_slash_command_unknown(self) -> None:
        """Test that unknown slash commands go to LLM classifier."""
        result, matched = analyze_prompt("/unknowncommand")

        # Unknown command → LLM classifier
        assert "intent-router" in result
        assert matched == []

    def test_no_slash_command_goes_to_llm(self) -> None:
        """Test that non-slash prompts go to LLM classifier."""
        result, matched = analyze_prompt("help with framework")

        # No direct keyword match anymore - goes to LLM
        assert "intent-router" in result
        assert "academic environment" in result
        assert matched == []

    def test_python_prompt_goes_to_llm(self) -> None:
        """Test that python prompts go to LLM classifier (no keyword matching)."""
        result, matched = analyze_prompt("write python code")

        # No direct keyword match - goes to LLM
        assert "intent-router" in result
        assert matched == []

    def test_empty_input(self) -> None:
        """Test that empty string returns empty tuple."""
        result, matched = analyze_prompt("")

        assert result == ""
        assert matched == []

    def test_framing_version_is_v4(self) -> None:
        """Test that framing version is v4-llm-first for A/B tracking."""
        assert FRAMING_VERSION == "v4-llm-first"

    def test_capabilities_file_has_sections(self) -> None:
        """Test that capabilities file has expected sections."""
        content = load_capabilities_text()
        assert "## Skills" in content
        assert "## Commands" in content
        assert "## Agents" in content
        assert "## MCP" in content

    def test_command_names_extracted(self) -> None:
        """Test that key commands are extracted from capabilities file."""
        commands = get_command_names()
        assert "meta" in commands
        assert "email" in commands
        assert "log" in commands


class TestDiagnosticPromptDetection:
    """Tests for detect_diagnostic_prompt function.

    Implements Layer 2 of verification-enforcement-gates.md spec.
    """

    @pytest.mark.parametrize(
        "prompt,expected",
        [
            # Positive cases - error indicator + investigation pattern
            ("why isn't the hook working?", True),
            ("fix this error please", True),
            ("debug the failing test", True),
            ("what's wrong with the output?", True),
            ("the build is broken, help", True),
            ("there's a bug in the parser", True),
            ("the test is not working", True),
            ("I have an issue with the config", True),
            ("there's a problem with authentication", True),
            ("figure out why the error occurs", True),
            # Negative cases - no error indicator
            ("check if we should use async", False),
            ("look into design options", False),
            ("investigate the architecture", False),
            ("help me write python code", False),
            ("convert this to PDF", False),
            ("remember my preferences", False),
            ("what is machine learning?", False),
            ("create a new task", False),
        ],
    )
    def test_detect_diagnostic_prompt(self, prompt: str, expected: bool) -> None:
        """Test that diagnostic prompts are correctly detected."""
        result = detect_diagnostic_prompt(prompt)
        assert result == expected, f"Expected {expected} for: {prompt}"

    def test_error_indicator_required(self) -> None:
        """Test that prompts without error indicators are not flagged."""
        # These have investigation words but no error indicator
        assert not detect_diagnostic_prompt("check if the server is ready")
        assert not detect_diagnostic_prompt("verify the configuration")
        assert not detect_diagnostic_prompt("is the service running")

    def test_error_indicator_alone_triggers(self) -> None:
        """Test that error indicator alone is sufficient."""
        # Has error indicator, triggers even without specific pattern
        assert detect_diagnostic_prompt("there's an error in this code")
        assert detect_diagnostic_prompt("this has a bug somewhere")
        assert detect_diagnostic_prompt("something is wrong here")


def test_prompt_router_uses_intent_router_agent() -> None:
    """Verify prompt router provides intent-router agent spawn instruction.

    When no slash command matches, the router provides an instruction for the
    main agent to spawn the intent-router agent for semantic classification.
    """
    import inspect

    from hooks.prompt_router import analyze_prompt

    source = inspect.getsource(analyze_prompt)

    assert "intent-router" in source, (
        "analyze_prompt() should reference intent-router agent for classification."
    )


def test_hook_script_execution_with_slash_command(hooks_dir) -> None:
    """Test prompt_router.py script execution via subprocess.

    Verifies that the hook script:
    - Accepts JSON input via stdin
    - Outputs valid JSON with correct structure
    - Returns direct routing for slash commands
    - Includes framingVersion for A/B measurement
    """
    hook_script = hooks_dir / "prompt_router.py"
    input_data = json.dumps({"prompt": "/meta show status"})

    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_data,
        capture_output=True,
        text=True,
        check=True,
    )

    output = json.loads(result.stdout)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert "additionalContext" in hook_output
    assert "meta" in hook_output["additionalContext"]
    assert "framingVersion" in hook_output
    assert hook_output["framingVersion"] == "v4-llm-first"
    assert hook_output.get("skillsMatched") == ["/meta"]


def test_hook_script_execution_without_slash_command(hooks_dir) -> None:
    """Test that non-slash prompts go to LLM classifier."""
    hook_script = hooks_dir / "prompt_router.py"
    input_data = json.dumps({"prompt": "help with python"})

    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_data,
        capture_output=True,
        text=True,
        check=True,
    )

    output = json.loads(result.stdout)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert "additionalContext" in hook_output
    assert "intent-router" in hook_output["additionalContext"]
    # No direct match - goes to LLM
    assert hook_output.get("skillsMatched") is None


def test_hook_injects_verification_reminder_for_diagnostic_prompt(hooks_dir) -> None:
    """Test that diagnostic prompts inject VERIFICATION_REMINDER.

    Implements Layer 2 of verification-enforcement-gates.md spec.
    """
    hook_script = hooks_dir / "prompt_router.py"
    input_data = json.dumps({"prompt": "why isn't the hook working? there's an error"})

    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_data,
        capture_output=True,
        text=True,
        check=True,
    )

    output = json.loads(result.stdout)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert "additionalContext" in hook_output

    context = hook_output["additionalContext"]
    assert "VERIFICATION PROTOCOL" in context, "Should inject verification reminder"
    assert "TodoWrite" in context, "Should include TodoWrite template"
    assert "Check actual current state" in context, "Should include checklist items"
    assert hook_output.get("diagnosticDetected") is True


def test_hook_no_verification_reminder_for_normal_prompt(hooks_dir) -> None:
    """Test that non-diagnostic prompts do NOT inject VERIFICATION_REMINDER."""
    hook_script = hooks_dir / "prompt_router.py"
    input_data = json.dumps({"prompt": "help me write python code"})

    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_data,
        capture_output=True,
        text=True,
        check=True,
    )

    output = json.loads(result.stdout)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    context = hook_output["additionalContext"]

    assert "VERIFICATION PROTOCOL" not in context, "Should NOT inject verification reminder"
    assert hook_output.get("diagnosticDetected") is False
