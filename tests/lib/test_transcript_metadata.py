"""Tests for CC session metadata capture and Gemini sidecar features.

Covers:
- extract_session_context: first-seen categorical fields, set aggregation for
  git_branches/permission_modes
- UsageStats.thinking_turns: counting thinking/redacted_thinking blocks from
  entry.message["content"] lists (not entry.content which is a dict)
- Entry.from_dict backward compatibility with old-format JSONL (missing new fields)
- Entry.from_dict forward parsing of new CC 2.1+ metadata fields
- reflection_to_insights: session_ctx passes git_branches / permission_modes
  through using plural keys
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure aops-core/lib is importable when running from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AOPS_CORE = str(_REPO_ROOT / "aops-core")
if _AOPS_CORE not in sys.path:
    sys.path.insert(0, _AOPS_CORE)

from lib.transcript_parser import Entry, UsageStats, extract_session_context, reflection_to_insights

# ---------------------------------------------------------------------------
# TestExtractSessionContext
# ---------------------------------------------------------------------------


class TestExtractSessionContext:
    """Tests for extract_session_context(entries) function."""

    def test_extracts_first_seen_values(self):
        """Single entry with all fields — verify values are extracted correctly."""
        entry = Entry(
            type="assistant",
            session_kind="interactive",
            user_type="external",
            entrypoint="cli",
            cwd="/home/user/project",
            client_version="2.1.152",
            git_branch="main",
            permission_mode="auto",
        )
        ctx = extract_session_context([entry])

        assert ctx["session_kind"] == "interactive"
        assert ctx["user_type"] == "external"
        assert ctx["entrypoint"] == "cli"
        assert ctx["cwd"] == "/home/user/project"
        assert ctx["client_version"] == "2.1.152"
        assert "main" in ctx["git_branches"]
        assert "auto" in ctx["permission_modes"]

    def test_collects_git_branches_as_set(self):
        """Two entries with different git_branch values — both should appear in git_branches."""
        entry1 = Entry(type="assistant", git_branch="main")
        entry2 = Entry(type="assistant", git_branch="dev")
        ctx = extract_session_context([entry1, entry2])

        assert "main" in ctx["git_branches"]
        assert "dev" in ctx["git_branches"]
        assert len(ctx["git_branches"]) == 2

    def test_empty_entries_returns_empty_ctx(self):
        """Empty list yields all None scalar fields and empty list fields."""
        ctx = extract_session_context([])

        assert ctx["session_kind"] is None
        assert ctx["user_type"] is None
        assert ctx["entrypoint"] is None
        assert ctx["cwd"] is None
        assert ctx["client_version"] is None
        assert ctx["git_branches"] == []
        assert ctx["permission_modes"] == []

    def test_ignores_none_fields(self):
        """Entries missing session_kind etc. don't break extraction — values stay None."""
        entry = Entry(type="assistant")  # all new metadata fields default to None
        ctx = extract_session_context([entry])

        assert ctx["session_kind"] is None
        assert ctx["user_type"] is None
        assert ctx["git_branches"] == []
        assert ctx["permission_modes"] == []

    def test_first_seen_wins_for_singular_fields(self):
        """session_kind is taken from the first entry that has it; later entries are ignored."""
        entry1 = Entry(type="assistant", session_kind="interactive")
        entry2 = Entry(type="assistant", session_kind="background")
        ctx = extract_session_context([entry1, entry2])

        assert ctx["session_kind"] == "interactive"

    def test_duplicate_git_branches_deduplicated(self):
        """Multiple entries with the same git_branch produce only one entry in the list."""
        entry1 = Entry(type="assistant", git_branch="main")
        entry2 = Entry(type="assistant", git_branch="main")
        ctx = extract_session_context([entry1, entry2])

        assert ctx["git_branches"] == ["main"]


# ---------------------------------------------------------------------------
# TestThinkingTurns
# ---------------------------------------------------------------------------


