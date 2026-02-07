"""Tests for subagent tool call extraction helpers.

These helpers are defined in conftest.py and used for testing multi-agent workflows.
"""


from .conftest import (
    count_task_calls,
    extract_subagent_tool_calls,
    extract_task_calls,
    task_tool_with_type,
)


class TestExtractSubagentToolCalls:
    """Tests for extract_subagent_tool_calls helper."""

    def test_extracts_task_tool_calls(self):
        """Task tool invocations are extracted with correct type."""
        tool_calls = [
            {"name": "Read", "input": {"file_path": "/some/file.py"}},
            {
                "name": "Task",
                "input": {
                    "subagent_type": "Explore",
                    "prompt": "Find Python files",
                    "model": "haiku",
                },
            },
            {"name": "Bash", "input": {"command": "ls"}},
        ]

        result = extract_subagent_tool_calls(tool_calls)

        assert len(result) == 1
        assert result[0]["type"] == "task"
        assert result[0]["name"] == "Explore"
        assert result[0]["prompt"] == "Find Python files"
        assert result[0]["model"] == "haiku"
        assert result[0]["index"] == 1

    def test_extracts_skill_tool_calls(self):
        """Skill tool invocations are extracted with correct type."""
        tool_calls = [
            {"name": "Read", "input": {"file_path": "/some/file.py"}},
            {
                "name": "Skill",
                "input": {"skill": "framework", "args": "do something"},
            },
        ]

        result = extract_subagent_tool_calls(tool_calls)

        assert len(result) == 1
        assert result[0]["type"] == "skill"
        assert result[0]["name"] == "framework"
        assert result[0]["args"] == "do something"
        assert result[0]["index"] == 1

    def test_extracts_both_task_and_skill_calls(self):
        """Both Task and Skill invocations are extracted together."""
        tool_calls = [
            {
                "name": "Task",
                "input": {"subagent_type": "critic", "prompt": "Review this"},
            },
            {
                "name": "Skill",
                "input": {"skill": "python-dev"},
            },
            {
                "name": "Task",
                "input": {"subagent_type": "Explore", "prompt": "Find files"},
            },
        ]

        result = extract_subagent_tool_calls(tool_calls)

        assert len(result) == 3

        # First is Task
        assert result[0]["type"] == "task"
        assert result[0]["name"] == "critic"
        assert result[0]["index"] == 0

        # Second is Skill
        assert result[1]["type"] == "skill"
        assert result[1]["name"] == "python-dev"
        assert result[1]["index"] == 1

        # Third is Task
        assert result[2]["type"] == "task"
        assert result[2]["name"] == "Explore"
        assert result[2]["index"] == 2

    def test_ignores_non_subagent_tools(self):
        """Non-subagent tools are ignored."""
        tool_calls = [
            {"name": "Read", "input": {"file_path": "/some/file.py"}},
            {"name": "Bash", "input": {"command": "ls"}},
            {"name": "Write", "input": {"file_path": "/new.py", "content": "x=1"}},
        ]

        result = extract_subagent_tool_calls(tool_calls)

        assert len(result) == 0

    def test_ignores_malformed_task_calls(self):
        """Task calls without subagent_type are skipped."""
        tool_calls = [
            {"name": "Task", "input": {"prompt": "Do something"}},  # Missing subagent_type
            {"name": "Task", "input": {}},  # Empty input
        ]

        result = extract_subagent_tool_calls(tool_calls)

        assert len(result) == 0

    def test_ignores_malformed_skill_calls(self):
        """Skill calls without skill name are skipped."""
        tool_calls = [
            {"name": "Skill", "input": {"args": "something"}},  # Missing skill
            {"name": "Skill", "input": {}},  # Empty input
        ]

        result = extract_subagent_tool_calls(tool_calls)

        assert len(result) == 0

    def test_preserves_raw_input(self):
        """Raw input dict is preserved for detailed assertions."""
        tool_calls = [
            {
                "name": "Task",
                "input": {
                    "subagent_type": "general-purpose",
                    "prompt": "Do task",
                    "model": "opus",
                    "run_in_background": True,
                    "max_turns": 10,
                },
            }
        ]

        result = extract_subagent_tool_calls(tool_calls)

        assert result[0]["input"]["max_turns"] == 10
        assert result[0]["run_in_background"] is True

    def test_empty_tool_calls(self):
        """Empty tool_calls list returns empty result."""
        result = extract_subagent_tool_calls([])
        assert result == []


