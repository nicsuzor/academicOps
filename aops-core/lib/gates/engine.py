import logging
import re
import time
from typing import Any

from hooks.schemas import HookContext

from lib.gate_model import GateResult, GateVerdict
from lib.gate_types import (
    GateCondition,
    GateConfig,
    GateState,
    GateStatus,
    GateTransition,
)
from lib.session_paths import get_gate_file_path
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

    def _evaluate_condition(
        self,
        condition: GateCondition,
        ctx: HookContext,
        state: GateState,
        session_state: SessionState,
    ) -> bool:
        # 0. Check Current Status
        if condition.current_status:
            if state.status != condition.current_status:
                return False

        # 1. Hook Event Match
        if condition.hook_event:
            # Match regex if it starts with ^ or ends with $ or contains |
            if any(c in condition.hook_event for c in "^$|[]()"):
                if not re.search(condition.hook_event, ctx.hook_event):
                    return False
            else:
                # Simple equality check for backward compatibility and speed
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

            if (
                ctx.tool_name
                and get_tool_category(ctx.tool_name) in condition.excluded_tool_categories
            ):
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

    def _render_template(
        self, template: str, ctx: HookContext, state: GateState, session_state: SessionState
    ) -> str:
        # Prepare context variables
        variables: dict[str, Any] = {
            "session_id": ctx.session_id,
            "tool_name": ctx.tool_name or "",
            "gate_status": getattr(state.status, "value", state.status),
            "ops_since_open": state.ops_since_open,
            "ops_since_close": state.ops_since_close,
            "blocked": state.blocked,
            "block_reason": state.block_reason or "",
            # Access metrics
            **state.metrics,
        }

        # Add deterministic temp_path if not already in metrics (P#102)
        if "temp_path" not in variables:
            variables["temp_path"] = str(get_gate_file_path(self.name, ctx.session_id))

        # Fail fast on missing template variables. The old defaultdict fallback
        # silently produced "(not set)" which caused gates to pass broken
        # instructions to agents (e.g. temp_path not in metrics).
        try:
            return template.format_map(variables)
        except KeyError as e:
            raise RuntimeError(
                f"Gate '{self.name}' template has unresolved variable {e}. "
                f"Available variables: {sorted(variables.keys())}. "
                f"Template: {template[:200]!r}"
            ) from e

    def _apply_transition(
        self,
        transition: GateTransition,
        ctx: HookContext,
        state: GateState,
        session_state: SessionState,
    ) -> GateResult:
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
            sys_msg = self._render_template(
                transition.system_message_template, ctx, state, session_state
            )

        ctx_inj = None
        if transition.context_injection_template:
            ctx_inj = self._render_template(
                transition.context_injection_template, ctx, state, session_state
            )

        # Custom Action (Side Effects)
        if transition.custom_action:
            from lib.gates.custom_actions import execute_custom_action

            result = execute_custom_action(transition.custom_action, ctx, state, session_state)
            if result:
                if result.system_message:
                    sys_msg = (
                        (sys_msg + "\n" + result.system_message)
                        if sys_msg
                        else result.system_message
                    )
                if result.context_injection:
                    ctx_inj = (
                        (ctx_inj + "\n\n" + result.context_injection)
                        if ctx_inj
                        else result.context_injection
                    )

        return GateResult.allow(system_message=sys_msg, context_injection=ctx_inj)

    def _evaluate_triggers(
        self, ctx: HookContext, session_state: SessionState
    ) -> GateResult | None:
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
                context_injection="\n\n".join(injections) if injections else None,
            )
        return None

    def _evaluate_countdown(
        self, ctx: HookContext, session_state: SessionState
    ) -> GateResult | None:
        """Evaluate countdown warning before threshold is reached.

        Returns a subtle informational message if we're approaching the
        threshold but haven't reached it yet. This gives agents advance
        notice to proactively run compliance checks.
        """
        countdown = self.config.countdown
        if not countdown:
            return None

        state = self._get_state(session_state)

        # Get current ops count based on configured metric
        if countdown.metric == "ops_since_open":
            current_ops = state.ops_since_open
        elif countdown.metric == "ops_since_close":
            current_ops = state.ops_since_close
        else:
            current_ops = state.metrics.get(countdown.metric, 0)

        threshold = countdown.threshold
        start_at = threshold - countdown.start_before

        # Only show countdown if we're in the window (start_at <= current < threshold)
        if current_ops < start_at or current_ops >= threshold:
            return None

        remaining = threshold - current_ops

        # Compute temp_path deterministically if not in metrics
        # Bug fix: aops-d3b46a51 - temp_path was showing "(not available)" in
        # countdown because it was only set when policy fired (at threshold).
        # Now we compute it using get_gate_file_path() so agents know the path
        # in advance.
        temp_path = state.metrics.get("temp_path")
        if not temp_path:
            temp_path = str(get_gate_file_path(self.name, ctx.session_id))

        # Render countdown message
        variables = {
            "remaining": remaining,
            "threshold": threshold,
            "current": current_ops,
            "gate_name": self.name,
            "temp_path": temp_path,
        }

        try:
            message = countdown.message_template.format_map(variables)
        except KeyError as e:
            logger.warning(f"Countdown template error for gate '{self.name}': {e}")
            message = f"📋 {remaining} turns until {self.name} check required."

        return GateResult.allow(system_message=message)

    def _evaluate_policies(
        self, ctx: HookContext, session_state: SessionState
    ) -> GateResult | None:
        """Evaluate policies (Blocking/Warning)."""
        state = self._get_state(session_state)

        for policy in self.config.policies:
            if self._evaluate_condition(policy.condition, ctx, state, session_state):
                # Policy matched!

                # Custom Action (Side Effects before message rendering)
                sys_msg_prefix = ""
                ctx_inj_prefix = ""
                if policy.custom_action:
                    from lib.gates.custom_actions import execute_custom_action

                    action_result = execute_custom_action(
                        policy.custom_action, ctx, state, session_state
                    )
                    if action_result:
                        if action_result.system_message:
                            sys_msg_prefix = action_result.system_message + "\n"
                        if action_result.context_injection:
                            ctx_inj_prefix = action_result.context_injection + "\n\n"

                sys_msg = self._render_template(policy.message_template, ctx, state, session_state)
                ctx_inj = None
                if policy.context_template:
                    ctx_inj = self._render_template(
                        policy.context_template, ctx, state, session_state
                    )

                # Combine prefixes
                final_sys_msg = sys_msg_prefix + sys_msg
                final_ctx_inj = ctx_inj_prefix + (ctx_inj if ctx_inj else "")

                if policy.verdict == "deny":
                    return GateResult.deny(
                        system_message=final_sys_msg,
                        context_injection=final_ctx_inj if final_ctx_inj else None,
                    )
                elif policy.verdict == "warn":
                    return GateResult.warn(
                        system_message=final_sys_msg,
                        context_injection=final_ctx_inj if final_ctx_inj else None,
                    )

        return None

    # --- Hook Interface ---

    def evaluate_triggers(
        self, context: HookContext, session_state: SessionState
    ) -> GateResult | None:
        """Evaluate only triggers (state updates), ignoring policies.

        Use this when bypassing gates for compliance subagents while still
        needing to update gate states.
        """
        return self._evaluate_triggers(context, session_state)

    def check(self, context: HookContext, session_state: SessionState) -> GateResult | None:
        """PreToolUse: Check policies and countdown warnings."""
        # Run triggers first to allow JIT state transitions (e.g. unblocking hydrator)
        trigger_result = self._evaluate_triggers(context, session_state)
        policy_result = self._evaluate_policies(context, session_state)

        # If policy blocks/warns, return that (countdown not needed)
        if policy_result and policy_result.verdict in (GateVerdict.DENY, GateVerdict.WARN):
            if trigger_result:
                # Merge trigger messages but keep policy verdict
                return GateResult(
                    verdict=policy_result.verdict,
                    system_message="\n".join(
                        filter(None, [trigger_result.system_message, policy_result.system_message])
                    ),
                    context_injection="\n\n".join(
                        filter(
                            None,
                            [trigger_result.context_injection, policy_result.context_injection],
                        )
                    ),
                    metadata={**trigger_result.metadata, **policy_result.metadata},
                )
            return policy_result

        # Check countdown warning (only if policy didn't trigger)
        countdown_result = self._evaluate_countdown(context, session_state)

        # Collect all results to merge
        results = [r for r in [trigger_result, policy_result, countdown_result] if r]

        if not results:
            return None
        if len(results) == 1:
            return results[0]

        # Merge all results
        # Verdict: deny > warn > allow
        verdict = GateVerdict.ALLOW
        for r in results:
            if r.verdict == GateVerdict.DENY:
                verdict = GateVerdict.DENY
                break
            elif r.verdict == GateVerdict.WARN:
                verdict = GateVerdict.WARN

        merged_metadata: dict = {}
        for r in results:
            merged_metadata.update(r.metadata)

        return GateResult(
            verdict=verdict,
            system_message="\n".join(filter(None, [r.system_message for r in results])),
            context_injection="\n\n".join(filter(None, [r.context_injection for r in results])),
            metadata=merged_metadata,
        )

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

    def on_user_prompt(
        self, context: HookContext, session_state: SessionState
    ) -> GateResult | None:
        return self._evaluate_triggers(context, session_state)

    def on_session_start(
        self, context: HookContext, session_state: SessionState
    ) -> GateResult | None:
        return self._evaluate_triggers(context, session_state)

    def on_after_agent(
        self, context: HookContext, session_state: SessionState
    ) -> GateResult | None:
        return self._evaluate_triggers(context, session_state)

    def on_subagent_stop(
        self, context: HookContext, session_state: SessionState
    ) -> GateResult | None:
        return self._evaluate_triggers(context, session_state)
