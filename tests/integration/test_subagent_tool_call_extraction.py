#!/usr/bin/env python3
"""Tests for subagent tool call extraction helper.

Tests the extract_subagent_tool_calls() function from conftest.py
to ensure clean test assertions for subagent behavior.
"""

from tests.conftest import extract_subagent_tool_calls


def test_extract_subagent_tool_calls_empty_list():
    """Test extraction from empty tool call list."""
    tool_calls = []
    result = extract_subagent_tool_calls(tool_calls)
    assert result == []


def test_extract_subagent_tool_calls_no_skill_invocations():
    """Test extraction when no Skill tools are invoked."""
    tool_calls = [
        {"name": "Read", "input": {"file_path": "/path/to/file"}},
        {"name": "Bash", "input": {"command": "ls -la"}},
        {"name": "Write", "input": {"file_path": "/path/to/file", "content": "text"}},
    ]
    result = extract_subagent_tool_calls(tool_calls)
    assert result == []


def test_extract_subagent_tool_calls_single_skill():
    """Test extraction with a single Skill invocation."""
    tool_calls = [
        {"name": "Read", "input": {"file_path": "/path/to/file"}},
        {
            "name": "Skill",
            "input": {"skill": "framework", "args": "some-argument"},
        },
        {"name": "Bash", "input": {"command": "ls -la"}},
    ]
    result = extract_subagent_tool_calls(tool_calls)

    assert len(result) == 1
    assert result[0]["name"] == "framework"
    assert result[0]["args"] == "some-argument"
    assert result[0]["index"] == 1
    assert "input" in result[0]


def test_extract_subagent_tool_calls_multiple_skills():
    """Test extraction with multiple Skill invocations."""
    tool_calls = [
        {"name": "Read", "input": {"file_path": "/path/to/file"}},
        {
            "name": "Skill",
            "input": {"skill": "framework", "args": "arg1"},
        },
        {"name": "Bash", "input": {"command": "ls -la"}},
        {
            "name": "Skill",
            "input": {"skill": "learn", "args": "arg2"},
        },
        {
            "name": "Skill",
            "input": {"skill": "audit", "args": "arg3"},
        },
    ]
    result = extract_subagent_tool_calls(tool_calls)

    assert len(result) == 3
    assert result[0]["name"] == "framework"
    assert result[0]["index"] == 1
    assert result[1]["name"] == "learn"
    assert result[1]["index"] == 3
    assert result[2]["name"] == "audit"
    assert result[2]["index"] == 4


def test_extract_subagent_tool_calls_malformed_skill():
    """Test extraction skips malformed Skill invocations."""
    tool_calls = [
        # Skill without skill parameter
        {
            "name": "Skill",
            "input": {"args": "something"},
        },
        # Valid skill
        {
            "name": "Skill",
            "input": {"skill": "framework", "args": "arg1"},
        },
        # Skill with empty skill name
        {
            "name": "Skill",
            "input": {"skill": "", "args": "arg2"},
        },
    ]
    result = extract_subagent_tool_calls(tool_calls)

    # Only the valid skill should be extracted
    assert len(result) == 1
    assert result[0]["name"] == "framework"


def test_extract_subagent_tool_calls_no_args():
    """Test extraction when Skill has no args parameter."""
    tool_calls = [
        {
            "name": "Skill",
            "input": {"skill": "framework"},
        },
    ]
    result = extract_subagent_tool_calls(tool_calls)

    assert len(result) == 1
    assert result[0]["name"] == "framework"
    assert result[0]["args"] == ""


def test_extract_subagent_tool_calls_preserves_input():
    """Test that full input dict is preserved for further inspection."""
    tool_calls = [
        {
            "name": "Skill",
            "input": {
                "skill": "pdf",
                "args": "-m 'test message'",
                "extra_param": "extra_value",
            },
        },
    ]
    result = extract_subagent_tool_calls(tool_calls)

    assert len(result) == 1
    assert result[0]["input"]["skill"] == "pdf"
    assert result[0]["input"]["args"] == "-m 'test message'"
    assert result[0]["input"]["extra_param"] == "extra_value"


def test_extract_subagent_tool_calls_with_fixture(extract_subagent_calls):
    """Test the pytest fixture wrapper works correctly."""
    tool_calls = [
        {
            "name": "Skill",
            "input": {"skill": "framework", "args": "audit-task"},
        },
        {
            "name": "Skill",
            "input": {"skill": "learn", "args": "experiment-1"},
        },
    ]
    result = extract_subagent_calls(tool_calls)

    assert len(result) == 2
    framework_calls = [c for c in result if c["name"] == "framework"]
    learn_calls = [c for c in result if c["name"] == "learn"]

    assert len(framework_calls) == 1
    assert len(learn_calls) == 1
    assert framework_calls[0]["args"] == "audit-task"
    assert learn_calls[0]["args"] == "experiment-1"


def test_extract_subagent_tool_calls_realistic_pattern(extract_subagent_calls):
    """Test extraction with realistic tool call sequence from session."""
    # This mimics a realistic pattern from a session where main agent
    # makes several tool calls and invokes skills
    tool_calls = [
        {"name": "Read", "input": {"file_path": "/home/user/writing/test.md"}},
        {"name": "Bash", "input": {"command": "find . -name '*.py'"}},
        {
            "name": "Skill",
            "input": {"skill": "audit", "args": "framework-governance"},
        },
        {"name": "Bash", "input": {"command": "git status"}},
        {
            "name": "Skill",
            "input": {"skill": "framework", "args": "enforce-hooks"},
        },
        {"name": "Write", "input": {"file_path": "/path/to/file", "content": "data"}},
    ]
    subagent_calls = extract_subagent_calls(tool_calls)

    assert len(subagent_calls) == 2
    assert subagent_calls[0]["name"] == "audit"
    assert subagent_calls[0]["index"] == 2
    assert subagent_calls[1]["name"] == "framework"
    assert subagent_calls[1]["index"] == 4
