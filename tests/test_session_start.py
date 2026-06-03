"""Test SessionStart gate functionality.

All tests use real objects and tmp_path — no mocks.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent / "aops-core"
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from hooks.schemas import HookContext
from hooks.session_env_setup import run_session_env_setup
from lib.gate_model import GateResult, GateVerdict
from lib.session_state import SessionState


def test_session_start_message_generation(tmp_path: Path, monkeypatch) -> None:
    """Verify SessionStart gate generates the correct info message."""
    # Point path resolution at tmp_path so real files get created there
    status_dir = tmp_path / "status"
    status_dir.mkdir()
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(status_dir))

    hook_log = tmp_path / "hooks.jsonl"
    monkeypatch.setattr(
        "hooks.session_env_setup.get_hook_log_path",
        lambda sid, transcript_path=None, date=None, client_type=None: hook_log,
    )

    state_file = status_dir / "20260410-10-abc12345.json"
    # Patch in both modules that import get_session_file_path
    state_file_fn = lambda sid, date=None, transcript_path=None, client_type=None: state_file
    monkeypatch.setattr(
        "hooks.session_env_setup.get_session_file_path",
        state_file_fn,
    )
    monkeypatch.setattr(
        "lib.session_state.get_session_file_path",
        state_file_fn,
    )

    # Disable automode install check during tests
    monkeypatch.setattr("hooks.session_env_setup.is_installed", lambda: True, raising=False)

    state = SessionState(
        session_id="session-123",
        date=datetime.now().strftime("%Y-%m-%d"),
        started_at=datetime.now().isoformat(),
    )

    ctx = HookContext(
        session_id="session-123",
        session_short_hash="abc12345",
        hook_event="SessionStart",
        raw_input={"session_id": "session-123"},
    )

    result = run_session_env_setup(ctx, state)

    assert result is not None
    assert isinstance(result, GateResult)
    assert result.verdict == GateVerdict.ALLOW

    # Check system_message has brief user-facing summary
    assert "Session Started: session-123" in result.system_message
    assert "abc12345" in result.system_message
    assert "State File:" in result.system_message
    assert str(state_file) in result.system_message
    assert f"Version: {state.version}" in result.system_message

    # Verify the state file was actually created on disk
    assert state_file.exists(), "State file should have been written to disk"


def test_session_start_ignored_for_other_events(tmp_path: Path, monkeypatch) -> None:
    """Non-SessionStart events return None."""
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))

    state = SessionState(
        session_id="session-456",
        date=datetime.now().strftime("%Y-%m-%d"),
        started_at=datetime.now().isoformat(),
    )

    ctx = HookContext(
        session_id="session-456",
        session_short_hash="def67890",
        hook_event="PreToolUse",
        raw_input={"session_id": "session-456"},
    )

    result = run_session_env_setup(ctx, state)
    assert result is None
