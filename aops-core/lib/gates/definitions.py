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
                # Brief user-facing summary
                message_template="⛔ Hydration required: invoke prompt-hydrator before proceeding",
                # Full agent instructions
                context_template=(
                    "**HYDRATION REQUIRED**\n\n"
                    "You must invoke the **prompt-hydrator** agent to load context before proceeding.\n\n"
                    "**Instruction**:\n"
                    "Run the hydrator with this command:\n"
                    "- Gemini: `delegate_to_agent(name='prompt-hydrator', query='Analyze context in {temp_path}')`\n"
                    "- Claude: `Task(subagent_type='prompt-hydrator', prompt='Analyze context in {temp_path}')`"
                ),
            )
        ],
    ),
    # --- Custodiet ---
    # Note: temp file reuse is implemented via session hash in write_temp_file() (P#102)
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
    # Closes after hydration, blocks edit tools until plan is reviewed and approved by critic.
    GateConfig(
        name="critic",
        description="Blocks edit tools until plan is reviewed and approved.",
        initial_status=GateStatus.OPEN,  # Open at session start (no plan yet)
        triggers=[
            # Hydration complete -> Close (plan exists, needs review)
            GateTrigger(
                condition=GateCondition(
                    hook_event="SubagentStop", subagent_type_pattern="hydrator"
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_template="📋 Plan ready for review. Invoke critic before editing.",
                ),
            ),
            # Fallback: Task tool with hydrator completes -> Close
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="Task",
                    tool_input_pattern="hydrator",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_template="📋 Plan ready for review. Invoke critic before editing.",
                ),
            ),
            # Critic review complete -> Open (can now edit)
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="critic"),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    reset_ops_counter=True,
                    system_message_template="👁️ Critic review complete. Edit tools enabled.",
                ),
            ),
            # Fallback: Task tool with critic completes -> Open
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="Task",
                    tool_input_pattern="critic",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    reset_ops_counter=True,
                ),
            ),
        ],
        policies=[
            # If Closed, block edit tools (except always_available)
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="PreToolUse",
                    tool_name_pattern="Edit|Write|NotebookEdit",
                ),
                verdict="deny",
                message_template="⛔ Critic review required before editing. Invoke critic agent first.",
                context_template=(
                    "**CRITIC REVIEW REQUIRED**\n\n"
                    "You must invoke the **critic** agent to review your plan before making edits.\n\n"
                    "**Instruction**:\n"
                    "- Claude: `Task(subagent_type='aops-core:critic', prompt='Review the plan in the hydration output')`"
                ),
            ),
        ],
    ),
    # --- QA ---
    # Blocks exit until planned requirements are verified by QA agent.
    # Requirements are set after hydration and approved by critic.
    GateConfig(
        name="qa",
        description="Blocks exit until planned requirements are verified.",
        initial_status=GateStatus.OPEN,  # Open at session start (no requirements yet)
        triggers=[
            # Critic approves plan -> Close (requirements now set, need verification before exit)
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="critic"),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_template="🧪 QA gate closed. Run QA before exiting.",
                ),
            ),
            # QA verification complete -> Open (can now exit)
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="qa"),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_template="🧪 QA verification complete. Exit allowed.",
                ),
            ),
            # Fallback: Task tool with qa completes -> Open
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="Task",
                    tool_input_pattern="qa",
                ),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
        ],
        policies=[
            # If Closed, block Stop (exit)
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                ),
                verdict="deny",
                message_template="⛔ QA verification required before exit. Invoke QA agent first.",
                context_template=(
                    "**QA VERIFICATION REQUIRED**\n\n"
                    "You must invoke the **qa** agent to verify planned requirements before exiting.\n\n"
                    "**Instruction**:\n"
                    "- Claude: `Task(subagent_type='aops-core:qa', prompt='Verify planned requirements are met')`"
                ),
            ),
        ],
    ),
    # --- Handover ---
    # TODO: Implement handover gate that blocks Stop until Framework Reflection is output.
    # Expected format (see aops-core/commands/learn.md):
    #   ## Framework Reflection
    #   **Prompts**: [trigger]
    #   **Guidance received**: [guidance or N/A]
    #   **Followed**: Yes/No
    #   **Outcome**: success/partial/blocked/failure
    #   **Accomplishments**: [list]
    #   **Friction points**: [list or "none"]
    #   **Root cause** (if not success): [category]
    #   **Proposed changes**: [list]
    #   **Next step**: [task reference if needed]
    #
    # Implementation requires:
    # - custom_check to detect reflection in recent output (via transcript/session reader)
    # - Block Stop hook until reflection detected
    # - Trigger open when valid reflection format is found
]
