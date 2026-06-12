"""Tests for session discovery and state tracking.

Defines the authoritative behavior for identifying unprocessed sessions.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from lib.session_reader import SessionInfo


def create_mock_session(path: Path, project: str, session_id: str, mtime_offset: int = 0) -> Path:
    """Create a mock session file with specified mtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"sessionId": session_id}))

    # Set mtime
    mtime = datetime.now(UTC) + timedelta(seconds=mtime_offset)
    os.utime(path, (mtime.timestamp(), mtime.timestamp()))
    return path


def create_mock_transcript(
    aca_data: Path, date_str: str, project: str, session_id: str, mtime_offset: int = 0
) -> Path:
    """Create a mock transcript file."""
    # Pattern: YYYYMMDD-project-sessionid-abridged.md
    transcript_dir = aca_data / "sessions" / "claude"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    prefix = session_id[:8]
    transcript_path = transcript_dir / f"{date_str}-{project}-{prefix}-abridged.md"
    transcript_path.write_text("# Mock Transcript")

    # Set mtime
    mtime = datetime.now(UTC) + timedelta(seconds=mtime_offset)
    os.utime(transcript_path, (mtime.timestamp(), mtime.timestamp()))
    return transcript_path


def create_mock_mining_json(aca_data: Path, session_id: str, mtime_offset: int = 0) -> Path:
    """Create a mock mining JSON file.

    v3.2: Unified session file at $ACA_DATA/sessions/summaries/{date}-{session_prefix}.json
    """
    mining_dir = aca_data / "sessions" / "summaries"
    mining_dir.mkdir(parents=True, exist_ok=True)

    # v1.0 format: {date}-{session_prefix}.json
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    session_prefix = session_id[:8] if len(session_id) >= 8 else session_id
    mining_path = mining_dir / f"{date_str}-{session_prefix}.json"
    mining_path.write_text(json.dumps({"session_id": session_id}))

    # Set mtime
    mtime = datetime.now(UTC) + timedelta(seconds=mtime_offset)
    os.utime(mining_path, (mtime.timestamp(), mtime.timestamp()))
    return mining_path


