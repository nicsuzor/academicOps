"""Tests for system_injected flag on timeline_events and user_prompts array.

Covers aops-519f8e11: producer-side classification of machine-injected user_prompt
turns so consumers can filter without hand-written noise regexes.

Key invariants:
- system_injected=True  → machine authored (task-notification, loaded_context,
                          polecat worker dispatch, skill bodies)
- system_injected=False → human typed (even /learn typed mid-session)
- user_prompts[]        → pre-filtered {timestamp, text} for system_injected=False
"""

from __future__ import annotations

from datetime import UTC, datetime

from lib.transcript_parser import (
    ConversationTurn,
    _is_system_injected_prompt,
    build_user_prompts,
    extract_timeline_events,
)


class TestIsSystemInjectedPrompt:
    """Unit tests for the _is_system_injected_prompt helper."""

    # --- genuinely human-typed: must return False ---

    def test_plain_question_is_user_typed(self) -> None:
        assert _is_system_injected_prompt("fix the login bug") is False

    def test_slash_learn_typed_by_user_is_user_typed(self) -> None:
        # A user typing "/learn" mid-session must NOT be flagged
        assert _is_system_injected_prompt("/learn") is False

    def test_short_follow_up_is_user_typed(self) -> None:
        assert _is_system_injected_prompt("ok, continue") is False

    def test_markdown_text_is_user_typed(self) -> None:
        assert _is_system_injected_prompt("## heading\nsome content") is False

    # --- machine-injected: must return True ---

    def test_empty_string_is_injected(self) -> None:
        assert _is_system_injected_prompt("") is True

    def test_task_notification_only_is_injected(self) -> None:
        text = (
            "<task-notification><task-id>x</task-id>"
            "<status>done</status><summary>ok</summary></task-notification>"
        )
        assert _is_system_injected_prompt(text) is True

    def test_loaded_context_prefix_is_injected(self) -> None:
        text = "<loaded_context>\nsome injected context here\n</loaded_context>"
        assert _is_system_injected_prompt(text) is True

    def test_polecat_worker_dispatch_is_injected(self) -> None:
        text = (
            "You are a polecat worker. Your task has already been claimed...\n\n"
            "## Your Task\n- **ID**: aops-1234\n"
        )
        assert _is_system_injected_prompt(text) is True

    def test_pre_dispatch_preamble_is_injected(self) -> None:
        text = "You are a pre-dispatch agent. Please evaluate..."
        assert _is_system_injected_prompt(text) is True

    def test_skill_body_invoked_prefix_is_injected(self) -> None:
        text = "**Invoked**: /learn\n\n**Purpose**: Learn from sessions..."
        assert _is_system_injected_prompt(text) is True

    def test_skill_body_purpose_prefix_is_injected(self) -> None:
        text = "**Purpose**\nThis skill does...\n"
        assert _is_system_injected_prompt(text) is True

    def test_skill_heading_hash_slash_is_injected(self) -> None:
        # Skill bodies injected as "# /learn\n..." headings
        text = "# /learn\n\nSkill body content here..."
        assert _is_system_injected_prompt(text) is True

    def test_skill_heading_triple_hash_is_injected(self) -> None:
        text = "### /deep-research\n\nResearch harness content..."
        assert _is_system_injected_prompt(text) is True

    def test_system_reminder_only_is_injected(self) -> None:
        text = "<system-reminder>Available agent types...</system-reminder>"
        assert _is_system_injected_prompt(text) is True

    def test_whitespace_only_is_injected(self) -> None:
        assert _is_system_injected_prompt("   \n\n  ") is True


