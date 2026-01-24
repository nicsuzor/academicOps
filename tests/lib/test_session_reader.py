"""Tests for lib/session_reader.py - Gate context extraction.

TDD Phase 2: Gate Context Extraction API
Tests configurable extraction for gate agents.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _make_timestamp(offset_seconds: int = 0) -> str:
    """Generate ISO timestamp with optional offset from base time."""
    base = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    ts = base + timedelta(seconds=offset_seconds)
    return ts.isoformat().replace("+00:00", "Z")


def _create_user_entry(prompt: str, offset: int = 0, is_meta: bool = False) -> dict:
    """Create a user message entry."""
    return {
        "type": "user",
        "uuid": f"user-{offset}",
        "timestamp": _make_timestamp(offset),
        "isMeta": is_meta,
        "message": {"content": [{"type": "text", "text": prompt}]},
    }


def _create_assistant_entry(offset: int = 0) -> dict:
    """Create an assistant response entry."""
    return {
        "type": "assistant",
        "uuid": f"assistant-{offset}",
        "timestamp": _make_timestamp(offset + 1),
        "message": {"content": [{"type": "text", "text": "I'll help with that."}]},
    }


def _create_skill_invocation_entry(skill_name: str, offset: int = 0) -> dict:
    """Create an assistant entry with Skill tool invocation."""
    return {
        "type": "assistant",
        "uuid": f"skill-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": f"tool-{offset}",
                    "name": "Skill",
                    "input": {"skill": skill_name},
                }
            ]
        },
    }


def _create_todowrite_entry(todos: list[dict], offset: int = 0) -> dict:
    """Create an assistant entry with TodoWrite tool invocation."""
    return {
        "type": "assistant",
        "uuid": f"todo-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": f"todo-tool-{offset}",
                    "name": "TodoWrite",
                    "input": {"todos": todos},
                }
            ]
        },
    }


def _create_tool_use_entry(tool_name: str, tool_input: dict, offset: int = 0) -> dict:
    """Create an assistant entry with a tool invocation."""
    return {
        "type": "assistant",
        "uuid": f"tool-{tool_name}-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": f"tool-{offset}",
                    "name": tool_name,
                    "input": tool_input,
                }
            ]
        },
    }


def _create_tool_result_entry(
    tool_id: str, result: str, is_error: bool = False, offset: int = 0
) -> dict:
    """Create a user entry with tool result."""
    return {
        "type": "user",
        "uuid": f"result-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                    "is_error": is_error,
                }
            ]
        },
    }


def _create_summary_entry(summary_text: str, offset: int = 0) -> dict:
    """Create a summary entry (memory context)."""
    return {
        "type": "summary",
        "uuid": f"summary-{offset}",
        "timestamp": _make_timestamp(offset),
        "summary": summary_text,
    }


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    """Write entries to JSONL file."""
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestExtractGateContextPrompts:
    """Test prompt extraction."""

    def test_extract_prompts_returns_last_n(self, tmp_path: Path) -> None:
        """Extract prompts returns last N user prompts."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("First prompt", 0),
            _create_assistant_entry(1),
            _create_user_entry("Second prompt", 10),
            _create_assistant_entry(11),
            _create_user_entry("Third prompt", 20),
            _create_assistant_entry(21),
            _create_user_entry("Fourth prompt", 30),
            _create_assistant_entry(31),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"prompts"}, max_turns=3)

        assert "prompts" in result
        assert len(result["prompts"]) == 3
        assert result["prompts"][0] == "Second prompt"
        assert result["prompts"][1] == "Third prompt"
        assert result["prompts"][2] == "Fourth prompt"

    def test_extract_prompts_skips_meta(self, tmp_path: Path) -> None:
        """Extract prompts skips meta/system messages."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Real prompt 1", 0),
            _create_assistant_entry(1),
            _create_user_entry("System injection", 10, is_meta=True),
            _create_assistant_entry(11),
            _create_user_entry("Real prompt 2", 20),
            _create_assistant_entry(21),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"prompts"}, max_turns=5)

        assert len(result["prompts"]) == 2
        assert "System injection" not in result["prompts"]


class TestExtractGateContextSkill:
    """Test skill extraction."""

    def test_extract_skill_returns_recent(self, tmp_path: Path) -> None:
        """Extract skill returns most recent Skill invocation."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("First", 0),
            _create_skill_invocation_entry("framework", 5),
            _create_user_entry("Second", 10),
            _create_skill_invocation_entry("python-dev", 15),
            _create_user_entry("Third", 20),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"skill"})

        assert result["skill"] == "python-dev"

    def test_extract_skill_returns_none_if_missing(self, tmp_path: Path) -> None:
        """Extract skill returns None if no Skill invocation."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Hello", 0),
            _create_assistant_entry(1),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"skill"})

        assert result["skill"] is None


class TestExtractGateContextTodos:
    """Test TodoWrite state extraction."""

    def test_extract_todos_returns_state(self, tmp_path: Path) -> None:
        """Extract todos returns current TodoWrite state."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        todos = [
            {"content": "Task 1", "status": "completed", "activeForm": "Doing 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Doing 2"},
            {"content": "Task 3", "status": "pending", "activeForm": "Doing 3"},
        ]
        entries = [
            _create_user_entry("Start work", 0),
            _create_todowrite_entry(todos, 5),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"todos"})

        assert "todos" in result
        assert result["todos"]["counts"]["completed"] == 1
        assert result["todos"]["counts"]["in_progress"] == 1
        assert result["todos"]["counts"]["pending"] == 1
        assert result["todos"]["in_progress_task"] == "Task 2"

    def test_extract_todos_returns_none_if_missing(self, tmp_path: Path) -> None:
        """Extract todos returns None if no TodoWrite."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [_create_user_entry("Hello", 0)]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"todos"})

        assert result["todos"] is None


class TestExtractGateContextIntent:
    """Test intent extraction."""

    def test_extract_intent_returns_first_prompt(self, tmp_path: Path) -> None:
        """Extract intent returns first non-meta user prompt."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("System context", 0, is_meta=True),
            _create_user_entry("Implement gate architecture", 5),
            _create_assistant_entry(6),
            _create_user_entry("Now add tests", 10),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"intent"})

        assert result["intent"] == "Implement gate architecture"

    def test_extract_intent_skips_command_prompts(self, tmp_path: Path) -> None:
        """Extract intent skips command expansions like /do."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            {
                "type": "user",
                "uuid": "cmd",
                "timestamp": _make_timestamp(0),
                "isMeta": True,
                "message": {
                    "content": "<command-name>/do</command-name><command-args>real intent</command-args>"
                },
            },
            _create_user_entry("fix the bug in parser.py", 5),
            _create_assistant_entry(6),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"intent"})

        assert result["intent"] == "fix the bug in parser.py"


class TestExtractGateContextTools:
    """Test tool calls extraction."""

    def test_extract_tools_returns_recent(self, tmp_path: Path) -> None:
        """Extract tools returns recent tool calls."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Read file", 0),
            _create_tool_use_entry("Read", {"file_path": "/path/to/file.py"}, 5),
            _create_tool_result_entry("tool-5", "file contents", offset=6),
            _create_tool_use_entry("Edit", {"file_path": "/path/to/file.py"}, 10),
            _create_tool_result_entry("tool-10", "edited", offset=11),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"tools"}, max_turns=5)

        assert "tools" in result
        assert len(result["tools"]) == 2
        assert result["tools"][0]["name"] == "Read"
        assert result["tools"][1]["name"] == "Edit"


