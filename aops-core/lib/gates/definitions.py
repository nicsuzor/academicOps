from hooks.gate_config import (
    COMMIT_GATE_MODE,
    CUSTODIET_GATE_MODE,
    CUSTODIET_TOOL_CALL_THRESHOLD,
    HANDOVER_GATE_MODE,
    HYDRATION_GATE_MODE,
    QA_GATE_MODE,
)

from lib.gate_types import (
    CountdownConfig,
    GateCondition,
    GateConfig,
    GatePolicy,
    GateStatus,
    GateTransition,
    GateTrigger,
)

# Note: SubagentStart is included in trigger patterns alongside SubagentStop so
# gates can transition as soon as the subagent is dispatched (e.g. opening a gate
# pre-emptively so the subagent's own tool calls aren't blocked). This is
# intentional, not a workaround — _call_gate_method now routes SubagentStart
# to gate.on_subagent_start() (fixed in aops-55bcf1a2).

GATE_CONFIGS = [
    # --- Hydration ---
    GateConfig(
        name="hydration",
        description="Ensures prompts are hydrated with context.",
        initial_status=GateStatus.CLOSED,  # Starts CLOSED. Opens when hydrator is dispatched.
        triggers=[
            # Hydrator dispatched or finishes -> Open (JIT gate open)
            # Fires on PreToolUse for Agent(subagent_type=prompt-hydrator), opening the
            # gate BEFORE the policy evaluates. This means: the Agent tool call itself is
            # always_available (bypasses policy), AND the trigger opens the gate so the
            # hydrator subagent's own tool calls (Read, Glob, etc.) are not blocked.
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|PreToolUse|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="^(aops-core:)?prompt-hydrator$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    reset_ops_counter=True,
                    system_message_key="hydration.opened",
                ),
            ),
            # User Prompt (not ignored) -> Close
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit", custom_check="is_hydratable"
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    custom_action="hydrate_prompt",
                    system_message_key="hydration.closed",
                    context_key="hydrator.instruction",
                ),
            ),
        ],
        policies=[
            # If Closed, Block/Warn ALL tools except infrastructure.
            # Read-only tools ARE subject to hydration — the intent is to force hydration
            # before ANY exploration. The gate opens JIT when the hydrator is dispatched
            # (via PreToolUse trigger above), so the hydrator's own reads succeed.
            # Compare with custodiet which excludes ["infrastructure", "read_only"].
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="PreToolUse",
                    excluded_tool_categories=["infrastructure", "always_available"],
                    custom_check="is_not_safe_toolsearch",
                ),
                verdict=HYDRATION_GATE_MODE,
                message_key="hydration.policy_message",
                context_key="hydration.block",
            )
        ],
    ),
    # --- Custodiet ---
    GateConfig(
        name="custodiet",
        description="Enforces periodic compliance checks.",
        initial_status=GateStatus.OPEN,
        countdown=CountdownConfig(
            start_before=7,
            threshold=CUSTODIET_TOOL_CALL_THRESHOLD,
            message_key="custodiet.countdown",
        ),
        triggers=[
            # Custodiet check -> Reset
            # PreToolUse is included so the trigger fires (resetting the counter)
            # BEFORE the policy evaluates. Without it, Agent(custodiet) is itself
            # blocked when ops >= threshold (deadlock: can't dispatch the agent
            # that would reset the counter). This mirrors how the hydration gate
            # opens on PreToolUse for the hydrator so the hydrator call is allowed.
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(PreToolUse|SubagentStart|SubagentStop)$",
                    subagent_type_pattern="^(aops-core:)?custodiet$",
                ),
                transition=GateTransition(
                    reset_ops_counter=True,
                    system_message_key="custodiet.verified",
                    context_key="custodiet.verified",
                ),
            ),
        ],
        policies=[
            # Threshold check (except infrastructure and read_only tools)
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    min_ops_since_open=CUSTODIET_TOOL_CALL_THRESHOLD,
                    excluded_tool_categories=["infrastructure", "always_available", "read_only"],
                ),
                verdict=CUSTODIET_GATE_MODE,
                message_key="custodiet.policy_message",
                context_key="custodiet.policy_context",
                custom_action="prepare_compliance_report",
            ),
        ],
    ),
    # --- QA ---
    # Blocks exit until planned requirements are verified by QA agent.
    GateConfig(
        name="qa",
        description="Ensures requirements compliance before exit.",
        initial_status=GateStatus.OPEN,
        triggers=[
            # Start -> Open
            GateTrigger(
                condition=GateCondition(hook_event="SessionStart"),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
            # QA agent verifies requirements -> Open gate
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="^(aops-core:)?qa$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="qa.complete",
                ),
            ),
        ],
        policies=[
            # Block Stop when CLOSED
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                ),
                verdict=QA_GATE_MODE,
                custom_action="prepare_qa_review",
                message_key="qa.policy_message",
                context_key="qa.policy_context",
            ),
        ],
    ),
    # --- Handover ---
    # Gate starts CLOSED.
    # Opens when /handover skill completes. Policy blocks Stop when CLOSED.
    GateConfig(
        name="handover",
        description="Requires Framework Reflection before exit.",
        initial_status=GateStatus.CLOSED,
        triggers=[
            # Task bound: update_task with status=in_progress -> Close
            # Work has begun, so handover will be required before exit.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="update_task",
                    tool_input_pattern="in_progress",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_key="handover.bound",
                ),
            ),
            # /dump skill completes -> Open
            # Uses subagent_type_pattern to match skill name extracted by router
            # (router.py extracts tool_input["skill"] into ctx.subagent_type)
            # Matches both Claude's Skill tool and Gemini's activate_skill tool.
            # Pattern matches "dump", "handover" (legacy), and aops-core: prefixed forms.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="^(Skill|activate_skill)$",
                    subagent_type_pattern="^(aops-core:)?(handover|dump)$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="handover.complete",
                ),
            ),
        ],
        policies=[
            # Block Stop when gate is CLOSED (dump not yet done)
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                ),
                verdict=HANDOVER_GATE_MODE,
                message_key="handover.policy_message",
                context_key="stop.handover_block",
            ),
        ],
    ),
    # --- Commit ---
    # Ensures changes are committed and pushed before exit.
    # Blocks Stop/SessionEnd if uncommitted work; Warns if unpushed commits.
    GateConfig(
        name="commit",
        description="Ensures changes are committed and pushed before exit.",
        initial_status=GateStatus.OPEN,
        policies=[
            # Block Stop/SessionEnd if uncommitted work
            GatePolicy(
                condition=GateCondition(
                    hook_event="^(Stop|SessionEnd)$",
                    custom_check="has_uncommitted_work",
                ),
                verdict=COMMIT_GATE_MODE,
                message_key="commit.uncommitted_block",
                context_key="commit.uncommitted_context",
            ),
            # Warn Stop/SessionEnd if unpushed commits
            GatePolicy(
                condition=GateCondition(
                    hook_event="^(Stop|SessionEnd)$",
                    custom_check="needs_commit_reminder",
                ),
                verdict="warn",
                message_key="commit.unpushed_reminder",
                context_key="commit.unpushed_context",
            ),
        ],
    ),
]
