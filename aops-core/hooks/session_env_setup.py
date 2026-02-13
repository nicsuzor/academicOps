#!/usr/bin/env python3
"""
Session environment setup hook for Claude Code.

Ensures AOPS, PYTHONPATH, and other required environment variables are
persisted for the duration of the Claude Code session using CLAUDE_ENV_FILE.
"""

import os
import sys
from pathlib import Path

# Ensure aops-core is in path for imports
HOOK_DIR = Path(__file__).parent
AOPS_CORE_DIR = HOOK_DIR.parent
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from lib.gate_model import GateResult, GateVerdict
from lib.session_paths import get_session_status_dir

from hooks.schemas import HookContext

# Gate enforcement mode environment variables
GATE_MODE_VARS = ("CUSTODIET_MODE", "TASK_GATE_MODE", "HYDRATION_GATE_MODE")
DEFAULT_GATE_MODE = "warn"


def set_persistent_env(env_dict: dict[str, str]):
    """Set environment variables persistently for the session, if possible."""

    # Claude Code support -- write to CLAUDE_ENV_FILE provided in session start hook:
    if env_path := os.environ.get("CLAUDE_ENV_FILE"):
        try:
            with open(env_path, "a") as f:
                for key, value in env_dict.items():
                    f.write(f"export {key}={value}\n")
        except Exception as e:
            print(f"WARNING: Failed to write to CLAUDE_ENV_FILE: {e}", file=sys.stderr)


def run_session_env_setup(ctx: HookContext) -> GateResult | None:
    """
    Logic from session_env_setup.sh migrated to Python.

    Sets:
    - CLAUDE_SESSION_ID
    - PYTHONPATH (includes aops-core)
    - AOPS_SESSION_STATE_DIR
    - AOPS_HOOK_LOG_PATH
    - Default gate enforcement modes (CUSTODIET_MODE, TASK_GATE_MODE, HYDRATION_GATE_MODE)
    - Other placeholder variables from original script
    """
    if ctx.hook_event != "SessionStart":
        return None

    persist = {}

    # 1. Persist Session ID
    if ctx.session_id:
        persist["CLAUDE_SESSION_ID"] = ctx.session_id

    # 2. Persist PYTHONPATH
    # Include aops-core in PYTHONPATH so hooks and scripts can find lib/
    aops_core = str(AOPS_CORE_DIR)
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    if aops_core not in current_pythonpath:
        new_pythonpath = f"{aops_core}:{current_pythonpath}".strip(":")
        persist["PYTHONPATH"] = new_pythonpath

    # 3. Persist AOPS_SESSION_STATE_DIR

    # Use centralized resolution from session_paths.py
    try:
        status_dir = get_session_status_dir(ctx.session_id, ctx.raw_input)
        persist["AOPS_SESSION_STATE_DIR"] = str(status_dir)
    except Exception as e:
        print(f"WARNING: Failed to determine session status dir: {e}", file=sys.stderr)

    # 4. Default Enforcement Modes (fail-safe defaults to "warn" if not set)
    # <!-- NS: no magic literals. -->
    # <!-- @claude 2026-02-07: Fixed. Extracted to GATE_MODE_VARS and DEFAULT_GATE_MODE constants at module level. -->
    for mode_var in GATE_MODE_VARS:
        current_val = os.environ.get(mode_var, DEFAULT_GATE_MODE)
        persist[mode_var] = current_val

    # Persist all environment variables
    set_persistent_env(persist)

    return GateResult(
        verdict=GateVerdict.ALLOW,
        metadata={"source": "session_env_setup", "persisted_vars": persist},
    )
