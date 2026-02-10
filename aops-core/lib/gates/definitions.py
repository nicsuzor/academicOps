import os

from lib.gate_types import (
    GateCondition,
    GateConfig,
    GatePolicy,
    GateStatus,
    GateTransition,
    GateTrigger,
)

CUSTODIET_TOOL_CALL_THRESHOLD = int(os.getenv("CUSTODIET_TOOL_CALL_THRESHOLD", 15))
CUSTODIET_GATE_MODE = os.getenv("CUSTODIET_GATE_MODE", "deny")  # deny or warn

GATE_CONFIGS = [
    # --- Hydration ---
    GateConfig(
        name="hydration",
        description="Ensures prompts are hydrated with context.",
        initial_status=GateStatus.CLOSED,
        triggers=[
            # Hydrator finishes -> Open
            GateTrigger(
                condition=GateCondition(
                    hook_event="SubagentStop", subagent_type_pattern="hydrator"
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    reset_ops_counter=True,
                    system_message_template="💧 Hydration complete. Gate OPEN.",
                ),
            ),
            # Task tool completes (fallback if not subagent)
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="Task",
                    tool_input_pattern="hydrator",
                ),
                transition=GateTransition(target_status=GateStatus.OPEN, reset_ops_counter=True),
            ),
            # User Prompt (not ignored) -> Close
            # Note: user_prompt_submit.py hook script also closes the gate and sets metrics.
            # This trigger ensures consistent state machine behavior.
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit", custom_check="is_hydratable"
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED, custom_action="hydrate_prompt"
                ),
            ),
            # DISPATCH: Main agent intends to call hydrator -> Open gate pre-emptively
            # This allows the hydrator subagent to use its tools without being blocked.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PreToolUse", tool_name_pattern="Task", tool_input_pattern="hydrator"
                ),
                transition=GateTransition(target_status=GateStatus.OPEN, reset_ops_counter=True),
            ),
            GateTrigger(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    tool_name_pattern="Skill",
                    tool_input_pattern="hydrator",
                ),
                transition=GateTransition(target_status=GateStatus.OPEN, reset_ops_counter=True),
            ),
            GateTrigger(
                condition=GateCondition(
                    hook_event="PreToolUse", tool_name_pattern="prompt-hydrator"
                ),
                transition=GateTransition(target_status=GateStatus.OPEN, reset_ops_counter=True),
            ),
            GateTrigger(
                condition=GateCondition(
                    hook_event="PreToolUse", tool_input_pattern="aops-core:prompt-hydrator"
                ),
                transition=GateTransition(target_status=GateStatus.OPEN, reset_ops_counter=True),
            ),
        ],
        policies=[
            # If Closed, Block tools (except always_available like Task, prompt-hydrator)
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="PreToolUse",
                    excluded_tool_categories=["always_available"],
                ),
                verdict="deny",
                message_template=(
                    "⛔ **HYDRATION REQUIRED**\n\n"
                    "You must invoke the **prompt-hydrator** agent to load context before proceeding.\n\n"
                    "**Instruction**:\n"
                    "Run the hydrator with this command:\n"
                    "- Gemini: `delegate_to_agent(name='prompt-hydrator', query='Analyze context in {temp_path}')`\n"
                    "- Claude: `Task(subagent_type='prompt-hydrator', prompt='Analyze context in {temp_path}')`"
                ),
                context_template="Hydration Context: {temp_path}",
            )
        ],
    ),
    # --- Custodiet ---
    GateConfig(
        name="custodiet",
        description="Enforces periodic compliance checks.",
        initial_status=GateStatus.OPEN,
        triggers=[
            # Custodiet check -> Reset
            GateTrigger(
                condition=GateCondition(hook_event="PostToolUse", tool_name_pattern="custodiet"),
                transition=GateTransition(
                    reset_ops_counter=True, system_message_template="🛡️ Compliance verified."
                ),
            ),
            GateTrigger(
                condition=GateCondition(
                    hook_event="SubagentStop", subagent_type_pattern="custodiet"
                ),
                transition=GateTransition(
                    reset_ops_counter=True, system_message_template="🛡️ Compliance verified."
                ),
            ),
            # Also reset if Task tool calls custodiet
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="Task",
                    tool_input_pattern="custodiet",
                ),
                transition=GateTransition(reset_ops_counter=True),
            ),
        ],
        policies=[
            # Threshold check (except always_available tools)
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    min_ops_since_open=CUSTODIET_TOOL_CALL_THRESHOLD,
                    excluded_tool_categories=["always_available"],
                ),
                verdict=CUSTODIET_GATE_MODE,
                message_template="Compliance check required ({ops_since_open} ops since last check).\nInvoke 'custodiet' agent.",
                context_template="Compliance Context: {temp_path}",
                custom_action="prepare_compliance_report",
            ),
            # Stop check (Uncommitted work)
            GatePolicy(
                condition=GateCondition(hook_event="Stop", custom_check="has_uncommitted_work"),
                verdict="deny",
                message_template="{block_reason}",
            ),
            # Stop warning (Unpushed commits)
            GatePolicy(
                condition=GateCondition(hook_event="Stop", custom_check="has_unpushed_commits"),
                verdict="warn",
                message_template="{warning_message}",
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
    GateConfig(
        name="critic",
        description="Encourages periodic review.",
        initial_status=GateStatus.OPEN,
        triggers=[
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="critic"),
                transition=GateTransition(
                    reset_ops_counter=True, system_message_template="👁️ Critic review complete."
                ),
            ),
        ],
        policies=[
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    min_ops_since_open=20,
                    excluded_tool_categories=["always_available"],
                ),
                verdict="warn",
                message_template="Consider invoking 'critic' for review ({ops_since_open} ops since last check).",
            )
        ],
    ),
    # --- QA ---
    GateConfig(
        name="qa",
        description="Ensures code quality.",
        initial_status=GateStatus.CLOSED,
        triggers=[
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="qa"),
                transition=GateTransition(
                    target_status=GateStatus.OPEN, system_message_template="🧪 QA complete."
                ),
            )
        ],
        policies=[
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    min_ops_since_open=30,
                    excluded_tool_categories=["always_available"],
                ),
                verdict="warn",
                message_template="Consider running QA ({ops_since_open} ops since last QA).",
            )
        ],
    ),
    # --- Handover ---
    # <!-- NS: revise this, this is NOT the handover gate. -->
    # GateConfig(
    #     name="handover",
    #     description="Manages session length.",
    #     initial_status=GateStatus.OPEN,
    #     triggers=[],
    #     policies=[
    #         # Note: min_turns_since_open is relative to last open.
    #         # If never closed, it equals global turns if opened at start.
    #         GatePolicy(
    #             condition=GateCondition(
    #                 hook_event="PreToolUse",
    #                 min_turns_since_open=50,
    #                 excluded_tool_categories=["always_available"],
    #             ),
    #             verdict="warn",
    #             message_template="Session is getting long ({ops_since_open} turns). Consider summarizing and starting a new session.",
    #         )
    #     ],
    # ),
]
