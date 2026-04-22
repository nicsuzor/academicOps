"""Regression test: find_sessions discovers Claude polecat sessions via rglob.

Claude Code stores its JSONL one level deeper than a shallow glob reaches
(e.g. <worker>/claude-sessions/<project>/-workspace/<id>.jsonl).  The fix
uses rglob to find JSONL files at any depth under each project directory.
"""

import sys
from pathlib import Path

import pytest

aops_core_dir = Path(__file__).parent.parent / "aops-core"
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from lib.session_reader import find_sessions


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
