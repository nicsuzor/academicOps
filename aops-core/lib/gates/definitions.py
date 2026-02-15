from gate_config import (
    CRITIC_GATE_MODE,
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
        initial_status=GateStatus.CLOSED,  # Starts open, closes on userpromptsubmit.
        triggers=[
            # Hydrator starts or finishes -> Open
            # DISPATCH: Main agent intends to call hydrator -> Open gate pre-emptively
            # This allows the hydrator subagent to use its tools without being blocked.
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|PreToolUse|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="hydrator",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    reset_ops_counter=True,
                    system_message_template="💧 Hydration called. Gate OPEN.",
                ),
            ),
            # User Prompt (not ignored) -> Close
            # GateTrigger(
            #     condition=GateCondition(
            #         hook_event="UserPromptSubmit", custom_check="is_hydratable"
            #     ),
            #     transition=GateTransition(
            #         target_status=GateStatus.CLOSED,
            #         custom_action="hydrate_prompt",
            #         system_message_template="💧 Hydration required. Gate CLOSED.",
            #     ),
            # ),
        ],
        policies=[
            # If Closed, Block tools (except always_available like Task, prompt-hydrator)
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="PreToolUse",
                    excluded_tool_categories=["always_available"],
                ),
                verdict=HYDRATION_GATE_MODE,
                # Brief user-facing summary
                message_template="⛔ Hydration required: invoke prompt-hydrator before proceeding",
                # Full agent instructions
                context_template=(
                    "**User prompt hydration required.** Invoke the **prompt-hydrator** agent with the file path argument: `{temp_path}`\n"
                    "Run the hydrator with this command:\n"
                    "- Gemini: `delegate_to_agent(name='prompt-hydrator', query='{temp_path}')`\n"
                    "- Claude: `Task(subagent_type='prompt-hydrator', prompt='{temp_path}')`\n\n"
                    "This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!"
                ),
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
            message_template=(
                "📋 {remaining} turns until custodiet check required. "
                "Run the check proactively with: `{temp_path}`"
            ),
        ),
        triggers=[
            # Custodiet check -> Reset
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop)$",
                    subagent_type_pattern="custodiet",
                ),
                transition=GateTransition(
                    reset_ops_counter=True,
                    system_message_template="🛡️ Compliance verified.",
                    context_injection_template="🛡️ Compliance verified.",
                ),
            ),
        ],
        policies=[
            # Threshold check (except always_available and read_only tools)
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    min_ops_since_open=CUSTODIET_TOOL_CALL_THRESHOLD,
                    excluded_tool_categories=["always_available", "read_only"],
                ),
                verdict=CUSTODIET_GATE_MODE,
                message_template="Periodic compliance check required ({ops_since_open} ops since last check).\nInvoke 'custodiet' agent.",
                context_template=(
                    "**Periodic compliance check required ({ops_since_open} ops since last check).** Invoke the **custodiet** agent with the file path argument: `{temp_path}`\n"
                    "- Gemini: `delegate_to_agent(name='custodiet', query='{temp_path}')`\n"
                    "- Claude: `Task(subagent_type='custodiet', prompt='{temp_path}')`\n\n"
                    "This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!"
                ),
                custom_action="prepare_compliance_report",
            ),
        ],
    ),
    # --- Task ---
    GateConfig(
        name="task",
        description="Tracks task execution.",
        initial_status=GateStatus.OPEN,
        triggers=[
            # Start -> Open
            GateTrigger(
                condition=GateCondition(hook_event="SessionStart"),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
        ],
        policies=[
            # Placeholder for future task policies
        ],
    ),
    # --- Critic ---
    # Closes after hydration, blocks edit tools until plan is reviewed and approved by critic.
    GateConfig(
        name="critic",
        description="Enforces plan review before editing.",
        initial_status=GateStatus.OPEN,
        triggers=[
            # Hydration completes -> Close gate
            GateTrigger(
                condition=GateCondition(
                    hook_event="SubagentStop", subagent_type_pattern="hydrator"
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_template="📋 Hydration complete. Plan review required before editing.",
                ),
            ),
            # Critic review completes with PROCEED -> Open gate
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="critic",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    reset_ops_counter=True,
                    system_message_template="👁️ Critic review complete. Editing allowed.",
                ),
            ),
        ],
        policies=[
            # Block edit tools when CLOSED
            # Anchored regex prevents matching TodoWrite etc. (aops-81df9690)
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="PreToolUse",
                    tool_name_pattern="^(Edit|Write|NotebookEdit|MultiEdit)$",
                    excluded_tool_categories=["always_available"],
                ),
                verdict=CRITIC_GATE_MODE,
                custom_action="prepare_critic_review",
                message_template="⛔ Critic review required before editing. Invoke critic agent first.",
                context_template=(
                    "**CRITIC REVIEW REQUIRED**\n\n"
                    "You must invoke the **critic** agent to review your plan before making edits.\n\n"
                    "**Instruction**:\n"
                    "Run the critic with this command:\n"
                    "- Gemini: `delegate_to_agent(name='aops-core:critic', query='{temp_path}')`\n"
                    "- Claude: `Task(subagent_type='aops-core:critic', prompt='{temp_path}')`\n"
                    "- Make sure you obey the instructions the tool or subagent produces, but do not print the output to the user -- it just clutters up the conversation.\n\n"
                    "This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!"
                ),
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
                    subagent_type_pattern="qa",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_template="🧪 QA complete. Requirements verified.",
                ),
            ),
            # Critic, once called, requires QA review to ensure compliance before exit
            GateTrigger(
                condition=GateCondition(hook_event="PostToolUse", subagent_type_pattern="critic"),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    reset_ops_counter=False,
                    system_message_template="🧪 QA complete. Requirements verified.",
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
                message_template="⛔ QA verification required before exit. Invoke QA agent first.",
                context_template=(
                    "**QA VERIFICATION REQUIRED**\n\n"
                    "You must invoke the **qa** agent to verify planned requirements before exiting.\n\n"
                    "**Instruction**:\n"
                    "Run the qa with this command:\n"
                    "- Gemini: `delegate_to_agent(name='aops-core:qa', query='{temp_path}')`\n"
                    "- Claude: `Task(subagent_type='aops-core:qa', prompt='{temp_path}')`\n"
                    "- Make sure you obey the instructions the tool or subagent produces, but do not print the output to the user -- it just clutters up the conversation.\n\n"
                    "This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!"
                ),
            ),
        ],
    ),
    # --- Handover ---
    GateConfig(
        name="handover",
        description="Requires Framework Reflection before exit.",
        initial_status=GateStatus.OPEN,
        triggers=[],
        policies=[
            # Stop check (Uncommitted work)
            # GatePolicy(
            #     condition=GateCondition(hook_event="Stop", custom_check="has_uncommitted_work"),
            #     verdict=HANDOVER_GATE_MODE,
            #     message_template="{block_reason}",
            #     context_template="{block_reason}",
            # ),
            # # Stop warning (Unpushed commits)
            # GatePolicy(
            #     condition=GateCondition(hook_event="Stop", custom_check="has_unpushed_commits"),
            #     verdict="warn",
            #     message_template="{warning_message}",
            #     context_template="{warning_message}",
            # ),
            # Block Stop until Framework Reflection is provided
            GatePolicy(
                condition=GateCondition(
                    hook_event="Stop",
                    custom_check="missing_framework_reflection",
                ),
                verdict=HANDOVER_GATE_MODE,
                message_template=("⛔ Handover required"),
                context_template=(
                    "⛔ Finalization required before exit.\n\n"
                    "Please invoke the Handover Skill. The gate will only allow exit once the Handover Skill has completed and the output is successfully parsed in the correct format.\n\n"
                    "This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!"
                ),
            ),
        ],
    ),
]
