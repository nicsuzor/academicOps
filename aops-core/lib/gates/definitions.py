from hooks.gate_config import (
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
                    system_message_template="💧 Hydration complete.",
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
                    system_message_template="💧 New user prompt detected; fresh hydration required.",
                    context_template="💧 New user prompt detected; fresh hydration required. Immediately invoke the **prompt-hydrator** agent with argument: `{temp_path}`\n",
                ),
            ),
        ],
        policies=[
            # If Closed, Block/Warn ALL tools except always_available.
            # Read-only tools ARE subject to hydration — the intent is to force hydration
            # before ANY exploration. The gate opens JIT when the hydrator is dispatched
            # (via PreToolUse trigger above), so the hydrator's own reads succeed.
            # Compare with custodiet which excludes ["always_available", "read_only"].
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="PreToolUse",
                    excluded_tool_categories=["always_available"],
                ),
                verdict=HYDRATION_GATE_MODE,
                # Brief user-facing summary
                message_template="💧 Hydration required.",
                # Full agent instructions
                context_template=(
                    "**ERROR:** You need to hydrate user prompts before you can use tools. To ensure alignment with project workflows and axioms, please invoke the **prompt-hydrator** agent with: `{temp_path}`\n\n"
                    "Command:\n"
                    "- Gemini: `delegate_to_agent(name='aops-core:prompt-hydrator', query='{temp_path}')`\n"
                    "- Claude: `Agent(subagent_type='aops-core:prompt-hydrator', prompt='{temp_path}')`\n\n"
                    "Invoke the prompt-hydrator to satisfy this gate."
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
                "◇ {remaining} turns until compliance check. \n"
                "Run the check proactively to avoid being blocked by invoking the **custodiet** agent with file path argument:\n`{temp_path}`\n\n"
            ),
        ),
        triggers=[
            # Custodiet check -> Reset
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop)$",
                    subagent_type_pattern="^(aops-core:)?custodiet$",
                ),
                transition=GateTransition(
                    reset_ops_counter=True,
                    system_message_template="◇ Compliance verified.",
                    context_template="◇ Compliance verified.",
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
                message_template="✕ Compliance check required ({ops_since_open} ops since last check).",
                context_template=(
                    "**ERROR:** Compliance check OVERDUE. You need to invoke the **custodiet** agent before you can use tools.\n\n"
                    "**Periodic compliance check required ({ops_since_open} ops since last check).** Invoke the **custodiet** agent with the file path argument: `{temp_path}`\n"
                    "- Gemini: `delegate_to_agent(name='custodiet', query='{temp_path}')`\n"
                    "- Claude: `Agent(subagent_type='custodiet', prompt='{temp_path}')`\n"
                ),
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
                    system_message_template="🧪 QA complete.",
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
                message_template="✕ QA verification required before exit.",
                context_template=(
                    "**QA VERIFICATION REQUIRED**\n\n"
                    "You must invoke the **qa** agent to verify planned requirements before exiting.\n\n"
                    "**Instruction**:\n"
                    "Run the qa with this command:\n"
                    "- Gemini: `delegate_to_agent(name='aops-core:qa', query='{temp_path}')`\n"
                    "- Claude: `Agent(subagent_type='aops-core:qa', prompt='{temp_path}')`\n"
                    "- Make sure you obey the instructions the tool or subagent produces, but do not print the output to the user -- it just clutters up the conversation.\n\n"
                    "This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!"
                ),
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
                    system_message_template="▶ Task bound. Handover required before exit.",
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
                    system_message_template="≡ Handover complete.",
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
                message_template="≡ Handover required before exit.",
                context_template=(
                    "≡ Finalization required before exit.\n\n"
                    "Please invoke the Dump Skill (`/dump`). The gate will only allow exit once the Dump Skill has completed.\n\n"
                ),
            ),
        ],
    ),
]
