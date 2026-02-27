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
from lib.session_paths import (
    get_all_gate_file_paths,
    get_hook_log_path,
    get_session_file_path,
    get_session_status_dir,
)
from lib.session_state import SessionState

from hooks.schemas import HookContext

# Gate enforcement mode environment variables
GATE_MODE_VARS = (
    "CUSTODIET_GATE_MODE",
    "HYDRATION_GATE_MODE",
    "QA_GATE_MODE",
    "HANDOVER_GATE_MODE",
)
DEFAULT_GATE_MODE = "warn"


def set_persistent_env(env_dict: dict[str, str]):
    """Set environment variables persistently for the session, if possible."""

    # Claude Code support -- write to CLAUDE_ENV_FILE provided in session start hook:
    if env_path := os.environ.get("CLAUDE_ENV_FILE"):
        try:
            with open(env_path, "a") as f:
                for key, value in env_dict.items():
                    f.write(f'export {key}="{value}"\n')
        except Exception as e:
            print(f"WARNING: Failed to write to CLAUDE_ENV_FILE: {e}", file=sys.stderr)


def run_session_env_setup(ctx: HookContext, state: SessionState) -> GateResult | None:
    """Session start initialization - fail-fast checks and user messages.


    Sets:
    - CLAUDE_SESSION_ID
    - PYTHONPATH (includes aops-core)
    - AOPS_SESSION_STATE_DIR
    - AOPS_HOOK_LOG_PATH
    - Default gate enforcement modes (CUSTODIET_GATE_MODE, HYDRATION_GATE_MODE, QA_GATE_MODE, HANDOVER_GATE_MODE)
    - Other placeholder variables from original script

    """

    from lib import hook_utils

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

    # Gemini-specific: validate hydration temp path infrastructure
    transcript_path = ctx.raw_input.get("transcript_path", "") if ctx.raw_input else ""
    if transcript_path and ".gemini" in str(transcript_path):
        try:
            hydration_temp_dir = hook_utils.get_hook_temp_dir("hydrator", ctx.raw_input)
            if not hydration_temp_dir.exists():
                hydration_temp_dir.mkdir(parents=True, exist_ok=True)
        except RuntimeError as e:
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"STATE ERROR: Hydration temp path missing from session state.\n\n"
                    f"Details: {e}\n\n"
                    f"Fix: Ensure Gemini CLI has initialized the project directory."
                ),
                metadata={"source": "session_start", "error": "gemini_temp_dir_missing"},
            )
        except OSError as e:
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"STATE ERROR: Cannot create hydration temp directory.\n\n"
                    f"Error: {e}\n\n"
                    f"Fix: Check directory permissions for ~/.gemini/tmp/"
                ),
                metadata={"source": "session_start", "error": "gemini_temp_dir_permission"},
            )

    # Session started messages
    messages = [
        f"Session Started: {ctx.session_id} ({short_hash})",
        f"Version: {state.version}",
        f"State File: {state_file_path}",
        f"Hooks log: {hook_log_path}",
        f"Transcript: {transcript_path}",
    ]

    # Sync ACA_DATA: commit pending changes, then pull remote
    aca_data = os.environ.get("ACA_DATA")
    if aca_data:
        try:
            from hooks.autocommit_state import (
                can_sync,
                commit_and_push_repo,
                fetch_and_check_divergence,
                has_repo_changes,
                pull_rebase_if_behind,
            )

            aca_path = Path(aca_data)
            if aca_path.exists() and (aca_path / ".git").exists():
                # Step 1: Commit+push any pending local changes (from CLI tools, Obsidian, etc.)
                if has_repo_changes(aca_path):
                    ok, commit_msg = commit_and_push_repo(
                        aca_path, commit_message="sync: session-start auto-commit"
                    )
                    if ok:
                        messages.append("ACA_DATA: committed pending changes")
                    else:
                        messages.append(f"ACA_DATA commit: {commit_msg}")

                # Step 2: Pull remote changes
                syncable, reason = can_sync(aca_path)
                if syncable:
                    is_behind, count, fetch_err = fetch_and_check_divergence(aca_path)
                    if fetch_err:
                        messages.append(f"ACA_DATA sync skipped: {fetch_err}")
                    elif is_behind:
                        ok, sync_msg = pull_rebase_if_behind(aca_path)
                        if ok:
                            messages.append(f"ACA_DATA: pulled {count} commits")
                        else:
                            messages.append(f"ACA_DATA sync failed: {sync_msg}")
                    # else: already up-to-date, no message needed
                else:
                    messages.append(f"ACA_DATA sync skipped: {reason}")
        except Exception as e:
            messages.append(f"ACA_DATA sync error: {e}")

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

    # 3. Persist gate mode environment variables
    for mode_var in GATE_MODE_VARS:
        current_val = os.environ.get(mode_var, DEFAULT_GATE_MODE)
        persist[mode_var] = current_val

    # 4. Persist paths
    try:
        persist["AOPS_SESSION_STATE_DIR"] = str(status_dir)
    except Exception as e:
        print(f"WARNING: Failed to determine session status dir: {e}", file=sys.stderr)

    persist["AOPS_HOOK_LOG_PATH"] = str(hook_log_path)
    persist["AOPS_SESSION_STATE_PATH"] = str(state_file_path)

    # 5. Persist gate file paths
    gate_paths = get_all_gate_file_paths(ctx.session_id, ctx.raw_input)
    for gate_name, gate_path in gate_paths.items():
        persist[f"AOPS_GATE_FILE_{gate_name.upper()}"] = str(gate_path)

    # 6. Set GH_TOKEN from AOPS_BOT_GH_TOKEN (credential isolation — issue #581)
    bot_token = os.environ.get("AOPS_BOT_GH_TOKEN")
    if bot_token:
        persist["GH_TOKEN"] = bot_token
        persist["GITHUB_TOKEN"] = bot_token

    # 7. Ensure /opt/homebrew/bin is in PATH for gh (common on macOS)
    current_path = os.environ.get("PATH", "")
    if "/opt/homebrew/bin" not in current_path:
        persist["PATH"] = f"/opt/homebrew/bin:{current_path}"

    # Persist all environment variables
    set_persistent_env(persist)

    return GateResult(
        verdict=GateVerdict.ALLOW,
        system_message="\n".join(messages),
        metadata={"source": "session_env_setup", "persisted_vars": persist},
    )
