---
id: workflows-reconcile
title: GH ↔ PKB Reconcile (Close-the-Loop)
type: spec
category: workflow
status: ready
created: 2026-05-13
updated: 2026-05-13
tags: [spec, workflow, reconcile, github, pkb, closure-loop]
related: [[daily-briefing-bundle]], [[feedback-loops]], [[pr-pipeline]], [[work-management]]
supersedes: academicOps PR #985 (closed)
---

# GH ↔ PKB Reconcile

This is a behavioural spec. It describes what an agent does when reconciling GitHub state with the PKB task graph. It does not describe directory layouts, CLI grammars, or verification scripts — the implementing agent decides those.

## Problem

The closure loop between GitHub (issues, PRs) and the PKB task graph is partial and duplicated. `/daily`, `/sleep`, and `/supervisor` each contain ad-hoc closure logic, and matching is done by whole-word title match and branch name — shitty NLP (AXIOMS § 235 / A7 Edge 3).

Four gap types:

1. **GH issue close → PKB `gates_on` update.** When a GH issue closes via `Closes #N` in a commit, no PKB task referencing that issue gets touched.
2. **Closed-not-merged PRs** are unconditionally excluded from `/daily` auto-close, but some are legitimately superseded and should close the task.
3. **Manual `gh issue close`** with `state_reason: not_planned` or `duplicate` — no PKB-side reconciliation.
4. **PKB task done → GH issue close/comment** absent beyond the GH-native `Closes #N` commit convention.

## Design constraints (non-negotiable)

