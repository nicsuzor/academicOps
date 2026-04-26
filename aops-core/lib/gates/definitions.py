import os

from hooks.gate_config import (
    ENFORCER_GATE_MODE,
    ENFORCER_TOOL_CALL_THRESHOLD,
    HANDOVER_GATE_MODE,
    QA_GATE_MODE,
)

# Orchestrator-boundary gate mode. Defaults to "warn". Set to "off" to disable.
# Hard-block ("deny") is Phase 3 per specs/orchestrator-boundary.md and is not
# yet activated — verify polecat efficiency first.
ORCHESTRATOR_BOUNDARY_GATE_MODE = os.environ.get("ORCHESTRATOR_BOUNDARY_GATE_MODE", "warn")

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
    # --- Enforcer ---
    GateConfig(
        name="enforcer",
        description="Enforces periodic compliance checks.",
        initial_status=GateStatus.OPEN,
        countdown=CountdownConfig(
            start_before=7,
            threshold=ENFORCER_TOOL_CALL_THRESHOLD,
            message_key="enforcer.countdown",
        ),
        triggers=[
            # Enforcer check -> Reset
            # PreToolUse is included so the trigger fires (resetting the counter)
            # BEFORE the policy evaluates. Without it, Agent(enforcer) is itself
            # blocked when ops >= threshold (deadlock: can't dispatch the agent
            # that would reset the counter).
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(PreToolUse|SubagentStart|SubagentStop)$",
                    subagent_type_pattern="^(aops[-_]core[:_])?(enforcer|rbg)$",
                ),
                transition=GateTransition(
                    reset_ops_counter=True,
                    system_message_key="enforcer.verified",
                    context_key="enforcer.verified",
                ),
            ),
        ],
        policies=[
            # Threshold check (except infrastructure and read_only tools)
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    min_ops_since_open=ENFORCER_TOOL_CALL_THRESHOLD,
                    excluded_tool_categories=["infrastructure", "always_available", "read_only"],
                ),
                verdict=ENFORCER_GATE_MODE,
                message_key="enforcer.policy_message",
                context_key="enforcer.policy_context",
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
    # Opens when end_session (default) or /dump (alias) skill completes.
    # Policy blocks Stop when CLOSED.
    GateConfig(
        name="handover",
        description="Requires structured session handover before exit.",
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
                    custom_action="reset_handover_invoked",
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
                    # no message to avoid spamming on every write tool use
                    system_message_key=None,
                    custom_action="reset_handover_invoked",
                ),
            ),
            # Handover skill completes -> Open
            # Uses subagent_type_pattern to match skill name extracted by router
            # (router.py extracts tool_input["skill"] into ctx.subagent_type)
            # Matches both Claude's Skill tool and Gemini's activate_skill tool.
            # Pattern matches "end_session" (default), "dump" (alias), "handover" (legacy),
            # and aops-core: prefixed forms.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="^(Skill|activate_skill)$",
                    subagent_type_pattern="^(aops-core:)?(handover|dump|end_session)$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="handover.complete",
                    custom_action="set_handover_invoked",
                ),
            ),
            # Gemini slash-command injection (UserPromptSubmit containing a handover template)
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                    prompt_pattern=r"^\s*#\s*/(dump|end_session)\s*[-—]\s*(Session Handover|Default session close)",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="handover.complete",
                    custom_action="set_handover_invoked",
                ),
            ),
            # Gemini fallback to Pauli subagent for handover
            GateTrigger(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    tool_name_pattern="^pauli$",
                    tool_input_pattern=r"/?\b(dump|end_session)\b|\bhandover\b",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="handover.complete",
                    custom_action="set_handover_invoked",
                ),
            ),
        ],
        policies=[
            # Block Stop when gate is CLOSED (handover not yet done)
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
    # --- Orchestrator Boundary ---
    # Level 4 detection for specs/orchestrator-boundary.md. Warns (does not
    # block) when the orchestrator session writes to project source outside
    # the framework allowlist. Polecat worker sessions are exempt (they set
    # POLECAT_SESSION_TYPE in the env). Hard-block mode is Phase 3 and not
    # yet wired — verify polecat efficiency first.
    GateConfig(
        name="orchestrator_boundary",
        description=(
            "Warns when the orchestrator session writes to project (non-framework) "
            "source files. See specs/orchestrator-boundary.md."
        ),
        initial_status=GateStatus.OPEN,
        policies=[
            GatePolicy(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    custom_check="is_orchestrator_project_write",
                ),
                verdict=ORCHESTRATOR_BOUNDARY_GATE_MODE,
                message_key=None,  # Short inline message; the rich guidance is in context_key.
                message_template=(
                    "Orchestrator boundary: write to project source detected. "
                    "Consider dispatching to polecat instead."
                ),
                context_key="orchestrator.boundary_warn",
            ),
        ],
    ),
]
