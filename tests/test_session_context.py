"""Tests for lib/session_context.py - Session Context Extraction.

Tests conversation-centric context extraction for dashboard display.
Per specs/overwhelm-dashboard.md Session Context Model.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


from lib.session_context import (
    SessionContext,
    extract_context_from_session_state,
    extract_session_context,
)


def _make_timestamp(offset_seconds: int = 0) -> str:
    """Generate ISO timestamp with optional offset from base time."""
    base = datetime(2026, 2, 3, 10, 0, 0, tzinfo=UTC)
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


def _create_assistant_entry(text: str, offset: int = 0) -> dict:
    """Create an assistant response entry."""
    return {
        "type": "assistant",
        "uuid": f"assistant-{offset}",
        "timestamp": _make_timestamp(offset + 1),
        "message": {"content": [{"type": "text", "text": text}]},
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
                    "id": f"tool-{offset}",
                    "name": "TodoWrite",
                    "input": {"todos": todos},
                }
            ]
        },
    }


class TestSessionContextDataclass:
    """Tests for SessionContext dataclass."""

    def test_has_meaningful_context_with_initial_prompt(self):
        """Session with initial prompt has meaningful context."""
        ctx = SessionContext(
            session_id="test-123",
            initial_prompt="Review PR #42",
        )
        assert ctx.has_meaningful_context() is True

    def test_has_meaningful_context_with_current_status(self):
        """Session with current status has meaningful context."""
        ctx = SessionContext(
            session_id="test-123",
            current_status="Working on tests",
        )
        assert ctx.has_meaningful_context() is True

    def test_has_meaningful_context_empty(self):
        """Session without prompt or status lacks meaningful context."""
        ctx = SessionContext(session_id="test-123")
        assert ctx.has_meaningful_context() is False

    def test_to_dict(self):
        """SessionContext serializes to dict correctly."""
        ctx = SessionContext(
            session_id="test-123",
            project="aops",
            initial_prompt="Fix bug",
            follow_up_prompts=["Also add tests"],
            last_user_message="Also add tests",
            current_status="Writing tests",
            planned_next_step="Run tests",
        )
        result = ctx.to_dict()

        assert result["session_id"] == "test-123"
        assert result["project"] == "aops"
        assert result["initial_prompt"] == "Fix bug"
        assert result["follow_up_prompts"] == ["Also add tests"]
        assert result["current_status"] == "Writing tests"


class TestExtractContextFromSessionState:
    """Tests for extract_context_from_session_state()."""

    def test_extracts_from_hydration(self):
        """Extracts initial prompt from hydration.original_prompt."""
        state = {
            "session_id": "abc-123",
            "started_at": "2026-02-03T10:00:00Z",
            "hydration": {
                "original_prompt": "Help me write tests",
                "hydrated_intent": "Write unit tests for session_context.py",
            },
            "main_agent": {},
            "insights": {"project": "aops"},
        }

        ctx = extract_context_from_session_state(state)

        assert ctx.session_id == "abc-123"
        assert ctx.initial_prompt == "Help me write tests"
        assert "Write unit tests" in ctx.current_status
        assert ctx.project == "aops"

    def test_extracts_from_main_agent(self):
        """Extracts task and last_prompt from main_agent."""
        state = {
            "session_id": "abc-123",
            "started_at": "2026-02-03T10:00:00Z",
            "hydration": {},
            "main_agent": {
                "current_task": "aops-12345",
                "last_prompt": "Fix the failing test",
            },
            "insights": {},
        }

        ctx = extract_context_from_session_state(state)

        assert ctx.last_user_message == "Fix the failing test"
        assert ctx.initial_prompt == "Fix the failing test"  # Falls back to last_prompt
        assert "aops-12345" in ctx.planned_next_step

    def test_handles_minimal_state(self):
        """Handles state with minimal fields."""
        state = {
            "session_id": "minimal-123",
        }

        ctx = extract_context_from_session_state(state)

        assert ctx.session_id == "minimal-123"
        assert ctx.initial_prompt == ""
        assert ctx.has_meaningful_context() is False


class TestExtractSessionContext:
    """Tests for extract_session_context() from transcript."""

    def test_extracts_initial_and_followup_prompts(self, tmp_path: Path):
        """Extracts initial prompt and follow-ups from transcript."""
        entries = [
            _create_user_entry("Implement feature X", offset=0),
            _create_assistant_entry("I'll help implement feature X.", offset=1),
            _create_user_entry("Also add documentation", offset=100),
            _create_assistant_entry("Adding documentation.", offset=101),
            _create_user_entry("Make it handle edge cases", offset=200),
            _create_assistant_entry("Handling edge cases.", offset=201),
        ]

        transcript = tmp_path / "session.jsonl"
        transcript.write_text("\n".join(json.dumps(e) for e in entries))

        ctx = extract_session_context(transcript, session_id="test-123")

        assert ctx.initial_prompt == "Implement feature X"
        assert "Also add documentation" in ctx.follow_up_prompts
        assert ctx.last_user_message == "Make it handle edge cases"

    def test_extracts_current_status_from_todowrite(self, tmp_path: Path):
        """Extracts current status from TodoWrite in_progress task."""
        entries = [
            _create_user_entry("Fix all the bugs", offset=0),
            _create_assistant_entry("I'll fix the bugs.", offset=1),
            _create_todowrite_entry(
                [
                    {"content": "Fix bug 1", "status": "completed", "activeForm": "Fixing bug 1"},
                    {"content": "Fix bug 2", "status": "in_progress", "activeForm": "Fixing bug 2"},
                    {"content": "Fix bug 3", "status": "pending", "activeForm": "Fixing bug 3"},
                ],
                offset=100,
            ),
        ]

        transcript = tmp_path / "session.jsonl"
        transcript.write_text("\n".join(json.dumps(e) for e in entries))

        ctx = extract_session_context(transcript, session_id="test-123")

        assert ctx.current_status == "Fix bug 2"
        assert ctx.planned_next_step == "Fix bug 3"

    def test_skips_system_injected_context(self, tmp_path: Path):
        """Ignores system-injected context (not actual user input)."""
        entries = [
            _create_user_entry("Do the thing", offset=0),
            _create_assistant_entry("Doing the thing.", offset=1),
            _create_user_entry("<system-reminder>This is injected</system-reminder>", offset=100),
            _create_user_entry("Actually do this instead", offset=200),
        ]

        transcript = tmp_path / "session.jsonl"
        transcript.write_text("\n".join(json.dumps(e) for e in entries))

        ctx = extract_session_context(transcript, session_id="test-123")

        assert ctx.initial_prompt == "Do the thing"
        assert ctx.last_user_message == "Actually do this instead"
        # System reminder should not appear in prompts
        assert all("system-reminder" not in p for p in ctx.follow_up_prompts)

    def test_handles_empty_transcript(self, tmp_path: Path):
        """Returns minimal context for empty transcript."""
        transcript = tmp_path / "session.jsonl"
        transcript.write_text("")

        ctx = extract_session_context(
            transcript, session_id="empty-123", project="test"
        )

        assert ctx.session_id == "empty-123"
        assert ctx.project == "test"
        assert ctx.has_meaningful_context() is False

    def test_handles_missing_file(self, tmp_path: Path):
        """Returns minimal context for missing file."""
        nonexistent = tmp_path / "nonexistent.jsonl"

        ctx = extract_session_context(nonexistent, session_id="missing-123")

        assert ctx.session_id == "missing-123"
        assert ctx.has_meaningful_context() is False

    def test_cleans_command_xml(self, tmp_path: Path):
        """Cleans XML-wrapped command prompts for display."""
        entries = [
            _create_user_entry(
                "<command-message>pull</command-message>\n"
                "<command-name>/pull</command-name>\n"
                "<command-args>aops-12345</command-args>",
                offset=0,
            ),
            _create_assistant_entry("Pulling task.", offset=1),
        ]

        transcript = tmp_path / "session.jsonl"
        transcript.write_text("\n".join(json.dumps(e) for e in entries))

        ctx = extract_session_context(transcript, session_id="test-123")

        # Should extract the command with args for context
        assert "/pull" in ctx.initial_prompt
        assert "aops-12345" in ctx.initial_prompt
