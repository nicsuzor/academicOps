"""Tests for discovering container/polecat sessions in $AOPS_SESSIONS/logs."""

import shutil
from pathlib import Path

from transcripts.runner import find_session_files, load_session

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"
SUBAGENT_FIXTURE = FIXTURES_DIR / "claude_subagent.jsonl"
SUBAGENT_META_FIXTURE = FIXTURES_DIR / "claude_subagent.meta.json"
AGY_FIXTURE = FIXTURES_DIR / "agy_session.jsonl"


def test_polecat_claude_session_discovery(tmp_path: Path) -> None:
    """Claude polecat trunk session under $AOPS_SESSIONS/logs is discovered, subagents and hooks are skipped."""
    sessions_dir = tmp_path / "sessions"
    project_dir = sessions_dir / "logs" / "20260805" / "session-claude-1" / "aops"
    subagents_dir = project_dir / "trunk-uuid-123" / "subagents"
    subagents_dir.mkdir(parents=True)

    trunk_file = project_dir / "trunk-uuid-123.jsonl"
    shutil.copy(CLAUDE_FIXTURE, trunk_file)
    shutil.copy(SUBAGENT_FIXTURE, subagents_dir / "agent-sub1.jsonl")
    shutil.copy(SUBAGENT_META_FIXTURE, subagents_dir / "agent-sub1.meta.json")
    (project_dir / "polecat-session-hooks.jsonl").write_text(
        '{"event": "start"}\n', encoding="utf-8"
    )

    found = find_session_files(sessions_dir)

    assert trunk_file in found
    assert not any("subagents" in p.parts for p in found)
    assert not any(p.name == "polecat-session-hooks.jsonl" for p in found)


def test_polecat_agy_session_discovery(tmp_path: Path) -> None:
    """agy polecat session under $AOPS_SESSIONS/logs/date/session/project/agy-brain/... is discovered."""
    sessions_dir = tmp_path / "sessions"
    brain_dir = (
        sessions_dir
        / "logs"
        / "20260805"
        / "session-agy-1"
        / "aops"
        / "agy-brain"
        / "01234567-89ab-cdef-0123-456789abcdef"
    )
    brain_dir.mkdir(parents=True)

    agy_file = brain_dir / "transcript.jsonl"
    shutil.copy(AGY_FIXTURE, agy_file)

    found = find_session_files(sessions_dir)

    assert agy_file in found
    loaded = load_session(agy_file)
    assert loaded is not None
    assert loaded.session_id != "unknown"


def test_discovery_ignores_runner_output_dir(tmp_path: Path) -> None:
    """Runner output under $AOPS_SESSIONS/transcripts/ is ignored during discovery."""
    sessions_dir = tmp_path / "sessions"
    transcripts_dir = sessions_dir / "transcripts" / "2026-08"
    transcripts_dir.mkdir(parents=True)

    (transcripts_dir / "20260805-07-aops-test.md").write_text("# Summary", encoding="utf-8")
    (transcripts_dir / "20260805-07-aops-test.full.md").write_text("# Full", encoding="utf-8")
    (transcripts_dir / "20260805-07-aops-test.html").write_text("<html/>", encoding="utf-8")
    (transcripts_dir / "20260805-07-aops-test.json").write_text("{}", encoding="utf-8")

    found = find_session_files(sessions_dir)

    assert not any("transcripts" in p.parts for p in found)


def test_discovery_with_empty_or_missing_logs_dir(tmp_path: Path) -> None:
    """Discovery does not crash when $AOPS_SESSIONS has no logs/ directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    found = find_session_files(sessions_dir)
    assert isinstance(found, list)
