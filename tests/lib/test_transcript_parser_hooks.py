"""Round-trip tests for hook JSONL parsing in transcript_parser.

Covers task-fc938187: ensures gate verdicts, system messages, and context
injections written by aops-core/hooks/unified_logger.py under the
``output`` key (CanonicalHookOutput) are surfaced in the parsed Entry
and rendered in the markdown output.

Also verifies legacy ``hookSpecificOutput`` schema still works.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from lib.transcript_parser import Entry, ParsedSession, SessionProcessor

# A realistic hook JSONL line as written by unified_logger.py — fields use
# snake_case and the gate result lives under ``output`` (CanonicalHookOutput).
HOOK_JSONL_SAMPLE: dict = {
    "session_id": "abcd1234-test-session",
    "logged_at": "2026-04-30T10:00:00+00:00",
    "exit_code": 2,
    "hook_event": "PreToolUse",
    "trace_id": "trace-001",
    "tool_name": "Write",
    "tool_input": {"file_path": "/tmp/x", "content": "..."},
    "transcript_path": "/sessions/abcd1234.jsonl",
    "raw_input": {},
    "output": {
        "system_message": "Write blocked by hydration gate",
        "verdict": "deny",
        "context_injection": "You must run /hydrate before writing",
        "updated_input": None,
        "metadata": {"gate": "hydration"},
    },
}


# Legacy Claude Code protocol shape — the data lives under hookSpecificOutput.
LEGACY_JSONL_SAMPLE: dict = {
    "type": "system_reminder",
    "timestamp": "2026-04-30T10:01:00+00:00",
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "exitCode": 0,
        "additionalContext": "Legacy CC context",
        "verdict": "allow",
    },
}


@pytest.fixture
def hook_jsonl_file(tmp_path: Path) -> Path:
    p = tmp_path / "hook.jsonl"
    with p.open("w") as f:
        f.write(json.dumps(HOOK_JSONL_SAMPLE) + "\n")
        f.write(json.dumps(LEGACY_JSONL_SAMPLE) + "\n")
    return p


class TestHookJsonlExtraction:
    def test_extracts_verdict_from_output_key(self, hook_jsonl_file: Path) -> None:
        parser = SessionProcessor()
        entries = parser._load_hook_entries(hook_jsonl_file)

        assert len(entries) == 2
        gate = entries[0]
        assert isinstance(gate, Entry)
        assert gate.hook_verdict == "deny"
        assert gate.hook_system_message == "Write blocked by hydration gate"
        assert gate.hook_context_injection == "You must run /hydrate before writing"
        assert gate.hook_event_name == "PreToolUse"
        assert gate.tool_name == "Write"
        assert gate.hook_exit_code == 2

    def test_legacy_hookspecificoutput_still_works(self, hook_jsonl_file: Path) -> None:
        parser = SessionProcessor()
        entries = parser._load_hook_entries(hook_jsonl_file)

        legacy = entries[1]
        assert legacy.hook_event_name == "UserPromptSubmit"
        assert legacy.hook_exit_code == 0
        assert legacy.additional_context == "Legacy CC context"
        # Verdict in CC schema also propagates
        assert legacy.hook_verdict == "allow"

    def test_map_function_handles_both_schemas_simultaneously(self) -> None:
        """Both output (our JSONL) AND hookSpecificOutput in one row."""
        merged = {
            "logged_at": "2026-04-30T10:00:00+00:00",
            "hook_event": "PreToolUse",
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "from cc",
            },
            "output": {
                "verdict": "ask",
                "system_message": "From canonical",
            },
        }

        entry_data = SessionProcessor._map_hook_jsonl_to_entry_data(merged)
        hso = entry_data["hookSpecificOutput"]
        # Both schemas merged into a single hookSpecificOutput dict
        assert hso["additionalContext"] == "from cc"
        assert hso["verdict"] == "ask"
        assert hso["systemMessage"] == "From canonical"
        assert hso["hookEventName"] == "PreToolUse"


class TestMarkdownRendering:
    def test_verdict_and_system_message_rendered_in_markdown(self, hook_jsonl_file: Path) -> None:
        parser = SessionProcessor()
        entries = parser._load_hook_entries(hook_jsonl_file)

        # Render in 'full' mode so all hook content is included
        session = ParsedSession(uuid="abcd1234-test-session")
        md = parser.format_session_as_markdown(
            session=session, entries=entries, agent_entries={}, variant="full"
        )

        assert "deny" in md, f"verdict 'deny' missing from markdown:\n{md}"
        assert "Write blocked by hydration gate" in md, (
            f"system_message missing from markdown:\n{md}"
        )
        # Context injection: either surfaced via the session-context section
        # at the top of the transcript, or tagged with +ctx Nc on the
        # compact tool-hook line.
        assert "+ctx" in md or "Hook context injections" in md
        # 'allow' verdict on legacy entry should NOT appear (default verdict suppressed)
        # but additional context should
        assert "Legacy CC context" in md