class TestExtractTimelineEventsSystemInjected:
    """system_injected field is set correctly on user_prompt events."""

    def _ts(self, n: int = 0) -> datetime:
        return datetime(2026, 6, 24, 10, n, 0, tzinfo=UTC)

    def _turn(self, text: str, ts_n: int = 0) -> ConversationTurn:
        return ConversationTurn(
            user_message=text,
            assistant_sequence=[],
            start_time=self._ts(ts_n),
            end_time=self._ts(ts_n),
        )

    def test_human_prompt_has_system_injected_false(self) -> None:
        turns = [self._turn("fix the bug", 1)]
        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        assert len(prompts) == 1
        assert prompts[0]["system_injected"] is False

    def test_task_notification_turn_has_system_injected_true(self) -> None:
        text = (
            "<task-notification><task-id>x</task-id>"
            "<status>done</status><summary>ok</summary></task-notification>"
        )
        turns = [self._turn(text, 1)]
        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        assert len(prompts) == 1
        assert prompts[0]["system_injected"] is True

    def test_worker_dispatch_turn_has_system_injected_true(self) -> None:
        text = (
            "You are a polecat worker. Your task has already been claimed.\n\n"
            "## Your Task\n- **ID**: aops-5678\n"
        )
        turns = [self._turn(text, 1)]
        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        assert len(prompts) == 1
        assert prompts[0]["system_injected"] is True

    def test_loaded_context_turn_has_system_injected_true(self) -> None:
        text = "<loaded_context>some big context block</loaded_context>"
        turns = [self._turn(text, 1)]
        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        assert len(prompts) == 1
        assert prompts[0]["system_injected"] is True

    def test_mixed_session_flags_correctly(self) -> None:
        """Human prompts get False, injected turns get True."""
        turns = [
            self._turn(
                "<task-notification><task-id>x</task-id>"
                "<status>done</status><summary>s</summary></task-notification>",
                ts_n=1,
            ),
            self._turn("what does this do?", ts_n=2),
            self._turn("You are a polecat worker. ## Your Task\n- ID: t1\n", ts_n=3),
            self._turn("/learn", ts_n=4),
            self._turn("<loaded_context>ctx</loaded_context>", ts_n=5),
        ]
        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]

        injected_flags = [p["system_injected"] for p in prompts]
        assert injected_flags == [True, False, True, False, True], injected_flags


class TestUserPromptsArray:
    """user_prompts field is built from timeline_events as {timestamp, text} objects."""

    def _ts(self, n: int = 0) -> datetime:
        return datetime(2026, 6, 24, 10, n, 0, tzinfo=UTC)

    def _turn(self, text: str, ts_n: int = 0) -> ConversationTurn:
        return ConversationTurn(
            user_message=text,
            assistant_sequence=[],
            start_time=self._ts(ts_n),
            end_time=self._ts(ts_n),
        )

    def _user_prompts_from_turns(self, turns: list) -> list[dict]:
        """Build user_prompts via the canonical build_user_prompts function."""
        events = extract_timeline_events(turns, "abcd1234")
        return build_user_prompts(events)

    def test_only_human_prompts_in_user_prompts(self) -> None:
        notification = (
            "<task-notification><task-id>x</task-id>"
            "<status>done</status><summary>s</summary></task-notification>"
        )
        turns = [
            self._turn(notification, ts_n=1),
            self._turn("fix the auth flow", ts_n=2),
            self._turn("You are a polecat worker. ## Your Task\n- ID: t1\n", ts_n=3),
            self._turn("ok done", ts_n=4),
        ]
        result = self._user_prompts_from_turns(turns)
        assert len(result) == 2
        texts = [r["text"] for r in result]
        assert "fix the auth flow" in texts
        assert "ok done" in texts

    def test_user_prompts_has_timestamp_and_text_keys(self) -> None:
        turns = [self._turn("hello world", ts_n=1)]
        result = self._user_prompts_from_turns(turns)
        assert len(result) == 1
        assert "timestamp" in result[0]
        assert "text" in result[0]
        assert result[0]["text"] == "hello world"

    def test_empty_session_produces_empty_user_prompts(self) -> None:
        notification = (
            "<task-notification><task-id>x</task-id>"
            "<status>done</status><summary>s</summary></task-notification>"
        )
        turns = [self._turn(notification, ts_n=1)]
        result = self._user_prompts_from_turns(turns)
        assert result == []

    def test_user_prompts_count_matches_filtered_events(self) -> None:
        """user_prompt_count should equal len(user_prompts), not total user_prompt events."""
        notification = (
            "<task-notification><task-id>x</task-id>"
            "<status>done</status><summary>s</summary></task-notification>"
        )
        turns = [
            self._turn(notification, ts_n=1),
            self._turn("real question", ts_n=2),
            self._turn("<loaded_context>ctx</loaded_context>", ts_n=3),
            self._turn("another real question", ts_n=4),
        ]
        events = extract_timeline_events(turns, "abcd1234")
        all_user_prompts = [e for e in events if e.get("type") == "user_prompt"]
        genuine = [e for e in all_user_prompts if not e.get("system_injected")]
        assert len(all_user_prompts) == 4
        assert len(genuine) == 2
