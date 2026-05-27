import os

from hooks.schemas import HookContext

from lib.gate_types import GateState
from lib.session_state import SessionState


def check_custom_condition(
    name: str, ctx: HookContext, state: GateState, session_state: SessionState
) -> bool:
    """
    Evaluate a named custom condition.
    """
    if name == "is_not_safe_toolsearch":
        # Returns False ONLY if ToolSearch is loading specific tools by name (select:*)
        # Returns True for everything else (including discovery ToolSearch)
        if ctx.tool_name == "ToolSearch":
            tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}
            query = tool_input.get("query", "")
            if isinstance(query, str) and "select:" in query:
                return False
        return True

    if name == "is_write_tool":
        from hooks.gate_config import get_tool_category

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
        # Defer enforcer block while agent has an in-progress todo item.
        # The enforcer trigger on TodoWrite PostToolUse keeps this metric
        # up to date. False (condition not met) when mid-edit, deferring the
        # block until the agent has finished its current sub-task. (#319)
        return not state.metrics.get("has_in_progress_todo", False)

    if name == "is_ida_block_mode":
        # IDA gate policy: active only when IDA_GATE_MODE is blocking.
        # Separating block vs warn into distinct policies lets each choose
        # appropriate message channels (context_key vs message_key) so
        # warn mode doesn't inadvertently upgrade Stop to decision=block.
        return os.environ.get("IDA_GATE_MODE", "warn") in ("block", "deny")

    if name == "is_ida_warn_mode":
        # IDA gate policy: active only when IDA_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only (user-visible)
        # rather than context_injection, so output_for_claude does not upgrade
        # the WARN verdict to decision=block for the Stop hook.
        return os.environ.get("IDA_GATE_MODE", "warn") == "warn"

    if name == "is_qa_block_mode":
        # QA gate policy: active only when QA_GATE_MODE is blocking.
        # Separating block vs warn into distinct policies lets each choose
        # appropriate message channels (context_key vs message_key) so
        # warn mode doesn't inadvertently upgrade Stop to decision=block.
        return os.environ.get("QA_GATE_MODE", "warn") in ("block", "deny")

    if name == "is_qa_warn_mode":
        # QA gate policy: active only when QA_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only (user-visible)
        # rather than context_injection, so output_for_claude does not upgrade
        # the WARN verdict to decision=block for the Stop hook.
        return os.environ.get("QA_GATE_MODE", "warn") == "warn"

    if name == "is_handover_block_mode":
        # Handover gate policy: active only when HANDOVER_GATE_MODE is blocking.
        # Same split pattern as QA and IDA gates.
        return os.environ.get("HANDOVER_GATE_MODE", "warn") in ("block", "deny")

    if name == "is_handover_warn_mode":
        # Handover gate policy: active only when HANDOVER_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only so Stop is
        # not upgraded to decision=block by output_for_claude.
        return os.environ.get("HANDOVER_GATE_MODE", "warn") == "warn"

    if name == "has_bound_task":
        return bool(session_state.main_agent.current_task)

    return False
