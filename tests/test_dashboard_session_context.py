"""
Tests for dashboard session context feature.

Tests TodoWrite state extraction from session files for the Active Sessions panel.
"""

import json
import tempfile
from pathlib import Path

import pytest

from lib.session_analyzer import extract_todowrite_from_session
from lib.session_reader import TodoWriteState, parse_todowrite_state


class TestParseTodowriteState:
    """Tests for parse_todowrite_state helper."""

    def test_extracts_todowrite_from_entries(self):
        """Should extract TodoWrite state from session entries."""
        entries = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "hello"}]}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TodoWrite",
                            "input": {
                                "todos": [
                                    {"content": "Task 1", "status": "completed", "activeForm": "Doing task 1"},
                                    {"content": "Task 2", "status": "in_progress", "activeForm": "Doing task 2"},
                                    {"content": "Task 3", "status": "pending", "activeForm": "Doing task 3"},
                                ]
                            },
                        }
                    ]
                },
            },
        ]

        result = parse_todowrite_state(entries)

        assert result is not None
        assert isinstance(result, TodoWriteState)
        assert len(result.todos) == 3
        assert result.counts == {"pending": 1, "in_progress": 1, "completed": 1}
        assert result.in_progress_task == "Task 2"

    def test_returns_none_for_no_todowrite(self):
        """Should return None when no TodoWrite found."""
        entries = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "hello"}]}},
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "response"}]
                },
            },
        ]

        result = parse_todowrite_state(entries)
        assert result is None

    def test_returns_most_recent_todowrite(self):
        """Should return the most recent TodoWrite state when multiple exist."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TodoWrite",
                            "input": {
                                "todos": [
                                    {"content": "Old task", "status": "pending", "activeForm": "Old"},
                                ]
                            },
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TodoWrite",
                            "input": {
                                "todos": [
                                    {"content": "New task", "status": "in_progress", "activeForm": "New"},
                                ]
                            },
                        }
                    ]
                },
            },
        ]

        result = parse_todowrite_state(entries)

        assert result is not None
        assert result.in_progress_task == "New task"

    def test_handles_empty_todos(self):
        """Should return None for TodoWrite with empty todos list."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TodoWrite",
                            "input": {"todos": []},
                        }
                    ]
                },
            },
        ]

        result = parse_todowrite_state(entries)
        assert result is None

    def test_counts_multiple_in_progress(self):
        """Should count all in_progress items but only return first as in_progress_task."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TodoWrite",
                            "input": {
                                "todos": [
                                    {"content": "First active", "status": "in_progress", "activeForm": "1"},
                                    {"content": "Second active", "status": "in_progress", "activeForm": "2"},
                                ]
                            },
                        }
                    ]
                },
            },
        ]

        result = parse_todowrite_state(entries)

        assert result is not None
        assert result.counts["in_progress"] == 2
        assert result.in_progress_task == "First active"


class TestExtractTodowriteFromSession:
    """Tests for extract_todowrite_from_session function."""

    def test_extracts_from_jsonl_file(self, tmp_path):
        """Should extract TodoWrite from a real JSONL session file."""
        session_file = tmp_path / "test-session.jsonl"
        entries = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "Start work"}]}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TodoWrite",
                            "input": {
                                "todos": [
                                    {"content": "Implement feature", "status": "in_progress", "activeForm": "Implementing"},
                                    {"content": "Write tests", "status": "pending", "activeForm": "Writing tests"},
                                ]
                            },
                        }
                    ]
                },
            },
        ]

        with open(session_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = extract_todowrite_from_session(session_file)

        assert result is not None
        assert result.in_progress_task == "Implement feature"
        assert result.counts["pending"] == 1
        assert result.counts["in_progress"] == 1

    def test_returns_none_for_missing_file(self, tmp_path):
        """Should return None for non-existent file."""
        missing = tmp_path / "does-not-exist.jsonl"

        result = extract_todowrite_from_session(missing)
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_path):
        """Should return None for empty session file."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")

        result = extract_todowrite_from_session(empty_file)
        assert result is None

    def test_handles_malformed_json(self, tmp_path):
        """Should skip malformed lines and still extract valid TodoWrite."""
        session_file = tmp_path / "malformed.jsonl"

        with open(session_file, "w") as f:
            f.write("not valid json\n")
            f.write(json.dumps({
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TodoWrite",
                            "input": {
                                "todos": [
                                    {"content": "Valid task", "status": "pending", "activeForm": "Valid"},
                                ]
                            },
                        }
                    ]
                },
            }) + "\n")
            f.write("another bad line\n")

        result = extract_todowrite_from_session(session_file)

        assert result is not None
        assert len(result.todos) == 1
        assert result.todos[0]["content"] == "Valid task"
