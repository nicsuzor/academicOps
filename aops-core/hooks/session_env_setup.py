#!/usr/bin/env -S uv run python
"""
Session environment setup hook for Claude Code.

Ensures AOPS, PYTHONPATH, and other required environment variables are
persisted for the duration of the Claude Code session using CLAUDE_ENV_FILE.
"""

import os
import shlex
import sys
from pathlib import Path

# Ensure aops-core is in path for imports
HOOK_DIR = Path(__file__).parent
AOPS_CORE_DIR = HOOK_DIR.parent
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from lib.gate_model import GateResult, GateVerdict
from lib.session_paths import (
    get_all_gate_file_paths,
    get_hook_log_path,
    get_session_file_path,
    get_session_status_dir,
)
from lib.session_state import SessionState

from hooks.schemas import HookContext


def set_persistent_env(env_dict: dict[str, str]):
    """Set environment variables persistently for the session, if possible."""

    # Claude Code support -- write to CLAUDE_ENV_FILE provided in session start hook:
    if env_path := os.environ.get("CLAUDE_ENV_FILE"):
        try:
            with open(env_path, "a") as f:
                for key, value in env_dict.items():
                    f.write(f"export {key}={shlex.quote(value)}\n")
        except Exception as e:
            print(f"WARNING: Failed to write to CLAUDE_ENV_FILE: {e}", file=sys.stderr)