class TestThinkingTurns:
    """Tests for UsageStats.thinking_turns counting via add_entry()."""

    def test_counts_thinking_block_in_message_content(self):
        """Entry with message.content list containing a thinking block increments thinking_turns."""
        entry = Entry(
            type="assistant",
            message={"content": [{"type": "thinking", "thinking": "let me reason through this"}]},
        )
        stats = UsageStats()
        stats.add_entry(entry)

        assert stats.thinking_turns == 1

    def test_no_thinking_when_content_is_dict(self):
        """Entry with message={} (no content list) yields thinking_turns=0."""
        entry = Entry(
            type="assistant",
            message={},
            # entry.content is a dict — not the list searched for thinking blocks
            content={"type": "thinking", "thinking": "ignored"},
        )
        stats = UsageStats()
        stats.add_entry(entry)

        assert stats.thinking_turns == 0

    def test_counts_redacted_thinking(self):
        """Entry with redacted_thinking block in message.content increments thinking_turns."""
        entry = Entry(
            type="assistant",
            message={"content": [{"type": "redacted_thinking", "data": "AQID"}]},
        )
        stats = UsageStats()
        stats.add_entry(entry)

        assert stats.thinking_turns == 1

    def test_accumulates_across_multiple_entries(self):
        """Multiple entries each with thinking blocks each increment the counter."""
        entry1 = Entry(
            type="assistant",
            message={"content": [{"type": "thinking", "thinking": "step 1"}]},
        )
        entry2 = Entry(
            type="assistant",
            message={"content": [{"type": "thinking", "thinking": "step 2"}]},
        )
        entry3 = Entry(type="assistant", message={})  # no thinking
        stats = UsageStats()
        for e in [entry1, entry2, entry3]:
            stats.add_entry(e)

        assert stats.thinking_turns == 2

    def test_content_list_without_thinking_blocks(self):
        """Content list with only non-thinking blocks does not count as thinking."""
        entry = Entry(
            type="assistant",
            message={"content": [{"type": "text", "text": "Hello"}]},
        )
        stats = UsageStats()
        stats.add_entry(entry)

        assert stats.thinking_turns == 0


# ---------------------------------------------------------------------------
# TestSessionMetadataBackwardCompat
# ---------------------------------------------------------------------------


class TestSessionMetadataBackwardCompat:
    """Tests for Entry.from_dict handling of old-format and new-format JSONL dicts."""

    def test_entry_from_dict_missing_new_fields(self):
        """Old-format dict with only type/uuid/message — from_dict should not raise;
        all new metadata fields default to None."""
        data = {
            "type": "assistant",
            "uuid": "old-entry-uuid",
            "message": {"role": "assistant", "content": "Hello"},
        }
        entry = Entry.from_dict(data)

        assert entry.type == "assistant"
        assert entry.session_kind is None
        assert entry.user_type is None
        assert entry.entrypoint is None
        assert entry.cwd is None
        assert entry.client_version is None
        assert entry.git_branch is None
        assert entry.permission_mode is None
        assert entry.attribution_plugin is None
        assert entry.attribution_skill is None
        assert entry.attribution_mcp_server is None
        assert entry.attribution_mcp_tool is None
        assert entry.stop_reason is None

    def test_entry_from_dict_new_fields_parsed(self):
        """New-format dict with CC 2.1+ metadata fields — from_dict maps camelCase to snake_case."""
        data = {
            "type": "assistant",
            "uuid": "new-entry-uuid",
            "message": {},
            "sessionKind": "bg",
            "userType": "external",
            "entrypoint": "cli",
            "version": "2.1.152",
            "gitBranch": "main",
            "permissionMode": "auto",
            "attributionPlugin": "my-plugin",
            "attributionSkill": "my-skill",
            "attributionMcpServer": "my-server",
            "attributionMcpTool": "my-tool",
        }
        entry = Entry.from_dict(data)

        assert entry.session_kind == "bg"
        assert entry.user_type == "external"
        assert entry.entrypoint == "cli"
        assert entry.client_version == "2.1.152"
        assert entry.git_branch == "main"
        assert entry.permission_mode == "auto"
        assert entry.attribution_plugin == "my-plugin"
        assert entry.attribution_skill == "my-skill"
        assert entry.attribution_mcp_server == "my-server"
        assert entry.attribution_mcp_tool == "my-tool"

    def test_entry_from_dict_stop_reason_from_top_level(self):
        """stopReason at top level of dict is captured in entry.stop_reason."""
        data = {
            "type": "assistant",
            "uuid": "stop-uuid",
            "message": {},
            "stopReason": "end_turn",
        }
        entry = Entry.from_dict(data)

        assert entry.stop_reason == "end_turn"

    def test_entry_from_dict_stop_reason_from_message(self):
        """stop_reason inside message dict is also captured."""
        data = {
            "type": "assistant",
            "uuid": "stop-uuid2",
            "message": {"stop_reason": "max_tokens"},
        }
        entry = Entry.from_dict(data)

        assert entry.stop_reason == "max_tokens"


