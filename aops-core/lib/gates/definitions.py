from hooks.gate_config import (
    CUSTODIET_GATE_MODE,
    CUSTODIET_TOOL_CALL_THRESHOLD,
    HANDOVER_GATE_MODE,
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
            # is blocked when ops >= threshold (deadlock: can't dispatch the agent
            # that would reset the counter).
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(PreToolUse|SubagentStart|SubagentStop)$",
                    subagent_type_pattern="^(aops-core:)?(custodiet|rbg)$",
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
                    subagent_type_pattern="^(aops-core:)?(qa|marsha)$",
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
    # Gate starts OPEN (so short interactive chats don't require handover).
    # Closes when work begins (task bound or write tool used).
    # Opens when /handover skill completes. Policy blocks Stop when CLOSED.
    GateConfig(
        name="handover",
        description="Requires Framework Reflection before exit.",
        initial_status=GateStatus.OPEN,
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
            # Write tool used -> Close
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    custom_check="is_write_tool",
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
            # Gemini /dump via slash command injection (UserPromptSubmit containing /dump template)
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                    prompt_pattern=r"^\s*#\s*/dump\s*-\s*Session Handover",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="handover.complete",
                ),
            ),
            # Gemini fallback to Pauli subagent for /dump
            GateTrigger(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    tool_name_pattern="^pauli$",
                    tool_input_pattern=r"/dump|handover",
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
]
