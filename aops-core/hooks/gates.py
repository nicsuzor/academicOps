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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hooks.schemas import HookContext

from lib.gate_model import GateResult

TEMPLATES_DIR = Path(__file__).parent / "templates"

GATE_AGENTS: dict[str, str] = {
    "hydration": "aops-core:prompt-hydrator",
    "custodiet": "aops-core:custodiet",
    "critic": "aops-core:critic",
    "qa": "aops-core:qa",
}


def check_tool_gate(ctx: HookContext) -> GateResult:
    """PreToolUse: Check if tool is allowed based on gate_config.py."""
    from hooks.gate_config import (
        GATE_MODE_DEFAULTS,
        GATE_MODE_ENV_VARS,
        GATE_OPENING_CONDITIONS,
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

    # Allow spawning hydrator and open hydration gate immediately
    # Tool names derived from gate_config.py GATE_OPENING_CONDITIONS
    hydrator_direct_tools = set(
        GATE_OPENING_CONDITIONS.get("hydration", {}).get("subagent_or_skill", [])
    )
    invocation_wrappers = {"Task", "Skill", "activate_skill", "delegate_to_agent"}

    if tool_name in invocation_wrappers or tool_name in hydrator_direct_tools:
        subagent = (
            (ctx.tool_input or {}).get("subagent_type", "")
            or (ctx.tool_input or {}).get("skill", "")
            or (ctx.tool_input or {}).get("name", "")
            or (ctx.tool_input or {}).get("agent_name", "")
        )
        # Check if subagent is hydrator OR tool_name itself is a direct hydrator call
        if "hydrator" in subagent.lower() or tool_name in hydrator_direct_tools:
            session_state.set_hydrator_active(ctx.session_id)
            # Open hydration gate immediately when hydrator is invoked (not just when it completes)
            # This allows the subagent to proceed with tool calls while hydrator runs
            session_state.clear_hydration_pending(ctx.session_id)
            return GateResult.allow()

    # Allow reads from hydrator files (solves hydrator bootstrap chicken-and-egg)
    # The hydrator needs to read its hydrate_*.md file, but the hydration gate
    # blocks reads until hydration completes. Allow reads from hydrator file paths.
    if _is_hydrator_file_read(tool_name, ctx.tool_input):
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
    mode = os.environ.get(GATE_MODE_ENV_VARS.get(first, ""), GATE_MODE_DEFAULTS.get(first, "warn"))

    agent = GATE_AGENTS.get(first, "")
    audit_path = _create_audit_file(ctx.session_id, first, ctx)

    gate_status = "\n".join(f"- {g}: {'✓' if g in passed else '✗'}" for g in required)

    if agent and audit_path:
        short_name = agent.split(":")[-1]
        next_instruction = f"  Invoke {agent} ({short_name}) agent with query: `{audit_path})`\n"
    elif agent:
        short_name = agent.split(":")[-1]
        next_instruction = f"Invoke {agent} ({short_name}) agent immediately.\n"
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


def update_gate_state(ctx: HookContext) -> GateResult | None:
    """PostToolUse/AfterAgent: Open/close gates based on conditions."""
    from hooks.gate_config import GATE_CLOSURE_TRIGGERS, GATE_OPENING_CONDITIONS
    from lib import session_state

    if ctx.hook_event not in ("PostToolUse", "AfterAgent"):
        return None

    messages = []
    tool_name = ctx.tool_name or ""
    tool_input = ctx.tool_input or {}
    
    # Check opening conditions
    for gate, cond in GATE_OPENING_CONDITIONS.items():
        if cond.get("event") != ctx.hook_event:
            continue
        if _matches_condition(cond, ctx):
            open_gate(ctx.session_id, gate)
            messages.append(f"✓ `{gate}` opened")

    # Only PostToolUse handles closure triggers and hydrator_active clearing
    if ctx.hook_event == "PostToolUse":
        # Check closure triggers
        for gate, triggers in GATE_CLOSURE_TRIGGERS.items():
            for trigger in triggers:
                if trigger.get("event") != "PostToolUse":
                    continue
                if _matches_trigger(trigger, tool_name, tool_input, ctx.session_id, gate):
                    close_gate(ctx.session_id, gate)
                    messages.append(f"✗ `{gate}` closed")

        # Clear hydrator_active when hydrator completes
        # Tool names derived from gate_config.py GATE_OPENING_CONDITIONS
        hydrator_direct_tools = set(
            GATE_OPENING_CONDITIONS.get("hydration", {}).get("subagent_or_skill", [])
        )
        invocation_wrappers = {"Task", "Skill", "activate_skill", "delegate_to_agent"}
        if tool_name in invocation_wrappers or tool_name in hydrator_direct_tools:
            subagent = tool_input.get("subagent_type", "") or tool_input.get("skill", "")
            if "hydrator" in (subagent or "").lower() or tool_name in hydrator_direct_tools:
                session_state.clear_hydrator_active(ctx.session_id)

    if messages:
        return GateResult.allow(context_injection="\n".join(messages))
    return None


def on_user_prompt(ctx: HookContext) -> GateResult | None:
    """UserPromptSubmit: Close gates that re-close on new input."""
    from hooks.gate_config import GATE_CLOSURE_TRIGGERS

    if ctx.hook_event != "UserPromptSubmit":
        return None

    for gate, triggers in GATE_CLOSURE_TRIGGERS.items():
        for trigger in triggers:
            if trigger.get("event") == "UserPromptSubmit":
                close_gate(ctx.session_id, gate)

    return None


def on_session_start(ctx: HookContext) -> GateResult | None:
    """SessionStart: Initialize gates."""
    from hooks.gate_config import GATE_INITIAL_STATE

    if ctx.hook_event != "SessionStart":
        return None

    for gate, initial in GATE_INITIAL_STATE.items():
        if initial == "open":
            open_gate(ctx.session_id, gate)

    return None


# =============================================================================
# HELPERS
# =============================================================================


def _is_hydrator_file_read(
    tool_name: str,
    tool_input: dict[str, Any] | None,
) -> bool:
    """Check if this is a read of a hydrator file.

    This solves the hydrator bootstrap problem:
    - The hydrator subagent needs to read its hydrate_*.md file
    - But the hydration gate blocks reads until hydration completes
    - We allow reads from paths containing /hydrator/hydrate_ to break the cycle

    This is safe because:
    1. Hydrator files are framework-generated, not user files
    2. Read-only operations have no side effects
    3. The pattern is specific enough to avoid unintended bypasses

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        True if this is a read of a hydrator file
    """
    # Only applies to read tools
    if tool_name not in ("Read", "read_file", "view_file"):
        return False

    if not tool_input:
        return False

    # Get the file being read
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path:
        return False

    # Allow reads from hydrator files
    # Gemini: ~/.gemini/tmp/<hash>/hydrator/hydrate_*.md
    # Claude: ~/.claude/projects/.../tmp/hydrator/hydrate_*.md
    if "/hydrator/hydrate_" in file_path:
        return True

    return False


def open_gate(session_id: str, gate: str) -> None:
    """Open a gate by setting the corresponding state flag."""
    from lib import session_state

    # Update unified gates dictionary
    state = session_state.get_or_create_session_state(session_id)
    state.setdefault("state", {}).setdefault("gates", {})[gate] = "open"
    
    # Also set individual flags for legacy compatibility and stop gate logic
    if gate == "hydration":
        session_state.clear_hydration_pending(session_id)
    elif gate == "critic":
        state["state"]["critic_invoked"] = True
    elif gate == "qa":
        state["state"]["qa_invoked"] = True
    elif gate == "handover":
        state["state"]["handover_skill_invoked"] = True
    elif gate == "custodiet":
        state.setdefault("state", {})["tool_calls_since_compliance"] = 0

    session_state.save_session_state(session_id, state)


def close_gate(session_id: str, gate: str) -> None:
    """Close a gate by clearing the corresponding state flag."""
    from lib import session_state

    # Update unified gates dictionary
    state = session_state.get_or_create_session_state(session_id)
    state.setdefault("state", {}).setdefault("gates", {})[gate] = "closed"
    
    # Also clear individual flags for legacy compatibility
    if gate == "hydration":
        session_state.set_hydration_pending(session_id, "")
    elif gate == "task":
        session_state.clear_current_task(session_id)
    elif gate == "critic":
        state["state"].pop("critic_invoked", None)
    elif gate == "qa":
        state["state"].pop("qa_invoked", None)
    elif gate == "handover":
        state["state"]["handover_skill_invoked"] = False

    session_state.save_session_state(session_id, state)


def _create_audit_file(session_id: str, gate: str, ctx: HookContext) -> Path | None:
    """Create rich audit file for gate using TemplateRegistry."""
    from lib.session_reader import build_rich_session_context
    from lib.template_registry import TemplateRegistry

    from lib import hook_utils

    # Align temp category with hydrator per user request
    category = "hydrator"

    # Try to load rich context if possible
    # Critic and custodiet get deep session context (full history, reasoning, diffs)
    # — they need to review/audit what actually happened across the whole session.
    # Other gates get the standard thin/wide context for scope-drift detection.
    transcript_path = ctx.transcript_path or ctx.raw_input.get("transcript_path")
    session_context = ""
    if transcript_path:
        if gate in ("critic", "custodiet"):
            from lib.session_reader import build_critic_session_context

            session_context = build_critic_session_context(transcript_path)
        else:
            session_context = build_rich_session_context(transcript_path)

    axioms, heuristics, skills = hook_utils.load_framework_content()
    custodiet_mode = os.environ.get("CUSTODIET_MODE", "block").lower()

    registry = TemplateRegistry.instance()

    # Fill template using unified logic
    try:
        content = registry.render(
            f"{gate}.context",
            {
                "session_id": session_id,
                "gate_name": gate,
                "tool_name": ctx.tool_name or "unknown",
                "session_context": session_context,
                "axioms_content": axioms,
                "heuristics_content": heuristics,
                "skills_content": skills,
                "custodiet_mode": custodiet_mode,
            },
        )
    except (KeyError, ValueError, FileNotFoundError):
        # Fallback to simple audit template if rich one fails
        try:
            content = registry.render(
                f"{gate}.audit",
                {
                    "session_id": session_id,
                    "gate_name": gate,
                    "tool_name": ctx.tool_name or "unknown",
                },
            )
        except (KeyError, ValueError, FileNotFoundError):
            return None

    # Write to temp (using aligned category)
    temp_dir = hook_utils.get_hook_temp_dir(category, ctx.raw_input)
    return hook_utils.write_temp_file(content, temp_dir, f"audit_{gate}_")


def _matches_condition(cond: dict[str, Any], ctx: HookContext) -> bool:
    """Check if opening condition matches."""
    tool_name = ctx.tool_name or ""
    tool_input = ctx.tool_input or {}
    tool_output = ctx.tool_output

    pattern = cond.get("tool_pattern")
    if pattern and not re.match(pattern, tool_name):
        return False

    subagent = cond.get("subagent_type")
    if subagent:
        # Check delegation tool inputs (Claude Task, Gemini delegate_to_agent, etc.)
        actual = (
            tool_input.get("subagent_type", "")
            or tool_input.get("agent_name", "")
            or tool_input.get("name", "")
            or tool_input.get("skill", "")
        )
        # Match if either is contained in the other (e.g. "hydrator" matches "aops-core:prompt-hydrator")
        # Also match when tool_name IS the agent (Gemini direct MCP call)
        short_subagent = subagent.split(":")[-1]
        if (
            subagent not in actual
            and short_subagent not in actual
            and actual not in subagent
            and tool_name not in (subagent, short_subagent)
        ):
            return False

    # Handle subagent_or_skill (list of acceptable values)
    subagent_or_skill = cond.get("subagent_or_skill")
    if subagent_or_skill:
        actual = (
            tool_input.get("subagent_type", "")
            or tool_input.get("agent_name", "")
            or tool_input.get("name", "")
            or tool_input.get("skill", "")
        )
        # Check if any of the acceptable values match
        matched = False
        for acceptable in subagent_or_skill:
            short_acceptable = acceptable.split(":")[-1]
            if (
                acceptable in actual
                or short_acceptable in actual
                or actual in acceptable
                or tool_name in (acceptable, short_acceptable)
            ):
                matched = True
                break
        if not matched:
            return False

    contains = cond.get("output_contains")
    if contains:
        # Check tool output (PostToolUse) OR agent response (AfterAgent)
        if ctx.hook_event == "AfterAgent":
            text = ctx.raw_input.get("prompt_response", "")
            if contains not in text:
                return False
        else:
            # Check if string appears in any string value of the output dict
            output_str = str(tool_output)
            if contains not in output_str:
                return False

    # Handle result_key and result_value (check specific output fields)
    result_key = cond.get("result_key")
    if result_key:
        result_value = cond.get("result_value")
        actual_value = tool_output.get(result_key) if isinstance(tool_output, dict) else None
        if actual_value != result_value:
            return False

    skill = cond.get("skill_name")
    if skill:
        actual = tool_input.get("skill", "") or tool_input.get("name", "")
        # Also match when tool_name IS the skill (Gemini direct MCP call)
        if skill not in actual and tool_name not in (skill, skill.split(":")[-1]):
            return False

    return True


def _matches_trigger(
    trigger: dict[str, Any],
    tool_name: str,
    tool_input: dict[str, Any],
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
        state = session_state.load_session_state(session_id)
        if state is None:
            return False
        state_data = state.get("state", {})
        count = state_data.get("tool_calls_since_compliance", 0)
        if count < threshold:
            return False

    return True