# ---------------------------------------------------------------------------
# TestInsightsShapeConsistency
# ---------------------------------------------------------------------------


class TestInsightsShapeConsistency:
    """Tests that reflection_to_insights preserves plural keys from session_ctx."""

    def _minimal_reflection(self) -> dict:
        """Return a minimal valid reflection dict accepted by reflection_to_insights."""
        return {
            "outcome": "success",
            "accomplishments": ["shipped the feature"],
            "prompts": "fix the bug",
            "friction_points": [],
            "proposed_changes": [],
        }

    def test_git_branches_uses_plural_key(self):
        """session_ctx with git_branches list — result must have key 'git_branches', not 'git_branch'."""
        ctx = {
            "git_branches": ["main", "dev"],
            "permission_modes": ["auto"],
            "session_kind": "interactive",
        }
        result = reflection_to_insights(
            reflection=self._minimal_reflection(),
            session_id="a1b2c3d4",
            date="2026-05-29",
            project="test-project",
            session_ctx=ctx,
        )

        assert "git_branches" in result, "Expected plural key 'git_branches' in insights result"
        assert result["git_branches"] == ["main", "dev"]
        # Singular key must NOT be present (would indicate a regression)
        assert "git_branch" not in result

    def test_permission_modes_uses_plural_key(self):
        """session_ctx with permission_modes list — result must have key 'permission_modes'."""
        ctx = {
            "git_branches": ["main"],
            "permission_modes": ["auto", "strict"],
            "session_kind": None,
        }
        result = reflection_to_insights(
            reflection=self._minimal_reflection(),
            session_id="b2c3d4e5",
            date="2026-05-29",
            project="test-project",
            session_ctx=ctx,
        )

        assert "permission_modes" in result, (
            "Expected plural key 'permission_modes' in insights result"
        )
        assert set(result["permission_modes"]) == {"auto", "strict"}

    def test_session_ctx_none_values_are_skipped(self):
        """session_ctx fields that are None are not written into the insights result."""
        ctx = {
            "session_kind": None,
            "user_type": None,
            "git_branches": [],
            "permission_modes": [],
        }
        result = reflection_to_insights(
            reflection=self._minimal_reflection(),
            session_id="c3d4e5f6",
            date="2026-05-29",
            project="test-project",
            session_ctx=ctx,
        )

        # None-valued keys should not appear in the result
        assert result.get("session_kind") is None or "session_kind" not in result
        assert result.get("user_type") is None or "user_type" not in result

    def test_session_ctx_passthrough_preserves_session_kind(self):
        """Non-None session_ctx values appear directly in the insights result."""
        ctx = {
            "session_kind": "bg",
            "user_type": "external",
            "entrypoint": "cli",
            "git_branches": [],
            "permission_modes": [],
        }
        result = reflection_to_insights(
            reflection=self._minimal_reflection(),
            session_id="d4e5f6a7",
            date="2026-05-29",
            project="test-project",
            session_ctx=ctx,
        )

        assert result.get("session_kind") == "bg"
        assert result.get("user_type") == "external"
        assert result.get("entrypoint") == "cli"
