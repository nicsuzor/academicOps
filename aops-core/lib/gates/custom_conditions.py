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

    if name == "is_dispatch_fidelity_violated":
        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}
        requested_tools = tool_input.get("tools")

        # If no tools requested, there's no reduction possible.
        if not requested_tools or not isinstance(requested_tools, list):
            return False

        from hooks.gate_config import extract_subagent_type

        subagent_type, _ = extract_subagent_type(ctx.tool_name, tool_input)
        if not subagent_type:
            return False

        import yaml

        from lib.paths import get_aops_root, get_skills_dir

        # Locate the subagent's definition file
        md_file = None
        candidates = [
            get_aops_root() / "agents" / f"{subagent_type}.md",
            get_skills_dir() / subagent_type / "SKILL.md",
        ]

        for candidate in candidates:
            if candidate.exists():
                md_file = candidate
                break

        if not md_file:
            # If we can't find it, we can't validate it. Assume OK or let downstream handle.
            return False

        try:
            content = md_file.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1]) or {}
            else:
                fm = {}
        except Exception:
            return False

        allowed_tools = fm.get("tools") or fm.get("allowed-tools") or []
        if isinstance(allowed_tools, str):
            allowed_tools = [t.strip() for t in allowed_tools.split(",")]
        elif not isinstance(allowed_tools, list):
            allowed_tools = []

        # Tool name mapping: Claude Code -> Gemini/generic
        # (We map requested Claude tools to their generic names, as .md files use generic names)
        CLAUDE_TO_GENERIC = {
            "Read": "read_file",
            "Write": "write_file",
            "Edit": "replace",
            "Glob": "glob",
            "Grep": "grep_search",
            "Bash": "run_shell_command",
            "Skill": "activate_skill",
            "Task": "activate_skill",
            "Agent": "activate_skill",
            "WebFetch": "web_fetch",
            "WebSearch": "google_web_search",
            "browser_navigate": "navigate_page",
            "browser_snapshot": "take_snapshot",
            "browser_take_screenshot": "take_screenshot",
            "browser_click": "click",
            "browser_wait_for": "wait_for",
            "browser_evaluate": "evaluate_script",
            "browser_type": "type_text",
            "browser_resize": "resize_page",
        }

        # Build the set of effective allowed tools.
        # Note: MCP tools with mcp__ in allowed_tools might be requested as mcp_ (single underscore)
        # or exactly match.
        effective_allowed = set()
        for t in allowed_tools:
            effective_allowed.add(t)
            if t.startswith("mcp__"):
                # Claude might request mcp_plugin_aops-core_pkb_search
                # while the file has mcp__plugin_aops-core_pkb__search
                # Let's map allowed mcp__ to single underscore for robust matching
                effective_allowed.add(t.replace("__", "_"))

        # Compare requested vs allowed
        dropped_tools = []
        for req_tool in requested_tools:
            # Map requested tool to generic name if it exists, else keep as is
            generic_req = CLAUDE_TO_GENERIC.get(req_tool, req_tool)
            # Also check if req_tool replaces __ with _
            req_with_double = req_tool.replace("mcp_plugin_", "mcp__plugin_").replace(
                "_pkb_", "_pkb__"
            )

            if (
                generic_req not in effective_allowed
                and req_tool not in effective_allowed
                and req_with_double not in effective_allowed
            ):
                dropped_tools.append(req_tool)

        if dropped_tools:
            # Store for the custom action to use
            state.metrics["dropped_tools"] = dropped_tools
            state.metrics["target_subagent"] = subagent_type
            return True

        return False

    return False
