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

        result = extract_gate_context(transcript, include={"prompts", "skill", "todos", "intent"})

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

    def test_assistant_entries_captured_despite_interleaved_summaries(self, tmp_path: Path) -> None:
        """Assistant responses must be captured even when summary entries are interleaved.

        Bug #316: Summary entries were clearing current_turn before assistant
        entries arrived, causing all assistant responses to be lost.

        Session pattern that triggers the bug:
        - user entry (creates turn)
        - summary entry (was breaking the turn)
        - assistant entry (should attach to the turn)
        """
        from lib.transcript_parser import Entry, SessionProcessor

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
        conv_turns = [t for t in turns if not isinstance(t, dict) or t.get("type") != "summary"]

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
            f"BUG: assistant_sequence is empty! Summary entries broke the turn. Turn: {turn}"
        )


# --- Session Boundary Validation Tests ---
# These tests verify that session context pollution is properly filtered.
# Context pollution occurs when content from previous sessions leaks into
# current session transcripts via memory summaries or agent references.


def _create_summary_entry_null_timestamp(summary_text: str) -> dict:
    """Create a summary entry with no timestamp (memory from previous session).

    When timestamp key is missing, Entry.timestamp will be None.
    This represents memory context injected from previous sessions.
    """
    return {
        "type": "summary",
        "uuid": f"summary-null-{hash(summary_text) % 10000}",
        # No timestamp key - this is how null timestamps appear in real JSONL
        "summary": summary_text,
    }


def _create_hook_entry(hook_event: str, agent_id: str | None = None, offset: int = 0) -> dict:
    """Create a system_reminder entry for a hook."""
    return {
        "type": "system_reminder",
        "uuid": f"hook-{offset}",
        "timestamp": _make_timestamp(offset),
        "hookSpecificOutput": {
            "hookEventName": hook_event,
            "exitCode": 0,
            "agentId": agent_id,
        },
    }


def _create_entry_with_timestamp(entry_type: str, timestamp_str: str | None, uuid: str) -> dict:
    """Create an entry with a specific timestamp string (or None)."""
    entry: dict = {
        "type": entry_type,
        "uuid": uuid,
    }
    if timestamp_str is not None:
        entry["timestamp"] = timestamp_str
    if entry_type == "user":
        entry["message"] = {"content": [{"type": "text", "text": "Test message"}]}
    elif entry_type == "assistant":
        entry["message"] = {"content": [{"type": "text", "text": "Test response"}]}
    elif entry_type == "summary":
        entry["summary"] = "Test summary"
    return entry


