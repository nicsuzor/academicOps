"""Tests for prompt router hook.

Tests the analyze_prompt() function that matches keywords to skill suggestions.
Uses motivational framing (v2) rather than imperative commands.
"""

import json
import subprocess
import sys

import pytest

from hooks.prompt_router import FRAMING_VERSION, analyze_prompt


class TestAnalyzePrompt:
    """Tests for analyze_prompt function."""

    def test_analyze_prompt_framework_keywords(self) -> None:
        """Test that framework keywords return motivational framework skill suggestion."""
        result, matched = analyze_prompt("help with framework")

        assert "framework" in result
        assert "CONTEXT AVAILABLE" in result
        assert "WHY THIS HELPS" in result
        assert matched == ["framework"]

    def test_analyze_prompt_python_keywords(self) -> None:
        """Test that python keywords return motivational python-dev skill suggestion."""
        result, matched = analyze_prompt("write python code")

        assert "python-dev" in result
        assert "CONTEXT AVAILABLE" in result
        assert matched == ["python-dev"]

    def test_analyze_prompt_no_match(self) -> None:
        """Test that unrecognized input offers Haiku classifier spawn."""
        result, matched = analyze_prompt("hello there")

        # When no keyword match, offer semantic classification via Haiku
        assert "CLASSIFIER AVAILABLE" in result
        assert "haiku" in result
        assert matched == []

    def test_analyze_prompt_multiple_matches(self) -> None:
        """Test that multiple keyword matches list all relevant skills."""
        result, matched = analyze_prompt("python framework")

        assert "python-dev" in result
        assert "framework" in result
        assert "Multiple relevant skills" in result
        assert "python-dev" in matched
        assert "framework" in matched

    def test_analyze_prompt_empty_input(self) -> None:
        """Test that empty string returns empty tuple."""
        result, matched = analyze_prompt("")

        assert result == ""
        assert matched == []

    def test_framing_version_is_v2(self) -> None:
        """Test that framing version is v2-motivational for A/B tracking."""
        assert FRAMING_VERSION == "v2-motivational"


def test_prompt_router_uses_haiku_subagent() -> None:
    """Verify prompt router provides Haiku subagent spawn instruction.

    Per spec (memory://specs/prompt-intent-router), when keywords match
    the router provides an instruction for the main agent to spawn a
    dedicated Haiku subagent for semantic intent classification.

    The implementation writes the prompt to a temp file and returns
    additionalContext with spawn instructions.
    """
    import inspect

    from hooks.prompt_router import analyze_prompt

    # Get the source code of analyze_prompt
    source = inspect.getsource(analyze_prompt)

    # The implementation should show evidence of subagent invocation
    # Look for patterns indicating Claude/subprocess/Task usage for classification
    subagent_patterns = [
        "subprocess",
        "claude",
        "haiku",
        "Task",
        "model=",
        "--model",
    ]

    has_subagent = any(pattern.lower() in source.lower() for pattern in subagent_patterns)

    assert has_subagent, (
        "analyze_prompt() uses keyword matching instead of Haiku subagent. "
        f"Found no subagent patterns in source:\n{source[:500]}..."
    )


def test_hook_script_execution_with_framework_prompt(hooks_dir) -> None:
    """Test prompt_router.py script execution via subprocess.

    Verifies that the hook script:
    - Accepts JSON input via stdin
    - Outputs valid JSON with correct structure
    - Returns framework skill suggestion for matching prompt
    - Includes framingVersion for A/B measurement
    """
    hook_script = hooks_dir / "prompt_router.py"
    input_data = json.dumps({"prompt": "help with framework"})

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
    assert "framework" in hook_output["additionalContext"]
    assert "framingVersion" in hook_output
    assert hook_output["framingVersion"] == "v2-motivational"
    assert hook_output.get("skillsMatched") == ["framework"]


