import time
import os
from typing import Any

from hooks.gate_config import get_tool_category
from hooks.schemas import HookContext
from hooks.session_end_commit_check import check_uncommitted_work
from lib.gate_model import GateResult, GateVerdict
from lib.gates.base import Gate
from lib.session_state import SessionState


class CustodietGate(Gate):
    """
    Custodiet Gate: Enforces periodic compliance checks for write operations
    and ensures clean session shutdown (commits, cleanup).
    """

    @property
    def name(self) -> str:
        return "custodiet"

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Check compliance threshold."""
        if not context.tool_name:
            return None

        tool_category = get_tool_category(context.tool_name)

        # Only enforce for write tools
        if tool_category != "write":
            return None

        # Check explicit block
        gate = session_state.get_gate(self.name)
        if gate.blocked:
            return self._create_block_result(context, f"Custodiet block active: {gate.block_reason}")

        # Check threshold
        # Legacy compat: check env var or config
        default = 7
        raw = os.environ.get("CUSTODIET_TOOL_CALL_THRESHOLD")
        try:
            threshold = int(raw) if raw else default
        except (ValueError, TypeError):
            threshold = default

        count = gate.metadata.get("tool_calls_since_compliance", 0)

        if count >= threshold:
            return self._create_block_result(context, f"Compliance check required ({count}/{threshold} operations).")

        return None

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Update counters."""
        tool_name = context.tool_name or ""
        tool_input = context.tool_input or {}

        system_messages = []

        gate = session_state.get_gate(self.name)

        # Check for reset (custodiet invoked)
        if self._is_custodiet_invocation(tool_name, tool_input):
            gate.metadata["tool_calls_since_compliance"] = 0
            gate.metadata["last_compliance_ts"] = time.time()
            # Also ensure gate is open/unblocked
            gate.blocked = False
            gate.block_reason = None
            system_messages.append("🛡️ [Gate] Compliance verified. Custodiet gate reset.")
        else:
            current = gate.metadata.get("tool_calls_since_compliance", 0)
            gate.metadata["tool_calls_since_compliance"] = current + 1
            # Only show message periodically or if nearing threshold?
            # For now, maybe suppress to avoid noise unless high?
            # system_messages.append(f"🛡️ [Gate] Tool calls since last Custodiet check: {current + 1}.")
            pass

        if system_messages:
            return GateResult.allow(system_message="\n".join(system_messages))

        return None

    def on_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """Stop: Check for uncommitted work."""
        # Check uncommitted work using shared logic
        result = check_uncommitted_work(context.session_id, context.transcript_path)

        if result.should_block:
            return GateResult.deny(
                system_message=result.message,
                context_injection=result.message
            )

        if result.reminder_needed:
            return GateResult.allow(
                system_message=result.message,
                context_injection=result.message
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
        from lib.gate_utils import create_audit_file
        # from lib.template_registry import TemplateRegistry # Removed: assume unavailable or use simpler approach

        mode = os.environ.get(GATE_MODE_ENV_VARS.get(self.name, ""), GATE_MODE_DEFAULTS.get(self.name, "warn"))

        # Create audit file path for context
        # audit_path = create_audit_file(context.session_id, self.name, context) # Simplify for now

        agent = "aops-core:custodiet"
        short_name = "custodiet"

        next_instruction = f"Invoke {agent} ({short_name}) agent immediately."

        msg = f"⛔ **GATE BLOCKED**: {reason}\n\n{next_instruction}"

        if mode == "block":
            return GateResult.deny(system_message=msg, context_injection=msg)
        return GateResult.warn(system_message=msg, context_injection=msg)
