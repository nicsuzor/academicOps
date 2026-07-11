from hooks.gate_config import (
    RBG_REVIEW_DEGRADE_THRESHOLD,
    RBG_REVIEW_GATE_MODE,  # noqa: F401  (referenced via custom_check, kept for discoverability)
    RBG_TOOL_CALL_THRESHOLD,
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
#   RBG    — periodic compliance self-check (PreToolUse threshold block).
#   rbg-review  — end-of-session rbg axiom audit, scoped to task-bound
#                 (polecat/crew) sessions only. Armed CLOSED for polecat/crew,
#                 OPEN (inert) for ad hoc interactive — so interactive users do
#                 NOT eat a per-turn rbg delay. The RBG every-N cadence is
#                 the in-session mechanism; this gate adds only the final
#                 backstop before a task-bound session exits. Placed ahead of
#                 qa/handover/ida so its DENY + rbg-dispatch instruction is the
#                 one delivered first; once rbg has run the gate clears and the
#                 later Stop gates take over. Serialises rbg-review ->
#                 qa/handover -> ida cleanly and never masks Ida.
#   qa          — verification-before-exit (Stop); ahead of handover so a missing
#                 verifier surfaces before the handover reminder.
#   handover    — structured-handover-before-exit (Stop): prevents work loss.
#   ida         — honesty reminder (Stop); advisory, lowest precedence.
# ----------------------------------------------------------------------
GATE_CONFIGS = [
    # --- RBG ---
    GateConfig(
        name="rbg",
        description="Enforces periodic compliance checks.",
        initial_status=GateStatus.OPEN,
        countdown=CountdownConfig(
            start_before=7,
            threshold=RBG_TOOL_CALL_THRESHOLD,
            message_key="rbg.countdown",
        ),
        triggers=[
            # RBG check -> Reset
            # PreToolUse is included so the trigger fires (resetting the counter)
            # BEFORE the policy evaluates. Without it, Agent(rbg) is itself
            # blocked when ops >= threshold (deadlock: can't dispatch the agent
            # that would reset the counter).
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(PreToolUse|SubagentStart|SubagentStop)$",
                    subagent_type_pattern="^(aops[-_](core|pkb)[:_])?rbg$",
                ),
                transition=GateTransition(
                    reset_ops_counter=True,
                    system_message_key="rbg.verified",
                    context_key="rbg.verified",
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
                    min_ops_since_open=RBG_TOOL_CALL_THRESHOLD,
                    excluded_tool_categories=["infrastructure", "always_available", "read_only"],
                    custom_check="not_mid_edit",
                ),
                session_mode_key="RBG_GATE_MODE",
                message_key="rbg.policy_message",
                context_key="rbg.policy_context",
                custom_action="prepare_compliance_report",
            ),
        ],
    ),
    # --- rbg-review (end-of-session rbg audit) ---
    # Directive (Nic, 2026-06-24, epic-f490bb11 — rework of the original
    # block-every-stop #1928): the heavy independent rbg axiom audit is a
    # Tier-2 backstop that must fire ONCE before a task-bound session exits —
    # NOT on every armed Stop, and NOT in ad hoc interactive discussions where
    # the user would notice the per-turn rbg delay. The rbg every-N cadence
    # (rbg gate, left untouched) remains the in-session mechanism; this gate
    # adds only the final exit backstop.
    #
    # SCOPING is env-var only (gates.rbg_review / RBG_REVIEW_GATE_MODE), NEVER
    # a code branch on session type. The lifecycle below (arm -> block ->
    # clear) is IDENTICAL for every session — the same initial_status, the
    # same triggers fire on every UserPromptSubmit regardless of who's driving.
    # What differs across surfaces is purely which MODE is in effect — resolved
    # from polecat.yaml's explicit per-surface `gates.rbg_review` (face/crew/
    # worker/subagent; note_296e5520 §4), never guessed or built in:
    #   * mode=off (the `face` surface's default posture — an ad hoc/direct
    #     CLI session): the CLOSED state is inert, since neither
    #     is_rbg_review_block_mode nor is_rbg_review_warn_mode ever matches
    #     "off" — no DENY/WARN is ever produced, so interactive users eat no
    #     per-turn rbg delay even though the gate mechanically arms/re-arms.
    #   * mode=block (the `crew`/`worker`/`subagent` surfaces' default posture,
    #     set explicitly via polecat.yaml's `gates.rbg_review` for that
    #     surface): while CLOSED, the Stop policy DENIES the exit and injects
    #     the rbg-dispatch instruction.
    #
    # Lifecycle (arm -> block -> clear):
    #   * BLOCK (mode=block/warn only): while CLOSED, the Stop policy
    #     denies/warns and injects the rbg-dispatch instruction so the agent
    #     actually runs rbg. The TRIGGER is structural (Stop event + armed
    #     flag) — NOT a content sniff. The qualitative judgment ("did this
    #     session comply?") is rbg's.
    #   * CLEAR: when the rbg subagent runs (SubagentStart/Stop/PostToolUse with
    #     subagent_type ~ rbg), the gate OPENS, resets the escape-hatch deny
    #     counter, and latches sticky_until UserPromptSubmit so the rbg
    #     discharge AND any follow-up edits do not re-block / re-arm THIS turn
    #     (gate-discharge re-trigger invariant — the rbg run must not loop).
    #
    # NOTE — deliberately NO fire-once "open on first Stop" trigger (unlike
    # qa/handover/ida). Those gates open on the first Stop so a retried Stop in
    # the same turn passes; that is fine for a block-once advisory but WRONG
    # here, because it would let the exit Stop pass WITHOUT rbg having run.
    # The gate stays CLOSED across repeated Stops until rbg actually runs.
    #
    # ESCAPE-HATCH (loud, not silent): the engine degrades DENY -> WARN-and-
    # allow after RBG_REVIEW_DEGRADE_THRESHOLD (default 5) consecutive Stop
    # blocks in one turn, emitting the rbg_review.degraded message. This
    # prevents the known infinite-Stop-loop incident if rbg dispatch is
    # structurally broken. It is failure-degradation ONLY — the healthy path
    # still requires rbg to run. The router-level 5-blocks-in-2-min override is
    # a second, independent net.
    GateConfig(
        name="rbg-review",
        description="Final rbg axiom audit before a task-bound session exits.",
        # Armed (CLOSED) from session start for EVERY session type. Whether
        # that matters at all is entirely down to RBG_REVIEW_GATE_MODE (above).
        initial_status=GateStatus.CLOSED,
        stop_deny_downgrade_threshold=RBG_REVIEW_DEGRADE_THRESHOLD,
        stop_deny_degraded_message_key="rbg_review.degraded",
        triggers=[
            # rbg subagent ran -> clear (OPEN), reset escape-hatch counter,
            # latch sticky until UserPromptSubmit so post-review fixes don't
            # re-block this turn. Matches the dispatched / completed / tool
            # forms (SubagentStart, SubagentStop, PostToolUse on the Agent/Task
            # spawn) and the aops-core:/aops-pkb: prefixes (rbg agent lives in
            # aops-pkb since the aops-pkb extraction).
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="^(aops[-_](core|pkb)[:_])?rbg$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="rbg_review.complete",
                    set_metrics={"stop_deny_count": 0},
                    sticky_until=["UserPromptSubmit"],
                ),
            ),
            # UserPromptSubmit -> re-arm (CLOSED) for the next turn cycle, EVERY
            # session type alike. The engine unsticks (sticky_until includes
            # UPS) BEFORE this trigger evaluates, so the transition to CLOSED
            # proceeds. Resets the escape-hatch counter so each turn gets a
            # fresh deny budget. Whether re-arming CLOSED produces any visible
            # effect is entirely down to RBG_REVIEW_GATE_MODE.
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    set_metrics={"stop_deny_count": 0},
                ),
            ),
            # Stop (when armed/CLOSED) -> Open: fire-once, WARN MODE ONLY (D1).
            # Warn hard-blocks once then opens so the turn proceeds. Block mode
            # has NO fire-once — it persists (re-DENYs) until rbg runs
            # (block-until-satisfied), bounded by the stop_deny_count hatch.
            GateTrigger(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                    custom_check="is_rbg_review_warn_mode",
                ),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
        ],
        policies=[
            # Block mode (default): DENY Stop while CLOSED + inject the rbg
            # dispatch instruction via the context channel. prepare_rbg_review
            # builds the turn-review file so {temp_path} resolves. There is NO
            # fire-once open here, so this re-fires every Stop until rbg runs
            # (or the escape-hatch degrades it).
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_rbg_review_block_mode",
                ),
                verdict=GateVerdict.DENY,
                custom_action="prepare_rbg_review",
                message_key="rbg_review.policy_message",
                context_key="rbg_review.policy_context",
            ),
            # Warn mode: non-blocking delivery. WARN (not DENY) rides the
            # agent_context_without_block channel (additionalContext) — the
            # agent sees the full dispatch instruction next turn without a
            # forced continuation. The fire-once trigger below still opens the
            # gate on this same Stop event so it does not re-fire mid-turn.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_rbg_review_warn_mode",
                ),
                verdict=GateVerdict.WARN,
                custom_action="prepare_rbg_review",
                message_key="rbg_review.policy_message",
                context_key="rbg_review.policy_context",
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
            # marsha (agent) and verify (skill) both live in aops-pkb since
            # the aops-pkb extraction, so match either plugin prefix.
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="^(aops-(core|pkb):)?(qa|verify|marsha)$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="qa.complete",
                    sticky_until=["UserPromptSubmit"],
                ),
            ),
            # Stop (when armed/CLOSED) -> Open: fire-once, WARN MODE ONLY. In warn
            # mode the gate hard-blocks once (D1) then opens so a retried Stop in
            # the same turn passes. In BLOCK mode there is deliberately NO
            # fire-once open — the gate persists (re-DENYs every Stop) until the
            # verifier-ran trigger opens it (block-until-satisfied). Loop safety in
            # block mode is the stop_deny_count escape hatch, not this trigger.
            GateTrigger(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                    custom_check="is_qa_warn_mode",
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
            # Resets the block-mode escape-hatch counter: the loop the counter
            # bounds is WITHIN a turn (Stop → forced-continue → Stop …); a
            # genuine new user turn is new work and gets a fresh deny budget
            # (mirrors rbg-review).
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                    custom_check="has_bound_task",
                    prompt_exclude_patterns=SLASH_COMMAND_PROMPT_PATTERNS,
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    set_metrics={"stop_deny_count": 0},
                ),
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
            # Warn mode: non-blocking delivery. WARN (not DENY) rides the
            # agent_context_without_block channel (additionalContext) — the
            # agent sees the full verification requirement next turn without a
            # forced continuation. The fire-once trigger above still opens the
            # gate on this same Stop event so it does not re-fire mid-turn.
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
    # Every session type starts OPEN and follows the SAME triggers — there is
    # no code branch on session type anywhere in this config. A session (any
    # surface) closes the gate the moment it does real work (task-bind / write
    # tool / claim_task) and reopens it when /end-session or /dump completes.
    # Whether a CLOSED gate actually holds up the exit Stop is entirely down to
    # HANDOVER_GATE_MODE (gates.handover in polecat.yaml, or a project's
    # .claude/settings.json for a direct CLI surface) plus the independent
    # turn_did_work exemption (read-only turns are exempt regardless of
    # gate status or mode — see is_handover_block_mode/is_handover_warn_mode in
    # custom_conditions.py). Policy blocks Stop when CLOSED.
    GateConfig(
        name="handover",
        description="Requires structured session handover before exit.",
        initial_status=GateStatus.OPEN,
        triggers=[
            # Task bound: update_task with status=in_progress -> Close, EVERY
            # session type alike. Also sets turn_did_work so the Stop policy
            # fires for this turn.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="update_task",
                    tool_input_pattern="in_progress",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_key="handover.bound",
                    custom_action="set_turn_did_work",
                ),
            ),
            # pkb claim_task -> Close (every session type).
            # A claimed task is real work, so the session is gated until handover.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="claim_task",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_key=None,
                    custom_action="set_turn_did_work",
                ),
            ),
            # Write / edit tool used -> Close (every session type). is_write_tool
            # natively treats shell tools as read-only when the gate is sticky /
            # no task bound, so /end-session discovery commands do not re-close it.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    custom_check="is_write_tool",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    system_message_key=None,
                    custom_action="set_turn_did_work",
                ),
            ),
            # Handover skill completes -> Open (sticky until UPS)
            # Uses subagent_type_pattern to match skill name extracted by router
            # (router.py extracts tool_input["skill"] into ctx.subagent_type)
            # Matches both Claude's Skill tool and Gemini's activate_skill tool.
            # Pattern matches "end_session" (canonical), "dump" (emergency),
            # "continue" (pause/hand-back — work in progress, task NOT concluded),
            # "handover" (legacy), and aops-core:/aops-pkb: prefixed forms.
            # dump/end_session moved core -> aops-interactive (aops-cf3fb2f0) ->
            # aops-pkb (ruling A10, aops-7ea63b63, dissolving the short-lived
            # aops-interactive plugin); continue/handover stayed in aops-core —
            # the prefix alternation covers both origins for the whole group
            # rather than per-name binding, mirroring how the rbg/qa gates
            # handle the aops-pkb move.
            # /continue opens the gate too: it delivers the honest scannable
            # resume summary, so a legitimate pause is not blocked by the
            # exit-discipline gate.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="^(Skill|activate_skill)$",
                    subagent_type_pattern="^(aops-(core|pkb):)?(handover|dump|end_session|continue)$",
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
            # Stop (when armed/CLOSED) -> Open: fire-once, WARN MODE ONLY (D1). In
            # warn mode handover hard-blocks once then opens so the turn proceeds.
            # In BLOCK mode there is NO fire-once — the gate persists (re-DENYs
            # every Stop) until the handover skill runs (block-until-satisfied);
            # loop safety is the stop_deny_count escape hatch.
            GateTrigger(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                    custom_check="is_handover_warn_mode",
                ),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
            # UserPromptSubmit -> re-arm for the next turn cycle, EVERY session
            # type alike. Re-arming CLOSED here is harmless for a read-only
            # turn: the block/warn policies below independently exempt
            # turn_did_work=False regardless of gate status, so a turn
            # that does no work of its own still exits cleanly — even if an
            # earlier turn in the same session did write something, because
            # reset_turn_did_work below clears the flag fresh for THIS turn
            # (aops_d18b2d4b — previously session-wide and never reset, so one
            # write anywhere in the session latched the full ceremony onto
            # every later no-op turn).
            # Slash-command turns (skill invocations such as /end-session,
            # /dump, /remember) are excluded: a finishing/meta skill owns its
            # own handover format and must not re-close the gate it just
            # satisfied (prompt_exclude_patterns suppresses the close — never
            # opens). The write-tool / task-claim close triggers above still
            # fire, so a slash turn that does real work is still gated.
            # Resets the block-mode escape-hatch counter: the loop the counter
            # bounds is WITHIN a turn (Stop → forced-continue → Stop …); a
            # genuine new user turn is new work and gets a fresh deny budget
            # (mirrors rbg-review).
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                    prompt_exclude_patterns=SLASH_COMMAND_PROMPT_PATTERNS,
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    set_metrics={"stop_deny_count": 0},
                    custom_action="reset_turn_did_work",
                ),
            ),
        ],
        policies=[
            # Block mode: advisory injected into agent context via reason channel.
            # Exempts read-only turns (turn_did_work=False) — a turn that
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
            # Warn mode: non-blocking delivery. WARN (not DENY) rides the
            # agent_context_without_block channel (additionalContext) — the
            # agent sees the full handover requirement next turn without a
            # forced continuation. The fire-once Stop trigger above still opens
            # the gate on this same Stop event so it does not re-fire mid-turn.
            # Exempts read-only turns (turn_did_work=False).
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
            # /continue skill invoked -> Open (sticky until UPS). The /continue
            # pause path already emits the honest, scannable resume summary this
            # gate exists to require, so the honesty reminder must NOT also fire
            # on the Stop that follows it. Mirrors the handover gate's skill-open
            # trigger; matches Claude's Skill and Gemini's activate_skill.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="^(Skill|activate_skill)$",
                    subagent_type_pattern="^(aops-core:)?continue$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    sticky_until=["UserPromptSubmit"],
                ),
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
            # On PreToolUse AskUserQuestion (mid-turn blocker challenge):
            #
            # Component C: inject capability-verification advisory so the agent
            # is reminded to verify live before asserting a blocker ("only you
            # can", "I can't run X", "needs auth"). Fires mid-turn at the moment
            # the blocker is manufactured — the only moment that catches the
            # agy-auth-halt incident class (issue #1751).
            #
            # Component B: re-close the gate (CLOSED is a no-op when already
            # CLOSED; re-closes when OPEN after a prior Stop fire-once). This
            # gives: block-once → allow-retry → re-close-on-AskUserQuestion →
            # re-block-on-next-Stop.
            #
            # Delivery: triggers use GateResult.allow + context_injection, so
            # this is advisory-inject only — AskUserQuestion is never denied.
            # Policies for never-block tools are skipped by is_never_block in
            # _evaluate_policies; triggers are NOT subject to that guard, so
            # the advisory reaches the agent via additionalContext (PreToolUse
            # hookSpecificOutput) without blocking the question.
            #
            # Arming posture: armed in ALL session types (including interactive)
            # because this incident class occurred in an interactive /pull.
            # The cost is one advisory nudge per AskUserQuestion — acceptable
            # given the gate mode is warn (never deny on this event path).
            GateTrigger(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    tool_name_pattern=r"^AskUserQuestion$",
                    custom_check="is_ida_active",
                ),
                transition=GateTransition(
                    target_status=GateStatus.CLOSED,
                    context_key="ida.askuserquestion_reminder",
                ),
            ),
        ],
        policies=[
            # Block mode: advisory injected into agent context via reason channel.
            # The short user-facing line is inline (the former ida-policy-message.md
            # template was deleted when ida·reminder moved to the (now-retired)
            # asyncRewake quiet-split — block mode keeps its visible reason, warn
            # mode does not).
            GatePolicy(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                    custom_check="is_ida_block_mode",
                ),
                verdict=GateVerdict.DENY,
                message_template="≡ Honesty check before exit.",
                context_key="ida.reminder",
            ),
            # Warn mode: non-blocking delivery. WARN (not DENY) rides the
            # agent_context_without_block channel (additionalContext) on
            # Claude — the agent sees the full reminder next turn without a
            # forced continuation; Claude also renders it to the user ("Stop
            # hook feedback"). Non-Claude client delivery of this WARN verdict
            # is unchanged from before this policy carried DENY — see
            # resolve_policy_for_agy for agy's Stop handling. The unconditional
            # fire-once trigger above still opens the gate after this fires, so
            # a retried Stop in the same turn is not re-blocked; re-arms on UPS.
            GatePolicy(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                    custom_check="is_ida_warn_mode",
                ),
                verdict=GateVerdict.WARN,
                context_key="ida.reminder",
            ),
        ],
    ),
]
