from typing import Any

from hooks.schemas import HookContext
from lib import session_state as session_state_lib
from lib.gate_model import GateResult, GateVerdict
from lib.gates.base import Gate
from lib.session_state import SessionState


class QaGate(Gate):
    """
    QA Gate: Requires QA verification before session end.
    """

    @property
    def name(self) -> str:
        return "qa"

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: QA gate doesn't block tools generally."""
        return None

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Open gate on QA invocation."""
        if self._is_qa_invocation(context.tool_name or "", context.tool_input or {}):
            session_state_lib.set_qa_invoked(context.session_id)
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="✓ `qa` opened (verification complete)"
            )
        return None

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """UserPromptSubmit: Reset gate on new prompt."""
        session_state_lib.clear_qa_invoked(context.session_id)
        return None

    def on_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """Stop: Require QA verification."""
        state = session_state
        if not state:
            return None

        # Check bypass
        if state.get("state", {}).get("gates_bypassed"):
            return None

        hydration_data = state.get("hydration", {})
        state_data = state.get("state", {})
        current_workflow = state_data.get("current_workflow")

        is_hydrated = hydration_data.get("hydrated_intent") is not None
        is_streamlined = current_workflow in (
            "interactive-followup",
            "simple-question",
            "direct-skill",
        )

        if is_hydrated and not is_streamlined:
            if not session_state_lib.is_qa_invoked(context.session_id):
                return GateResult(
                    verdict=GateVerdict.DENY,
                    context_injection=(
                        "⛔ **BLOCKED: QA Verification Required**\n"
                        "**Action Required**: Invoke QA agent to verify your work.\n"
                        "After QA passes, invoke `/handover` again to end the session."
                    ),
                    metadata={"source": "stop_gate_qa_check"},
                )

        return None

    def _is_qa_invocation(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Check if tool call is invoking QA."""
        if tool_name in ("qa", "aops-core:qa"):
            return True

        if tool_name in ("Task", "Skill", "activate_skill", "delegate_to_agent"):
            subagent = (
                tool_input.get("subagent_type", "")
                or tool_input.get("skill", "")
                or tool_input.get("name", "")
                or tool_input.get("agent_name", "")
            )
            if subagent and "qa" in subagent.lower():
                return True

        return False
