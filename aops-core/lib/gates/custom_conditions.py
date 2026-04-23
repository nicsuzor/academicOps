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

        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else None
        return ctx.tool_name is not None and get_tool_category(ctx.tool_name, tool_input) == "write"

    if name == "is_orchestrator_project_write":
        # Fires PostToolUse on Edit/Write to non-framework project source in an
        # orchestrator (non-polecat) session. See specs/orchestrator-boundary.md.
        from lib.orchestrator_boundary import (
            is_orchestrator_session,
            is_project_source_write,
        )

        if not is_orchestrator_session():
            return False
        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else None
        return is_project_source_write(ctx.tool_name, tool_input, ctx.cwd)

    return False
