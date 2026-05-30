"""Regression test: find_sessions discovers Claude polecat sessions via rglob.

Claude Code stores its JSONL one level deeper than a shallow glob reaches
(e.g. <worker>/claude-sessions/<project>/-workspace/<id>.jsonl).  The fix
uses rglob to find JSONL files at any depth under each project directory.
"""

import json
import sys
from pathlib import Path

import pytest

aops_core_dir = Path(__file__).parent.parent / "aops-core"
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from lib.session_reader import _load_agy_workspace_map, find_sessions


def test_find_sessions_discovers_deeply_nested_claude_polecat_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    A Claude polecat session whose JSONL lives in a -workspace subdirectory
    is discovered by rglob even though a shallow glob would miss it.
    """
    sessions_root = tmp_path / "sessions"
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_root))

    workspace_dir = (
        sessions_root / "polecats" / "worker1" / "claude-sessions" / "project" / "-workspace"
    )
    workspace_dir.mkdir(parents=True)

    session_id = "abcdef123456"
    jsonl_file = workspace_dir / f"{session_id}.jsonl"
    jsonl_file.write_text('{"type":"say","text":"hello"}\n')

    result = find_sessions(
        claude_projects_dir=tmp_path / "no-claude",
        include_gemini=False,
        include_antigravity=False,
        include_cowork=False,
    )

    session_ids = [s.session_id for s in result]
    assert session_id in session_ids, (
        f"Expected session {session_id!r} to be discovered via rglob; got: {session_ids}"
    )


def test_find_sessions_excludes_claude_session_state_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """*-claude-session.json state files are not returned as sessions."""
    sessions_root = tmp_path / "sessions"
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_root))

    workspace_dir = (
        sessions_root / "polecats" / "worker2" / "claude-sessions" / "proj" / "-workspace"
    )
    workspace_dir.mkdir(parents=True)

    state_file = workspace_dir / "abc123-claude-session.json"
    state_file.write_text('{"session_id": "abc123"}')

    result = find_sessions(
        claude_projects_dir=tmp_path / "no-claude",
        include_gemini=False,
        include_antigravity=False,
        include_cowork=False,
    )
    assert result == [], f"State files must not appear as sessions; got: {result}"


def test_find_sessions_excludes_gemini_session_sidecar_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """*-session.json Gemini sidecar files must not be returned as sessions.

    Polecat Gemini workers store a ``*-session.json`` sidecar alongside the
    ``chats/session-*.jsonl`` chat file. This sidecar is Gemini metadata
    (sessionId, gates, turn_count) — NOT a conversation. Before aops-b7e6630a,
    the polecat discovery picked it up via rglob("*.json") and attempted to
    parse it, producing 0 meaningful entries and a spurious skip log line.
    """
    sessions_root = tmp_path / "sessions"
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_root))

    proj_dir = sessions_root / "polecats" / "aops-b7e6630a" / "claude-sessions" / "aops"
    proj_dir.mkdir(parents=True)

    # The Gemini sidecar — must be excluded.
    sidecar = proj_dir / "20260523-2030-c8bffa1d-workspace-gemini-task-b7e6630a-session.json"
    sidecar.write_text('{"sessionId": "c8bffa1d", "global_turn_count": 2}')

    # An AOPS insights file alongside it — also no conversations, just metadata.
    insights = proj_dir / "20260523-2030-c8bffa1d-workspace-gemini-task-b7e6630a.json"
    insights.write_text('{"session_id": "c8bffa1d", "gates": {}}')

    result = find_sessions(
        claude_projects_dir=tmp_path / "no-claude",
        include_gemini=False,
        include_antigravity=False,
        include_cowork=False,
    )

    sidecar_sessions = [s for s in result if "session.json" in s.path.name]
    assert sidecar_sessions == [], (
        f"Gemini *-session.json sidecar must not appear as a session; got: {sidecar_sessions}"
    )


def test_find_sessions_discovers_gemini_bind_mount_chats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gemini polecat chats bind-mounted to the sessions repo are discoverable.

    Polecat mounts ``<sessions_repo>/polecats/<task>/<project>/chats`` into
    the container's ``/home/worker/.gemini/tmp/workspace/chats``, so the
    chats land at the host path without any ``.gemini/tmp/`` prefix. The
    discovery glob must still find them; this guards against a regression
    that would silently drop transcripts (aops-7cf3cd1a / issue #1153).
    """
    sessions_root = tmp_path / "sessions"
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_root))

    chats_dir = sessions_root / "polecats" / "aops-7cf3cd1a" / "aops" / "chats"
    chats_dir.mkdir(parents=True)

    session_id = "a5234d3e"
    chat_file = chats_dir / f"session-2026-05-23T08-18-{session_id}.jsonl"
    chat_file.write_text(
        '{"role": "user", "parts": [{"text": "hi"}]}\n',
        encoding="utf-8",
    )

    result = find_sessions(
        claude_projects_dir=tmp_path / "no-claude",
        include_gemini=True,
        include_antigravity=False,
        include_cowork=False,
    )

    session_ids = [s.session_id for s in result]
    assert session_id in session_ids, (
        f"Expected gemini session {session_id!r} to be discovered at "
        f"bind-mount-source path; got: {session_ids}"
    )


