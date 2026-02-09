import os
import time
from typing import Any

from hooks.gate_config import get_tool_category
from hooks.schemas import HookContext
from lib import session_state as session_state_lib
from lib.gate_model import GateResult, GateVerdict
from lib.gate_utils import create_audit_file
from lib.gates.base import Gate
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry


class CustodietGate(Gate):
    """
    Custodiet Gate: Enforces periodic compliance checks for write operations.
    """

    @property
    def name(self) -> str:
        return "custodiet"

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Check compliance threshold."""
        tool_category = get_tool_category(context.tool_name or "")

        # Only enforce for write tools
        if tool_category != "write":
            return None

        # Check explicit block
        if session_state_lib.is_custodiet_blocked(context.session_id):
            return self._create_block_result(context, "Custodiet block active.")

        # Check threshold
        threshold = session_state_lib.get_custodiet_threshold()
        count = session_state.get("state", {}).get("tool_calls_since_compliance", 0)

        if count >= threshold:
            return self._create_block_result(context, f"Compliance check required ({count}/{threshold} operations).")

        return None

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Update counters."""
        tool_name = context.tool_name or ""
        tool_input = context.tool_input or {}

        system_messages = []

        # Access generic state
        state = session_state.setdefault("state", {})
        state.setdefault("tool_calls_since_compliance", 0)
        state.setdefault("last_compliance_ts", 0.0)

        # Check for reset (custodiet invoked)
        if self._is_custodiet_invocation(tool_name, tool_input):
            state["tool_calls_since_compliance"] = 0
            state["last_compliance_ts"] = time.time()
            system_messages.append("🛡️ [Gate] Compliance verified. Custodiet gate reset.")
        else:
            state["tool_calls_since_compliance"] += 1
            system_messages.append(f"🛡️ [Gate] Tool calls since last Custodiet check: {state['tool_calls_since_compliance']}.")

        session_state_lib.save_session_state(context.session_id, session_state)

        if system_messages:
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="\n".join(system_messages)
            )

        return None

    def _is_custodiet_invocation(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        """Check if tool call is invoking custodiet."""
        if tool_name in ("custodiet", "aops-core:custodiet"):
            return True

        if tool_name in ("Task", "Skill", "activate_skill", "delegate_to_agent"):
            subagent = (
                tool_input.get("subagent_type", "")
                or tool_input.get("skill", "")
                or tool_input.get("name", "")
                or tool_input.get("agent_name", "")
            )
            if subagent and "custodiet" in subagent.lower():
                return True

        return False

    def _create_block_result(self, context: HookContext, reason: str) -> GateResult:
        """Create block result."""
        from hooks.gate_config import GATE_MODE_DEFAULTS, GATE_MODE_ENV_VARS

        mode = os.environ.get(GATE_MODE_ENV_VARS.get(self.name, ""), GATE_MODE_DEFAULTS.get(self.name, "warn"))

        # Create audit file path for context
        audit_path = create_audit_file(context.session_id, self.name, context)

        agent = "aops-core:custodiet"
        short_name = "custodiet"

        if audit_path:
            next_instruction = f"Invoke {agent} ({short_name}) agent with query: `{audit_path}`"
        else:
            next_instruction = f"Invoke {agent} ({short_name}) agent immediately."

        try:
            msg = TemplateRegistry.instance().render(
                "tool.gate_message",
                {
                    "mode": mode,
                    "tool_name": context.tool_name,
                    "tool_category": get_tool_category(context.tool_name or ""),
                    "missing_gates": "custodiet",
                    "gate_status": "- custodiet: ✗",
                    "next_instruction": next_instruction,
                },
            )
        except Exception:
            msg = f"⛔ **GATE BLOCKED**: {reason}\n\n{next_instruction}"

        if mode == "block":
            return GateResult.deny(system_message=msg, context_injection=msg)
        return GateResult.warn(system_message=msg, context_injection=msg)
