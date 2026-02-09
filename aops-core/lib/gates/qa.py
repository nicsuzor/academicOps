from typing import Any

from hooks.schemas import HookContext
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
            session_state.open_gate(self.name)
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="✓ `qa` opened (verification complete)"
            )
        return None

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """UserPromptSubmit: Reset gate on new prompt."""
        session_state.close_gate(self.name)
        return None

    def on_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """Stop: Require QA verification."""
        # Check bypass
        if session_state.state.get("gates_bypassed"):
            return None

        hydration = session_state.hydration
        is_hydrated = hydration.hydrated_intent is not None

        current_workflow = session_state.state.get("current_workflow")
        is_streamlined = current_workflow in (
            "interactive-followup",
            "simple-question",
            "direct-skill",
        )

        if is_hydrated and not is_streamlined:
            if not session_state.is_gate_open(self.name):
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
