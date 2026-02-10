"""
Unified Gate System - Dispatcher.

Iterates through registered gates to enforce policies.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from hooks.schemas import HookContext
from hooks.unified_logger import get_hook_log_path
from lib import hook_utils, session_paths
from lib.gate_model import GateResult, GateVerdict
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState

if TYPE_CHECKING:
    pass


def _ensure_initialized() -> None:
    """Initialize gate registry if needed."""
    GateRegistry.initialize()


def check_tool_gate(ctx: HookContext, state: SessionState) -> GateResult:
    """PreToolUse: Check all gates."""
    _ensure_initialized()

    # Global Bypass: Allow hydrator's own tool calls
    if state.state.get("hydrator_active"):
        return GateResult.allow()

    # Category Bypass: Always-available tools bypass ALL gates (including hydration)
    from hooks.gate_config import get_tool_category
    if ctx.tool_name and get_tool_category(ctx.tool_name) == "always_available":
        return GateResult.allow()

    # Iterate all gates
    # First deny wins
    for gate in GateRegistry.get_all_gates():
        result = gate.check(ctx, state)
        if result and result.verdict == GateVerdict.DENY:
            return result
        if result and result.verdict == GateVerdict.WARN:
             # For now, return the first warning/block.
             return result

    return GateResult.allow()


def update_gate_state(ctx: HookContext, state: SessionState) -> GateResult | None:
    """PostToolUse: Update all gates."""
    _ensure_initialized()

    messages = []
    
    for gate in GateRegistry.get_all_gates():
        result = gate.on_tool_use(ctx, state)
        if result and result.system_message:
            messages.append(result.system_message)

    if messages:
        return GateResult.allow(system_message="\n".join(messages))

    return None


def on_user_prompt(ctx: HookContext, state: SessionState) -> GateResult | None:
    """UserPromptSubmit: Notify all gates."""
    _ensure_initialized()

    messages = []
    context_injections = []

    for gate in GateRegistry.get_all_gates():
        result = gate.on_user_prompt(ctx, state)
        if result:
            if result.system_message:
                messages.append(result.system_message)
            if result.context_injection:
                context_injections.append(result.context_injection)

    # Combine results
    if messages or context_injections:
        return GateResult.allow(
            system_message="\n".join(messages) if messages else None,
            context_injection="\n\n".join(context_injections) if context_injections else None
        )

    return None


def on_session_start(ctx: HookContext, state: SessionState) -> GateResult | None:
    """SessionStart: Notify all gates and perform initialization."""
    _ensure_initialized()
    
    # --- Fail-Fast Initialization Logic (Restored) ---
    
    short_hash = session_paths.get_session_short_hash(ctx.session_id)
    hook_log_path = get_hook_log_path(ctx.session_id, ctx.raw_input)
    state_file_path = session_paths.get_session_file_path(ctx.session_id, input_data=ctx.raw_input)

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

    # GEMINI-SPECIFIC: Validate hydration temp path infrastructure
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
                    f"⛔ **STATE ERROR**: Hydration temp path missing from session state.\n\n"
                    f"Details: {e}\n\n"
                    f"Fix: Ensure Gemini CLI has initialized the project directory."
                ),
                metadata={"source": "session_start", "error": "gemini_temp_dir_missing"},
            )
        except OSError as e:
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"⛔ **STATE ERROR**: Cannot create hydration temp directory.\n\n"
                    f"Error: {e}\n\n"
                    f"Fix: Check directory permissions for ~/.gemini/tmp/"
                ),
                metadata={"source": "session_start", "error": "gemini_temp_dir_permission"},
            )

    # --- Notify Gates ---

    messages = [
        f"🚀 Session Started: {ctx.session_id} ({short_hash})",
        f"State File: {state_file_path}",
        f"Hooks log: {hook_log_path}",
        f"Transcript: {transcript_path}",
    ]

    for gate in GateRegistry.get_all_gates():
        result = gate.on_session_start(ctx, state)
        if result and result.system_message:
            messages.append(result.system_message)

    return GateResult.allow(system_message="\n".join(messages))


def check_stop_gate(ctx: HookContext, state: SessionState) -> GateResult | None:
    """Stop: Check all gates."""
    _ensure_initialized()

    for gate in GateRegistry.get_all_gates():
        result = gate.on_stop(ctx, state)
        if result and result.verdict == GateVerdict.DENY:
            return result
        # Also return warnings?
        if result and result.verdict == GateVerdict.WARN:
            return result

    return None


def on_after_agent(ctx: HookContext, state: SessionState) -> GateResult | None:
    """AfterAgent: Notify all gates."""
    _ensure_initialized()

    messages = []
    context_injections = []

    for gate in GateRegistry.get_all_gates():
        result = gate.on_after_agent(ctx, state)
        if result:
            if result.system_message:
                messages.append(result.system_message)
            if result.context_injection:
                context_injections.append(result.context_injection)

    if messages or context_injections:
        return GateResult.allow(
            system_message="\n".join(messages) if messages else None,
            context_injection="\n\n".join(context_injections) if context_injections else None
        )

    return None

def on_subagent_stop(ctx: HookContext, state: SessionState) -> GateResult | None:
    """SubagentStop: Notify all gates."""
    _ensure_initialized()

    messages = []

    for gate in GateRegistry.get_all_gates():
        result = gate.on_subagent_stop(ctx, state)
        if result and result.system_message:
            messages.append(result.system_message)

    if messages:
        return GateResult.allow(system_message="\n".join(messages))

    return None
