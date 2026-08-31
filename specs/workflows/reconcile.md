---
id: workflows-reconcile
title: GH ↔ PKB Reconcile (Close-the-Loop)
type: spec
category: workflow
status: ready
tags: [spec, workflow, reconcile, github, pkb, closure-loop]
related:
  - feedback-loops
  - pr-pipeline
  - work-management
---

# GH ↔ PKB Reconcile

The reconcile procedure itself lives in `plugins/aops/skills/reconcile/SKILL.md` and is not
restated here. This spec carries the design constraints that bind it, the frontmatter and
event-log surfaces it reads and writes, and the target shape of the GitHub-issue leg it does not
yet cover.

## Coverage

The skill's scope is tasks and the pull requests they resolve against. Four closure gaps exist;
one is covered.

| Gap                                                                                    | State                                         |
| -------------------------------------------------------------------------------------- | --------------------------------------------- |
| GH issue closed via `Closes #N` → PKB task carrying `gates_on` for it                  | Not built — forward-issue leg, below          |
| Closed-not-merged PR that was legitimately superseded                                  | Built — the skill's pull-request routing step |
| Manual `gh issue close` with `state_reason: not_planned` or `duplicate`                | Not built — forward-issue leg, below          |
| PKB task done → GH issue comment/close beyond the native `Closes #N` commit convention | Not built — reverse direction, M3             |

## Design constraints

1. **One canonical owner.** The procedure lives in one skill. Other skills invoke it; they do not
   re-implement it.
2. **No shitty NLP.** Mechanical matching is allowed only on guaranteed-structured surfaces
   (frontmatter fields, the GH API's `closingIssuesReferences`, frontmatter URLs). Anywhere prose
   is involved, an agent reads it.
3. **State lives in PKB frontmatter.** Deltas between GH state and PKB state surface through a
   short-lived event log, which is a queue of unprocessed deltas, not state.
4. **All task writes go through PKB MCP.** That is the concurrency primitive.
5. **Nothing is flagged for a person without a surface that renders it.** The sweep's own
   synthesized result is that surface. A `needs_user_call` flag with no consumer that renders it
   is a `halt-on-failure` violation.
6. **Reverse direction defaults to comment-only** on GH, citing PKB task ID and closing commit
   SHA. Auto-close the GH issue only for framework-owned repos, and only where the task carries
   an explicit `closes_issues:` marker (never `gates_on:`).
7. **No bespoke scripts, no bespoke library, no custom cron entrypoint, no new hooks.** Agents do
   this work with PKB MCP, `gh`, and Read/Write.
8. **The implementing agent owns file layout, naming, invocation grammar, and verification
   approach**, defended by the constraints above.

## Invocation contexts

The context changes the input subset, not the procedure.

| Context    | Owner                                                                        | Input subset                                                               |
| ---------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Engagement | The `reconcile` skill, commissioned by the interactive face on re-engagement | The absence window: claims taken before it, pull requests closed during it |
| Batch      | The `remember` skill's consolidation cycle, delegating to `reconcile`        | The cycle's window, at the cycle's pacing                                  |
| On-demand  | The `reconcile` skill, invoked directly                                      | Full sweep across every non-terminal task and its pull requests            |

Each subset is pull requests only. Once the forward-issue leg lands, each extends to the open
issues in the same window.

The face does not touch the knowledge base, so its engagement sweep is a delegation: it
commissions an agent that runs the skill and returns one synthesized result.

**The reverse direction is not a fourth context.** What a task's completion resolves on the issue
tracker belongs on the release path that already writes the task — `dump` and `pull` — on a
different trigger, which reconcile does not run.

## Frontmatter markers

Two task frontmatter fields, PKB-lint validated. Both are legal on one task simultaneously; the
same issue number appearing in both emits a lint warning, not a hard block.

**`closes_issues: [N, M]`** — this task's completion resolves the listed GH issues. On completion,
the agent on the release path comments on each citing the closing commit SHA, and for
framework-owned repos also closes the issue. Validation: integer values; warn if a listed issue is
already closed at write time.

**`gates_on: [N, M]`** — this task is blocked or monitored by the listed GH issues. When a listed
issue closes, the forward sweep writes a `needs_user_call` event; detection never auto-completes
the task. **Not built** — no skill reads this field today.

## Event log

Path: `$AOPS_SESSIONS/state/gh-pkb-deltas.json`. Append-only, file-locked, events older than 48h
pruned on write. The TTL is wider than the sweep cadence so a skipped day still catches the
previous day's events.

Each event records: timestamp, direction (forward / reverse), what triggered it, the GH or PKB
object that triggered it, how it was matched, the action taken, the target object, and a
free-text `notes` field used as the surface text when the event renders in a sweep's result.

The implementing agent picks the concrete shape. The binding constraints are that the file is
short-lived and append-only, and that the next sweep can read it to render what needs a person's
decision. Over-structuring is the failure mode: a field only ever read as natural-language
context stays prose.

## Forward-issue leg — target shape

Structured surfaces, matched mechanically:

- `closes_issues: [N]` / `gates_on: [N]` → `gh issue view N --json state`.
- `closingIssuesReferences` from the GH API — the structured field, never regex over commit text.

Prose surfaces, read by an agent that returns a typed JSON answer with a confidence enum. One
question: does this manually-closed issue correspond to a PKB task? (issue title, body, labels;
top-5 PKB search candidates → task ID, confidence, reason).

**Routing.** `confidence: low` always falls through to `needs_user_call`. `confidence: high` with
a positive match auto-actions only for the `pr_merged` trigger; every other trigger falls through
to `needs_user_call` regardless of confidence. `needs_user_call` also covers an issue closing
with `state_reason: not_planned` or `duplicate`, and a `gates_on` event firing on a task with
multiple blocking issues.

This routing governs **matching** only. The skill's own cancellation authority — a world-fact
established under a written evidence burden — is separate and does not route through it.

## DRY discipline

No other skill carries closure-loop logic of its own. Verification is by audit: the agent landing
each milestone reads the touched skills and answers, by reading, "does any other skill still
contain closure-loop logic?"

## Legacy backfill

Blocked on the forward-issue leg landing first. A one-off agent session, run after that leg lands
and before the forward sweep runs on a cadence.

The agent considers all open GH issues across framework repos and all PKB tasks in the taxonomy's
actionable set, reads the prose, and classifies each relationship — does this task close that
issue, is it gated on it, or is there no relationship. Uncertain cases go to the event log with
the ambiguous phrase quoted, surfacing in the next sweep's result. Closed and done records are
read-only.

Cheap pre-filtering over a string field (skip items whose body contains no GitHub-reference shape)
is permitted; the relationship classification is always agent-read, never regex.

## Landing milestones

Sequencing checkpoints, not implementation tickets.

- **M1 — Skill exists and is invocable.** One skill, PKB lint validates the new frontmatter
  fields, a handful of cases worked end-to-end by hand.
- **M2 — Forward sweeps adopted.** Engagement and batch contexts both reach the skill; no other
  skill carries closure-loop logic. DRY audit clean.
- **M3 — Reverse direction adopted at release.** `dump` and `pull` read `closes_issues:` and act
  on it on the release path, not by invoking reconcile. No new hooks.
- **M4 — Backfill run.**

## Open question

Should `closes_issues` accept cross-repo references like `owner/repo#N`? Default no (single-repo
numeric); revisit if a use case emerges.
