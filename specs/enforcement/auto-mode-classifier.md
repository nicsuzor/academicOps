---
id: auto-mode-classifier
title: Auto-Mode Classifier — the framework's judgment gate at the per-action boundary
type: spec
status: draft
tier: core
depends_on: [enforcement]
tags: [enforcement, automode, classifier, judgment, framework-architecture]
---

# Auto-Mode Classifier — the framework's judgment gate at the per-action boundary

Claude Code's auto mode delegates tool-call approvals to a model-based
classifier that runs before every tool call. It reads a **stripped
transcript** (the user's messages in full, plus bare tool-call names and
parameters — not the agent's prose or prior tool outputs) plus the
framework's prose rules (`environment` / `allow` / `soft_deny` /
`hard_deny`). It returns **allow** or **deny** — there is no "ask" verdict.
A denial comes back to the agent as a tool result with a reason, on the
expectation the agent finds a safer path rather than routes around it.

## Admission criteria — a rule belongs in the classifier iff _all_ hold

| # | Criterion                             | The question to ask                                                                                                                               | If it fails                                                                                                 |
| - | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 1 | **Judgment-requiring**                | Would a deterministic check need brittle heuristics / regex-for-meaning and false-positive?                                                       | A clean path/AST/flag check works → use `policy_enforcer` or a pre-commit hook, not the classifier.         |
| 2 | **Per-action observable**             | Is the violation visible in {user messages + the proposed tool call + its parameters} alone, without the agent's reasoning or prior tool outputs? | Only observable across the session or in the agent's prose → enforcer subagent / IDA / review.              |
| 3 | **Pre-execution is the right moment** | Does catching it _before_ the call beats warning _after_?                                                                                         | Post-hoc is fine or better → PostToolUse / enforcer / review.                                               |
| 4 | **Not already covered**               | Is it un-caught by any cheaper, reliable mechanism today?                                                                                         | Already caught → don't duplicate (`single-source-of-truth`).                                                |
| 5 | **Evidence of recurrence**            | Are agents demonstrably _not_ already good at this (≥3 cited recurrences, or explicit user direction)?                                            | No evidence → premature; log it, don't add it.                                                              |
| 6 | **Survives the denial-cost test**     | Will it fire _rarely and precisely_, and hand the agent a clear safer path on the first denial?                                                   | Fires often / no clean alternative → it will kill autonomous sessions (see Cost model). Redesign or reject. |

## Cost model — the constraints that shape every rule

- **There is no nudge channel — only deny.** The classifier's only agent-visible output is a denial with a reason returned as a tool result. To "nudge" toward better behaviour you must _deny the worse action_ and write the reason as the redirect you want read.
- **Death-by-denial is the dominant risk.** In headless / autonomous operation there is no human to approve a blocked action. Claude Code **terminates the process after 3 consecutive or 20 total denials**. A rule that fires on, say, 10% of tool calls will _kill long autonomous runs_ — rules must fire rarely, on clear violations only, and give a one-shot safer path.
- **The denial budget is shared across all rules.** The 3-consecutive / 20-total ceiling is _aggregate_, not per-rule. Calibrate against the _sum_ of every rule's fire rate — two individually-safe rules can jointly cross the ceiling. Add a rule only once the existing rules' aggregate fire rate is known to leave headroom.

## Rule-writing form

Write each rule as **prose stating principle + reasoning + cue + carve-outs**, never a rule-ID lookup or keyword pattern. Each rule states:

1. **The principle** and, in one clause, **why it matters** — cite the axiom slug it serves (e.g. `judgment-non-delegable`) from [`AXIOMS.md`](../../.agents/rules/AXIOMS.md).
2. **The cue** the classifier should look for in the action + user context — the observable signal, since it cannot see reasoning.
3. **What counts as a violation**, and the **safer path** to name in the denial.
4. **Explicit carve-outs** — when the same action is fine. The classifier handles disjunctions ("deny X when bypassing tests; allow X when validating") as prose.

Default every new behavioural rule to `soft_deny` (context-overridable); escalate to `hard_deny` only on evidence that a `soft_deny` was bypassed with reproducible consequences.

**Current state: the rule set is empty.** No `autoMode` rules are seeded yet — the mechanism, spec, and pyramid placement exist, but the classifier's behavioural rule set has zero entries. New rules follow the evidence loop above and land via [`ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md).

## References

- [CC Auto Mode engineering post](https://www.anthropic.com/engineering/claude-code-auto-mode) — canonical external description.
- [`specs/enforcement/enforcement.md`](enforcement.md) — enforcement design statement (pyramid, escalation discipline).
- [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) — operative register (where this classifier's rules are recorded).
