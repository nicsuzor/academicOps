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

    return False
