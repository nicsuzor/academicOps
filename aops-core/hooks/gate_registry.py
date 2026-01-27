"""
Gate Registry: Defines the logic for specific gates.

This module contains the "Conditions" that gates evaluate.
"""

from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import json
import sys
import os

# Adjust imports to work within the aops-core environment
# This assumes the script is run with PYTHONPATH set to aops-core root
try:
    from lib import session_state
    from hooks import custodiet_gate
    from hooks import hydration_gate
except ImportError:
    # Fallback for when running directly or in tests without full context
    pass


class GateContext:
    """Context passed to gate evaluators."""

    def __init__(self, session_id: str, event_name: str, input_data: Dict[str, Any]):
        self.session_id = session_id
        self.event_name = event_name
        self.input_data = input_data
        self.tool_name = input_data.get("tool_name")
        self.tool_input = input_data.get("tool_input", {})
        self.transcript_path = input_data.get("transcript_path")


def check_hydration_gate(ctx: GateContext) -> Optional[Dict[str, Any]]:
    """
    Check if hydration is required.
    Returns None if allowed, or an output dict if blocked.
    """
    # Using logic migrated from hydration_gate.py

    # Bypass for subagent sessions
    if hydration_gate.is_subagent_session():
        return None

    # Check if hydration is pending
    if not session_state.is_hydration_pending(ctx.session_id):
        return None

    # Check if this is the hydrator being invoked
    is_hydrator = ctx.tool_name == "Task" and hydration_gate.is_hydrator_task(
        ctx.tool_input
    )
    is_gemini = hydration_gate.is_gemini_hydration_attempt(
        ctx.tool_name, ctx.tool_input
    )

    if is_hydrator or is_gemini:
        # Clear gate and allow
        session_state.clear_hydration_pending(ctx.session_id)
        return None

    # Block
    block_msg = hydration_gate.get_block_message()
    from lib.hook_utils import make_deny_output

    return make_deny_output(block_msg)


def check_custodiet_gate(ctx: GateContext) -> Optional[Dict[str, Any]]:
    """
    Check compliancy via Custodiet.
    Returns None if allowed (or no check needed), or an output dict with instruction if check needed.
    """
    # Skip for certain tools
    skip_tools = {"Read", "Glob", "Grep", "mcp__memory__retrieve_memory"}
    if ctx.tool_name in skip_tools:
        return None

    # Increment counter
    tool_count = custodiet_gate.increment_tool_count(ctx.session_id)

    if tool_count >= custodiet_gate.TOOL_CALL_THRESHOLD:
        try:
            instruction = custodiet_gate.build_audit_instruction(
                ctx.transcript_path, ctx.tool_name or "unknown", ctx.session_id
            )
            from lib.hook_utils import make_context_output

            output = make_context_output(
                instruction, "PostToolUse", wrap_in_reminder=True
            )
            custodiet_gate.reset_compliance_state(ctx.session_id)
            return output
        except Exception as e:
            # Log error but fail-safe (don't crash the hook system for an audit check)
            print(f"Custodiet error: {e}", file=sys.stderr)
            return None

    return None


# Registry of available gate checks
GATE_CHECKS = {
    "hydration": check_hydration_gate,
    "custodiet": check_custodiet_gate,
}