class TestExtractGateContextErrors:
    """Test error extraction."""

    def test_extract_errors_returns_recent(self, tmp_path: Path) -> None:
        """Extract errors returns recent tool errors."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Run tests", 0),
            _create_tool_use_entry("Bash", {"command": "pytest"}, 5),
            _create_tool_result_entry(
                "tool-5", "FAILED: test_foo.py::test_bar", is_error=True, offset=6
            ),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"errors"}, max_turns=5)

        assert "errors" in result
        assert len(result["errors"]) == 1
        # New format includes tool_name, input_summary, and error (not content)
        assert result["errors"][0]["tool_name"] == "Bash"
        assert "FAILED" in result["errors"][0]["error"]

    def test_extract_errors_empty_if_none(self, tmp_path: Path) -> None:
        """Extract errors returns empty list if no errors."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Hello", 0),
            _create_assistant_entry(1),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include={"errors"}, max_turns=5)

        assert result["errors"] == []


class TestExtractGateContextMultiple:
    """Test multiple extraction types."""

    def test_extract_multiple_types(self, tmp_path: Path) -> None:
        """Can extract multiple context types in one call."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        todos = [{"content": "Task 1", "status": "pending", "activeForm": "Task"}]
        entries = [
            _create_user_entry("Implement feature", 0),
            _create_skill_invocation_entry("framework", 5),
            _create_todowrite_entry(todos, 10),
        ]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(
            transcript, include={"prompts", "skill", "todos", "intent"}
        )

        assert "prompts" in result
        assert "skill" in result
        assert "todos" in result
        assert "intent" in result
        assert result["skill"] == "framework"
        assert result["intent"] == "Implement feature"

    def test_empty_include_returns_empty_dict(self, tmp_path: Path) -> None:
        """Empty include set returns empty dict."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        entries = [_create_user_entry("Hello", 0)]
        _write_jsonl(transcript, entries)

        result = extract_gate_context(transcript, include=set())

        assert result == {}