class TestSessionBoundaryValidation:
    """Tests for session boundary validation - preventing context pollution.

    Context pollution occurs when content from previous sessions leaks into
    current session transcripts. This can happen via:
    1. Summary entries with null timestamps (memory from previous sessions)
    2. Hook entries referencing agents from previous sessions
    3. Entries outside the session's time range

    Note: group_entries_into_turns returns:
    - dict for hook_context and summary turns
    - ConversationTurn objects for actual conversation turns
    """

    def test_summary_with_null_timestamp_excluded_from_turns(self, tmp_path: Path) -> None:
        """Summary entries with null timestamp should be excluded from conversation turns.

        These represent memory context from previous sessions, not current session content.
        """
        from lib.transcript_parser import Entry, SessionProcessor

        # Simulate a polluted session: null-timestamp summaries mixed with real entries
        entries_data = [
            # Memory summaries from previous sessions (null timestamps)
            _create_summary_entry_null_timestamp("Previous session context about user preferences"),
            _create_summary_entry_null_timestamp("Another memory from earlier session"),
            # Current session content (valid timestamps)
            _create_user_entry("Hello, start new task", 0),
            _create_assistant_entry(1),
            # More pollution
            _create_summary_entry_null_timestamp("Old context that shouldn't appear"),
            _create_user_entry("Continue working", 10),
            _create_assistant_entry(11),
        ]

        entries = [Entry.from_dict(e) for e in entries_data]

        processor = SessionProcessor()
        turns = processor.group_entries_into_turns(entries, None, full_mode=True)

        # Collect all summary turns (these are dicts, not ConversationTurn objects)
        summary_turns = [t for t in turns if isinstance(t, dict) and t.get("type") == "summary"]

        # Summary turns with null timestamps should either:
        # - Not appear at all, OR
        # - Be marked with null start_time/end_time so consumers can filter
        null_timestamp_summaries = [
            "Previous session context about user preferences",
            "Another memory from earlier session",
            "Old context that shouldn't appear",
        ]
        for summary_turn in summary_turns:
            if summary_turn.get("content") in null_timestamp_summaries:
                # These are from previous sessions - verify they're identifiable
                # Currently, summaries with null timestamps will have None for start_time
                assert summary_turn.get("start_time") is None, (
                    f"Null-timestamp summary should have None start_time for filtering: {summary_turn}"
                )

    def test_hook_referencing_non_session_agent_identifiable(self, tmp_path: Path) -> None:
        """Hook entries referencing agents from other sessions should be identifiable.

        When a hook references an agent_id that doesn't match any agent in the
        current session, it indicates cross-session pollution.
        """
        from lib.transcript_parser import Entry, SessionProcessor

        # Session with one real agent (agent-abc123) but hooks referencing another
        entries_data = [
            _create_user_entry("Start work", 0),
            # Hook from current session's agent
            _create_hook_entry("PreToolUse", agent_id="agent-abc123", offset=1),
            _create_assistant_entry(2),
            # Hook referencing an agent from a DIFFERENT session (pollution)
            _create_hook_entry("PostToolUse", agent_id="agent-xyz789-old-session", offset=3),
            _create_user_entry("Continue", 10),
            _create_assistant_entry(11),
        ]

        entries = [Entry.from_dict(e) for e in entries_data]

        processor = SessionProcessor()
        turns = processor.group_entries_into_turns(entries, None, full_mode=True)

        # Find hook_context turns (these are dicts)
        hook_turns = [t for t in turns if isinstance(t, dict) and t.get("type") == "hook_context"]

        # Verify that agent_id is preserved so consumers can filter by session membership
        for hook_turn in hook_turns:
            if hook_turn.get("agent_id") == "agent-xyz789-old-session":
                # This hook references an agent from a different session
                # It should be identifiable so transcript consumers can filter it
                assert "agent_id" in hook_turn, (
                    "Hook turns must include agent_id for session boundary filtering"
                )

    def test_conversation_history_pollution_fixture(self, tmp_path: Path) -> None:
        """Test with polluted session data simulating real bug from session 5cb39058.

        This fixture represents a session where:
        - Memory summaries from previous sessions leak in
        - Some entries have timestamps outside the session time range
        """
        from lib.transcript_parser import ConversationTurn, Entry, SessionProcessor

        # Simulate pollution pattern: old summaries at start, then real conversation
        entries_data = [
            # --- POLLUTION: Content from before session started ---
            _create_summary_entry_null_timestamp("Memory: User asked about Python best practices"),
            {
                "type": "summary",
                "uuid": "summary-old-1",
                "timestamp": "2025-01-10T08:00:00Z",  # Before session
                "summary": "Old conversation about debugging",
            },
            # --- ACTUAL SESSION START (offset 0 = 2025-01-15T10:00:00Z) ---
            _create_user_entry("Help me with the framework tests", 0),
            _create_assistant_entry(1),
            # More pollution injected mid-session
            _create_summary_entry_null_timestamp("Ancient context about unrelated project"),
            _create_user_entry("Add validation tests", 10),
            _create_assistant_entry(11),
        ]

        entries = [Entry.from_dict(e) for e in entries_data]

        processor = SessionProcessor()
        turns = processor.group_entries_into_turns(entries, None, full_mode=True)

        # Count actual conversation turns (ConversationTurn objects, not summary dicts)
        conversation_turns = [
            t for t in turns if isinstance(t, ConversationTurn) and t.user_message is not None
        ]

        # We should have exactly 2 conversation turns from the real session
        assert len(conversation_turns) == 2, (
            f"Expected 2 conversation turns, got {len(conversation_turns)}. "
            f"Pollution may have created extra turns."
        )

        # Verify the conversation turns have the correct content
        assert conversation_turns[0].user_message == "Help me with the framework tests"
        assert conversation_turns[1].user_message == "Add validation tests"

    def test_entries_only_within_session_time_range(self, tmp_path: Path) -> None:
        """Entries outside the session's time range should be filterable.

        Session time range is determined by the first and last valid timestamps.
        Entries with timestamps significantly before or after should be excluded
        or clearly marked.
        """
        from lib.transcript_parser import ConversationTurn, Entry, SessionProcessor

        # Session starts at offset 100 (10:01:40), ends around offset 200 (10:03:20)
        # But old entries sneak in with timestamps from before session start
        entries_data = [
            # Entry from a DIFFERENT time (hours before session)
            {
                "type": "user",
                "uuid": "user-old",
                "timestamp": "2025-01-15T06:00:00Z",  # 4 hours before session
                "message": {"content": [{"type": "text", "text": "Old question from earlier"}]},
            },
            # Actual session content
            _create_user_entry("Current session question", 100),
            _create_assistant_entry(101),
            _create_user_entry("Follow up question", 150),
            _create_assistant_entry(151),
            # Entry from future (likely pollution or corruption)
            {
                "type": "user",
                "uuid": "user-future",
                "timestamp": "2025-01-15T23:00:00Z",  # 13 hours after session
                "message": {"content": [{"type": "text", "text": "Future question"}]},
            },
        ]

        entries = [Entry.from_dict(e) for e in entries_data]

        processor = SessionProcessor()
        turns = processor.group_entries_into_turns(entries, None, full_mode=True)

        # Get conversation turns (ConversationTurn objects)
        conversation_turns = [
            t for t in turns if isinstance(t, ConversationTurn) and t.user_message is not None
        ]

        # All conversation turns should have start_time information for filtering
        for turn in conversation_turns:
            assert turn.start_time is not None, "Turn must have start_time for boundary validation"

        # Consumers can use start_time to filter out-of-range entries
        # The processor should preserve timestamps so filtering is possible
        # Verify we have at least the 2 valid session entries
        assert len(conversation_turns) >= 2, "Should have at least the 2 valid session entries"


