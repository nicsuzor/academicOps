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

        # Refinement (aops-2283a8b0): treat shell tools as read-only if handover
        # was just invoked or no task is bound. This prevents the gate from
        # re-closing on discovery/status tools (e.g. git status, echo).
        if (
            session_state.state.get("handover_skill_invoked")
            or not session_state.main_agent.current_task
        ):
            if ctx.tool_name in ("Bash", "run_shell_command", "shell", "execute_code"):
                return False

        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else None
        return ctx.tool_name is not None and get_tool_category(ctx.tool_name, tool_input) == "write"

    return False
