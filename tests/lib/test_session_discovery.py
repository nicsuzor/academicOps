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
    from lib.session_reader import SessionState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id="session1",
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionState.PENDING_TRANSCRIPT


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

    from lib.session_reader import SessionState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id="session1",
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionState.PENDING_TRANSCRIPT


def test_identify_unprocessed_missing_mining(mock_env):
    """Transcript exists but no mining JSON is unprocessed."""
    date_str = datetime.now(UTC).strftime("%Y%m%d")

    # Create transcript (newer than session)
    create_mock_transcript(mock_env["aca_data"], date_str, "my-project", "session1", mtime_offset=0)

    # Create raw session (older)
    session_file = mock_env["projects"] / "my-project" / "session1.jsonl"
    create_mock_session(session_file, "my-project", "session1", mtime_offset=-60)

    from lib.session_reader import SessionState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id="session1",
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionState.PENDING_MINING


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

    from lib.session_reader import SessionState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id="session1",
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionState.PROCESSED


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

    from lib.session_reader import SessionInfo, SessionState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="my-project",
        session_id=full_id,
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])
    assert state == SessionState.PROCESSED


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

    from lib.session_reader import SessionInfo, SessionState, get_session_state

    session_info = SessionInfo(
        path=session_file,
        project="academicOps",
        session_id=full_id,
        last_modified=datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC),
    )

    state = get_session_state(session_info, mock_env["aca_data"])

    # The proof: even with UUID vs Prefix mismatch, it finds the transcript and sees it is newer
    assert state == SessionState.PROCESSED