class TestExtractGateContextEdgeCases:
    """Test edge cases."""

    def test_missing_transcript_returns_empty(self, tmp_path: Path) -> None:
        """Missing transcript returns empty dict."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "nonexistent.jsonl"
        result = extract_gate_context(transcript, include={"prompts"})

        assert result == {}

    def test_empty_transcript_returns_empty(self, tmp_path: Path) -> None:
        """Empty transcript returns empty dict."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        transcript.write_text("")

        result = extract_gate_context(transcript, include={"prompts"})

        assert result == {} or result.get("prompts") == []

    def test_invalid_json_handled_gracefully(self, tmp_path: Path) -> None:
        """Invalid JSON lines are skipped gracefully."""
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "session.jsonl"
        with open(transcript, "w") as f:
            f.write("not json\n")
            f.write(json.dumps(_create_user_entry("Valid prompt", 0)) + "\n")

        result = extract_gate_context(transcript, include={"prompts"})

        # Should still get the valid prompt
        assert len(result.get("prompts", [])) == 1


class TestGroupEntriesIntoTurns:
    """Test conversation turn grouping - Issue #316."""

    def test_assistant_entries_captured_despite_interleaved_summaries(
        self, tmp_path: Path
    ) -> None:
        """Assistant responses must be captured even when summary entries are interleaved.

        Bug #316: Summary entries were clearing current_turn before assistant
        entries arrived, causing all assistant responses to be lost.

        Session pattern that triggers the bug:
        - user entry (creates turn)
        - summary entry (was breaking the turn)
        - assistant entry (should attach to the turn)
        """
        from lib.session_reader import Entry, SessionProcessor

        # Create entries matching the bug pattern from session 138295b6
        entries_data = [
            _create_summary_entry("Context summary 1", 0),
            _create_summary_entry("Context summary 2", 1),
            _create_user_entry("Fix the crontab issue", 2),
            _create_summary_entry("More context", 3),  # This was breaking the turn
            _create_summary_entry("Even more context", 4),
            _create_assistant_entry(5),  # This should be captured!
            {
                "type": "assistant",
                "uuid": "assistant-tool-6",
                "timestamp": _make_timestamp(6),
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tool-123",
                            "name": "Bash",
                            "input": {"command": "crontab -l"},
                        }
                    ]
                },
            },
        ]

        # Convert to Entry objects
        entries = [Entry.from_dict(e) for e in entries_data]

        processor = SessionProcessor()
        turns = processor.group_entries_into_turns(entries, None, full_mode=True)

        # Find the conversation turn (not summary turns)
        conv_turns = [
            t for t in turns if not isinstance(t, dict) or t.get("type") != "summary"
        ]

        # Must have at least one conversation turn
        assert len(conv_turns) >= 1, "No conversation turns found"

        # Get the first actual conversation turn
        turn = conv_turns[0]

        # The turn must have assistant_sequence with content
        if hasattr(turn, "assistant_sequence"):
            assistant_seq = turn.assistant_sequence
        else:
            assistant_seq = turn.get("assistant_sequence", [])

        assert len(assistant_seq) > 0, (
            f"BUG: assistant_sequence is empty! "
            f"Summary entries broke the turn. "
            f"Turn: {turn}"
        )


