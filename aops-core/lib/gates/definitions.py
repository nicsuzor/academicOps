from lib.gate_types import GateConfig, GateTrigger, GatePolicy, GateCondition, GateTransition, GateStatus

GATE_CONFIGS = [
    # --- Hydration ---
    GateConfig(
        name="hydration",
        description="Ensures prompts are hydrated with context.",
        initial_status=GateStatus.CLOSED,
        triggers=[
            # Hydrator finishes -> Open
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="hydrator"),
                transition=GateTransition(target_status=GateStatus.OPEN, reset_ops_counter=True, system_message_template="💧 Hydration complete. Gate OPEN.")
            ),
            # Task tool completes (fallback if not subagent)
            GateTrigger(
                condition=GateCondition(hook_event="PostToolUse", tool_name_pattern="Task", tool_input_pattern="hydrator"),
                transition=GateTransition(target_status=GateStatus.OPEN, reset_ops_counter=True)
            ),
            # User Prompt (not ignored) -> Close
            # Note: user_prompt_submit.py hook script also closes the gate and sets metrics.
            # This trigger ensures consistent state machine behavior.
            GateTrigger(
                condition=GateCondition(hook_event="UserPromptSubmit", custom_check="is_hydratable"),
                transition=GateTransition(target_status=GateStatus.CLOSED)
            )
        ],
        policies=[
            # If Closed, Block tools
            # Note: We rely on user_prompt_submit.py to set 'temp_path' metric.
            GatePolicy(
                condition=GateCondition(current_status=GateStatus.CLOSED, hook_event="PreToolUse"),
                verdict="deny",
                message_template="Hydration required! Please run the hydrator agent with:\n{temp_path}",
                context_template="Hydration Context: {temp_path}"
            )
        ]
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
                transition=GateTransition(reset_ops_counter=True, system_message_template="🛡️ Compliance verified.")
            ),
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="custodiet"),
                transition=GateTransition(reset_ops_counter=True, system_message_template="🛡️ Compliance verified.")
            ),
            # Also reset if Task tool calls custodiet
            GateTrigger(
                condition=GateCondition(hook_event="PostToolUse", tool_name_pattern="Task", tool_input_pattern="custodiet"),
                transition=GateTransition(reset_ops_counter=True)
            )
        ],
        policies=[
            # Threshold check
            GatePolicy(
                condition=GateCondition(hook_event="PreToolUse", min_ops_since_open=7),
                verdict="deny", # Or warn based on env var? For now deny.
                message_template="Compliance check required ({ops_since_open} ops since last check).\nInvoke 'custodiet' agent.",
            ),
            # Stop check (Uncommitted work)
            GatePolicy(
                condition=GateCondition(hook_event="Stop", custom_check="has_uncommitted_work"),
                verdict="deny",
                message_template="{block_reason}"
            ),
            # Stop warning (Unpushed commits)
            GatePolicy(
                condition=GateCondition(hook_event="Stop", custom_check="has_unpushed_commits"),
                verdict="warn",
                message_template="{warning_message}"
            )
        ]
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
                transition=GateTransition(target_status=GateStatus.OPEN)
            ),
        ],
        policies=[
            # Placeholder for future task policies
        ]
    ),

    # --- Critic ---
    GateConfig(
        name="critic",
        description="Encourages periodic review.",
        initial_status=GateStatus.OPEN,
        triggers=[
             GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="critic"),
                transition=GateTransition(reset_ops_counter=True, system_message_template="👁️ Critic review complete.")
            ),
        ],
        policies=[
            GatePolicy(
                condition=GateCondition(hook_event="PreToolUse", min_ops_since_open=20),
                verdict="warn",
                message_template="Consider invoking 'critic' for review ({ops_since_open} ops since last check)."
            )
        ]
    ),

    # --- QA ---
    GateConfig(
        name="qa",
        description="Ensures code quality.",
        initial_status=GateStatus.CLOSED,
        triggers=[
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop", subagent_type_pattern="qa"),
                transition=GateTransition(target_status=GateStatus.OPEN, system_message_template="🧪 QA complete.")
            )
        ],
        policies=[
             GatePolicy(
                condition=GateCondition(hook_event="PreToolUse", min_ops_since_open=30),
                verdict="warn",
                message_template="Consider running QA ({ops_since_open} ops since last QA)."
            )
        ]
    ),

    # --- Handover ---
    GateConfig(
        name="handover",
        description="Manages session length.",
        initial_status=GateStatus.OPEN,
        triggers=[],
        policies=[
            # Note: min_turns_since_open is relative to last open.
            # If never closed, it equals global turns if opened at start.
            GatePolicy(
                condition=GateCondition(hook_event="PreToolUse", min_turns_since_open=50),
                verdict="warn",
                message_template="Session is getting long ({ops_since_open} turns). Consider summarizing and starting a new session."
            )
        ]
    )
]
