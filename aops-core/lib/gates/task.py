from typing import Any

from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from lib.gates.base import Gate
from lib.session_state import SessionState
from lib import session_state as session_state_lib


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
        if session_state_lib.get_current_task(context.session_id):
            return None

        # Task not bound - Block
        return self._create_block_result(context)

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Detect task binding/unbinding and track subagents."""

        # --- Subagent Tracking ---
        # Track subagent invocations for stop gate (checks has_run_subagents)
        tool_input = context.tool_input or {}
        tool_name = context.tool_name or ""

        subagent_type = (
            tool_input.get("subagent_type")
            or tool_input.get("agent_name")
            or tool_input.get("skill")
            or tool_input.get("name")
        )
        # Gemini direct MCP: tool_name IS the agent
        if not subagent_type and tool_name not in (
            "Task",
            "Skill",
            "delegate_to_agent",
            "activate_skill",
        ):
            subagent_type = tool_name

        if subagent_type:
            try:
                subagents = session_state.setdefault("subagents", {})
                # Handle potential mixed types (legacy int count vs dict)
                current = subagents.get(subagent_type, 0)
                if isinstance(current, int):
                    subagents[subagent_type] = current + 1
                else:
                    # If it's a dict (from record_subagent_invocation), just keep it there
                    # We just need the key to exist for len(subagents) check.
                    # But we should probably update a counter inside it if possible?
                    # For now, just ensure key exists.
                    pass

                session_state_lib.save_session_state(context.session_id, session_state)
            except Exception:
                pass

        # --- Task Binding ---
        try:
            from lib.event_detector import StateChange, detect_tool_state_changes
            from lib.hook_utils import get_task_id_from_result
        except ImportError:
            return None

        tool_result = context.tool_output

        changes = detect_tool_state_changes(tool_name, tool_input, tool_result)

        if StateChange.UNBIND_TASK in changes:
            current = session_state_lib.get_current_task(context.session_id)
            if current:
                session_state_lib.clear_current_task(context.session_id)
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
            current = session_state_lib.get_current_task(context.session_id)
            if current and current != task_id:
                return GateResult(
                    verdict=GateVerdict.ALLOW,
                    system_message=f"Note: Session already bound to task {current}, ignoring {task_id}",
                )

            session_state_lib.set_current_task(context.session_id, task_id, source=source)
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message=f"Task bound to session: {task_id}",
            )

        return None

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """UserPromptSubmit: No-op (Task binding persists)."""
        return None

    def on_session_start(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """SessionStart: Initialize task state."""
        # Task starts unbound (None)
        return None

    def _create_block_result(self, context: HookContext) -> GateResult:
        """Create a block result for the gate."""
        import os
        from hooks.gate_config import GATE_MODE_ENV_VARS, GATE_MODE_DEFAULTS, get_tool_category
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
