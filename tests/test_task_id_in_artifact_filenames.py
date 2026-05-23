"""End-to-end test: $AOPS_TASK_ID flows into every session-bound artifact filename.

Acceptance criteria:
  Given a task ID, a single grep across $AOPS_SESSIONS returns ALL artefacts
  for that task (transcripts, hook logs, client logs, session JSON, status
  files). Polecat sessions include task ID in all filenames, not just the
  parent directory.

This is the integration check. The unit-level coverage of
``generate_session_filename(task_id=...)`` lives in
``tests/lib/test_session_naming.py::TestTaskIdAlignment``. Here we verify
that *every writer callsite* passes ``task_id`` through, by exercising the
public path-builder API with ``AOPS_TASK_ID`` set in the environment.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# 8-char hex shortform is the grep target. The full task ID has the form
# ``task-<8-hex>-<slug>``; we expect every artefact filename to contain
# ``task-<8-hex>``.
TASK_ID = "task-deadbeef-test-fixture"
TASK_SHORT = "deadbeef"
SESSION_ID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture(autouse=True)
def _clear_env_vars(monkeypatch):
    """Clear env vars that leak from live sessions (mirrors test_session_paths)."""
    for var in (
        "AOPS_SESSION_STATE_DIR",
        "AOPS_HOOK_LOG_PATH",
        "AOPS_GATE_FILE_ENFORCER",
        "GEMINI_SESSION_ID",
        "POLECAT_CREW_NAME",
        "POLECAT_SESSION_TYPE",
        "CLAUDE_PROJECT_DIR",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AOPS_MACHINE", "testmachine")


@pytest.fixture
def aops_sessions(tmp_path: Path, monkeypatch) -> Path:
    """Point AOPS_SESSIONS at a tmp directory with the standard subdirs."""
    sessions = tmp_path / "sessions"
    for sub in ("transcripts", "summaries", "hooks", "client-logs", "status"):
        (sessions / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions))
    return sessions


@pytest.fixture
def with_task_id(monkeypatch):
    """Set AOPS_TASK_ID to the test value."""
    monkeypatch.setenv("AOPS_TASK_ID", TASK_ID)


@pytest.fixture
def without_task_id(monkeypatch):
    """Ensure AOPS_TASK_ID is unset (negative-test fixture)."""
    monkeypatch.delenv("AOPS_TASK_ID", raising=False)


# ---------------------------------------------------------------------------
# Positive: AOPS_TASK_ID set → task short hash appears in every filename
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "artifact_type,subdir",
    [
        ("transcript-full", "transcripts"),
        ("transcript-abridged", "transcripts"),
        ("insights", "summaries"),
        ("hooks", "hooks"),
        ("client", "client-logs"),
    ],
)
def test_generate_session_filename_includes_task_short_hash(artifact_type, subdir, with_task_id):
    """Each artifact type — passed task_id — must contain the 8-char hash."""
    from lib import session_naming

    filename = session_naming.generate_session_filename(
        SESSION_ID,
        timestamp=datetime(2026, 4, 30, 12, 34).astimezone(),
        repo="academicops",
        slug="session",
        artifact_type=artifact_type,
        task_id=os.environ.get("AOPS_TASK_ID"),
    )
    assert TASK_SHORT in filename, (
        f"{artifact_type} filename {filename!r} missing task short hash {TASK_SHORT!r}"
    )
    assert f"task-{TASK_SHORT}" in filename, (
        f"{artifact_type} filename {filename!r} missing 'task-' prefix"
    )


def test_hook_log_path_includes_task_short_hash(aops_sessions, with_task_id):
    """get_hook_log_path reads $AOPS_TASK_ID and embeds it in the filename."""
    from lib.session_paths import get_hook_log_path

    path = get_hook_log_path(SESSION_ID, date="2026-04-30T12:34:00+00:00")
    assert TASK_SHORT in path.name, f"hook log {path.name!r} missing {TASK_SHORT!r}"
    assert path.name.endswith("-hooks.jsonl")


def test_session_file_path_includes_task_short_hash(aops_sessions, with_task_id):
    """get_session_file_path reads $AOPS_TASK_ID and embeds it in the filename."""
    from lib.session_paths import get_session_file_path

    # Stub status dir resolution to land on aops_sessions
    with patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": str(aops_sessions / "status")}):
        path = get_session_file_path(SESSION_ID, date="2026-04-30T12:34:00+00:00")
    assert TASK_SHORT in path.name, f"session JSON {path.name!r} missing {TASK_SHORT!r}"


def test_gate_file_path_includes_task_short_hash(aops_sessions, with_task_id):
    """get_gate_file_path reads $AOPS_TASK_ID and embeds it in the filename."""
    from lib.session_paths import get_gate_file_path

    path = get_gate_file_path("enforcer", SESSION_ID, date="2026-04-30T12:34:00+00:00")
    assert TASK_SHORT in path.name, f"gate file {path.name!r} missing {TASK_SHORT!r}"
    assert path.name.endswith("-enforcer.md")


def test_insights_file_path_includes_task_short_hash(aops_sessions, with_task_id):
    """insights_generator.get_insights_file_path reads $AOPS_TASK_ID."""
    from lib.insights_generator import get_insights_file_path

    path = get_insights_file_path(
        date="2026-04-30",
        session_id=SESSION_ID,
        slug="something",
        project="academicops",
        hour="12",
    )
    assert TASK_SHORT in path.name, f"insights file {path.name!r} missing {TASK_SHORT!r}"


def test_transcript_filename_includes_task_short_hash(aops_sessions, with_task_id):
    """scripts/transcript._generate_transcript_filename embeds task_id from env."""
    import sys
    from pathlib import Path as P

    # Ensure scripts/ is importable
    repo_root = P(__file__).parent.parent
    scripts_dir = repo_root / "aops-core" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from transcript import _generate_transcript_filename

    fake_session_path = aops_sessions / f"{SESSION_ID}.jsonl"
    fake_session_path.write_text('{"timestamp":"2026-04-30T12:34:00Z"}\n')

    base, _, _, _, _ = _generate_transcript_filename(fake_session_path, entries=[])
    assert TASK_SHORT in base, f"transcript base {base!r} missing {TASK_SHORT!r}"


# ---------------------------------------------------------------------------
# Single-grep contract: a single hash is reachable across all subdirs
# ---------------------------------------------------------------------------


def test_single_grep_finds_all_artifacts(aops_sessions, with_task_id):
    """End-to-end: write one filename per subdir, then grep finds all of them."""
    from lib import session_naming

    timestamp = datetime(2026, 4, 30, 12, 34).astimezone()
    written: list[Path] = []
    for artifact_type, subdir in (
        ("transcript-full", "transcripts"),
        ("transcript-abridged", "transcripts"),
        ("insights", "summaries"),
        ("hooks", "hooks"),
        ("client", "client-logs"),
    ):
        filename = session_naming.generate_session_filename(
            SESSION_ID,
            timestamp=timestamp,
            repo="academicops",
            slug="session",
            artifact_type=artifact_type,
            task_id=os.environ.get("AOPS_TASK_ID"),
        )
        path = aops_sessions / subdir / filename
        path.write_text("test")
        written.append(path)

    # Single grep across $AOPS_SESSIONS for the task short hash
    found = list(aops_sessions.rglob(f"*{TASK_SHORT}*"))
    found_names = {p.name for p in found}
    expected_names = {p.name for p in written}
    assert expected_names <= found_names, (
        f"single-grep failed to find every artefact. missing: {expected_names - found_names}"
    )


# ---------------------------------------------------------------------------
# Negative: AOPS_TASK_ID unset → no fake hex masquerading as a task ID
# ---------------------------------------------------------------------------


def test_no_task_id_no_task_prefix_in_filename(without_task_id):
    """Non-task sessions must not get a fabricated 'task-XXXXXXXX-' segment."""
    from lib import session_naming

    filename = session_naming.generate_session_filename(
        SESSION_ID,
        timestamp=datetime(2026, 4, 30, 12, 34).astimezone(),
        repo="academicops",
        slug="session",
        task_id=os.environ.get("AOPS_TASK_ID"),  # None
    )
    assert "task-" not in filename, f"non-task session leaked 'task-' into filename {filename!r}"


def test_no_task_id_hook_log_no_task_prefix(aops_sessions, without_task_id):
    """get_hook_log_path with no AOPS_TASK_ID must not embed a task prefix."""
    from lib.session_paths import get_hook_log_path

    path = get_hook_log_path(SESSION_ID, date="2026-04-30T12:34:00+00:00")
    assert "task-" not in path.name, f"non-task hook log leaked 'task-' into filename {path.name!r}"


def test_no_task_id_session_file_no_task_prefix(aops_sessions, without_task_id):
    """get_session_file_path with no AOPS_TASK_ID must not embed a task prefix."""
    from lib.session_paths import get_session_file_path

    with patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": str(aops_sessions / "status")}):
        path = get_session_file_path(SESSION_ID, date="2026-04-30T12:34:00+00:00")
    assert "task-" not in path.name, (
        f"non-task session JSON leaked 'task-' into filename {path.name!r}"
    )


# ---------------------------------------------------------------------------
# find_sessions() must still work (existing-discovery contract)
# ---------------------------------------------------------------------------


def test_existing_transcript_glob_still_matches_task_prefixed_filename(aops_sessions, with_task_id):
    """get_session_state's transcript-discovery walk must keep matching.

    session_reader uses ``*-*-{session_prefix}*-abridged.md`` to find a
    transcript by session prefix. Adding ``-task-XXXXXXXX-`` between the
    shortform and the slug must not break that pattern, and the lookup must
    walk both flat-legacy and rotated ``YYYY-MM/`` layouts (aops-b975b185).
    """
    from lib import session_naming
    from lib.transcript_paths import iter_rotated_files

    timestamp = datetime(2026, 4, 30, 12, 34).astimezone()
    filename = session_naming.generate_session_filename(
        SESSION_ID,
        timestamp=timestamp,
        repo="academicops",
        slug="session",
        artifact_type="transcript-abridged",
        task_id=os.environ.get("AOPS_TASK_ID"),
    )
    # Place under the rotated subdir — exercises the new layout end-to-end.
    rotated_dir = aops_sessions / "transcripts" / "2026-04"
    rotated_dir.mkdir(parents=True, exist_ok=True)
    path = rotated_dir / filename
    path.write_text("# test transcript")

    session_prefix = SESSION_ID[:8]
    matches = list(
        iter_rotated_files(aops_sessions / "transcripts", f"*-*-{session_prefix}*-abridged.md")
    )
    assert path in matches, (
        f"recursive walk failed to surface rotated transcript {path!r}; matches={matches!r}"
    )
