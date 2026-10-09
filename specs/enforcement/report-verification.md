---
id: enforcement-report-verification
title: Report Verification -- Premise-Check Protocol and Arrival Gates
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, premise-check, hooks]
---

# Report Verification -- Premise-Check Protocol and Arrival Gates

This specification defines the verification protocol by which an agent receiving an
incoming report judges its logic before acting on it or relaying it to other agents
or users, and the hook mechanics that hold the receiver to it.

The operative instructions are the `premise-check` skill
(`plugins/ida/skills/premise-check/SKILL.md`). The mechanics are
`plugins/ida/hooks/premise_check_gate.py` (arming and the gate) and
`plugins/ida/hooks/premise_check_verdict.py` (verdict recording).

## Governing Principles

1. **Verification is qualitative judgment:** No mechanical parser or regex filter
   can determine whether an argument holds. Verification is strictly an agentic
   qualitative assessment.
2. **Form, not facts:** The receiver checks the quality of the report's logic
   against the original ask. It does not open sources, re-run work, or authenticate
   the reporter's records to confirm the facts, and it adds no requirements the
   original ask did not set. Rigour is matched to the output's purpose.
3. **Delivery channels guide and never decide:** Hooks provide timely advisory
   reminders (JIT injection) and procedural friction (the premise-check gate). They
   inspect session metadata and whether a verdict has been recorded, never report
   text or substance.

## The Premise-Check Procedure

The receiving agent asks three questions of the report:

1. **Can the evidence support the claims?** Each load-bearing claim names checkable
   evidence (a PR, commit, node id, `file:line`, a quoted output) that, if it is what
   the report says, would show the claim. The reporter's statement of what it did is
   evidence of the work; a pointer is evidence of where it was saved.
2. **Do the claims lead to the conclusion?** The steps are valid: no unstated
   premise, no inference passed off as observation, no conclusion wider than the
   evidence.
3. **Does the conclusion fully answer the original ask?** Every part of the ask is
   addressed, in the ask's own terms.

The check runs when a peer or worker report arrives, and before any claim -- the
receiver's own included -- goes up the chain. The user's own messages are asks, not
reports, and are never checked.

### Categorical Verdicts

The receiver concludes the premise-check by recording one verdict token
(`VERDICTS` in `premise_check_verdict.py`) with a free-text reason:

- **`PASS`**: All three questions hold.
- **`REVISE`**: The logic holds in part; the reason names what is missing or does
  not follow.
- **`FAIL`**: The report does not answer the ask, or its conclusion does not follow
  from it.

A `REVISE` or `FAIL` goes back to its author. It does not reach the user hedged; it
reaches the user only once it passes.

## Arrival-Time Mechanics and Procedural Friction

The gate applies only to sessions whose agent type is ida or sara (`ida:ida`,
`ida`, `ida:sara`, `sara`). Every other agent is unaffected.

1. **Advisory JIT reminder:** On `UserPromptSubmit`, when the prompt begins with a
   peer envelope (`<cross-session-message`, `<teammate-message`, `<task-notification`),
   `rule_against_hearsay` injects the hearsay reminder (`"## A peer report arrived"`)
   for ida and sara, directing them to run `/premise-check` on it. User prompts --
   typed console input and `<channel ...>` messages from Telegram or Discord -- never
   trigger it.
2. **Arming (`premise_check_arm`):**
   - On `UserPromptSubmit`, a prompt beginning with a peer envelope arms the gate
     with a claim id derived from the envelope (tag, sender, and the first 80
     characters of the body) and injects the exact verdict command to run. User
     messages never arm it.
   - On `PostToolUse` and `PostToolBatch`, a call to a subagent-dispatch tool
     (`Agent`, `Task`, `invoke_subagent`) arms the gate, with a claim id from the
     call's description or prompt (first 80 characters) or its tool-use id.
     `PostToolBatch` is registered for Claude Code only.
3. **The gate (`premise_check_handler`):** While armed, the gate:
   - refuses `PreToolUse` on `Agent`, `Task`, `invoke_subagent`, `SendMessage`,
     `AskUserQuestion`, and `Dump`, on every attempt, until a verdict is recorded;
   - blocks `Stop`, giving the session another turn. The dispatcher skips all
     handlers on the re-fired stop (`stop_hook_active`), so a stop is withheld once
     per stop chain.

   Channel reply tools (such as `telegram_reply`) are not on the refused list. The
   refusal and block messages name the claim that armed the gate and give the
   runnable verdict command.
4. **Disarming:** Recording a verdict disarms the gate. The agent runs
   `scripts/verdict.py` in the skill directory (a wrapper around
   `premise_check_verdict.py`) with `--report <claim> --verdict PASS|REVISE|FAIL` and
   `--reason`, or `--reason-file <path>` (`-` for stdin) to keep free text off the
   command line. The session id defaults to `$AOPS_SESSION_ID`, which the
   `SessionStart` hook exports to `CLAUDE_ENV_FILE`; otherwise `--session` is
   required. Gate state is a per-session JSON file under the system temp directory
   (`aops_premise_check/`, overridable with `AOPS_PREMISE_CHECK_DIR`).
5. **Modes and override:** `PREMISE_CHECK_GATE_MODE` is `block` by default; `warn`
   injects the gate message instead of refusing or blocking, and `off` disables the
   gate. A truthy `PREMISE_CHECK_OVERRIDE`, `PREMISE_CHECK_GATE_OVERRIDE`,
   `AOP_FORCE`, or `AOP_OVERRIDE` also disables it.

The gate is strictly structural: it checks whether a verdict is recorded in local
session state and never inspects report text.

## Observability and Telemetry

Recording a verdict emits one OpenTelemetry TOOL span (`tool.name`
`premise_check_verdict`) through the `claude_code_tracer` export pipeline, parented
to the session's current trace when one exists. It carries:

- `premise_check.claim_id`: the claim the verdict is for.
- `premise_check.verdict`: `PASS`, `REVISE`, or `FAIL`.
- `premise_check.reason`: the reason, truncated.

Span emission is best-effort: when tracing is unconfigured or the export is not
acknowledged, the verdict is still recorded and the gate disarmed, and the script
says so on stderr. No span is emitted on arrival or arming.
