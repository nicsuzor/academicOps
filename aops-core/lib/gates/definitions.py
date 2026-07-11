from hooks.gate_config import (
    EXIT_REFLECTION_DEGRADE_THRESHOLD,
    EXIT_REFLECTION_GATE_MODE,  # noqa: F401  (referenced via custom_check, kept for discoverability)
    SLASH_COMMAND_PROMPT_PATTERNS,
)

from lib.gate_model import GateVerdict
from lib.gate_types import (
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
#      registration order in this GATE_CONFIGS list.
#
# The order and its rationale (highest precedence first):
#   exit_reflection — one consolidated Stop gate (aops_4c2949d9, replacing the
#                      former rbg-review + qa + handover trio, and retiring the
#                      turn-based `rbg` PreToolUse counter entirely — nothing
#                      fires mid-session on any surface any more). Two tiers,
#                      selected per-Stop by session scope, never by a
#                      session-type code branch (H3): FULL for a task-bound
#                      main-agent session that did work this turn (RBG-lens
#                      self-audit, durable capture, commit->push->PR, /learn,
#                      /remember, prose handover with a substance-vs-form
#                      guardrail); LITE — a non-blocking honesty/self-
#                      reflection reminder only, the ida-gate lineage — for
#                      everyone else (subagents, no bound task, or a read-only
#                      turn on a bound task).
#   ida             — per-turn honesty reminder (Stop); advisory, lowest
#                      precedence, head-surface only. UNTOUCHED by this
#                      consolidation — its disposition migrates separately
#                      (note_296e5520 module (b)).
# ----------------------------------------------------------------------
GATE_CONFIGS = [
    # --- Exit reflection (consolidated rbg-review + qa + handover) ---
    # Replaces three separate Stop gates with one. Armed (CLOSED) from session
    # start for EVERY session type — no code branch on session type anywhere
    # in this config (H3); posture is expressed solely via
    # EXIT_REFLECTION_GATE_MODE. Which TIER applies (full checklist vs
    # lightweight reminder) is resolved per-Stop by
    # `is_exit_reflection_full_scope` in custom_conditions.py — is_subagent,
    # has-a-bound-task, and turn_did_work — never by session_type.
    #
    # Legal exits (no no-legal-exit deadlock, per note_296e5520 §1):
    #   1. The FULL-tier reflection auditor actually runs (rbg/qa/verify/
    #      marsha/exit-reflection subagent match) -> OPEN.
    #   2. An HONEST completion or failure handback: `release_task` with
    #      status in {merge_ready, done, blocked, review, partial, cancelled}
    #      -> OPEN immediately. A stated failure reason is a legal exit exactly
    #      like a verified success (note_296e5520 §1: "Checkable evidence OR a
    #      stated failure reason").
    #   3. `/end-session`, `/dump`, or `/continue` completes -> OPEN.
    #   4. The engine's stop-deny escape hatch (EXIT_REFLECTION_DEGRADE_
    #      THRESHOLD consecutive Stop denies in one turn) degrades DENY to
    #      WARN-and-allow — failure-degradation only, never a normal bypass.
    #   5. WARN-mode Stops are fire-once by construction (never persist), and
    #      the LITE tier never denies at all.
    GateConfig(
        name="exit_reflection",
        description=(
            "Consolidated exit-reflection: full checklist for task-bound "
            "sessions that did work this turn; lightweight honesty reminder "
            "for everyone else (subagents, no bound task, read-only turns)."
        ),
        initial_status=GateStatus.CLOSED,
        stop_deny_downgrade_threshold=EXIT_REFLECTION_DEGRADE_THRESHOLD,
        stop_deny_degraded_message_key="exit_reflection.degraded",
        triggers=[
            # Task bound (update_task -> in_progress): records the task id on
            # session_state.main_agent.current_task (bind_task_from_tool_input
            # — has_bound_task/the FULL-tier scope check read this field but
            # nothing set it before this trigger existed, aops_4c2949d9) +
            # counts as work this turn (a claim is itself real work).
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="update_task",
                    tool_input_pattern="in_progress",
                ),
                transition=GateTransition(
                    system_message_key="exit_reflection.bound",
                    custom_action="bind_task_from_tool_input",
                ),
            ),
            # claim_task -> binds the task id + counts as work this turn.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="claim_task",
                ),
                transition=GateTransition(custom_action="bind_task_from_tool_input"),
            ),
            # Write / edit tool used -> counts as work this turn. is_write_tool
            # natively treats shell tools as read-only when the gate is sticky
            # / no task bound, so discovery commands (git status, etc.) don't
            # flip a read-only turn into a full-tier one.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    custom_check="is_write_tool",
                ),
                transition=GateTransition(custom_action="set_turn_did_work"),
            ),
            # HONEST legal exit: release_task with ANY terminal status —
            # delivered (merge_ready/done) or an honest failure/pause
            # (blocked/review/partial/cancelled) — opens the gate immediately.
            # A stated failure reason is a legal exit; this must never re-block
            # a session that has honestly handed back (note_296e5520 §1).
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="release_task",
                    # tool_input is matched via str(dict) — Python repr uses
                    # single quotes, JSON uses double — so the quote char
                    # itself is tolerant here, not hardcoded to either.
                    tool_input_pattern=r"""['"]status['"]\s*:\s*['"](merge_ready|done|blocked|review|partial|cancelled)['"]""",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="exit_reflection.complete",
                    set_metrics={"stop_deny_count": 0},
                    sticky_until=["UserPromptSubmit"],
                ),
            ),
            # Reflection auditor ran (rbg / qa / verify / marsha / a dedicated
            # exit-reflection subagent) -> Open, sticky until UPS so follow-up
            # fixes don't re-close it (marsha/rbg -> fix -> block loop).
            # Matches both the aops-core: and aops-pkb: prefixes (the audit
            # agents moved to aops-pkb; aops_4c2949d9 keeps both alive).
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="^(aops[-_](core|pkb)[:_])?(rbg|qa|verify|marsha|exit[-_]reflection)$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="exit_reflection.complete",
                    set_metrics={"stop_deny_count": 0},
                    sticky_until=["UserPromptSubmit"],
                ),
            ),
            # Finishing skill (/end-session, /dump, /continue — legacy
            # /handover name still matched) completes -> Open, sticky until
            # UPS. /continue is the pause path: it emits its own honest
            # scannable resume summary without concluding the task, so it
            # counts as a legal exit here too.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PostToolUse",
                    tool_name_pattern="^(Skill|activate_skill)$",
                    subagent_type_pattern="^(aops-(core|pkb):)?(handover|dump|end_session|continue)$",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="exit_reflection.complete",
                    sticky_until=["UserPromptSubmit"],
                ),
            ),
            # Gemini slash-command injection (UserPromptSubmit containing a
            # handover template) — same finishing-skill open, Gemini's form.
            GateTrigger(
                condition=GateCondition(
                    hook_event="UserPromptSubmit",
                    prompt_pattern=r"^\s*#\s*/(dump|end_session)\s*[-—]\s*(Session Handover|Default session close)",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="exit_reflection.complete",
                    sticky_until=["UserPromptSubmit"],
                ),
            ),
            # Gemini fallback to the pauli subagent for handover.
            GateTrigger(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    tool_name_pattern="^pauli$",
                    tool_input_pattern=r"/?\b(dump|end_session)\b|\bhandover\b",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    system_message_key="exit_reflection.complete",
                    sticky_until=["UserPromptSubmit"],
                ),
            ),
            # Stop (when armed/CLOSED) -> Open: fire-once, WARN-mode paths
            # only (see is_exit_reflection_fire_once). The FULL tier's BLOCK
            # mode deliberately has NO fire-once here — it persists (re-DENYs
            # every Stop) until a legal exit above fires or the escape hatch
            # degrades it. The LITE tier is WARN-only by construction, so it
            # always fires-once.
            GateTrigger(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                    custom_check="is_exit_reflection_fire_once",
                ),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
            # UserPromptSubmit -> re-arm (CLOSED) for the next turn cycle,
            # EVERY session type alike. Resets the block-mode escape-hatch
            # counter (a new user turn is new work, fresh deny budget) and
            # resets turn_did_work to False so a no-op turn gets the lite tier
            # even if an earlier turn wrote something. Slash-command turns
            # (skill invocations) are excluded: a finishing/meta skill owns
            # its own format and must not re-arm the gate it just satisfied.
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
            # FULL tier, block mode: DENY Stop while CLOSED + inject the full
            # checklist via the context channel. prepare_exit_reflection_full
            # builds the audit file so {temp_path} resolves. No fire-once here
            # (see triggers above) — re-fires every Stop until a legal exit.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_exit_reflection_full_block_mode",
                ),
                verdict=GateVerdict.DENY,
                custom_action="prepare_exit_reflection_full",
                message_key="exit_reflection.policy_message",
                context_key="exit_reflection.policy_context",
            ),
            # FULL tier, warn mode: non-blocking delivery, fire-once per turn.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_exit_reflection_full_warn_mode",
                ),
                verdict=GateVerdict.WARN,
                custom_action="prepare_exit_reflection_full",
                message_key="exit_reflection.policy_message",
                context_key="exit_reflection.policy_context",
            ),
            # LITE tier: subagents, no bound task, or a read-only turn on a
            # bound task. Lightweight honesty/self-reflection reminder ONLY —
            # the ida-gate lineage (claims discipline + criterion-substitution
            # check). NEVER denies — reminder-only, no deadlock risk, no audit
            # file, no custom_action.
            GatePolicy(
                condition=GateCondition(
                    current_status=GateStatus.CLOSED,
                    hook_event="Stop",
                    custom_check="is_exit_reflection_lite_active",
                ),
                verdict=GateVerdict.WARN,
                context_key="exit_reflection.lite_reminder",
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
    # UNTOUCHED by the exit_reflection consolidation (aops_4c2949d9) — this
    # gate's disposition (head-surface scoping) migrates separately as
    # note_296e5520 module (b).
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
            # on the Stop that follows it. Mirrors the exit_reflection gate's
            # skill-open trigger; matches Claude's Skill and Gemini's
            # activate_skill.
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
