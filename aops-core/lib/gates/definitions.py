from hooks.gate_config import (
    ENFORCER_GATE_MODE,
    ENFORCER_TOOL_CALL_THRESHOLD,
    SENTINEL_GATE_MODE,
    SLASH_COMMAND_PROMPT_PATTERNS,
)

from lib.gate_model import GateVerdict
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

# --- Gate precedence (reviewable composition order) -------------------
# When two or more gates fire on the same event, the outcome must be reviewable.
# The composition order is explicit and deterministic:
#
#   1. Verdict tier dominates first. The router and the engine merge results
#      DENY > WARN > ALLOW — a deny from any gate beats a warn from any other,
#      regardless of position. "First deny wins".
#   2. Within a tier, iteration order breaks ties — and iteration order is the
#      registration order in this GATE_CONFIGS list. So the gate earlier in
#      this list wins a same-tier collision.
#
# The order and its rationale (highest precedence first):
#   sentinel  — PreToolUse destructive-op safety block; protects the user's
#               environment, never advisory. Highest-stakes forcing function.
#   enforcer  — periodic compliance self-check (PreToolUse threshold block).
#   qa        — verification-before-exit (Stop); ahead of handover so a missing
#               verifier surfaces before the handover reminder.
#   handover  — structured-handover-before-exit (Stop): prevents work loss.
#   ida       — honesty reminder (Stop); advisory, lowest precedence.
# ----------------------------------------------------------------------
GATE_CONFIGS = [
    # --- Sentinel ---
    # Named for its role as a guardian. Stateless PreToolUse gate that blocks
    # destructive operations targeting protected user-environment paths before
    # they execute. Origin: GitHub issue #106 — an agent deleted a working
    # Gemini extension installation without evidence it was broken.
    #
    # Three-class protection:
    # (1) Shell tools (Bash, run_shell_command, shell, execute_code):
    #     blocked when command contains a destructive verb (rm, mv, rmdir,
    #     unlink, truncate) AND a protected path reference.
    # (2) Write-file tools (Edit, Write, write_file, replace):
    #     blocked when the target file_path/path resolves to a protected path.
    # No state transitions — the gate is always armed. Mode default: block.
    GateConfig(
        name="sentinel",
        description="Blocks destructive operations targeting protected user-environment paths.",
        initial_status=GateStatus.OPEN,
        triggers=[],  # Stateless — no open/close lifecycle
        policies=[
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    # Covers shell tools and write-file tools (Claude + Gemini names).
                    # tool_name_pattern is an early-exit optimisation; the
                    # custom check also validates tool_name internally.
                    tool_name_pattern=(
                        r"^(?:Bash|run_shell_command|shell|execute_code"
                        r"|Edit|Write|write_file|replace)$"
                    ),
                    custom_check="is_destructive_env_op",
                ),
                verdict=SENTINEL_GATE_MODE,
                message_key="sentinel.policy_message",
                context_key="sentinel.policy_context",
            ),
        ],
    ),
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
    # Closes when a task is claimed (update_task → in_progress) so the Stop
    # policy can require a verifier (marsha / qa / verify) before exit.
    # Sessions without a claimed task skip the QA gate entirely.
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
            # Verifier subagent runs -> Open gate (sticky until UPS).
            # sticky_until keeps the gate open so writes to fix marsha's
            # findings don't re-close it (prevents marsha→fix→block loop).
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="^(aops-core:)?(qa|verify|marsha)$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="qa.complete",
                    sticky_until=["UserPromptSubmit"],
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
            # Engine unsticks (sticky_until includes UPS) before this
            # trigger evaluates, so the transition to CLOSED proceeds.
            # Only re-arms when a task is bound — sessions without a
            # claimed task skip the QA gate entirely.
            # Slash-command turns (skill invocations) are excluded: they own
            # their own finishing format, so they must not re-arm the gate
            # (prompt_exclude_patterns suppresses the close — never opens).
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                    custom_check="has_bound_task",
                    prompt_exclude_patterns=SLASH_COMMAND_PROMPT_PATTERNS,
                ),
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
                verdict=GateVerdict.DENY,
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
                verdict=GateVerdict.WARN,
                custom_action="prepare_qa_review",
                message_key="qa.policy_message",
                context_key="qa.policy_context",
            ),
        ],
    ),
    # --- Handover ---
    # Polecat/crew sessions start CLOSED (autonomous work must always hand over).
    # Interactive sessions start OPEN (coordinator/junior doesn't need forced handover).
    # Close triggers only fire in polecat/crew sessions.
    # Opens when /end-session or /dump skill completes.
    # Policy blocks Stop when CLOSED.
    GateConfig(
        name="handover",
        description="Requires structured session handover before exit.",
        initial_status=GateStatus.OPEN,
        initial_status_by_session_type={
            "polecat": GateStatus.CLOSED,
            "crew": GateStatus.CLOSED,
        },
        triggers=[
            # Task bound: update_task with status=in_progress -> Close
            # Only in polecat/crew sessions — interactive sessions (junior
            # supervising agents) manage task state without needing handover.
            # Also sets session_did_work so the Stop policy fires for this session.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="update_task",
                    tool_input_pattern="in_progress",
                    session_type_filter=["polecat", "crew"],
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_key="handover.bound",
                    custom_action="set_session_did_work",
                ),
            ),
            # Write tool used -> Close (polecat/crew only)
            # When handover is sticky (post-skill), the engine suppresses
            # this close transition natively.
            # Also sets session_did_work so the Stop policy fires for this session.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    custom_check="is_write_tool",
                    session_type_filter=["polecat", "crew"],
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_key=None,
                    custom_action="set_session_did_work",
                ),
            ),
            # Handover skill completes -> Open (sticky until UPS)
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
                    sticky_until=["UserPromptSubmit"],
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
                    sticky_until=["UserPromptSubmit"],
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
                    sticky_until=["UserPromptSubmit"],
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
            # UserPromptSubmit -> re-arm for the next turn cycle (polecat/crew only).
            # Interactive sessions never close the handover gate.
            # Slash-command turns (skill invocations such as /end-session,
            # /dump, /remember) are excluded: a finishing/meta skill owns its
            # own handover format and must not re-close the gate it just
            # satisfied (prompt_exclude_patterns suppresses the close — never
            # opens). The write-tool / task-claim close triggers above still
            # fire, so a slash turn that does real work is still gated.
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                    session_type_filter=["polecat", "crew"],
                    prompt_exclude_patterns=SLASH_COMMAND_PROMPT_PATTERNS,
                ),
                transition=GateTransition(target_status=GateStatus.CLOSED),
            ),
        ],
        policies=[
            # Block mode: advisory injected into agent context via reason channel.
            # Exempts read-only sessions (session_did_work=False) — a session that
            # used no write tools and claimed no task needs no handover (aops-16a15a05).
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_handover_block_mode",
                ),
                verdict=GateVerdict.DENY,
                message_key="handover.policy_message",
                context_key="stop.handover_block",
            ),
            # Warn mode: block-once — advisory injected into agent context via
            # the warn+context_injection upgrade path in output_for_claude().
            # Gate opens on first Stop (fire-once trigger above) so subsequent
            # Stops in the same turn are not re-blocked. Re-arms on UPS.
            # Exempts read-only sessions (session_did_work=False) — same rationale.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_handover_warn_mode",
                ),
                verdict=GateVerdict.WARN,
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
            # Slash-command turns (skill invocations such as /end-session,
            # /dump, /remember) are excluded: a finishing/meta skill that runs
            # after an honesty reflection owns its own format and must not arm
            # a second redundant ida reflection on the Stop that follows it
            # (prompt_exclude_patterns suppresses the close — never opens).
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                    prompt_exclude_patterns=SLASH_COMMAND_PROMPT_PATTERNS,
                ),
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
                verdict=GateVerdict.DENY,
                message_key="ida.policy_message",
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
                verdict=GateVerdict.WARN,
                message_key="ida.policy_message",
                context_key="ida.reminder",
            ),
        ],
    ),
]
