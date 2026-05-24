"""Gate posture — resolved at SessionStart, immutable for the session.

Provides get_gate_mode() for all gate checks. Reads from:
  1. The posture file (AOPS_GATE_POSTURE_FILE) — written at SessionStart and
     locked read-only (chmod 444). Mid-session env var changes (e.g. agent
     appending to CLAUDE_ENV_FILE) cannot affect it.
  2. os.environ fallback — backward compat / no-posture-file environments
     (tests, minimal installs without polecat).
  3. Built-in defaults.

Fix for GitHub issue #1234: gate posture was previously re-resolved from
os.environ at every hook-fire. An agent that appended to CLAUDE_ENV_FILE
could weaken its own enforcement surface mid-session.
"""

import json
import os
import stat
from pathlib import Path

POSTURE_FILE_ENV = "AOPS_GATE_POSTURE_FILE"

_ENV_VAR_MAP: dict[str, str] = {
    "handover": "HANDOVER_GATE_MODE",
    "qa": "QA_GATE_MODE",
    "enforcer": "ENFORCER_GATE_MODE",
    "hydration": "HYDRATION_GATE_MODE",
    "ida": "IDA_GATE_MODE",
    "enforcer_threshold": "ENFORCER_TOOL_CALL_THRESHOLD",
}

_DEFAULTS: dict[str, str] = {
    "handover": "warn",
    "qa": "warn",
    "enforcer": "warn",
    "hydration": "off",
    "ida": "warn",
    "enforcer_threshold": "50",
}


def get_gate_mode(name: str) -> str:
    """Return gate mode string for the given short gate name.

    Args:
        name: "handover", "qa", "enforcer", "hydration", "ida", or
              "enforcer_threshold".

    Read order:
      1. AOPS_GATE_POSTURE_FILE (locked at SessionStart) — preferred.
      2. Env var fallback (HANDOVER_GATE_MODE, etc.) — backward compat.
      3. Built-in default.
    """
    posture_path = os.environ.get(POSTURE_FILE_ENV)
    if posture_path:
        try:
            data = json.loads(Path(posture_path).read_text())
            if name in data:
                return str(data[name])
        except (OSError, json.JSONDecodeError):
            pass

    env_var = _ENV_VAR_MAP.get(name)
    if env_var:
        env_val = os.environ.get(env_var)
        if env_val is not None:
            return env_val

    return _DEFAULTS.get(name, "warn")


def write_posture_file(path: Path) -> None:
    """Snapshot current gate posture to path and lock it read-only (chmod 444).

    Reads gate modes from os.environ (stamped at container launch by
    polecat/_apply_gate_env, or set by the user's shell environment).
    Called once at SessionStart, before the agent can issue any tool calls.

    After writing, the file is made read-only so the agent cannot overwrite
    it — even if it later appends to CLAUDE_ENV_FILE.
    """
    data = {
        name: os.environ.get(env_var, _DEFAULTS[name]) for name, env_var in _ENV_VAR_MAP.items()
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 444
