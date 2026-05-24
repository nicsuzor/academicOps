from hooks.gate_config import (
    ENFORCER_GATE_MODE,
    ENFORCER_TOOL_CALL_THRESHOLD,
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
            # Track in-progress todo state (for mid-edit phase detection, #319)
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="^TodoWrite$",
                ),
                transition=GateTransition(
                    custom_action="update_todo_in_progress",
                ),
            ),
        ],
        policies=[
            # Threshold check (except infrastructure and read_only tools)
            # Deferred when agent has an in-progress todo (mid-multi-step-edit, #319)
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    min_ops_since_open=ENFORCER_TOOL_CALL_THRESHOLD,
                    excluded_tool_categories=["infrastructure", "always_available", "read_only"],
                    custom_check="not_mid_edit",
                ),
                verdict=ENFORCER_GATE_MODE,
                message_key="enforcer.policy_message",
                context_key="enforcer.policy_context",
                custom_action="prepare_compliance_report",
            ),
        ],
    ),
    # --- QA ---
    # Starts OPEN (short interactive chats don't need verification).
    # Closes when work begins (task bound, or any write tool used) so the Stop
    # policy can require a verifier (marsha / qa / verify) before exit.
    # Reopens when the verifier subagent runs to completion.
    # Policy blocks Stop when CLOSED.
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
            # Task bound: update_task with status=in_progress -> Close
            # Work has begun, so verification will be required before exit.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="update_task",
                    tool_input_pattern="in_progress",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                ),
            ),
            # Write tool used -> Close. Shares is_write_tool with handover;
            # the bash-as-read carve-out keyed on handover_skill_invoked also
            # applies here, so `git status` after /end-session doesn't re-close.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    custom_check="is_write_tool",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    # no message to avoid spamming on every write tool use
                    system_message_key=None,
                ),
            ),
            # Verifier subagent runs -> Open gate
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="^(aops-core:)?(qa|verify|marsha)$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="qa.complete",
                ),
            ),
            # Stop (when armed/CLOSED) -> Open: fire-once so a retried Stop in
            # the same turn passes through without re-blocking.
            GateTrigger(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                ),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
            # UserPromptSubmit -> re-arm for the next turn cycle.
            GateTrigger(
                condition=GateCondition(hook_event="UserPromptSubmit"),
                transition=GateTransition(target_status=GateStatus.CLOSED),
            ),
        ],
        policies=[
            # Block mode: advisory injected into agent context via reason channel.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_qa_block_mode",
                ),
                verdict="block",
                custom_action="prepare_qa_review",
                message_key="qa.policy_message",
                context_key="qa.policy_context",
            ),
            # Warn mode: block-once — advisory injected into agent context via
            # the warn+context_injection upgrade path in output_for_claude().
            # Gate opens on first Stop (fire-once trigger above) so subsequent
            # Stops in the same turn are not re-blocked. Re-arms on UPS.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_qa_warn_mode",
                ),
                verdict="warn",
                custom_action="prepare_qa_review",
                message_key="qa.policy_message",
                context_key="qa.policy_context",
            ),
        ],
    ),
    # --- Handover ---
    # Gate starts OPEN (so short interactive chats don't require handover).
    # Closes when work begins (task bound or write tool used).
    # Opens when /end-session (canonical full close) or /dump (emergency bail)
    # skill completes — both satisfy the handover gate.
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
            # Pattern matches "end_session" (canonical), "dump" (emergency), "handover" (legacy),
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
            # Stop (when armed/CLOSED) -> Open: fire-once so a retried Stop in
            # the same turn passes through without re-blocking.
            GateTrigger(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                ),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
            # UserPromptSubmit -> re-arm for the next turn cycle.
            GateTrigger(
                condition=GateCondition(hook_event="UserPromptSubmit"),
                transition=GateTransition(target_status=GateStatus.CLOSED),
            ),
        ],
        policies=[
            # Block mode: advisory injected into agent context via reason channel.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_handover_block_mode",
                ),
                verdict="block",
                message_key="handover.policy_message",
                context_key="stop.handover_block",
            ),
            # Warn mode: block-once — advisory injected into agent context via
            # the warn+context_injection upgrade path in output_for_claude().
            # Gate opens on first Stop (fire-once trigger above) so subsequent
            # Stops in the same turn are not re-blocked. Re-arms on UPS.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_handover_warn_mode",
                ),
                verdict="warn",
                message_key="handover.policy_message",
                context_key="stop.handover_block",
            ),
        ],
    ),
    # --- Ida ---
    # Named for Ida B. Wells — investigative journalist who built her career
    # on documented evidence ("turn the light of truth upon them"). Honesty
    # reminder with per-turn lifecycle: fires once per UPS→Stop cycle, then
    # opens so retried Stops in the same turn are not re-blocked. Re-arms on
    # the next UserPromptSubmit. Targets criterion substitution, narrative-as-
    # proof, fabricated diagnostics, skipped verification, positive-framing
    # bias, unverified keystone assumptions, and subagent-output laundering
    # (issues #621, #563, #380, #430, #359, #798, #549, #624, #317, #100,
    # #376, #437, #391, #416, #335, #932, #822, #714). Mode resolved from
    # polecat.yaml gates.ida — set to "off" to disable.
    #
    # Lifecycle: armed (CLOSED) → fires on Stop → opens → re-armed on UPS.
    #
    # Warn mode (default): block-once per turn. Advisory delivered as
    # context_injection so it reaches the agent via the warn+ctx_inj upgrade
    # path in output_for_claude(). Gate opens on first Stop (fire-once trigger)
    # so subsequent Stops in the same turn pass. Re-arms on UserPromptSubmit.
    # Claude Code's Stop schema does not support hookSpecificOutput, so
    # context_injection via decision=block+reason is the only agent-visible
    # channel — non-blocking advisory injection on Stop does not exist.
    #
    # Block mode: same context_injection path, same fire-once lifecycle.
    GateConfig(
        name="ida",
        description="Reminds the agent to show proof for assertions before stopping.",
        initial_status=GateStatus.CLOSED,  # Armed from session start
        triggers=[
            # On Stop (when armed/CLOSED): open gate so policy doesn't fire
            # again in the same turn (e.g. if agent retries Stop after block).
            GateTrigger(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                ),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
            # On UserPromptSubmit: re-arm gate for the next turn cycle.
            GateTrigger(
                condition=GateCondition(hook_event="UserPromptSubmit"),
                transition=GateTransition(target_status=GateStatus.CLOSED),
            ),
        ],
        policies=[
            # Block mode: advisory injected into agent context via reason channel.
            GatePolicy(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                    custom_check="is_ida_block_mode",
                ),
                verdict="block",
                context_key="ida.reminder",
            ),
            # Warn mode: block-once — advisory injected into agent context via
            # the warn+context_injection upgrade path in output_for_claude().
            # Gate opens on first Stop (fire-once trigger above) so subsequent
            # Stops in the same turn are not re-blocked. Re-arms on UPS.
            GatePolicy(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                    custom_check="is_ida_warn_mode",
                ),
                verdict="warn",
                message_key="ida.reminder",
                context_key="ida.reminder",
            ),
        ],
    ),
]
