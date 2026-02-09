from typing import Any

from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from lib.gates.base import Gate
from lib.session_state import SessionState


class TaskGate(Gate):
    """
    Task Gate: Ensures a task is bound to the session before allowing write operations.
    Also tracks subagent invocations.
    """

    @property
    def name(self) -> str:
        return "task"

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Check if task is bound for write tools."""
        from hooks.gate_config import get_tool_category

        tool_category = get_tool_category(context.tool_name or "")

        # Only enforce for write tools
        if tool_category != "write":
            return None

        # Check if task is bound
        if session_state.main_agent.current_task:
            return None

        # Task not bound - Block
        return self._create_block_result(context)

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Detect task binding/unbinding and track subagents."""

        # --- Subagent Tracking ---
        tool_input = context.tool_input or {}
        tool_name = context.tool_name or ""

        subagent_type = (
            tool_input.get("subagent_type")
            or tool_input.get("agent_name")
            or tool_input.get("skill")
            or tool_input.get("name")
        )
        if not subagent_type and tool_name not in (
            "Task",
            "Skill",
            "delegate_to_agent",
            "activate_skill",
        ):
            subagent_type = tool_name

        if subagent_type:
            current = session_state.subagents.get(subagent_type, {})
            # Initialize if empty
            if not current:
                current = {"invocations": 0}

            # Increment
            invocations = current.get("invocations", 0)
            current["invocations"] = invocations + 1

            session_state.subagents[subagent_type] = current

        # --- Task Binding ---
        try:
            from lib.event_detector import StateChange, detect_tool_state_changes
            from lib.hook_utils import get_task_id_from_result
        except ImportError:
            return None

        tool_result = context.tool_output

        changes = detect_tool_state_changes(tool_name, tool_input, tool_result)

        if StateChange.UNBIND_TASK in changes:
            current = session_state.main_agent.current_task
            if current:
                session_state.main_agent.current_task = None
                return GateResult(
                    verdict=GateVerdict.ALLOW,
                    system_message=f"Task completed and unbound from session: {current}",
                )
            return None

        if StateChange.BIND_TASK in changes:
            task_id = get_task_id_from_result(tool_result)
            if not task_id:
                return None

            source = "claim"
            current = session_state.main_agent.current_task
            if current and current != task_id:
                return GateResult(
                    verdict=GateVerdict.ALLOW,
                    system_message=f"Note: Session already bound to task {current}, ignoring {task_id}",
                )

            session_state.main_agent.current_task = task_id
            session_state.main_agent.task_binding_source = source
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message=f"Task bound to session: {task_id}",
            )

        return None

    def on_subagent_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """SubagentStop: Update subagent stats."""
        # unified_logger handles recording invocation details (output, duration)
        # TaskGate just tracks existence/counts if not handled in on_tool_use.
        # But on_tool_use handles the *start*. SubagentStop handles the *end*.

        # We can update the subagent record with result details
        subagent_type = context.subagent_type or ""
        if subagent_type and subagent_type in session_state.subagents:
            data = session_state.subagents[subagent_type]
            # Store last result snippet?
            # Unified logger does this better.
            # I'll leave this empty unless we need specific state updates.
            pass
        return None

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        return None

    def on_session_start(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        return None

    def _create_block_result(self, context: HookContext) -> GateResult:
        """Create a block result for the gate."""
        import os
        from hooks.gate_config import GATE_MODE_DEFAULTS, GATE_MODE_ENV_VARS, get_tool_category
        from lib.template_registry import TemplateRegistry

        mode = os.environ.get(GATE_MODE_ENV_VARS.get(self.name, ""), GATE_MODE_DEFAULTS.get(self.name, "warn"))

        try:
            msg = TemplateRegistry.instance().render(
                "tool.gate_message",
                {
                    "mode": mode,
                    "tool_name": context.tool_name,
                    "tool_category": get_tool_category(context.tool_name or ""),
                    "missing_gates": "task",
                    "gate_status": "- task: ✗",
                    "next_instruction": "Use task management tools to claim or create a task.",
                },
            )
        except Exception:
             msg = "⛔ **GATE BLOCKED**: Task binding required.\n\nUse task management tools to claim or create a task."

        if mode == "block":
            return GateResult.deny(system_message=msg, context_injection=msg)
        return GateResult.warn(system_message=msg, context_injection=msg)
