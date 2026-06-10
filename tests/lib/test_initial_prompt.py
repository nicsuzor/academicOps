"""Tests for initial-prompt extraction and cleaning (aops-efffc1f7).

The overwhelm dashboard needs the user's own first substantive prompt to answer
"what was I doing here?". These cover the two helpers that derive it from raw
timeline events:

  - ``clean_prompt_text``    — strip control envelopes + worker-preamble scaffolding
  - ``extract_initial_prompt`` — first ``user_prompt`` event that survives cleaning
"""

from __future__ import annotations

from lib.transcript_parser import clean_prompt_text, extract_initial_prompt


class TestCleanPromptText:
    def test_empty_returns_empty(self) -> None:
        assert clean_prompt_text("") == ""
        assert clean_prompt_text(None) == ""  # type: ignore[arg-type]

    def test_plain_prompt_unchanged(self) -> None:
        assert clean_prompt_text("fix the login bug") == "fix the login bug"

    def test_strips_task_notification_envelope(self) -> None:
        text = (
            "<task-notification><task-id>x</task-id><status>done</status>"
            "<summary>ok</summary></task-notification>\nnow do the next thing"
        )
        cleaned = clean_prompt_text(text)
        assert "task-notification" not in cleaned
        assert cleaned == "now do the next thing"

    def test_strips_system_reminder(self) -> None:
        text = "<system-reminder>be honest</system-reminder>\nreal user words"
        assert clean_prompt_text(text) == "real user words"

    def test_strips_tool_use_id(self) -> None:
        text = "<tool-use-id>abc123</tool-use-id> actual prompt"
        cleaned = clean_prompt_text(text)
        assert "tool-use-id" not in cleaned
        assert "actual prompt" in cleaned

    def test_strips_worker_preamble_to_task_spec(self) -> None:
        text = (
            "You are a polecat worker. Your task has already been claimed and your "
            "worktree is ready; the task context is below.\n\n"
            "**Search the PKB first.** Before you act...\n\n"
            "## Your Task\n\n- **ID**: aops-1234\n- **Title**: do the thing\n"
        )
        cleaned = clean_prompt_text(text)
        assert "You are a polecat worker" not in cleaned
        assert cleaned.startswith("## Your Task")
        assert "do the thing" in cleaned

    def test_non_worker_preamble_text_preserved(self) -> None:
        # A prompt that merely mentions "task" must not be truncated.
        text = "Please refactor the Your Task section of the README"
        assert clean_prompt_text(text) == text


class TestExtractInitialPrompt:
    def test_none_events(self) -> None:
        assert extract_initial_prompt(None) is None
        assert extract_initial_prompt([]) is None

    def test_first_substantive_prompt(self) -> None:
        events = [
            {"type": "user_prompt", "description": "what does this code do?"},
            {"type": "tool_call", "tool": "Read"},
            {"type": "user_prompt", "description": "now fix it"},
        ]
        assert extract_initial_prompt(events) == "what does this code do?"

    def test_skips_control_only_prompt(self) -> None:
        # First user turn is a pure auto-resume notification → skip to the real one.
        events = [
            {
                "type": "user_prompt",
                "description": "<task-notification><task-id>x</task-id>"
                "<status>done</status><summary>s</summary></task-notification>",
            },
            {"type": "user_prompt", "description": "the real first ask"},
        ]
        assert extract_initial_prompt(events) == "the real first ask"

    def test_ignores_non_user_prompt_events(self) -> None:
        events = [
            {"type": "tool_call", "tool": "Bash", "description": "ls"},
            {"type": "task_create", "description": "make a task"},
            {"type": "user_prompt", "description": "hello there"},
        ]
        assert extract_initial_prompt(events) == "hello there"

    def test_all_control_returns_none(self) -> None:
        events = [
            {"type": "user_prompt", "description": "<system-reminder>x</system-reminder>"},
        ]
        assert extract_initial_prompt(events) is None