class TestAntigravityCliDiscovery:
    """Tests for agy (antigravity-cli) session discovery."""

    def test_discovers_antigravity_cli_brain_sessions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sessions in ~/.gemini/antigravity-cli/brain/ are discovered."""
        monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        brain_dir = tmp_path / ".gemini" / "antigravity-cli" / "brain" / "abc12345-uuid"
        brain_dir.mkdir(parents=True)
        (brain_dir / "task.md").write_text("# My task")

        result = find_sessions(
            claude_projects_dir=tmp_path / "no-claude",
            include_gemini=False,
            include_antigravity=True,
            include_cowork=False,
        )

        agy_sessions = [s for s in result if s.source == "antigravity"]
        assert len(agy_sessions) == 1
        assert agy_sessions[0].session_id == "abc12345"

    def test_project_attribution_from_history_jsonl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Project name derived from workspace in history.jsonl, not hardcoded."""
        monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        uuid = "deadbeef-1234-5678-9abc-def012345678"
        brain_dir = tmp_path / ".gemini" / "antigravity-cli" / "brain" / uuid
        brain_dir.mkdir(parents=True)
        (brain_dir / "task.md").write_text("# Build dashboard")

        history = tmp_path / ".gemini" / "antigravity-cli" / "history.jsonl"
        history.write_text(
            json.dumps({"conversationId": uuid, "workspace": "/home/nic/src/overwhelm-dashboard"})
            + "\n"
        )

        result = find_sessions(
            claude_projects_dir=tmp_path / "no-claude",
            include_gemini=False,
            include_antigravity=True,
            include_cowork=False,
        )

        agy_sessions = [s for s in result if s.source == "antigravity"]
        assert len(agy_sessions) == 1
        assert agy_sessions[0].project == "overwhelm-dashboard"

    def test_project_attribution_from_last_conversations_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to last_conversations.json when history.jsonl is missing."""
        monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        uuid = "cafebabe-0000-1111-2222-333344445555"
        brain_dir = tmp_path / ".gemini" / "antigravity-cli" / "brain" / uuid
        brain_dir.mkdir(parents=True)
        (brain_dir / "implementation_plan.md").write_text("# Plan")

        cache_dir = tmp_path / ".gemini" / "antigravity-cli" / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "last_conversations.json").write_text(
            json.dumps({"/home/nic/src/labeler": uuid})
        )

        result = find_sessions(
            claude_projects_dir=tmp_path / "no-claude",
            include_gemini=False,
            include_antigravity=True,
            include_cowork=False,
        )

        agy_sessions = [s for s in result if s.source == "antigravity"]
        assert len(agy_sessions) == 1
        assert agy_sessions[0].project == "labeler"

    def test_dedup_prefers_newer_mtime(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When same UUID exists in both old and new paths, newer mtime wins."""
        monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        uuid = "11111111-2222-3333-4444-555566667777"

        old_brain = tmp_path / ".gemini" / "antigravity" / "brain" / uuid
        old_brain.mkdir(parents=True)
        old_file = old_brain / "task.md"
        old_file.write_text("# Old task")

        new_brain = tmp_path / ".gemini" / "antigravity-cli" / "brain" / uuid
        new_brain.mkdir(parents=True)
        new_file = new_brain / "task.md"
        new_file.write_text("# New task")

        import os
        import time

        past = time.time() - 3600
        os.utime(old_file, (past, past))

        result = find_sessions(
            claude_projects_dir=tmp_path / "no-claude",
            include_gemini=False,
            include_antigravity=True,
            include_cowork=False,
        )

        agy_sessions = [s for s in result if s.source == "antigravity"]
        assert len(agy_sessions) == 1
        assert agy_sessions[0].path == new_brain

    def test_fallback_project_name_when_no_workspace_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to 'antigravity' when no workspace mapping exists."""
        monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        brain_dir = tmp_path / ".gemini" / "antigravity-cli" / "brain" / "nomatch-uuid"
        brain_dir.mkdir(parents=True)
        (brain_dir / "task.md").write_text("# Unmapped")

        result = find_sessions(
            claude_projects_dir=tmp_path / "no-claude",
            include_gemini=False,
            include_antigravity=True,
            include_cowork=False,
        )

        agy_sessions = [s for s in result if s.source == "antigravity"]
        assert len(agy_sessions) == 1
        assert agy_sessions[0].project == "antigravity"

    def test_load_agy_workspace_map_empty_when_no_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns empty dict when no agy data files exist."""
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        assert _load_agy_workspace_map() == {}

    def test_project_filter_works_with_workspace_derived_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Project filter matches against workspace-derived project names."""
        monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        uuid = "filterme-1234-5678-9abc-def012345678"
        brain_dir = tmp_path / ".gemini" / "antigravity-cli" / "brain" / uuid
        brain_dir.mkdir(parents=True)
        (brain_dir / "task.md").write_text("# Filtered")

        history = tmp_path / ".gemini" / "antigravity-cli" / "history.jsonl"
        history.write_text(
            json.dumps({"conversationId": uuid, "workspace": "/home/nic/src/my-project"}) + "\n"
        )

        matched = find_sessions(
            project="my-project",
            claude_projects_dir=tmp_path / "no-claude",
            include_gemini=False,
            include_antigravity=True,
            include_cowork=False,
        )
        assert len([s for s in matched if s.source == "antigravity"]) == 1

        not_matched = find_sessions(
            project="other-project",
            claude_projects_dir=tmp_path / "no-claude",
            include_gemini=False,
            include_antigravity=True,
            include_cowork=False,
        )
        assert len([s for s in not_matched if s.source == "antigravity"]) == 0
