from lib.gate_types import GateState
from lib.hook_context import HookContext
from lib.session_state import SessionState
from lib.tool_categories import get_tool_category


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


def _exit_reflection_full_scope(ctx: HookContext, session_state: SessionState) -> bool:
    """True when this Stop belongs to the exit-reflection gate's FULL-checklist
    audience: a task-bound main-agent session that did real work this turn
    (polecat / crew-after-`/pull` / interactive-with-claimed-task, per
    note_296e5520 §1).

    Everyone else — subagents, a session with no claimed task, or a task-bound
    session on a pure read-only turn — gets the lightweight honesty-only tier
    instead (`is_exit_reflection_lite_active` below). The read-only-turn
    carve-out preserves the handover gate's hard-won exemption (aops-16a15a05,
    aops_d18b2d4b): a no-op turn doesn't owe a full exit ceremony just because
    a task is claimed session-wide.
    """
    if ctx.is_subagent:
        return False
    if not session_state.main_agent.current_task:
        return False
    return session_state.turn_did_work


def check_custom_condition(
    name: str, ctx: HookContext, state: GateState, session_state: SessionState
) -> bool:
    """
    Evaluate a named custom condition.
    """
    if name == "is_write_tool":
        # Treat shell tools as read-only when the exit_reflection gate is
        # sticky (post-skill) or no task is bound — prevents the gate from
        # re-closing on discovery/status commands (e.g. git status after
        # /end-session).
        gate_state = session_state.gates.get("exit_reflection")
        if (gate_state and gate_state.sticky) or not session_state.main_agent.current_task:
            if ctx.tool_name in ("Bash", "run_shell_command", "shell", "execute_code"):
                return False

        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else None
        return ctx.tool_name is not None and get_tool_category(ctx.tool_name, tool_input) == "write"

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

    if name == "is_exit_reflection_full_block_mode":
        # exit_reflection gate, FULL tier, block mode: task-bound session that
        # did work this turn, and EXIT_REFLECTION_GATE_MODE is blocking.
        # Delivers the full checklist via context_injection (upgraded to
        # decision=block on Stop) — persists (no fire-once) until a legal exit
        # (auditor ran, or an honest release_task failure/completion) opens
        # the gate.
        if not _exit_reflection_full_scope(ctx, session_state):
            return False
        return _gate_mode(session_state, "EXIT_REFLECTION_GATE_MODE") in ("block", "deny")

    if name == "is_exit_reflection_full_warn_mode":
        # exit_reflection gate, FULL tier, warn mode: same scope, non-blocking
        # delivery. Fire-once per turn (see is_exit_reflection_fire_once).
        if not _exit_reflection_full_scope(ctx, session_state):
            return False
        return _gate_mode(session_state, "EXIT_REFLECTION_GATE_MODE") == "warn"

    if name == "is_exit_reflection_lite_active":
        # exit_reflection gate, LITE tier: everyone NOT in full scope
        # (subagents, no bound task, or a read-only turn on a bound task).
        # Lightweight honesty/self-reflection reminder ONLY — the ida-gate
        # lineage — and NEVER denies (reminder only, no deadlock risk).
        if _exit_reflection_full_scope(ctx, session_state):
            return False
        return _gate_mode(session_state, "EXIT_REFLECTION_GATE_MODE") in ("warn", "block", "deny")

    if name == "is_exit_reflection_fire_once":
        # Stop (while CLOSED) -> OPEN, fire-once — mirrors every other
        # warn-mode gate so a retried Stop in the same turn passes. The FULL
        # tier's BLOCK mode deliberately has NO fire-once here (persist-until-
        # satisfied, matching the retired rbg-review/qa/handover gates'
        # block-mode behaviour) — its only exits are a real auditor run, an
        # honest release_task call, or the stop-deny escape hatch. The LITE
        # tier is WARN-only by construction, so it always fires-once.
        if _exit_reflection_full_scope(ctx, session_state):
            return _gate_mode(session_state, "EXIT_REFLECTION_GATE_MODE") == "warn"
        return _gate_mode(session_state, "EXIT_REFLECTION_GATE_MODE") in ("warn", "block", "deny")

    if name == "has_bound_task":
        return bool(session_state.main_agent.current_task)

    if name == "turn_did_work":
        # True if the current turn has used a write tool or claimed a task.
        # Used directly in triggers/conditions that need this signal without
        # combining it with a gate-mode check (aops-16a15a05, aops_d18b2d4b).
        return session_state.turn_did_work

    return False
