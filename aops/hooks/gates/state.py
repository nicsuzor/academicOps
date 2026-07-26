"""Trivial per-session state: one JSON file per session in a temp dir.

No ``SessionState`` module, no naming/paths subsystem, no import cycle.
Stateful gates mutate the dict the dispatcher hands them; the dispatcher
saves it back after every run. Stateless gates take the same dict and
ignore it.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def _state_dir() -> Path:
    override = os.environ.get("AOPS_GATE_STATE_DIR")
    base = Path(override) if override else Path(tempfile.gettempdir()) / "aops-gate-state"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _path(session_id: str) -> Path:
    return _state_dir() / f"{session_id or 'unknown'}.json"


def load(session_id: str) -> dict:
    path = _path(session_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save(session_id: str, state: dict) -> None:
    _path(session_id).write_text(json.dumps(state))
