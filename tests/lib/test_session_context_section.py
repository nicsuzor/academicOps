"""Tests for the ``## Session Context`` section in transcript markdown.

The Session Context section surfaces injected and read bootstrap material at
the top of a transcript so a reviewer can see what the agent had visible
before its first response. Three categories are covered:

  1. Software-injected hook context (``contextInjection`` payloads, files
     loaded via hooks like CLAUDE.md / MEMORY.md echoes).
  2. System reminders (``additionalContext`` from system_reminder entries).
  3. Agent-read files (``Read`` tool calls in the first ~10 turns).

Sessions with none of the above should NOT render the section at all.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lib.session_reader import SessionProcessor


def _ts(offset_seconds: int = 0) -> str:
    base = datetime(2025, 6, 1, 9, 0, 0, tzinfo=UTC)
    return (base + timedelta(seconds=offset_seconds)).isoformat().replace("+00:00", "Z")


def _user(prompt: str, offset: int = 0) -> dict:
    return {
        "type": "user",
        "uuid": f"user-{offset}",
        "timestamp": _ts(offset),
        "message": {"content": [{"type": "text", "text": prompt}]},
    }


def _assistant_text(text: str, offset: int = 0) -> dict:
    return {
        "type": "assistant",
        "uuid": f"asst-{offset}",
        "timestamp": _ts(offset),
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _read_tool_use(file_path: str, tool_id: str, offset: int = 0) -> dict:
    return {
        "type": "assistant",
        "uuid": f"toolu-{offset}",
        "timestamp": _ts(offset),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": "Read",
                    "input": {"file_path": file_path},
                }
            ]
        },
    }


def _read_tool_result(tool_id: str, body: str, offset: int = 0) -> dict:
    return {
        "type": "user",
        "uuid": f"toolr-{offset}",
        "timestamp": _ts(offset),
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": body,
                }
            ]
        },
    }


def _hook_context_injection(
    files_loaded: list[str],
    injection: str,
    event: str = "SessionStart",
    offset: int = 0,
) -> dict:
    return {
        "type": "system_reminder",
        "uuid": f"hook-inj-{offset}",
        "timestamp": _ts(offset),
        "hookSpecificOutput": {
            "hookEventName": event,
            "exitCode": 0,
            "filesLoaded": files_loaded,
            "contextInjection": injection,
        },
    }


def _system_reminder(text: str, event: str = "PostToolUse", offset: int = 0) -> dict:
    return {
        "type": "system_reminder",
        "uuid": f"sysrem-{offset}",
        "timestamp": _ts(offset),
        "hookSpecificOutput": {
            "hookEventName": event,
            "exitCode": 0,
            "additionalContext": text,
        },
    }


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


def _render(session_path: Path, variant: str) -> str:
    processor = SessionProcessor()
    summary, entries, agent_entries = processor.parse_session_file(session_path)
    return processor.format_session_as_markdown(
        summary,
        entries,
        agent_entries=agent_entries,
        variant=variant,
    )


def _extract_section(md: str, heading: str = "## Session Context") -> str:
    """Slice out just the Session Context section so assertions about its
    contents aren't polluted by content rendered elsewhere in the transcript
    (e.g. the same Read shown again inside a turn body, or the per-turn
    hook rendering that lives outside the structured section).

    The Session Context section ends at:
      - the next top-level ``## `` heading, OR
      - the first per-turn ``> 🪝`` header (unified compact rendering), OR
      - the first legacy ``### Hook:`` header (old rendering, kept for safety), OR
      - the first legacy ``- Hook(`` bullet (older rendering, kept for safety).
    """
    if heading not in md:
        return ""
    start = md.index(heading)
    rest = md[start + len(heading) :]
    candidates = []
    next_h2 = rest.find("\n## ")
    if next_h2 != -1:
        candidates.append(next_h2)
    per_turn_hook = rest.find("\n> 🪝")
    if per_turn_hook != -1:
        candidates.append(per_turn_hook)
    legacy_hook_h3 = rest.find("\n### Hook:")
    if legacy_hook_h3 != -1:
        candidates.append(legacy_hook_h3)
    legacy_hook = rest.find("\n- Hook(")
    if legacy_hook != -1:
        candidates.append(legacy_hook)
    if not candidates:
        return md[start:]
    end = min(candidates)
    return md[start : start + len(heading) + end]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSessionContextSection:
    def test_section_omitted_when_no_context(self, tmp_path: Path) -> None:
        """A session with only normal user/assistant turns has no Session
        Context section at all (silent no-op)."""
        session_file = tmp_path / "no-context.jsonl"
        _write_jsonl(
            session_file,
            [
                _user("Hello, what's 2+2?", offset=0),
                _assistant_text("4", offset=1),
            ],
        )
        for variant in ("abridged", "full"):
            md = _render(session_file, variant)
            assert "## Session Context" not in md, (
                f"Expected no Session Context section in {variant} variant when "
                f"no context was injected/read, but found one."
            )

    def test_abridged_lists_filenames_only(self, tmp_path: Path) -> None:
        """Abridged variant surfaces filenames + labels but not file bodies."""
        session_file = tmp_path / "abridged.jsonl"
        long_injection = "CLAUDE.md content " * 80  # ~1.5kb
        long_read_body = "Repository file body line\n" * 60  # > 500 chars
        _write_jsonl(
            session_file,
            [
                _hook_context_injection(
                    files_loaded=["/repo/CLAUDE.md", "/repo/.agents/CORE.md"],
                    injection=long_injection,
                    event="SessionStart",
                    offset=0,
                ),
                _system_reminder(
                    "Reminder: verify before claiming success.",
                    event="PostToolUse",
                    offset=1,
                ),
                _user("Look at the readme", offset=2),
                _read_tool_use("/repo/README.md", "tool-1", offset=3),
                _read_tool_result("tool-1", long_read_body, offset=4),
                _assistant_text("Reviewed.", offset=5),
            ],
        )
        md = _render(session_file, "abridged")
        section = _extract_section(md)

        assert section, "Session Context section must be present in abridged"
        # Hook injection: filenames surfaced as basenames, NOT full body.
        assert "CLAUDE.md" in section
        assert "CORE.md" in section
        assert "Hook context injections" in section
        # The long injection body itself should NOT be inlined in abridged.
        assert long_injection not in section
        # System reminder summary should appear (label + char count).
        assert "PostToolUse" in section
        # Early Read filename surfaced.
        assert "README.md" in section
        # Body of the Read should NOT appear in the Session Context section
        # itself (the Read body still appears later inside its turn).
        assert "Repository file body line" not in section

    def test_full_includes_bodies_with_details_for_long(self, tmp_path: Path) -> None:
        """Full variant includes full bodies; long ones go inside <details>."""
        session_file = tmp_path / "full.jsonl"
        long_injection = "Bootstrap context line.\n" * 40  # > 500 chars
        short_reminder = "Short reminder."
        long_read_body = "// File contents\n" * 60  # > 500 chars
        short_read_body = "tiny file"
        _write_jsonl(
            session_file,
            [
                _hook_context_injection(
                    files_loaded=["/repo/MEMORY.md"],
                    injection=long_injection,
                    event="SessionStart",
                    offset=0,
                ),
                _system_reminder(short_reminder, event="UserPromptSubmit", offset=1),
                _user("read two files", offset=2),
                _read_tool_use("/repo/big.txt", "t-1", offset=3),
                _read_tool_result("t-1", long_read_body, offset=4),
                _read_tool_use("/repo/small.txt", "t-2", offset=5),
                _read_tool_result("t-2", short_read_body, offset=6),
                _assistant_text("Done.", offset=7),
            ],
        )
        md = _render(session_file, "full")
        section = _extract_section(md)

        assert section, "Session Context section must be present in full"

        # Long hook injection wrapped in <details>; long Read body too.
        details_count = section.count("<details>")
        assert details_count >= 2, (
            f"Expected at least 2 <details> blocks (long injection + long Read), "
            f"got {details_count}. Section:\n{section[:2000]}"
        )
        # Full injection body present (inside details).
        assert "Bootstrap context line." in section
        # Short reminder NOT wrapped in details — appears as a code block.
        assert short_reminder in section
        # Long Read body fully present (in details).
        assert "// File contents" in section
        # Short Read body present in the section.
        assert short_read_body in section

    def test_abridged_and_full_diverge(self, tmp_path: Path) -> None:
        """Abridged is filenames-only; full surfaces actual bodies."""
        session_file = tmp_path / "diverge.jsonl"
        injection = "Bootstrap line.\n" * 5  # Short, inline in full mode.
        _write_jsonl(
            session_file,
            [
                _hook_context_injection(
                    files_loaded=["/repo/CLAUDE.md"],
                    injection=injection,
                    event="SessionStart",
                    offset=0,
                ),
                _user("ok", offset=1),
                _assistant_text("ok", offset=2),
            ],
        )
        abridged_md = _render(session_file, "abridged")
        full_md = _render(session_file, "full")
        abridged = _extract_section(abridged_md)
        full = _extract_section(full_md)

        # Abridged section must NOT contain the injection body verbatim
        # (although the body may still appear in the existing per-turn hook
        # rendering further down — that is unrelated to this section).
        assert "Bootstrap line." not in abridged
        # Full section MUST contain it.
        assert "Bootstrap line." in full
        # Both sections should reference the loaded file.
        assert "CLAUDE.md" in abridged
        assert "CLAUDE.md" in full

    def test_idempotent_regeneration(self, tmp_path: Path) -> None:
        """Re-rendering the same session twice produces identical sections."""
        session_file = tmp_path / "idem.jsonl"
        _write_jsonl(
            session_file,
            [
                _hook_context_injection(
                    files_loaded=["/repo/CLAUDE.md"],
                    injection="Some context.",
                    event="SessionStart",
                    offset=0,
                ),
                _system_reminder("Reminder text.", event="PostToolUse", offset=1),
                _user("hello", offset=2),
                _read_tool_use("/repo/notes.md", "tid-1", offset=3),
                _read_tool_result("tid-1", "notes body", offset=4),
                _assistant_text("ack", offset=5),
            ],
        )
        first = _render(session_file, "full")
        second = _render(session_file, "full")
        # Strip the date_str / first_timestamp from frontmatter — those are
        # derived from entry timestamps which ARE deterministic in this
        # fixture, so the entire output must match byte-for-byte.
        assert first == second, "Session Context rendering must be idempotent"

    def test_hook_only_session_renders(self, tmp_path: Path) -> None:
        """Sessions with hook injections but NO early Reads still render the
        section (just the hook bullets)."""
        session_file = tmp_path / "hook-only.jsonl"
        _write_jsonl(
            session_file,
            [
                _hook_context_injection(
                    files_loaded=["/repo/CLAUDE.md"],
                    injection="Hook context.",
                    event="SessionStart",
                    offset=0,
                ),
                _user("hi", offset=1),
                _assistant_text("hi back", offset=2),
            ],
        )
        for variant in ("abridged", "full"):
            md = _render(session_file, variant)
            assert "## Session Context" in md, (
                f"Hook-only session should still render Session Context "
                f"({variant}). Got:\n{md[:1500]}"
            )
            assert "CLAUDE.md" in md
            assert "Early file reads" not in md, (
                f"No Reads happened — early-reads block should not appear ({variant})."
            )

    def test_reads_after_max_turns_are_excluded(self, tmp_path: Path) -> None:
        """Reads happening after the early-turn window do not pollute the
        Session Context section."""
        session_file = tmp_path / "late-reads.jsonl"
        entries: list[dict] = []
        # 12 conversation turns; the Read happens in turn 12 — past the
        # default max_turns=10 window.
        offset = 0
        for turn_idx in range(12):
            entries.append(_user(f"turn {turn_idx}", offset=offset))
            offset += 1
            entries.append(_assistant_text(f"reply {turn_idx}", offset=offset))
            offset += 1
        # Now a late Read.
        entries.append(_read_tool_use("/repo/late.md", "late-1", offset=offset))
        offset += 1
        entries.append(_read_tool_result("late-1", "late body", offset=offset))
        _write_jsonl(session_file, entries)

        for variant in ("abridged", "full"):
            md = _render(session_file, variant)
            # No injected/read bootstrap context at all → section omitted.
            assert "## Session Context" not in md, (
                f"Late-only Reads should not produce a Session Context section ({variant})."
            )