class TestExtractQuestionsFromAgentResponse:
    """Test extraction of questions from agent responses."""

    def test_extract_questions_finds_single_question(self) -> None:
        """Extract questions from text containing a single question."""
        from lib.session_reader import _extract_questions_from_text

        text = "Here is some context. What would you like to do?"
        questions = _extract_questions_from_text(text)

        assert len(questions) == 1
        assert "What would you like to do" in questions[0]

    def test_extract_questions_finds_multiple_questions(self) -> None:
        """Extract questions from text with multiple questions."""
        from lib.session_reader import _extract_questions_from_text

        text = "Which task should I add? Did you want me to use all of them? Or just some?"
        questions = _extract_questions_from_text(text)

        assert len(questions) == 3
        assert any("Which task" in q for q in questions)
        assert any("Did you want" in q for q in questions)
        assert any("Or just some" in q for q in questions)

    def test_extract_questions_handles_empty_text(self) -> None:
        """Extract questions from empty text returns empty list."""
        from lib.session_reader import _extract_questions_from_text

        questions = _extract_questions_from_text("")
        assert questions == []

    def test_extract_questions_deduplicates(self) -> None:
        """Extract questions deduplicates identical questions."""
        from lib.session_reader import _extract_questions_from_text

        text = "What do you want? What do you want? Something else?"
        questions = _extract_questions_from_text(text)

        # Should have 2 questions (first is deduplicated, third is different)
        assert len(questions) == 2

    def test_extract_questions_cleans_whitespace(self) -> None:
        """Extract questions removes leading/trailing whitespace."""
        from lib.session_reader import _extract_questions_from_text

        text = "  What is this?   How about this?  "
        questions = _extract_questions_from_text(text)

        assert len(questions) == 2
        assert questions[0] == "What is this?"
        assert questions[1] == "How about this?"

    def test_extract_router_context_includes_agent_questions(self, tmp_path: Path) -> None:
        """Router context includes extracted agent questions."""
        from lib.session_reader import extract_router_context

        transcript = tmp_path / "session.jsonl"
        # Create a conversation where agent asks a question
        entries = [
            _create_user_entry("Add tasks", 0),
            {
                "type": "assistant",
                "uuid": "assistant-1",
                "timestamp": _make_timestamp(1),
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "I can help with that. Which tasks would you like to add?",
                        }
                    ]
                },
            },
            _create_user_entry("all", 10),
        ]
        _write_jsonl(transcript, entries)

        context = extract_router_context(transcript)

        # Context should include the extracted question
        assert "Agent questions" in context or "Which tasks" in context
        # Most importantly, the context should show "all" with the question context
        assert "all" in context or "recent" in context.lower()