class TestExtractTaskCalls:
    """Tests for extract_task_calls helper."""

    def test_extracts_only_task_calls(self):
        """Only Task tool invocations are extracted."""
        tool_calls = [
            {"name": "Read", "input": {"file_path": "/file.py"}},
            {"name": "Task", "input": {"subagent_type": "Explore", "prompt": "Find"}},
            {"name": "Skill", "input": {"skill": "framework"}},
            {"name": "Task", "input": {"subagent_type": "critic", "prompt": "Review"}},
        ]

        result = extract_task_calls(tool_calls)

        assert len(result) == 2
        assert result[0]["subagent_type"] == "Explore"
        assert result[1]["subagent_type"] == "critic"

    def test_extracts_all_task_fields(self):
        """All relevant Task fields are extracted."""
        tool_calls = [
            {
                "name": "Task",
                "input": {
                    "subagent_type": "general-purpose",
                    "prompt": "Do the thing",
                    "model": "sonnet",
                    "run_in_background": True,
                },
            }
        ]

        result = extract_task_calls(tool_calls)

        assert result[0]["subagent_type"] == "general-purpose"
        assert result[0]["prompt"] == "Do the thing"
        assert result[0]["model"] == "sonnet"
        assert result[0]["run_in_background"] is True
        assert result[0]["index"] == 0

    def test_handles_missing_optional_fields(self):
        """Optional fields default appropriately."""
        tool_calls = [
            {"name": "Task", "input": {"subagent_type": "Explore", "prompt": "Find"}}
        ]

        result = extract_task_calls(tool_calls)

        assert result[0]["model"] is None
        assert result[0]["run_in_background"] is False


class TestTaskToolWithType:
    """Tests for task_tool_with_type helper."""

    def test_finds_matching_subagent_type(self):
        """Returns True when matching subagent_type exists."""
        tool_calls = [
            {"name": "Read", "input": {}},
            {"name": "Task", "input": {"subagent_type": "Explore", "prompt": "Find"}},
        ]

        assert task_tool_with_type(tool_calls, "Explore") is True

    def test_returns_false_when_no_match(self):
        """Returns False when no matching subagent_type."""
        tool_calls = [
            {"name": "Task", "input": {"subagent_type": "Explore", "prompt": "Find"}}
        ]

        assert task_tool_with_type(tool_calls, "critic") is False

    def test_returns_false_when_no_task_calls(self):
        """Returns False when no Task tool calls exist."""
        tool_calls = [
            {"name": "Read", "input": {}},
            {"name": "Skill", "input": {"skill": "framework"}},
        ]

        assert task_tool_with_type(tool_calls, "Explore") is False

    def test_exact_match_required(self):
        """Subagent type matching is exact, not substring."""
        tool_calls = [
            {"name": "Task", "input": {"subagent_type": "general-purpose", "prompt": ""}}
        ]

        assert task_tool_with_type(tool_calls, "general") is False
        assert task_tool_with_type(tool_calls, "general-purpose") is True


class TestCountTaskCalls:
    """Tests for count_task_calls helper."""

    def test_counts_task_calls(self):
        """Returns correct count of Task tool invocations."""
        tool_calls = [
            {"name": "Task", "input": {"subagent_type": "Explore", "prompt": ""}},
            {"name": "Read", "input": {}},
            {"name": "Task", "input": {"subagent_type": "critic", "prompt": ""}},
            {"name": "Task", "input": {"subagent_type": "qa", "prompt": ""}},
        ]

        assert count_task_calls(tool_calls) == 3

    def test_returns_zero_when_no_task_calls(self):
        """Returns 0 when no Task tool calls exist."""
        tool_calls = [
            {"name": "Read", "input": {}},
            {"name": "Skill", "input": {"skill": "framework"}},
        ]

        assert count_task_calls(tool_calls) == 0

    def test_ignores_malformed_task_calls(self):
        """Malformed Task calls (no subagent_type) are not counted."""
        tool_calls = [
            {"name": "Task", "input": {"subagent_type": "Explore", "prompt": ""}},
            {"name": "Task", "input": {"prompt": "No type"}},  # Malformed
            {"name": "Task", "input": {}},  # Malformed
        ]

        assert count_task_calls(tool_calls) == 1
