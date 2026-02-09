"""
Gate Registry: Defines the logic for specific gates.

This module contains the "Conditions" that gates evaluate.
"""

import sys
from pathlib import Path

from hooks.schemas import HookContext
from lib.gate_model import GateResult

# Import unified gate functions from gates.py
from hooks.gates import (
    check_stop_gate as _check_stop_gate,
    check_tool_gate as _check_tool_gate,
    on_after_agent as _on_after_agent,
    on_session_start as _on_session_start,
    on_user_prompt as _on_user_prompt,
    update_gate_state as _update_gate_state,
)

# --- Unified Logger Gate ---

def run_unified_logger(ctx: HookContext) -> GateResult | None:
    """Log hook events to session file."""
    try:
        from hooks.unified_logger import log_event_to_session
        # log_event_to_session now returns GateResult directly (no dict conversion)
        return log_event_to_session(ctx.session_id, ctx.hook_event, ctx.raw_input)
    except ImportError:
        return None
    except Exception as e:
        print(f"WARNING: unified_logger error: {e}", file=sys.stderr)
        return None

# --- ntfy Push Notification Gate ---

def run_ntfy_notifier(ctx: HookContext) -> GateResult | None:
    """Send push notifications."""
    try:
        from lib.paths import get_ntfy_config
        config = get_ntfy_config()
        if not config:
            return None

        from hooks.ntfy_notifier import (
            notify_session_start,
            notify_session_stop,
            notify_subagent_stop,
            notify_task_bound,
            notify_task_completed,
        )
        from lib import session_state

        # SessionStart notification
        if ctx.hook_event == "SessionStart":
            notify_session_start(config, ctx.session_id)
            return None

        # Stop notification
        if ctx.hook_event == "Stop":
            try:
                current_task = session_state.get_current_task(ctx.session_id)
            except Exception:
                current_task = None
            notify_session_stop(config, ctx.session_id, current_task)
            return None

        # PostToolUse: task binding and subagent completion
        if ctx.hook_event == "PostToolUse":
            # Check for task binding
            TASK_BINDING_TOOLS = {
                "mcp__plugin_aops-core_task_manager__update_task",
                "mcp__plugin_aops-core_task_manager__claim_next_task",
                "mcp__plugin_aops-core_task_manager__complete_task",
                "mcp__plugin_aops-core_task_manager__complete_tasks",
                "update_task",
                "claim_next_task",
                "complete_task",
                "complete_tasks",
            }
            if ctx.tool_name in TASK_BINDING_TOOLS:
                tool_input = ctx.tool_input
                if "status" in tool_input and "id" in tool_input:
                    status = tool_input["status"]
                    task_id = tool_input["id"]

                    if status == "in_progress":
                        notify_task_bound(config, ctx.session_id, task_id)
                    elif status == "done":
                        notify_task_completed(config, ctx.session_id, task_id)

            # Check for subagent completion (Task tool)
            if ctx.tool_name in ("Task", "delegate_to_agent"):
                agent_type = "unknown"
                if "subagent_type" in ctx.tool_input:
                    agent_type = ctx.tool_input["subagent_type"]
                elif "agent_name" in ctx.tool_input:
                    agent_type = ctx.tool_input["agent_name"]

                verdict = None
                if tool_result := ctx.tool_output:
                    if isinstance(tool_result, dict) and "verdict" in tool_result:
                        verdict = tool_result["verdict"]

                notify_subagent_stop(config, ctx.session_id, agent_type, verdict)

    except Exception as e:
        print(f"WARNING: ntfy_notifier error: {e}", file=sys.stderr)
        return None
    return None

# --- Session Env Setup ---

def run_session_env_setup(ctx: HookContext) -> GateResult | None:
    try:
        from hooks.session_env_setup import run_session_env_setup as setup_func
        return setup_func(ctx)
    except ImportError:
        return None

# --- Generate Transcript ---

def run_generate_transcript(ctx: HookContext) -> GateResult | None:
    if ctx.hook_event != "Stop":
        return None

    transcript_path = ctx.raw_input.get("transcript_path")
    if not transcript_path:
        return None

    try:
        import subprocess

        root_dir = Path(__file__).parent.parent
        script_path = root_dir / "scripts" / "transcript_push.py"

        if not script_path.exists():
            script_path = root_dir / "scripts" / "transcript.py"

        if script_path.exists():
            subprocess.run(
                [sys.executable, str(script_path), transcript_path],
                check=False,
                capture_output=True,
                text=True,
            )
    except Exception as e:
        print(f"WARNING: generate_transcript error: {e}", file=sys.stderr)

    return None

# Registry of available gate checks
# We map legacy keys to unified functions or no-ops
GATE_CHECKS = {
    # Universal gates
    "unified_logger": run_unified_logger,
    "ntfy_notifier": run_ntfy_notifier,
    "session_env_setup": run_session_env_setup,

    # SessionStart gates
    "session_start": _on_session_start, # Handles creating session state AND notifying gates
    "gate_init": lambda ctx: None,  # Handled by session_start (on_session_start)

    # UserPromptSubmit gates
    "user_prompt_submit": _on_user_prompt,
    "gate_reset": lambda ctx: None,  # Handled by on_user_prompt

    # PreToolUse gates
    "tool_gate": _check_tool_gate,

    # PostToolUse gates
    "task_binding": lambda ctx: None, # Handled by update_gate_state
    "accountant": lambda ctx: None, # Handled by update_gate_state
    "gate_update": _update_gate_state,

    # AfterAgent gates
    "agent_response": _on_after_agent,

    # Stop gates
    "stop_gate": _check_stop_gate,
    "generate_transcript": run_generate_transcript,
}