1. **One canonical owner.** The reconcile procedure lives in one skill. Other skills invoke it; they do not re-implement it.
2. **No Shitty NLP.** Mechanical matching is allowed only on guaranteed-structured surfaces (frontmatter fields, the GH API's `closingIssuesReferences` structured field, frontmatter URLs). Anywhere prose is involved, an agent reads it.
3. **State lives in PKB frontmatter** (the graph). Deltas between GH state and PKB state are surfaced through a short-lived (≤48h) event log — same staleness contract as `pr-state.json`. The log is a queue of unprocessed deltas, not state.
4. **All task writes go through PKB MCP.** That is the concurrency primitive.
5. **`needs_user_call` has exactly one rendering consumer**: `/daily`'s "What Needs Attention → Needs your call" section. Writing the flag without that consumer is an A8 violation.
6. **Reverse direction default**: comment-only on GH (cite PKB task ID + closing commit SHA). Auto-close the GH issue only for framework-owned repos and only when the task carries an explicit `closes_issues:` marker (not `gates_on:`).
7. **No bespoke scripts, no bespoke library, no custom cron entrypoint, no new hooks.** Agents do this work using existing tools (PKB MCP, `gh`, Read/Write). _(This is the revision from PR #985: the prior design proposed `aops-core/lib/reconcile/` + `scripts/reconcile.py --forward/--reverse/--full` + cron wiring + a `pkb__complete_task` hook. Nic's review: "no scripts. trust agents to take care of this in a smart way, don't delegate to dumb bash." The script layer is removed.)_
8. **Implementing agent owns file layout, naming, invocation grammar, and verification approach.** This spec does not mandate a directory tree, file names, mode flags, or audit mechanism. Those are downstream decisions the agent makes when landing the work, defended by the constraints above.

## Invocation contexts

The same reconcile procedure runs in three contexts. The context changes the input subset, not the procedure.

| Context       | Triggering agent                             | Input subset                                                                         |
| ------------- | -------------------------------------------- | ------------------------------------------------------------------------------------ |
| Forward sweep | `/daily`                                     | Recently-closed GH issues, recently-merged or closed-not-merged PRs since last sweep |
| Reverse       | `/end-session` or `/pull` on task completion | The just-completed task and its `closes_issues:` markers                             |
| On-demand     | User invocation (e.g., `/reconcile`)         | Full sweep across all active tasks and open issues                                   |

Agents in these contexts invoke the reconcile skill. They do not run scripts. They do not call into a library. The skill body is prose that the invoking agent reads and follows.

## Frontmatter markers

Two task frontmatter fields, PKB-lint validated:

**`closes_issues: [N, M]`** — this task's completion resolves the listed GH issues. On task completion, the agent in reverse-direction context adds a GH comment to each citing the closing commit SHA. For issues in framework-owned repos, the agent also closes the issue; otherwise comment-only. Validation: integer values; warn if a listed issue is already closed at write time.

**`gates_on: [N, M]`** — this task is blocked or monitored by the listed GH issues. When any listed issue closes (forward sweep detects this), the agent writes a `needs_user_call` event for the task. Detection never auto-completes the task; the user decides disposition.

Both fields are legal on the same task simultaneously (a task can both depend on and resolve an issue). The same number appearing in both emits a lint warning — probable data-entry error, not a hard block.

## Event log

Path: `$AOPS_SESSIONS/state/gh-pkb-deltas.json`. Append-only. Events older than 48h pruned on write. Concurrency: file-locked, same primitive as `pr-state.json`. The 48h TTL matches `/daily`'s query window so a daily skill that skips a day still catches yesterday's events.

Each event records: timestamp, direction (forward / reverse), what triggered it, the GH or PKB object that triggered it, how it was matched, what action the agent took, the target object, and a free-text `notes` field used as the surface text when the event renders in `/daily`.

The implementing agent picks the concrete shape (field names, JSON structure, whether to use a discriminator or separate event types). The constraint is that the file is short-lived, append-only, and that `/daily` can read it to render the "Needs your call" surface. Over-structuring this is the failure mode — most fields exist to give `/daily` enough context to render a one-line cue with a link; if a field is only ever read by an LLM as natural-language context, it should stay prose.

## Three matching surfaces

**(a) Guaranteed structured → mechanical.** Direct lookup, no agent call:

- `pr_url` frontmatter → exact string match against `pr-state.json`.
- `closes_issues: [N]` / `gates_on: [N]` → `gh issue view N --json state`.
- `closingIssuesReferences` field from the GH API (structured, not regex over commit text).
- Task-ID pattern in a PR body string field — pattern-match against the PR body as a single field, not as parsed prose.

**(b) Semantic → agent reads the prose.** Where matching needs human-like judgment, the reconcile agent asks a sub-agent (one focused Claude call per question) a structured question and gets back a typed JSON answer with a confidence enum. The three questions the procedure currently asks:

- Does this PR correspond to this task? (PR title, task title, task body excerpt → match bool, confidence, reason)
- Is this closed-not-merged PR superseded? (PR body, timeline, linked issues → superseded_by, disposition)
- Does this manually-closed issue correspond to a PKB task? (issue title, body, labels; top-5 PKB search candidates → task ID, confidence, reason)

Routing: `confidence: low` always falls through to (c). `confidence: high` with a positive match auto-actions only for the `pr_merged` trigger; all other triggers fall through to (c) regardless of confidence. The user retains final judgment everywhere except the merged-PR happy path.

**(c) Ambiguous → `needs_user_call`.** Written when the agent returns low confidence, when an issue closes with `state_reason: not_planned` or `duplicate`, when a closed-not-merged PR has no superseding PR identified, or when a `gates_on` event fires on a task with multiple blocking issues.

## DRY discipline

After this skill exists, the closure-loop logic in `/daily`, `/sleep`, `/supervisor`, and the hook tree must be removed (those skills invoke reconcile instead).

Verification is by audit — the agent landing each milestone reads the touched skills and confirms no duplicate logic remains. The audit is qualitative ("does any other skill still contain closure-loop logic?"), not a syntactic absence check. If the audit can be automated later, that is a separate design question; until then the auditing agent does it by reading.

## Legacy backfill

A one-off agent session, run after the skill lands, before forward sweep is wired into `/daily`'s daily run.

The agent considers all open GH issues across framework repos and all PKB tasks in active statuses (`queued | in_progress | review | merge_ready`). For each, the agent reads the prose and classifies the relationship — does this task close that issue, is it gated on it, or is there no relationship? Uncertain cases get written to the event log with the ambiguous phrase quoted, surfacing in the next `/daily`.

The agent may pre-filter cheaply (e.g., skip items whose body contains no GitHub-reference shape at all) — that is candidate gating over a string field, not prose classification. The judgment call about relationship type is always agent-read, never regex.

Closed and done records are read-only. The candidate set is roughly 282 open issues + active tasks.

## Landing milestones

These are sequencing checkpoints, not implementation tickets. The implementing agent owns file layout and naming.

- **M1 — Skill exists and is manually invocable.** The reconcile procedure is documented as a skill, PKB lint validates the new frontmatter fields, a handful of cases have been worked end-to-end by hand.
- **M2 — Forward sweep adopted by `/daily`.** `/daily` invokes reconcile in forward-sweep context. Closure-loop fragments in `daily/SKILL.md` and `progress-sync.md` are removed. DRY audit clean.
- **M3 — Reverse direction adopted by `/end-session` and `/pull`.** Those skills invoke reconcile in reverse context on task completion. No new hooks added.
- **M4 — Backfill run.** One agent session, scope as above. Done.

## Open questions

- Where does an `issue-state.json` (analogous to `pr-state.json`) get populated? Candidate: the same cron that refreshes `pr-state.json`. Resolved separately — not blocking this spec.
- Should `closes_issues` accept cross-repo references like `owner/repo#N`? Default no (single-repo numeric). Revisit if a use case emerges.

## Provenance and revision history

- **2026-05-13 — Originating session.** PKB task `aops-ea3eaa53`. PR #985 on `nicsuzor/academicOps` shipped a script-heavy version (`aops-core/lib/reconcile/` + `scripts/reconcile.py` + cron + hook). Nic closed with "no scripts. trust agents to take care of this in a smart way."
- **2026-05-13 — Relocation to brain.** Spec moved here, script layer removed.
- **2026-05-13 — Revision after `/learn`.** Pauli's forensic review (issues [#1001–#1004](https://github.com/nicsuzor/academicOps/issues/1004) on academicOps) flagged residual script-shaped grammar in the relocated spec: a mandated directory tree (`aops-core/skills/reconcile/{SKILL.md, references/...}`), CLI-flag-shaped mode names (`--backfill`), grep-based DRY verification, and over-specified JSON for prose-payload events. This revision removes all four: file layout left to the implementing agent (new constraint #8), modes named by English clause not flag, DRY verification described as a qualitative audit, event-log schema described in prose with the agent choosing concrete shape. The "no scripts" principle now extends to the grammar of the spec itself.