def run_session_env_setup(ctx: HookContext, state: SessionState) -> GateResult | None:
    """Session start initialization - fail-fast checks and user messages.


    Sets:
    - CLAUDE_SESSION_ID
    - PYTHONPATH (includes aops-core)
    - AOPS_SESSION_STATE_DIR
    - AOPS_HOOK_LOG_PATH
    - Other placeholder variables from original script

    """

    if ctx.hook_event != "SessionStart":
        return None

    persist = {}

    # Use precomputed short_hash from context
    short_hash = ctx.session_short_hash
    hook_log_path = get_hook_log_path(ctx.session_id, ctx.raw_input)
    state_file_path = get_session_file_path(ctx.session_id, input_data=ctx.raw_input)
    status_dir = get_session_status_dir(ctx.session_id, ctx.raw_input)

    # Fail-fast: ensure state file can be written
    if not state_file_path.exists():
        try:
            state.save()
        except OSError as e:
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"FAIL-FAST: Cannot write session state file.\n"
                    f"Path: {state_file_path}\n"
                    f"Error: {e}\n"
                    f"Fix: Check directory permissions and disk space."
                ),
                metadata={"source": "session_start", "error": str(e)},
            )

    transcript_path = ctx.raw_input.get("transcript_path", "") if ctx.raw_input else ""

    # Session started messages
    messages = [
        f"Session Started: {ctx.session_id} ({short_hash})",
        f"Version: {state.version}",
        f"State File: {state_file_path}",
        f"Hooks log: {hook_log_path}",
        f"Transcript: {transcript_path}",
    ]

    # Bridge userConfig → ACA_DATA for Claude Code plugin installs.
    # Claude exports plugin userConfig values as CLAUDE_PLUGIN_OPTION_<KEY>.
    # Persist as ACA_DATA so all hooks/scripts can find it.
    if not os.environ.get("ACA_DATA") and os.environ.get("CLAUDE_PLUGIN_OPTION_ACA_DATA"):
        aca_data_val = os.environ["CLAUDE_PLUGIN_OPTION_ACA_DATA"]
        persist["ACA_DATA"] = aca_data_val
        os.environ["ACA_DATA"] = aca_data_val

    # Check pkb binary availability
    from lib.binary_install import check_pkb_available

    pkb_status = check_pkb_available()
    if pkb_status:
        messages.append(pkb_status)

    # Ensure auto mode classifier rules are installed
    try:
        from lib.automode import install, is_installed

        if not is_installed():
            ok, msg = install()
            if ok:
                messages.append(f"autoMode: {msg}")
            else:
                messages.append(f"autoMode: skipped ({msg})")
    except Exception as e:
        messages.append(f"autoMode: check failed ({e})")

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

    # 3. Persist paths
    # Persist AOPS_SESSIONS and POLECAT_HOME so subagents (worktree agents,
    # macOS app sessions) write transcripts/summaries to the correct git-synced
    # directory instead of falling back to ~/.polecat/sessions/.
    for var in ("AOPS_SESSIONS", "POLECAT_HOME"):
        val = os.environ.get(var)
        if val:
            persist[var] = val

    try:
        persist["AOPS_SESSION_STATE_DIR"] = str(status_dir)
    except Exception as e:
        print(f"WARNING: Failed to determine session status dir: {e}", file=sys.stderr)

    persist["AOPS_HOOK_LOG_PATH"] = str(hook_log_path)
    persist["AOPS_SESSION_STATE_PATH"] = str(state_file_path)

    # 4. Persist gate file paths
    gate_paths = get_all_gate_file_paths(ctx.session_id, ctx.raw_input)
    for gate_name, gate_path in gate_paths.items():
        persist[f"AOPS_GATE_FILE_{gate_name.upper()}"] = str(gate_path)

    # 5. Persist gate mode defaults for non-shell runtimes (macOS app)
    # These are normally inherited from ~/.env.local via interactive zsh.
    # When missing, gate_config.py falls back to "warn"; we persist that
    # so subsequent hooks in this session also get the defaults.
    from hooks.gate_config import (
        CUSTODIET_GATE_MODE,
        CUSTODIET_TOOL_CALL_THRESHOLD,
        HANDOVER_GATE_MODE,
        QA_GATE_MODE,
    )

    gate_mode_vars = {
        "HANDOVER_GATE_MODE": HANDOVER_GATE_MODE,
        "QA_GATE_MODE": QA_GATE_MODE,
        "CUSTODIET_GATE_MODE": CUSTODIET_GATE_MODE,
        "CUSTODIET_TOOL_CALL_THRESHOLD": str(CUSTODIET_TOOL_CALL_THRESHOLD),
    }
    for var, val in gate_mode_vars.items():
        if not os.environ.get(var):
            persist[var] = val

    # 6. Apply agent-env-map.conf credential isolation mappings (issue #581)
    # (was step 5 before gate mode persistence was added)
    from lib.agent_env import get_env_mapping_persist_dict

    persist.update(get_env_mapping_persist_dict())

    # 7. Ensure required CLIs (uv, gh, etc.) are accessible in PATH.
    # Centralised in lib/path_bootstrap — shared logic with ensure-path.sh.
    from lib.path_bootstrap import detect_path_additions

    updated_path = detect_path_additions(os.environ.get("PATH", ""))
    if updated_path:
        persist["PATH"] = updated_path
        # Also update live env so subprocesses spawned later in this hook
        # invocation find the tools immediately (persist only applies to
        # future Claude tool calls via CLAUDE_ENV_FILE).
        os.environ["PATH"] = updated_path

    # 8. Inject Tier 1 Core context (CORE.md)
    # This ensures Claude Code receives the essential framework context.
    core_md_path = AOPS_CORE_DIR / "CORE.md"
    if core_md_path.exists():
        try:
            core_content = core_md_path.read_text().strip()
            if core_content:
                messages.extend(
                    [
                        "",
                        "--- FRAMEWORK CORE ---",
                        core_content,
                        "----------------------",
                        "",
                    ]
                )
        except Exception as e:
            print(f"WARNING: Failed to read CORE.md: {e}", file=sys.stderr)

    # Persist all environment variables
    set_persistent_env(persist)

    return GateResult(
        verdict=GateVerdict.ALLOW,
        system_message="\n".join(messages),
        metadata={"source": "session_env_setup", "persisted_vars": persist},
    )
