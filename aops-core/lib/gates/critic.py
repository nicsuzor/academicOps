import os
import re
from typing import Any

from hooks.gate_config import get_tool_category
from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from lib.gate_utils import create_audit_file
from lib.gates.base import Gate
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry


class CriticGate(Gate):
    """
    Critic Gate: Requires plan review before destructive actions or session end.
    """

    @property
    def name(self) -> str:
        return "critic"

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Check if critic has approved plan."""
        tool_category = get_tool_category(context.tool_name or "")

        # Only enforce for write tools
        if tool_category != "write":
            return None

        # Check if critic invoked (gate is open)
        if session_state.is_gate_open(self.name):
            return None

        return self._create_block_result(context, "Critic approval required for write operations.")

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Open gate on approval."""
        # Check if tool is critic
        if not self._is_critic_invocation(context.tool_name or "", context.tool_input or {}):
            return None

        # Check for approval in output
        output_str = str(context.tool_output or "")
        if "APPROVED" in output_str:
            session_state.open_gate(self.name)
            session_state.hydration.critic_verdict = "PROCEED"
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="✓ `critic` opened (plan approved)"
            )

        return None

    def on_subagent_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """SubagentStop: Check verdict."""
        subagent_type = context.subagent_type or ""
        if "critic" in subagent_type.lower():
            verdict = None
            result = context.tool_output

            if isinstance(result, dict):
                verdict = result.get("verdict")
            elif isinstance(result, str):
                for v in ["PROCEED", "REVISE", "HALT"]:
                    if v in result.upper():
                        verdict = v
                        break

            if verdict == "PROCEED":
                session_state.open_gate(self.name)
                session_state.hydration.critic_verdict = verdict
                return GateResult.allow(system_message="✓ `critic` opened (subagent approved)")

        return None

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """UserPromptSubmit: Reset gate on new prompt (new intent = new plan)."""
        session_state.close_gate(self.name)
        session_state.hydration.critic_verdict = None
        return None

    def on_after_agent(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """AfterAgent: Check for approval in agent response."""
        response_text = context.raw_input.get("prompt_response", "")
        if "APPROVED" in response_text:
            session_state.open_gate(self.name)
            session_state.hydration.critic_verdict = "PROCEED"
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="✓ `critic` opened (plan approved in response)"
            )
        return None

    def on_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """Stop: Require critic if hydration just finished."""
        # Check bypass
        if session_state.state.get("gates_bypassed"):
            return None

        is_hydrated = session_state.hydration.hydrated_intent is not None

        # Check subagents ran
        has_run_subagents = len(session_state.subagents) > 0

        current_workflow = session_state.state.get("current_workflow")
        is_streamlined = current_workflow in (
            "interactive-followup",
            "simple-question",
            "direct-skill",
        )

        # Hydration pending check (legacy bag)
        hydration_pending = session_state.state.get("hydration_pending", False)
        is_trivial_session = not hydration_pending and not is_hydrated

        # Only require critic if hydration actually occurred and no work was done yet
        if is_hydrated and not has_run_subagents and not is_streamlined and not is_trivial_session:
             return GateResult(
                verdict=GateVerdict.DENY,
                context_injection="⛔ **BLOCKED**: Immediate stop after hydration requires Critic review.\n\nInvoke `critic` agent to review the plan.",
                metadata={"source": "stop_gate_critic_check"},
             )

        return None

    def _is_critic_invocation(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Check if tool call is invoking critic."""
        if tool_name in ("critic", "aops-core:critic"):
            return True

        if tool_name in ("Task", "Skill", "activate_skill", "delegate_to_agent"):
            subagent = (
                tool_input.get("subagent_type", "")
                or tool_input.get("skill", "")
                or tool_input.get("name", "")
                or tool_input.get("agent_name", "")
            )
            if subagent and "critic" in subagent.lower():
                return True

        return False

    def _create_block_result(self, context: HookContext, reason: str) -> GateResult:
        """Create block result."""
        from hooks.gate_config import GATE_MODE_DEFAULTS, GATE_MODE_ENV_VARS

        mode = os.environ.get(GATE_MODE_ENV_VARS.get(self.name, ""), GATE_MODE_DEFAULTS.get(self.name, "warn"))

        audit_path = create_audit_file(context.session_id, self.name, context)

        if audit_path:
             next_instruction = f"Invoke `critic` agent with query: `{audit_path}`"
        else:
             next_instruction = "Invoke `critic` agent to review the plan."

        try:
            msg = TemplateRegistry.instance().render(
                "tool.gate_message",
                {
                    "mode": mode,
                    "tool_name": context.tool_name,
                    "tool_category": get_tool_category(context.tool_name or ""),
                    "missing_gates": "critic",
                    "gate_status": "- critic: ✗",
                    "next_instruction": next_instruction,
                },
            )
        except Exception:
            msg = f"⛔ **GATE BLOCKED**: {reason}\n\n{next_instruction}"

        if mode == "block":
            return GateResult.deny(system_message=msg, context_injection=msg)
        return GateResult.warn(system_message=msg, context_injection=msg)
