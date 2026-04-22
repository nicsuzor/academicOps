"""Regression test: find_sessions discovers Claude polecat sessions via state-file index.

Claude Code stores its JSONL one level deeper than the standard glob depth
(e.g. <worker>/claude-sessions/<project>/-workspace/<id>.jsonl).  The fix
adds a secondary scan for *-claude-session.json state files whose jsonl_path
field points to the JSONL, allowing discovery regardless of nesting depth.
"""

import json
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
    (below the glob depth) is discovered via the *-claude-session.json index.

    Without the state-file index scan, find_sessions would return an empty list
    because glob("*.jsonl") only reaches one level deep from claude_sessions_dir.
    """
    sessions_root = tmp_path / "sessions"
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_root))

    # JSONL is nested one level deeper than the standard glob reaches:
    # <sessions>/polecats/<worker>/claude-sessions/<project>/-workspace/<id>.jsonl
    workspace_dir = (
        sessions_root / "polecats" / "worker1" / "claude-sessions" / "project" / "-workspace"
    )
    workspace_dir.mkdir(parents=True)

    session_id = "abcdef123456"
    jsonl_file = workspace_dir / f"{session_id}.jsonl"
    jsonl_file.write_text('{"type":"say","text":"hello"}\n')

    # State file is a sibling of the JSONL; jsonl_path stores the container-internal
    # absolute path (which won't resolve on the host — only the filename matters).
    state_file = workspace_dir / f"{session_id}-claude-session.json"
    state_file.write_text(
        json.dumps({"jsonl_path": f"/container/internal/path/{session_id}.jsonl"})
    )

    result = find_sessions(
        claude_projects_dir=tmp_path / "no-claude",
        include_gemini=False,
        include_antigravity=False,
        include_cowork=False,
    )

    session_ids = [s.session_id for s in result]
    assert session_id in session_ids, (
        f"Expected session {session_id!r} to be discovered via state-file index; got: {session_ids}"
    )


def test_find_sessions_skips_state_file_without_jsonl_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """State files with no jsonl_path field are silently skipped."""
    sessions_root = tmp_path / "sessions"
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_root))

    # Put the state file in -workspace/ so it's below the glob's reach but
    # still found by rglob; no jsonl_path means it should be silently skipped.
    workspace_dir = (
        sessions_root / "polecats" / "worker2" / "claude-sessions" / "proj" / "-workspace"
    )
    workspace_dir.mkdir(parents=True)

    state_file = workspace_dir / "no-path-claude-session.json"
    state_file.write_text(json.dumps({"other_field": "value"}))

    result = find_sessions(
        claude_projects_dir=tmp_path / "no-claude",
        include_gemini=False,
        include_antigravity=False,
        include_cowork=False,
    )
    assert result == []
