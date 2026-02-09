"""
Unified Gate System - Dispatcher.

Iterates through registered gates to enforce policies.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from hooks.schemas import HookContext
from hooks.unified_logger import get_hook_log_path
from lib import hook_utils, session_paths, session_state
from lib.gate_model import GateResult, GateVerdict
from lib.gates.critic import CriticGate
from lib.gates.custodiet import CustodietGate
from lib.gates.handover import HandoverGate
from lib.gates.hydration import HydrationGate
from lib.gates.qa import QaGate
from lib.gates.registry import GateRegistry
from lib.gates.task import TaskGate

if TYPE_CHECKING:
    pass

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _ensure_initialized() -> None:
    """Initialize gate registry if needed."""
    if not GateRegistry._initialized:
        GateRegistry.register(HydrationGate())
        GateRegistry.register(TaskGate())
        GateRegistry.register(CustodietGate())
        GateRegistry.register(CriticGate())
        GateRegistry.register(QaGate())
        GateRegistry.register(HandoverGate())
        GateRegistry._initialized = True


def check_tool_gate(ctx: HookContext) -> GateResult:
    """PreToolUse: Check all gates."""
    _ensure_initialized()

    # Load session state once
    state = session_state.load_session_state(ctx.session_id)
    if not state:
        # If no state (first turn?), we can't really check much,
        # but hydration gate handles this (fail-closed).
        pass

    # Global Bypass: Allow hydrator's own tool calls
    # This prevents recursive loops and allows the hydrator to work freely.
    if session_state.is_hydrator_active(ctx.session_id):
        return GateResult.allow()

    # Iterate all gates
    # First deny wins
    for gate in GateRegistry.get_all_gates():
        result = gate.check(ctx, state) # type: ignore
        if result and result.verdict == GateVerdict.DENY:
            return result
        if result and result.verdict == GateVerdict.WARN:
             # For now, return the first warning/block.
             return result

    return GateResult.allow()


def update_gate_state(ctx: HookContext) -> GateResult | None:
    """PostToolUse: Update all gates."""
    _ensure_initialized()

    state = session_state.load_session_state(ctx.session_id)

    messages = []
    
    for gate in GateRegistry.get_all_gates():
        result = gate.on_tool_use(ctx, state) # type: ignore
        if result and result.system_message:
            messages.append(result.system_message)

    if messages:
        return GateResult.allow(system_message="\n".join(messages))

    return None


def on_user_prompt(ctx: HookContext) -> GateResult | None:
    """UserPromptSubmit: Notify all gates."""
    _ensure_initialized()

    state = session_state.load_session_state(ctx.session_id)

    messages = []
    context_injections = []

    for gate in GateRegistry.get_all_gates():
        result = gate.on_user_prompt(ctx, state) # type: ignore
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


def on_session_start(ctx: HookContext) -> GateResult | None:
    """SessionStart: Notify all gates and perform initialization."""
    _ensure_initialized()
    
    # --- Fail-Fast Initialization Logic (Restored) ---
    
    short_hash = session_paths.get_session_short_hash(ctx.session_id)
    hook_log_path = get_hook_log_path(ctx.session_id, ctx.raw_input)
    state_file_path = session_paths.get_session_file_path(ctx.session_id, input_data=ctx.raw_input)

    # FAIL-FAST: Actually create the state file
    try:
        state = session_state.get_or_create_session_state(ctx.session_id)
        session_state.save_session_state(ctx.session_id, state)

        # Verify the file was actually written
        if not state_file_path.exists():
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"FAIL-FAST: State file not created at expected path.\n"
                    f"Expected: {state_file_path}\n"
                    f"Check AOPS_SESSION_STATE_DIR env var and directory permissions.\n\n"
                ),
                metadata={"source": "session_start", "error": "state_file_not_created"},
            )
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
        result = gate.on_session_start(ctx, state) # type: ignore
        if result and result.system_message:
            messages.append(result.system_message)

    return GateResult.allow(system_message="\n".join(messages))


def check_stop_gate(ctx: HookContext) -> GateResult | None:
    """Stop: Check all gates."""
    _ensure_initialized()

    state = session_state.load_session_state(ctx.session_id)

    for gate in GateRegistry.get_all_gates():
        result = gate.on_stop(ctx, state) # type: ignore
        if result and result.verdict == GateVerdict.DENY:
            return result

    return None


def on_after_agent(ctx: HookContext) -> GateResult | None:
    """AfterAgent: Notify all gates."""
    _ensure_initialized()

    state = session_state.load_session_state(ctx.session_id)

    messages = []
    context_injections = []

    for gate in GateRegistry.get_all_gates():
        result = gate.on_after_agent(ctx, state) # type: ignore
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


# =============================================================================
# HELPERS (Legacy/Shared)
# =============================================================================

def _create_audit_file(session_id: str, gate: str, ctx: HookContext) -> Path | None:
    """Create rich audit file for gate using TemplateRegistry."""
    pass

def open_gate(session_id: str, gate: str) -> None:
    """Open a gate (Legacy/Testing Wrapper)."""
    session_state.set_gate_status(session_id, gate, "open")

def close_gate(session_id: str, gate: str) -> None:
    """Close a gate (Legacy/Testing Wrapper)."""
    session_state.set_gate_status(session_id, gate, "closed")