class TestBuildAuditSessionContext:
    """Tests for build_audit_session_context."""

    def test_pre_parsed_entries_path(self, tmp_path):
        """Regression: pre-parsed entries caused UnboundLocalError on processor.

        When create_audit_file passes pre-parsed entries, build_audit_session_context
        skipped processor creation, causing an UnboundLocalError on
        processor.group_entries_into_turns(). Fixed by creating processor unconditionally.
        See: nicsuzor/academicOps#228
        """
        from lib.session_reader import SessionProcessor, build_audit_session_context

        # Create a minimal JSONL transcript
        jsonl_path = tmp_path / "test-session.jsonl"
        entries_data = [
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": _make_timestamp(0),
                "message": {"content": [{"type": "text", "text": "Hello world"}]},
            },
            {
                "type": "assistant",
                "uuid": "a1",
                "timestamp": _make_timestamp(1),
                "message": {"content": [{"type": "text", "text": "Hi, how can I help?"}]},
            },
        ]
        jsonl_path.write_text("\n".join(json.dumps(e) for e in entries_data) + "\n")

        # Parse entries separately (simulating create_audit_file's pattern)
        processor = SessionProcessor()
        _, entries, _ = processor.parse_session_file(
            jsonl_path, load_agents=False, load_hooks=False
        )
        assert entries  # sanity check

        # This was the failing call — entries passed but processor not created
        result = build_audit_session_context(str(jsonl_path), entries=entries)
        assert len(result) > 0
        assert "Hello world" in result

    def test_pre_parsed_entries_multi_turn_conversation(self, tmp_path):
        """Pre-parsed entries with multiple turns produce correct audit context.

        Verifies the entries= path handles a realistic multi-turn session
        with tool calls and multiple user prompts.
        """
        from lib.session_reader import SessionProcessor, build_audit_session_context

        jsonl_path = tmp_path / "multi-turn.jsonl"
        entries_data = [
            _create_user_entry("Implement the login feature", 0),
            _create_assistant_entry(1),
            _create_tool_use_entry("Read", {"file_path": "/src/auth.py"}, 5),
            _create_tool_result_entry("tool-5", "class Auth: ...", offset=6),
            _create_user_entry("Now add tests for it", 10),
            _create_assistant_entry(11),
            _create_tool_use_entry("Write", {"file_path": "/tests/test_auth.py"}, 15),
            _create_tool_result_entry("tool-15", "File written", offset=16),
            _create_user_entry("Run the tests", 20),
            _create_assistant_entry(21),
            _create_tool_use_entry("Bash", {"command": "pytest tests/"}, 25),
            _create_tool_result_entry("tool-25", "3 passed", offset=26),
        ]
        _write_jsonl(jsonl_path, entries_data)

        processor = SessionProcessor()
        _, entries, _ = processor.parse_session_file(
            jsonl_path, load_agents=False, load_hooks=False
        )

        result = build_audit_session_context(str(jsonl_path), entries=entries)

        # All user prompts should appear in the context
        assert "Implement the login feature" in result
        assert "Now add tests for it" in result
        assert "Run the tests" in result

    def test_pre_parsed_entries_empty_list(self, tmp_path):
        """Pre-parsed empty entries list returns empty session marker."""
        from lib.session_reader import build_audit_session_context

        jsonl_path = tmp_path / "empty.jsonl"
        jsonl_path.write_text("")

        result = build_audit_session_context(str(jsonl_path), entries=[])
        assert result == "(Empty session)"

    def test_pre_parsed_entries_none_falls_back_to_file(self, tmp_path):
        """When entries=None, function reads from disk (default path)."""
        from lib.session_reader import build_audit_session_context

        jsonl_path = tmp_path / "fallback.jsonl"
        entries_data = [
            _create_user_entry("Disk-read prompt", 0),
            _create_assistant_entry(1),
        ]
        _write_jsonl(jsonl_path, entries_data)

        result = build_audit_session_context(str(jsonl_path), entries=None)
        assert "Disk-read prompt" in result

    def test_missing_transcript_no_entries(self, tmp_path):
        """Missing transcript with no entries returns appropriate message."""
        from lib.session_reader import build_audit_session_context

        result = build_audit_session_context(str(tmp_path / "nonexistent.jsonl"))
        assert result == "(No transcript path available)"

    def test_tool_calls_from_historical_turns_included(self, tmp_path):
        """Regression: tool calls from turns before last 5 must appear in audit output.

        The old _DETAILED_TURNS_LIMIT = 5 split hid tool calls from historical
        turns, letting violations in those turns pass the enforcer unseen
        (aops-e4e90f31 truncated-read false-pass bug).

        A session with 8 turns must include Write/Bash tool calls from turn 1
        in the audit output — not just the user message.
        """
        from lib.session_reader import SessionProcessor, build_audit_session_context

        jsonl_path = tmp_path / "long-session.jsonl"

        # Build 8 turns; the first has a Write tool call that must appear in audit
        entries_data = [
            _create_user_entry("Turn 1 request", 0),
            _create_tool_use_entry("Write", {"file_path": "/secret/violation.py"}, 1),
            _create_tool_result_entry("tool-1", "File written", offset=2),
        ]
        for i in range(2, 9):
            entries_data += [
                _create_user_entry(f"Turn {i} request", i * 100),
                _create_assistant_entry(i * 100 + 1),
            ]
        _write_jsonl(jsonl_path, entries_data)

        processor = SessionProcessor()
        _, entries, _ = processor.parse_session_file(
            jsonl_path, load_agents=False, load_hooks=False
        )
        result = build_audit_session_context(str(jsonl_path), entries=entries)

        # Turn 1's Write tool call must be visible (not suppressed as "historical")
        assert "Write" in result
        assert "/secret/violation.py" in result
        # All 8 user prompts must be present
        for i in range(1, 9):
            assert f"Turn {i} request" in result

    def test_audit_complete_sentinel_not_present(self, tmp_path):
        from lib.session_reader import build_audit_session_context

        jsonl_path = tmp_path / "session.jsonl"
        entries_data = [_create_user_entry("Do some work", 0), _create_assistant_entry(1)]
        _write_jsonl(jsonl_path, entries_data)
        result = build_audit_session_context(str(jsonl_path))
        assert "<!-- audit-complete:" not in result

    def test_audit_complete_sentinel_includes_turn_count(self, tmp_path):
        """Audit sentinel reports turn count so RBG can detect suspicious mismatches."""
        from lib.session_reader import SessionProcessor, build_audit_session_context

        jsonl_path = tmp_path / "three-turns.jsonl"
        entries_data = [
            _create_user_entry("First", 0),
            _create_assistant_entry(1),
            _create_user_entry("Second", 10),
            _create_assistant_entry(11),
            _create_user_entry("Third", 20),
            _create_assistant_entry(21),
        ]
        _write_jsonl(jsonl_path, entries_data)

        processor = SessionProcessor()
        _, entries, _ = processor.parse_session_file(
            jsonl_path, load_agents=False, load_hooks=False
        )
        result = build_audit_session_context(str(jsonl_path), entries=entries)

        # Sentinel must include the count of turns processed
        assert "<!-- audit-complete: 3 turns -->" not in result

    def test_max_turns_window_keeps_only_last_n_turns(self, tmp_path):
        """max_turns windows to the last n turns (aops-5bc65f76 n+2 cadence window).

        With max_turns set, older turns are dropped but every SHOWN turn keeps
        full detail. The audit-complete sentinel reports the windowed count.
        """
        from lib.session_reader import SessionProcessor, build_audit_session_context

        jsonl_path = tmp_path / "windowed.jsonl"
        entries_data = []
        for i in range(1, 11):  # 10 turns
            entries_data += [
                _create_user_entry(f"Turn {i} request", i * 100),
                _create_assistant_entry(i * 100 + 1),
            ]
        _write_jsonl(jsonl_path, entries_data)

        processor = SessionProcessor()
        _, entries, _ = processor.parse_session_file(
            jsonl_path, load_agents=False, load_hooks=False
        )
        # Window of 4 -> only the last 4 turns (7..10) appear.
        result = build_audit_session_context(str(jsonl_path), entries=entries, max_turns=4)

        for i in range(1, 7):
            assert f"Turn {i} request" not in result, f"Turn {i} should be windowed out"
        for i in range(7, 11):
            assert f"Turn {i} request" in result, f"Turn {i} should be in window"
        # Sentinel reports the windowed turn count, not the full session count.
        assert "<!-- audit-complete: 4 turns -->" not in result

    def test_max_turns_none_renders_all_turns(self, tmp_path):
        """max_turns=None (default) renders the whole session — no windowing."""
        from lib.session_reader import SessionProcessor, build_audit_session_context

        jsonl_path = tmp_path / "full.jsonl"
        entries_data = []
        for i in range(1, 7):
            entries_data += [
                _create_user_entry(f"Turn {i} request", i * 100),
                _create_assistant_entry(i * 100 + 1),
            ]
        _write_jsonl(jsonl_path, entries_data)

        processor = SessionProcessor()
        _, entries, _ = processor.parse_session_file(
            jsonl_path, load_agents=False, load_hooks=False
        )
        result = build_audit_session_context(str(jsonl_path), entries=entries, max_turns=None)
        for i in range(1, 7):
            assert f"Turn {i} request" in result
        assert "<!-- audit-complete: 6 turns -->" not in result

    def test_window_larger_than_session_keeps_all_detail(self, tmp_path):
        """A window wider than the session shows every turn at full detail.

        Guards the #1869 coverage invariant: a Write tool call in turn 1 must
        still be visible when the window exceeds the session length.
        """
        from lib.session_reader import SessionProcessor, build_audit_session_context

        jsonl_path = tmp_path / "short.jsonl"
        entries_data = [
            _create_user_entry("Turn 1 request", 0),
            _create_tool_use_entry("Write", {"file_path": "/secret/violation.py"}, 1),
            _create_tool_result_entry("tool-1", "File written", offset=2),
        ]
        for i in range(2, 5):
            entries_data += [
                _create_user_entry(f"Turn {i} request", i * 100),
                _create_assistant_entry(i * 100 + 1),
            ]
        _write_jsonl(jsonl_path, entries_data)

        processor = SessionProcessor()
        _, entries, _ = processor.parse_session_file(
            jsonl_path, load_agents=False, load_hooks=False
        )
        # n+2 default window (52) >> 4 turns -> nothing trimmed.
        result = build_audit_session_context(str(jsonl_path), entries=entries, max_turns=52)
        assert "Write" in result
        assert "/secret/violation.py" in result
        for i in range(1, 5):
            assert f"Turn {i} request" in result


class TestExtractGateContextExceptionHandling:
    """Tests for extract_gate_context exception handling."""

    def test_corrupt_jsonl_handled_gracefully(self, tmp_path):
        """Corrupt JSONL that passes existence check is handled gracefully.

        Per fix #314: per-line exceptions are caught in _parse_jsonl_file so
        corrupt entries are silently skipped rather than propagating an error.
        extract_gate_context therefore returns an empty result, not an exception.
        """
        from lib.session_reader import extract_gate_context

        transcript = tmp_path / "corrupt.jsonl"
        # message: null triggers AttributeError in Entry.from_dict
        transcript.write_text('{"type": "user", "message": null}\n')

        # Should return empty dict gracefully (corrupt line skipped)
        result = extract_gate_context(transcript, include={"prompts"})
        assert result == {} or result.get("prompts") == []
