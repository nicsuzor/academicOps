"""
Unified Gate System - Simple PreToolUse/PostToolUse enforcement.

Uses lib/session_state for gate status (derived from state fields).
Configuration in gate_config.py.

Functions:
- check_tool_gate: PreToolUse - blocks tools if required gates aren't open
- update_gate_state: PostToolUse - opens/closes gates based on conditions
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from hooks.schemas import HookContext

from lib.gate_model import GateResult

TEMPLATES_DIR = Path(__file__).parent / "templates"

GATE_AGENTS: Dict[str, str] = {
    "hydration": "aops-core:prompt-hydrator",
    "custodiet": "aops-core:custodiet",
    "critic": "aops-core:critic",
    "qa": "aops-core:qa",
}


def check_tool_gate(ctx: "HookContext") -> GateResult:
    """PreToolUse: Check if tool is allowed based on gate_config.py."""
    from hooks.gate_config import (
        GATE_MODE_DEFAULTS,
        GATE_MODE_ENV_VARS,
        get_required_gates,
        get_tool_category,
    )
    from lib import session_state

    if ctx.hook_event != "PreToolUse":
        return GateResult.allow()

    tool_name = ctx.tool_name or ""

    # Allow hydrator's own tool calls
    if session_state.is_hydrator_active(ctx.session_id):
        return GateResult.allow()

    # Allow spawning hydrator
    if tool_name == "Task":
        subagent = (ctx.tool_input or {}).get("subagent_type", "")
        if "hydrator" in subagent.lower():
            # <!-- NS: this should just be in the ordinary config for always_allowed tools. -->
            session_state.set_hydrator_active(ctx.session_id)
            return GateResult.allow()

    # Always-available tools bypass all gates
    if get_tool_category(tool_name) == "always_available":
        return GateResult.allow()

    # Check required gates
    required = get_required_gates(tool_name)
    if not required:
        return GateResult.allow()

    passed = session_state.get_passed_gates(ctx.session_id)
    missing = [g for g in required if g not in passed]
    if not missing:
        return GateResult.allow()

    # Build block message using template registry
    from lib.template_registry import TemplateRegistry

    first = missing[0]
    mode = os.environ.get(
        GATE_MODE_ENV_VARS.get(first, ""), GATE_MODE_DEFAULTS.get(first, "warn")
    )

    agent = GATE_AGENTS.get(first, "")
    audit_path = _create_audit_file(ctx.session_id, first, ctx)

    gate_status = "\n".join(f"- {g}: {'✓' if g in passed else '✗'}" for g in required)

    # <!-- NS: instructions need revision to provide both gemini cli and claude code snippets. Also need to ensure that the Task tool call is properly formatted for both agents. -->
    if agent and audit_path:
        next_instruction = f'`Task(subagent_type="{agent}", prompt="Analyze {audit_path}")`'
    elif agent:
        next_instruction = f'`Task(subagent_type="{agent}")`'
    else:
        next_instruction = f"Satisfy `{first}` gate"

    msg = TemplateRegistry.instance().render(
        "tool.gate_message",
        {
            "mode": mode,
            "tool_name": tool_name,
            "tool_category": get_tool_category(tool_name),
            "missing_gates": ", ".join(missing),
            "gate_status": gate_status,
            "next_instruction": next_instruction,
        },
    )

    if mode == "block":
        return GateResult.deny(system_message=msg, context_injection=msg)
    return GateResult.warn(system_message=msg, context_injection=msg)


def update_gate_state(ctx: "HookContext") -> Optional[GateResult]:
    """PostToolUse: Open/close gates based on conditions."""
    from hooks.gate_config import GATE_CLOSURE_TRIGGERS, GATE_OPENING_CONDITIONS
    from lib import session_state

    if ctx.hook_event != "PostToolUse":
        return None

    messages = []
    tool_name = ctx.tool_name or ""
    tool_input = ctx.tool_input or {}
    # <!-- NS: move all the logic for normalising ctx and converting from gemini/claude into the ctx pydantic object as a property for easier access and reuse. Make sure we share the same code with the transcript generator. -->
    tool_output = ctx.tool_output

    # Check opening conditions
    for gate, cond in GATE_OPENING_CONDITIONS.items():
        if cond.get("event") != "PostToolUse":
            continue
        if _matches_condition(cond, tool_name, tool_input, tool_output):
            _open_gate(ctx.session_id, gate)
            messages.append(f"✓ `{gate}` opened")

    # Check closure triggers
    for gate, triggers in GATE_CLOSURE_TRIGGERS.items():
        for trigger in triggers:
            if trigger.get("event") != "PostToolUse":
                continue
            if _matches_trigger(trigger, tool_name, tool_input, ctx.session_id, gate):
                _close_gate(ctx.session_id, gate)
                messages.append(f"✗ `{gate}` closed")

    # Clear hydrator_active when hydrator completes
    if tool_name in ("Task", "Skill"):
        subagent = tool_input.get("subagent_type", "") or tool_input.get("skill", "")
        if "hydrator" in subagent.lower():
            session_state.clear_hydrator_active(ctx.session_id)

    if messages:
        return GateResult.allow(context_injection="\n".join(messages))
    return None


def on_user_prompt(ctx: "HookContext") -> Optional[GateResult]:
    """UserPromptSubmit: Close gates that re-close on new input."""
    from hooks.gate_config import GATE_CLOSURE_TRIGGERS

    if ctx.hook_event != "UserPromptSubmit":
        return None

    for gate, triggers in GATE_CLOSURE_TRIGGERS.items():
        for trigger in triggers:
            if trigger.get("event") == "UserPromptSubmit":
                _close_gate(ctx.session_id, gate)

    return None


def on_session_start(ctx: "HookContext") -> Optional[GateResult]:
    """SessionStart: Initialize gates."""
    from hooks.gate_config import GATE_INITIAL_STATE

    if ctx.hook_event != "SessionStart":
        return None

    for gate, initial in GATE_INITIAL_STATE.items():
        if initial == "open":
            _open_gate(ctx.session_id, gate)

    return None


# =============================================================================
# HELPERS
# =============================================================================


def _open_gate(session_id: str, gate: str) -> None:
    """Open a gate by setting the corresponding state flag."""
    from lib import session_state

    if gate == "hydration":
        session_state.clear_hydration_pending(session_id)
    elif gate == "task":
        # Task gate is opened by task_binding - nothing to do here
        pass
    elif gate == "critic":
        session_state.set_critic_invoked(session_id, "APPROVED")
    elif gate == "qa":
        session_state.set_qa_invoked(session_id)
    elif gate == "handover":
        session_state.set_handover_skill_invoked(session_id)
    elif gate == "custodiet":
        # Reset tool call counter
        state = session_state.get_or_create_session_state(session_id)
        state.setdefault("state", {})["tool_calls_since_compliance"] = 0
        session_state.save_session_state(session_id, state)


def _close_gate(session_id: str, gate: str) -> None:
    """Close a gate by clearing the corresponding state flag."""
    from lib import session_state

    if gate == "hydration":
        session_state.set_hydration_pending(session_id, "")
    elif gate == "task":
        session_state.clear_current_task(session_id)
    elif gate == "critic":
        session_state.clear_critic_invoked(session_id)
    elif gate == "qa":
        session_state.clear_qa_invoked(session_id)
    elif gate == "handover":
        session_state.clear_handover_skill_invoked(session_id)


def _create_audit_file(
    session_id: str, gate: str, ctx: "HookContext"
) -> Optional[Path]:
    """Create audit file for gate if template exists."""
    template = TEMPLATES_DIR / f"{gate}-audit.md"
    if not template.exists():
        return None

    content = template.read_text().format(
        session_id=session_id,
        gate_name=gate,
        tool_name=ctx.tool_name or "unknown",
    )

    # Write to temp
    from lib import hook_utils

    temp_dir = hook_utils.get_hook_temp_dir(gate, ctx.raw_input)
    return hook_utils.write_temp_file(content, temp_dir, f"{gate}_")


def _matches_condition(
    cond: Dict[str, Any],
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Dict[str, Any],
) -> bool:
    """Check if opening condition matches."""
    pattern = cond.get("tool_pattern")
    if pattern and not re.match(pattern, tool_name):
        return False

    subagent = cond.get("subagent_type")
    if subagent and subagent not in tool_input.get("subagent_type", ""):
        return False

    contains = cond.get("output_contains")
    if contains:
        # Check if string appears in any string value of the output dict
        output_str = str(tool_output)
        if contains not in output_str:
            return False

    skill = cond.get("skill_name")
    if skill:
        actual = tool_input.get("skill", "") or tool_input.get("name", "")
        if skill not in actual:
            return False

    return True


def _matches_trigger(
    trigger: Dict[str, Any],
    tool_name: str,
    tool_input: Dict[str, Any],
    session_id: str,
    gate: str,
) -> bool:
    """Check if closure trigger matches."""
    from hooks.gate_config import get_tool_category
    from lib import session_state

    pattern = trigger.get("tool_pattern")
    if pattern and not re.match(pattern, tool_name):
        return False

    category = trigger.get("tool_category")
    if category and get_tool_category(tool_name) != category:
        return False

    # Threshold counter
    counter = trigger.get("threshold_counter")
    if counter:
        threshold = trigger.get("threshold_value", 0)
        state = session_state.get_or_create_session_state(session_id)
        state_data = state.setdefault("state", {})
        count = state_data.get("tool_calls_since_compliance", 0) + 1
        state_data["tool_calls_since_compliance"] = count
        session_state.save_session_state(session_id, state)
        if count < threshold:
            return False

    return True
