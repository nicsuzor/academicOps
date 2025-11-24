"""Tests for prompt router hook.

Tests the analyze_prompt() function that matches keywords to skill suggestions.
"""

import json
import subprocess
import sys

import pytest

from hooks.prompt_router import analyze_prompt


class TestAnalyzePrompt:
    """Tests for analyze_prompt function."""

    def test_analyze_prompt_framework_keywords(self) -> None:
        """Test that framework keywords return framework skill suggestion."""
        result = analyze_prompt("help with framework")

        assert "framework" in result
        assert "SKILL SUGGESTION" in result

    def test_analyze_prompt_python_keywords(self) -> None:
        """Test that python keywords return python-dev skill suggestion."""
        result = analyze_prompt("write python code")

        assert "python-dev" in result
        assert "SKILL SUGGESTION" in result

    def test_analyze_prompt_no_match(self) -> None:
        """Test that unrecognized input returns empty string."""
        result = analyze_prompt("hello there")

        assert result == ""

    def test_analyze_prompt_multiple_matches(self) -> None:
        """Test that multiple keyword matches mention multiple skills."""
        result = analyze_prompt("python framework")

        assert "python-dev" in result
        assert "framework" in result
        assert "multiple skills" in result

    def test_analyze_prompt_empty_input(self) -> None:
        """Test that empty string returns empty string."""
        result = analyze_prompt("")

        assert result == ""


@pytest.mark.xfail(
    reason="Current implementation uses keyword matching, not Haiku subagent - "
    "spec requires merged intent+skills classifier via dedicated Haiku subagent"
)
def test_prompt_router_uses_haiku_subagent() -> None:
    """Verify prompt router spawns Haiku subagent for intent classification.

    Per spec (memory://specs/prompt-intent-router), the router should:
    1. Spawn a dedicated Haiku subagent
    2. Perform merged intent + skills classification
    3. Return semantic analysis, not just keyword matches

    This test should FAIL until we implement the Haiku subagent.
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
    assert "additionalContext" in output["hookSpecificOutput"]
    assert "framework" in output["hookSpecificOutput"]["additionalContext"]