@pytest.fixture
def mock_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set up mock environment for discovery."""
    claude_projects = tmp_path / "claude_projects"
    aca_data = tmp_path / "aca_data"

    claude_projects.mkdir(exist_ok=True)
    aca_data.mkdir(exist_ok=True)

    monkeypatch.setenv("ACA_DATA", str(aca_data))
    # Mock get_sessions_dir to point to our claude_projects

    return {
        "projects": claude_projects,
        "aca_data": aca_data,
    }


def test_identify_unprocessed_missing_transcript(mock_env):
    """Session without transcript is unprocessed."""
    # Create raw session
    session_file = mock_env["projects"] / "my-project" / "session1.jsonl"
    create_mock_session(session_file, "my-project", "session1")

    # Use our (to be implemented) consolidated logic
    from lib.session_reader import SessionPipelineState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id="session1",
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionPipelineState.PENDING_TRANSCRIPT


def test_identify_unprocessed_outdated_transcript(mock_env):
    """Session newer than transcript is unprocessed."""
    # Create transcript first (older)
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    create_mock_transcript(
        mock_env["aca_data"], date_str, "my-project", "session1", mtime_offset=-60
    )

    # Create raw session (newer)
    session_file = mock_env["projects"] / "my-project" / "session1.jsonl"
    create_mock_session(session_file, "my-project", "session1", mtime_offset=0)

    from lib.session_reader import SessionPipelineState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id="session1",
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionPipelineState.PENDING_TRANSCRIPT


def test_identify_unprocessed_missing_mining(mock_env):
    """Transcript exists but no mining JSON is unprocessed."""
    date_str = datetime.now(UTC).strftime("%Y%m%d")

    # Create transcript (newer than session)
    create_mock_transcript(mock_env["aca_data"], date_str, "my-project", "session1", mtime_offset=0)

    # Create raw session (older)
    session_file = mock_env["projects"] / "my-project" / "session1.jsonl"
    create_mock_session(session_file, "my-project", "session1", mtime_offset=-60)

    from lib.session_reader import SessionPipelineState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id="session1",
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionPipelineState.PENDING_MINING


def test_identify_processed_full_id(mock_env):
    """Session with both transcript and full ID mining JSON is processed."""
    date_str = datetime.now(UTC).strftime("%Y%m%d")

    # Create mining JSON (newest)
    create_mock_mining_json(mock_env["aca_data"], "session1", mtime_offset=0)

    # Create transcript (middle)
    create_mock_transcript(
        mock_env["aca_data"], date_str, "my-project", "session1", mtime_offset=-30
    )

    # Create raw session (oldest)
    session_file = mock_env["projects"] / "my-project" / "session1.jsonl"
    create_mock_session(session_file, "my-project", "session1", mtime_offset=-60)

    from lib.session_reader import SessionPipelineState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id="session1",
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionPipelineState.PROCESSED


def test_identify_processed_prefix_id(mock_env):
    """Session with both transcript and prefix ID mining JSON is processed."""
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    full_id = "abc12345def67890"
    prefix = "abc12345"

    # Create mining JSON with prefix (newest)
    create_mock_mining_json(mock_env["aca_data"], prefix, mtime_offset=0)

    # Create transcript (middle)
    create_mock_transcript(mock_env["aca_data"], date_str, "my-project", full_id, mtime_offset=-30)

    # Create raw session (oldest)
    session_file = mock_env["projects"] / "my-project" / f"{full_id}.jsonl"
    create_mock_session(session_file, "my-project", full_id, mtime_offset=-60)

    from lib.session_reader import SessionInfo, SessionPipelineState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id=full_id,
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionPipelineState.PROCESSED


def test_idempotency_transcript_newer_than_session(mock_env):
    """If transcript is newer than session, it should be marked PROCESSED (idempotent)."""
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    full_id = "138295b6-8274-4861-9568-3a3ba05cc9b3"
    prefix = "138295b6"

    # 1. Create Raw Session (Oldest)
    session_file = mock_env["projects"] / "academicOps" / f"{full_id}.jsonl"
    create_mock_session(session_file, "academicOps", full_id, mtime_offset=-3600)  # 1 hour ago

    # 2. Create Transcript (Middle)
    create_mock_transcript(
        mock_env["aca_data"], date_str, "academicOps", full_id, mtime_offset=-1800
    )  # 30 mins ago

    # 3. Create Mining JSON (Newest)
    create_mock_mining_json(mock_env["aca_data"], prefix, mtime_offset=0)  # Now

    from lib.session_reader import SessionInfo, SessionPipelineState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="academicOps",
        session_id=full_id,
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])

    # The proof: even with UUID vs Prefix mismatch, it finds the transcript and sees it is newer
    assert state == SessionPipelineState.PROCESSED


def test_find_sessions_dedupes_cowork(monkeypatch, tmp_path):
    from lib.session_reader import find_sessions

    # Setup mock claude dir with ingested cowork-logs
    claude_projects_dir = tmp_path / "claude_projects"
    cowork_logs = tmp_path / "sessions" / "cowork-logs" / "12345678"
    cowork_logs.mkdir(parents=True)
    (cowork_logs / "session.jsonl").write_text("{}")

    # Mock get_sessions_repo
    monkeypatch.setattr("lib.session_reader.get_sessions_repo", lambda: tmp_path / "sessions")

    # Setup mock raw cowork dir
    raw_root = tmp_path / "raw_cowork"
    raw_session_dir = raw_root / "org_abc" / "local_12345678-abcd" / "outputs"
    raw_session_dir.mkdir(parents=True)
    (raw_session_dir / "audit.jsonl").write_text("{}")

    # Mock cowork_source_roots
    monkeypatch.setattr("lib.session_reader.cowork_source_roots", lambda: [raw_root])

    sessions = find_sessions(
        claude_projects_dir=claude_projects_dir,
        include_gemini=False,
        include_antigravity=False,
        include_cowork=True,
    )

    # Both ingested and raw share the '12345678' prefix, they should be deduped
    assert len(sessions) == 1
    # The ingested one is found first in claude_dirs loop
    assert sessions[0].session_id == "12345678"
    assert sessions[0].project == "12345678"


def test_find_sessions_raw_cowork(monkeypatch, tmp_path):
    from lib.session_reader import find_sessions

    # Setup mock raw cowork dir with no ingested overlap
    raw_root = tmp_path / "raw_cowork"
    raw_session_dir = raw_root / "org_abc" / "local_99999999-abcd" / "outputs"
    raw_session_dir.mkdir(parents=True)
    (raw_session_dir / "audit.jsonl").write_text("{}")

    # Mock cowork_source_roots
    monkeypatch.setattr("lib.session_reader.cowork_source_roots", lambda: [raw_root])

    sessions = find_sessions(
        claude_projects_dir=tmp_path / "claude_projects",
        include_gemini=False,
        include_antigravity=False,
        include_cowork=True,
    )

    assert len(sessions) == 1
    assert sessions[0].session_id == "99999999"
    assert sessions[0].project == "cowork"


def test_find_sessions_antigravity_cli_new_format(monkeypatch, tmp_path):
    """New antigravity-cli brain dirs have no top-level markdown — the whole
    conversation lives under .system_generated/logs/. Discovery must find them
    by the structured transcript jsonl, not require a .md file (which used to
    silently drop every new-format session).
    """
    from lib.session_reader import find_sessions

    fake_home = tmp_path / "home"
    brain = fake_home / ".gemini" / "antigravity-cli" / "brain"
    logs = brain / "60e16c42-a07a-4c65-9ed7-f7362162bc7e" / ".system_generated" / "logs"
    logs.mkdir(parents=True)
    (logs / "transcript_full.jsonl").write_text(
        json.dumps(
            {
                "step_index": 0,
                "source": "USER_EXPLICIT",
                "type": "USER_INPUT",
                "status": "DONE",
                "created_at": "2026-06-03T04:47:47Z",
                "content": "<USER_REQUEST>\nhi\n</USER_REQUEST>",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(fake_home))

    sessions = find_sessions(
        claude_projects_dir=tmp_path / "claude_projects",
        include_gemini=False,
        include_antigravity=True,
        include_cowork=False,
    )

    ag = [s for s in sessions if s.source == "antigravity"]
    assert len(ag) == 1
    assert ag[0].session_id == "60e16c42"
