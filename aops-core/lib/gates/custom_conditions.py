from lib.gate_types import GateState
from lib.hook_context import HookContext
from lib.session_state import SessionState
from lib.tool_categories import COMPLIANCE_SUBAGENT_TYPES, get_tool_category


def _gate_mode(session_state: SessionState, var_name: str) -> str:
    """Resolve a *_GATE_MODE value, preferring the SessionStart-anchored copy.

    Claude Code hooks strip the shell environment before inner-loop (non
    SessionStart) invocations, so a bare `os.environ`/gate_config read here
    can silently see the wrong (default) value mid-session. `session_state
    .gate_modes` is populated once at SessionStart, when the real environment
    is intact, so it is authoritative when present. Falling back to
    gate_config covers tests/ad-hoc invocations that set the env var directly
    without going through SessionStart.
    """
    if var_name in session_state.gate_modes:
        return session_state.gate_modes[var_name]
    from hooks import gate_config

    return getattr(gate_config, var_name)


def check_custom_condition(
    name: str, ctx: HookContext, state: GateState, session_state: SessionState
) -> bool:
    """
    Evaluate a named custom condition.
    """
    if name == "is_write_tool":
        # Treat shell tools as read-only when the handover gate is sticky
        # (post-skill) or no task is bound — prevents gates from re-closing
        # on discovery/status commands (e.g. git status after /end-session).
        handover_state = session_state.gates.get("handover")
        if (handover_state and handover_state.sticky) or not session_state.main_agent.current_task:
            if ctx.tool_name in ("Bash", "run_shell_command", "shell", "execute_code"):
                return False

        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else None
        return ctx.tool_name is not None and get_tool_category(ctx.tool_name, tool_input) == "write"

    if name == "not_mid_edit":
        # Defer RBG block while agent has an in-progress todo item.
        # The RBG trigger on TodoWrite PostToolUse keeps this metric
        # up to date. False (condition not met) when mid-edit, deferring the
        # block until the agent has finished its current sub-task. (#319)
        return not state.metrics.get("has_in_progress_todo", False)

    if name == "is_ida_active":
        # IDA gate trigger: fires when IDA mode is warn or block (not off).
        # Used by the AskUserQuestion trigger which must never deny — the
        # trigger delivers advisory context injection only (GateResult.allow).
        # Posture resolves via the SessionStart-anchored value (see
        # _gate_mode) — NOT a bare os.environ read, which inner-loop hook
        # invocations see with a stripped environment.
        return _gate_mode(session_state, "IDA_GATE_MODE") in ("warn", "block", "deny")

    if name == "is_ida_block_mode":
        # IDA gate policy: active only when IDA_GATE_MODE is blocking.
        # Separating block vs warn into distinct policies lets each choose
        # appropriate message channels (context_key vs message_key) so
        # warn mode doesn't inadvertently upgrade Stop to decision=block.
        return _gate_mode(session_state, "IDA_GATE_MODE") in ("block", "deny")

    if name == "is_ida_warn_mode":
        # IDA gate policy: active only when IDA_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only (user-visible)
        # rather than context_injection, so output_for_claude does not upgrade
        # the WARN verdict to decision=block for the Stop hook.
        return _gate_mode(session_state, "IDA_GATE_MODE") == "warn"

    if name == "is_qa_block_mode":
        # QA gate policy: active only when QA_GATE_MODE is blocking.
        # Separating block vs warn into distinct policies lets each choose
        # appropriate message channels (context_key vs message_key) so
        # warn mode doesn't inadvertently upgrade Stop to decision=block.
        return _gate_mode(session_state, "QA_GATE_MODE") in ("block", "deny")

    if name == "is_qa_warn_mode":
        # QA gate policy: active only when QA_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only (user-visible)
        # rather than context_injection, so output_for_claude does not upgrade
        # the WARN verdict to decision=block for the Stop hook.
        return _gate_mode(session_state, "QA_GATE_MODE") == "warn"

    if name == "is_rbg_review_block_mode":
        # RBG-review gate policy: active only when RBG_REVIEW_GATE_MODE is
        # blocking. Block mode delivers the dispatch instruction via the
        # context_injection channel (upgraded to decision=block on Stop), which
        # is what makes the agent actually run rbg. This is the directive's
        # required posture: a real DENY until rbg has run for the armed turn.
        return _gate_mode(session_state, "RBG_REVIEW_GATE_MODE") in ("block", "deny")

    if name == "is_rbg_review_warn_mode":
        # RBG-review gate policy: active only when RBG_REVIEW_GATE_MODE is warn.
        # Warn still injects the dispatch instruction (block-once per turn via
        # the warn+context_injection upgrade path), but does not hard-hold the
        # session. Provided for parity / staged rollout; default mode is block.
        return _gate_mode(session_state, "RBG_REVIEW_GATE_MODE") == "warn"

    if name == "is_handover_block_mode":
        # Handover gate policy: active only when HANDOVER_GATE_MODE is blocking
        # AND the CURRENT TURN did real work (write tool or task claim).
        # Read-only turns (turn_did_work=False) are exempt — they need no
        # structured handover (aops-16a15a05, aops_d18b2d4b).
        if not session_state.turn_did_work:
            return False
        return _gate_mode(session_state, "HANDOVER_GATE_MODE") in ("block", "deny")

    if name == "is_handover_warn_mode":
        # Handover gate policy: active only when HANDOVER_GATE_MODE is warn
        # AND the current turn did real work. Same read-only exemption as block mode.
        if not session_state.turn_did_work:
            return False

        # D1 (uniform stop-gate behaviour): warn hard-blocks ONCE per turn like
        # every other warn gate — the single forced continuation IS the nudge,
        # so the former soft interactive rate-limiting (spec mem-438429c5
        # §5.4-5.5) is superseded and removed. Fire-once (the warn-mode Stop
        # trigger in definitions.py) is now the whole cadence.
        return _gate_mode(session_state, "HANDOVER_GATE_MODE") == "warn"

    if name == "not_compliance_subagent":
        # deliverable-verify gate condition (task-1029fccb): skip the
        # reminder when the subagent that just stopped IS a compliance
        # agent (rbg/marsha) — auditing the auditor's own SubagentStop is
        # a recursion, not a narrowing of the surface this gate exists to
        # catch (relayed deliverables from ordinary delegated work).
        return ctx.subagent_type not in COMPLIANCE_SUBAGENT_TYPES

    if name == "has_bound_task":
        return bool(session_state.main_agent.current_task)

    if name == "turn_did_work":
        # True if the current turn has used a write tool or claimed a task.
        # Used directly in triggers/conditions that need this signal without
        # combining it with a gate-mode check (aops-16a15a05, aops_d18b2d4b).
        return session_state.turn_did_work

    return False
