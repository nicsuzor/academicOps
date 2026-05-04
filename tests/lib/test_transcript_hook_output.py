"""Round-trip tests for transcript parser reading hook gate results from CanonicalHookOutput.

Covers task-fc938187: the parser must read verdict/system_message/context_injection
from data["output"] (CanonicalHookOutput written by hooks/unified_logger.py) — not
just from data["hookSpecificOutput"] (Claude-Code-native protocol). The fallback
to hookSpecificOutput remains for legacy/CC-native logs.
"""

from __future__ import annotations

import json
from pathlib import Path

from lib.transcript_parser import SessionProcessor, SessionSummary


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


class TestHookOutputRoundTrip:
    """Verify gate results survive the logger->parser->markdown pipeline."""

    def test_canonical_hook_output_fields_surface_on_entry(self, tmp_path: Path) -> None:
        """A real-shape hook JSONL record (matching unified_logger.py:69) is parsed
        into an Entry whose verdict/system_message/context_injection are populated.
        """
        hook_file = tmp_path / "test-hooks.jsonl"
        # Real-shape record: HookLogEntry fields (HookContext + logged_at + exit_code +
        # output containing CanonicalHookOutput dump).
        record = {
            "session_id": "sess-fc938187",
            "trace_id": "trace-1",
            "hook_event": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
            "transcript_path": "/tmp/sess-fc938187.jsonl",
            "logged_at": "2026-04-30T10:00:00+00:00",
            "exit_code": 1,
            "output": {
                "system_message": "Deny: rm -rf is destructive.",
                "verdict": "deny",
                "context_injection": "Reminder: destructive bash blocked by policy.",
                "updated_input": None,
                "metadata": {"gate": "PolicyEnforcer"},
            },
            "raw_input": {},
        }
        _write_jsonl(hook_file, [record])

        processor = SessionProcessor()
        entries = processor._load_hook_entries(hook_file)

        assert len(entries) == 1
        entry = entries[0]
        assert entry.type == "system_reminder"
        assert entry.hook_event_name == "PreToolUse"
        assert entry.tool_name == "Bash"
        assert entry.hook_verdict == "deny"
        assert entry.hook_system_message == "Deny: rm -rf is destructive."
        assert entry.hook_context_injection == ("Reminder: destructive bash blocked by policy.")

    def test_legacy_hookspecificoutput_fallback_still_works(self, tmp_path: Path) -> None:
        """If a record only has hookSpecificOutput (CC-native shape), fields still surface."""
        hook_file = tmp_path / "legacy-hooks.jsonl"
        record = {
            "session_id": "sess-legacy",
            "hook_event": "PreToolUse",
            "logged_at": "2026-04-30T10:00:00+00:00",
            "exit_code": 0,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "verdict": "allow",
                "systemMessage": "ok",
                "contextInjection": "legacy injection",
            },
        }
        _write_jsonl(hook_file, [record])

        processor = SessionProcessor()
        entries = processor._load_hook_entries(hook_file)

        assert len(entries) == 1
        entry = entries[0]
        assert entry.hook_verdict == "allow"
        assert entry.hook_system_message == "ok"
        assert entry.hook_context_injection == "legacy injection"

    def test_canonical_output_overrides_hookspecific_when_both_present(
        self, tmp_path: Path
    ) -> None:
        """CanonicalHookOutput.output is the authoritative source — wins over the legacy key."""
        hook_file = tmp_path / "both-hooks.jsonl"
        record = {
            "session_id": "sess-both",
            "hook_event": "PreToolUse",
            "logged_at": "2026-04-30T10:00:00+00:00",
            "exit_code": 1,
            "output": {
                "verdict": "deny",
                "system_message": "canonical wins",
                "context_injection": None,
                "metadata": {},
            },
            "hookSpecificOutput": {
                "verdict": "allow",
                "systemMessage": "legacy loses",
            },
        }
        _write_jsonl(hook_file, [record])

        processor = SessionProcessor()
        entries = processor._load_hook_entries(hook_file)

        entry = entries[0]
        assert entry.hook_verdict == "deny"
        assert entry.hook_system_message == "canonical wins"

    def test_hook_results_render_in_markdown(self, tmp_path: Path) -> None:
        """format_session_as_markdown renders verdict + system_message + context_injection
        with recognisable markers (🛑 Hook denied / ℹ️ Hook message / Injected context).
        """
        hook_file = tmp_path / "render-hooks.jsonl"
        record = {
            "session_id": "sess-render",
            "hook_event": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
            "logged_at": "2026-04-30T10:00:00+00:00",
            "exit_code": 1,
            "output": {
                "system_message": "Deny: rm -rf is destructive.",
                "verdict": "deny",
                "context_injection": "Reminder: destructive bash blocked by policy.",
                "metadata": {},
            },
        }
        _write_jsonl(hook_file, [record])

        processor = SessionProcessor()
        entries = processor._load_hook_entries(hook_file)

        session = SessionSummary(uuid="sess-render", summary="Test session")
        markdown = processor.format_session_as_markdown(
            session, entries, agent_entries=None, variant="full"
        )

        # Tool-related hooks (PreToolUse/PostToolUse) render as compact
        # one-line annotations. The blocking-verdict marker, the system
        # message, and the context-injection size all need to be visible.
        assert "🛑" in markdown, f"Blocking verdict marker missing from markdown:\n{markdown}"
        assert "deny" in markdown
        assert "Deny: rm -rf is destructive." in markdown, (
            f"System message missing from markdown:\n{markdown}"
        )
        # Context injection is surfaced via session-context section ("Hook
        # context injections") plus a +ctx Nc tag in the compact line.
        assert "+ctx" in markdown or "Hook context injections" in markdown
