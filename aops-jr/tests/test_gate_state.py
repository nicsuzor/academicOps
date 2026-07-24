"""State helper: one JSON file per session, in a temp dir."""

import sys
from pathlib import Path

_JR_HOOKS = str(Path(__file__).resolve().parent.parent / "hooks")
if _JR_HOOKS not in sys.path:
    sys.path.insert(0, _JR_HOOKS)

from gates import state as gate_state


def test_load_missing_session_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_GATE_STATE_DIR", str(tmp_path))
    assert gate_state.load("no-such-session") == {}


def test_save_then_load_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_GATE_STATE_DIR", str(tmp_path))
    gate_state.save("s1", {"flag": True, "n": 3})
    assert gate_state.load("s1") == {"flag": True, "n": 3}


def test_sessions_are_isolated_by_id(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_GATE_STATE_DIR", str(tmp_path))
    gate_state.save("s1", {"a": 1})
    gate_state.save("s2", {"a": 2})
    assert gate_state.load("s1") == {"a": 1}
    assert gate_state.load("s2") == {"a": 2}


def test_corrupt_state_file_is_treated_as_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_GATE_STATE_DIR", str(tmp_path))
    (tmp_path / "s1.json").write_text("not json")
    assert gate_state.load("s1") == {}
