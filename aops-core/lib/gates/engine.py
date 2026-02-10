import logging
import re
import time
from collections import defaultdict
from typing import Any, Dict, Optional

from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from lib.gate_types import GateConfig, GateState, GateStatus, GateTransition, GateCondition
from lib.session_state import SessionState

logger = logging.getLogger(__name__)

class GenericGate:
    """
    Generic Gate Engine that executes declarative GateConfig.
    """
    def __init__(self, config: GateConfig):
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    def _get_state(self, session_state: SessionState) -> GateState:
        # Ensure state exists
        if self.name not in session_state.gates:
            session_state.gates[self.name] = GateState(status=self.config.initial_status)
        return session_state.gates[self.name]

    def _evaluate_condition(self, condition: GateCondition, ctx: HookContext, state: GateState, session_state: SessionState) -> bool:
        # 0. Check Current Status
        if condition.current_status:
            if state.status != condition.current_status:
                return False

        # 1. Hook Event Match
        if condition.hook_event:
            # Simple equality check
            if condition.hook_event != ctx.hook_event:
                return False

        # 2. Tool Name Pattern
        if condition.tool_name_pattern:
            if not ctx.tool_name:
                return False
            if not re.search(condition.tool_name_pattern, ctx.tool_name):
                return False

        # 2.5 Excluded Tool Categories
        if condition.excluded_tool_categories:
            from hooks.gate_config import get_tool_category
            if ctx.tool_name and get_tool_category(ctx.tool_name) in condition.excluded_tool_categories:
                return False

        # 3. Tool Input Pattern
        if condition.tool_input_pattern:
            # Stringify tool_input and regex search
            input_str = str(ctx.tool_input)
            if not re.search(condition.tool_input_pattern, input_str):
                return False

        # 3.5 Subagent Type Pattern
        if condition.subagent_type_pattern:
            if not ctx.subagent_type:
                return False
            if not re.search(condition.subagent_type_pattern, ctx.subagent_type):
                return False

        # 4. State Metrics Checks
        if condition.min_ops_since_open is not None:
            if state.ops_since_open < condition.min_ops_since_open:
                return False
        if condition.min_ops_since_close is not None:
            if state.ops_since_close < condition.min_ops_since_close:
                return False
        if condition.min_turns_since_open is not None:
            current_turn = session_state.global_turn_count
            diff = current_turn - state.last_open_turn
            if diff < condition.min_turns_since_open:
                return False
        # ... implement other metric checks as needed ...

        # 5. Custom Check
        if condition.custom_check:
            # Import dynamically or use registry
            from lib.gates.custom_conditions import check_custom_condition
            if not check_custom_condition(condition.custom_check, ctx, state, session_state):
                return False

        return True

    def _render_template(self, template: str, ctx: HookContext, state: GateState, session_state: SessionState) -> str:
        # Prepare context variables
        variables = {
            "session_id": ctx.session_id,
            "tool_name": ctx.tool_name or "",
            "gate_status": getattr(state.status, 'value', state.status),
            "ops_since_open": state.ops_since_open,
            "ops_since_close": state.ops_since_close,
            "blocked": state.blocked,
            "block_reason": state.block_reason or "",
            # Access metrics
            **state.metrics
        }

        # Safe format using format_map with default for missing keys
        try:
            return template.format_map(defaultdict(lambda: "(not set)", variables))
        except (KeyError, ValueError, IndexError):
             # Fallback: simple replacement with default for missing keys
             result = template
             for key, val in variables.items():
                 result = result.replace(f"{{{key}}}", str(val))
             # Replace any remaining {placeholder} with "(not set)"
             result = re.sub(r'\{(\w+)\}', '(not set)', result)
             return result

    def _apply_transition(self, transition: GateTransition, ctx: HookContext, state: GateState, session_state: SessionState) -> GateResult:
        # Update Status
        if transition.target_status and transition.target_status != state.status:
            # Change state
            state.status = transition.target_status
            if transition.target_status == GateStatus.OPEN:
                state.last_open_ts = time.time()
                state.last_open_turn = session_state.global_turn_count
                state.ops_since_open = 0
            elif transition.target_status == GateStatus.CLOSED:
                state.last_close_ts = time.time()
                state.last_close_turn = session_state.global_turn_count
                state.ops_since_close = 0

        # Update Metrics
        if transition.reset_ops_counter:
            state.ops_since_open = 0
            state.ops_since_close = 0

        for key, value in transition.set_metrics.items():
            state.metrics[key] = value

        for key in transition.increment_metrics:
            state.metrics[key] = state.metrics.get(key, 0) + 1

        # Render Messages
        sys_msg = None
        if transition.system_message_template:
            sys_msg = self._render_template(transition.system_message_template, ctx, state, session_state)

        ctx_inj = None
        if transition.context_injection_template:
            ctx_inj = self._render_template(transition.context_injection_template, ctx, state, session_state)

        # Custom Action (Side Effects)
        if transition.custom_action:
            from lib.gates.custom_actions import execute_custom_action
            result = execute_custom_action(transition.custom_action, ctx, state, session_state)
            if result:
                if result.system_message:
                    sys_msg = (sys_msg + "\n" + result.system_message) if sys_msg else result.system_message
                if result.context_injection:
                    ctx_inj = (ctx_inj + "\n\n" + result.context_injection) if ctx_inj else result.context_injection

        return GateResult.allow(system_message=sys_msg, context_injection=ctx_inj)

    def _evaluate_triggers(self, ctx: HookContext, session_state: SessionState) -> GateResult | None:
        """Evaluate triggers (Transitions)."""
        state = self._get_state(session_state)

        messages = []
        injections = []
        transition_occurred = False

        for trigger in self.config.triggers:
            if self._evaluate_condition(trigger.condition, ctx, state, session_state):
                result = self._apply_transition(trigger.transition, ctx, state, session_state)
                if result.system_message:
                    messages.append(result.system_message)
                if result.context_injection:
                    injections.append(result.context_injection)
                transition_occurred = True
                # Break after first match to ensure deterministic state transition
                break

        if transition_occurred:
            return GateResult.allow(
                system_message="\n".join(messages) if messages else None,
                context_injection="\n\n".join(injections) if injections else None
            )
        return None

    def _evaluate_policies(self, ctx: HookContext, session_state: SessionState) -> GateResult | None:
        """Evaluate policies (Blocking/Warning)."""
        state = self._get_state(session_state)

        for policy in self.config.policies:
            if self._evaluate_condition(policy.condition, ctx, state, session_state):
                # Policy matched!
                sys_msg = self._render_template(policy.message_template, ctx, state, session_state)
                ctx_inj = None
                if policy.context_template:
                    ctx_inj = self._render_template(policy.context_template, ctx, state, session_state)

                if policy.verdict == "deny":
                    return GateResult.deny(system_message=sys_msg, context_injection=ctx_inj)
                elif policy.verdict == "warn":
                    return GateResult.warn(system_message=sys_msg, context_injection=ctx_inj)

        return None

    # --- Hook Interface ---

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Check policies."""
        return self._evaluate_policies(context, session_state)

    def on_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """Stop: Check policies (blocking) AND Evaluate triggers (cleanup)."""
        # First check policies (blocking)
        policy_result = self._evaluate_policies(context, session_state)
        if policy_result and policy_result.verdict == GateVerdict.DENY:
            return policy_result

        # If not blocked, evaluate triggers (side effects like cleanup)
        trigger_result = self._evaluate_triggers(context, session_state)

        # Merge if policy warned and trigger happened?
        # Usually policy warning is more important.
        if policy_result and policy_result.verdict == GateVerdict.WARN:
             return policy_result

        return trigger_result

    def on_tool_use(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PostToolUse: Evaluate triggers."""
        # Update metrics
        state = self._get_state(session_state)
        if state.status == GateStatus.OPEN:
            state.ops_since_open += 1
        else:
            state.ops_since_close += 1

        return self._evaluate_triggers(context, session_state)

    def on_user_prompt(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        return self._evaluate_triggers(context, session_state)

    def on_session_start(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        return self._evaluate_triggers(context, session_state)

    def on_after_agent(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        return self._evaluate_triggers(context, session_state)

    def on_subagent_stop(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        return self._evaluate_triggers(context, session_state)
