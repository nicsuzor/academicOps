---
id: workflows-reconcile
title: GH ↔ PKB Reconcile (Close-the-Loop)
type: spec
category: workflow
status: ready
tags: [spec, workflow, reconcile, github, pkb, closure-loop]
related: [[feedback-loops]], [[pr-pipeline]], [[work-management]]
---

# GH ↔ PKB Reconcile

This is a behavioural spec. It describes what an agent does when reconciling GitHub state with the PKB task graph. It does not describe directory layouts, CLI grammars, or verification scripts — the implementing agent decides those.

## Problem

The closure loop between GitHub (issues, PRs) and the PKB task graph is partial, and where it runs it matches by whole-word title and branch name — shitty NLP (the `judgment-non-delegable` axiom).

Four gap types. Of these, only #2 is built into the `reconcile` skill today — the
skill's own scope is "tasks and the pull requests they resolve against," and it
carries no issue-matching logic. #1, #3, and #4 are specified below as the
target shape of a forward-issue leg that does not exist yet; nothing in this
spec should be read as claiming they currently run.

1. **GH issue close → PKB `gates_on` update.** When a GH issue closes via `Closes #N` in a commit, no PKB task referencing that issue gets touched. **Not built.**
2. **Closed-not-merged PRs** are unconditionally excluded from auto-close, but some are legitimately superseded and should close the task. **Built** — see the `reconcile` skill's pull-request routing step.
3. **Manual `gh issue close`** with `state_reason: not_planned` or `duplicate` — no PKB-side reconciliation. **Not built.**
4. **PKB task done → GH issue close/comment** absent beyond the GH-native `Closes #N` commit convention. **Not built** — this is the reverse direction; see below and M3.

## Design constraints (non-negotiable)

1. **One canonical owner.** The reconcile procedure lives in one skill. Other skills invoke it; they do not re-implement it.
2. **No Shitty NLP.** Mechanical matching is allowed only on guaranteed-structured surfaces (frontmatter fields, the GH API's `closingIssuesReferences` structured field, frontmatter URLs). Anywhere prose is involved, an agent reads it.
3. **State lives in PKB frontmatter** (the graph). Deltas between GH state and PKB state are surfaced through a short-lived (≤48h) event log. The log is a queue of unprocessed deltas, not state.
4. **All task writes go through PKB MCP.** That is the concurrency primitive.
5. **Nothing is flagged for a person without a surface that renders it.** The sweep's own synthesized result is that surface — it leads with what needs a person's decision. Writing a `needs_user_call` flag to the graph with no consumer that renders it is a `halt-on-failure` violation.
6. **Reverse direction default**: comment-only on GH (cite PKB task ID + closing commit SHA). Auto-close the GH issue only for framework-owned repos and only when the task carries an explicit `closes_issues:` marker (not `gates_on:`).
7. **No bespoke scripts, no bespoke library, no custom cron entrypoint, no new hooks.** Agents do this work using existing tools (PKB MCP, `gh`, Read/Write).
8. **Implementing agent owns file layout, naming, invocation grammar, and verification approach.** This spec does not mandate a directory tree, file names, mode flags, or audit mechanism. Those are downstream decisions the agent makes when landing the work, defended by the constraints above.

## Invocation contexts

The reconcile procedure runs in three contexts. The context changes the input subset, not the procedure.

| Context    | Owner                                                                        | Input subset                                                               |
| ---------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Engagement | The `reconcile` skill, commissioned by the interactive face on re-engagement | The absence window: claims taken before it, pull requests closed during it |
| Batch      | The `remember` skill's consolidation cycle, delegating to `reconcile`        | The cycle's window, at the cycle's pacing                                  |
| On-demand  | The `reconcile` skill, invoked directly                                      | Full sweep across every non-terminal task and its pull requests            |

Every row's input subset is pull requests only, matching the skill's current
scope. Once the forward-issue leg (gap types #1 and #3 above) is built, each
row's subset extends to the open issues in the same window.

The face does not touch the knowledge base — a prohibition on what is hers to do, not a claim about what tools a session hands her — so its engagement sweep is a delegation: it commissions an agent that runs the skill and returns one synthesized result.

**The reverse direction is not a fourth context of this procedure.** A task completing, and what its completion resolves on the issue tracker, belongs on the release path that already writes the task — a different act on a different trigger, which reconcile does not run. It is not built: no skill in the tree reads `closes_issues:` today, and M3 below is where it lands.

Agents in the three contexts invoke the reconcile skill. None of them runs a script or calls into a library. The skill body is prose that the invoking agent reads and follows.

## Frontmatter markers

Two task frontmatter fields, PKB-lint validated:

**`closes_issues: [N, M]`** — this task's completion resolves the listed GH issues. On task completion, the agent on the release path adds a GH comment to each citing the closing commit SHA. For issues in framework-owned repos, the agent also closes the issue; otherwise comment-only. Validation: integer values; warn if a listed issue is already closed at write time.

**`gates_on: [N, M]`** — this task is blocked or monitored by the listed GH issues. When any listed issue closes (forward sweep detects this), the agent writes a `needs_user_call` event for the task. Detection never auto-completes the task; the user decides disposition. **Not built** — the `reconcile` skill does not read this field or query issue state today; this is the target shape of the forward-issue leg (gap type #1).

Both fields are legal on the same task simultaneously (a task can both depend on and resolve an issue). The same number appearing in both emits a lint warning — probable data-entry error, not a hard block.

## Event log

Path: `$AOPS_SESSIONS/state/gh-pkb-deltas.json`. Append-only, file-locked. Events older than 48h pruned on write. The 48h TTL is deliberately wider than the expected sweep cadence, so a sweep that skips a day still catches the previous day's events.

Each event records: timestamp, direction (forward / reverse), what triggered it, the GH or PKB object that triggered it, how it was matched, what action the agent took, the target object, and a free-text `notes` field used as the surface text when the event renders in a sweep's result.

The implementing agent picks the concrete shape (field names, JSON structure, whether to use a discriminator or separate event types). The constraint is that the file is short-lived, append-only, and that the next sweep can read it to render what needs a person's decision. Over-structuring this is the failure mode — most fields exist to give the sweep's result enough context to render a one-line cue with a link; if a field is only ever read by an LLM as natural-language context, it should stay prose.

## Three matching surfaces

**(a) Guaranteed structured → mechanical.** Direct lookup, no agent call:

- `pr_url` frontmatter → exact string match against the pull request's own state, read from `gh`. **Built.**
- Task-ID pattern in a PR body string field — pattern-match against the PR body as a single field, not as parsed prose. **Built.**
- `closes_issues: [N]` / `gates_on: [N]` → `gh issue view N --json state`. **Not built** — forward-issue leg.
- `closingIssuesReferences` field from the GH API (structured, not regex over commit text). **Not built** — forward-issue leg.

**(b) Semantic → agent reads the prose.** Where matching needs human-like judgment, the reconcile agent asks a sub-agent (one focused Claude call per question) a structured question and gets back a typed JSON answer with a confidence enum. The three questions the procedure currently asks:

- Does this PR correspond to this task? (PR title, task title, task body excerpt → match bool, confidence, reason) **Built.**
- Is this closed-not-merged PR superseded? (PR body, timeline, linked issues → superseded_by, disposition) **Built.**
- Does this manually-closed issue correspond to a PKB task? (issue title, body, labels; top-5 PKB search candidates → task ID, confidence, reason) **Not built** — forward-issue leg (gap type #3).

Routing: `confidence: low` always falls through to (c). `confidence: high` with a positive match auto-actions only for the `pr_merged` trigger; all other triggers fall through to (c) regardless of confidence. The user retains final judgment everywhere except the merged-PR happy path.

**(c) Ambiguous → `needs_user_call`.** Written when the agent returns low confidence, or when a closed-not-merged PR has no superseding PR identified. Once the forward-issue leg is built, this also covers an issue closing with `state_reason: not_planned` or `duplicate`, and a `gates_on` event firing on a task with multiple blocking issues.

## DRY discipline

No other skill carries closure-loop logic of its own. The consolidation cycle delegates its staleness-and-closure stage to reconcile rather than restating it, and any surface that grows a closure need invokes reconcile instead of re-implementing one.

Verification is by audit — the agent landing each milestone reads the touched skills and confirms no duplicate logic remains. The audit is qualitative ("does any other skill still contain closure-loop logic?"), not a syntactic absence check. If the audit can be automated later, that is a separate design question; until then the auditing agent does it by reading.

## Legacy backfill

Blocked on the forward-issue leg (gap types #1 and #3) landing first — this pass
classifies task/issue relationships the current skill does not yet detect. A
one-off agent session, run after that leg lands, before the forward sweep runs
on a cadence.

The agent considers all open GH issues across framework repos and all PKB tasks in the taxonomy's actionable set. For each, the agent reads the prose and classifies the relationship — does this task close that issue, is it gated on it, or is there no relationship? Uncertain cases get written to the event log with the ambiguous phrase quoted, surfacing in the next sweep's result.

The agent may pre-filter cheaply (e.g., skip items whose body contains no GitHub-reference shape at all) — that is candidate gating over a string field, not prose classification. The judgment call about relationship type is always agent-read, never regex.

Closed and done records are read-only. The candidate set is roughly 282 open issues + active tasks.

## Landing milestones

These are sequencing checkpoints, not implementation tickets. The implementing agent owns file layout and naming.

- **M1 — Skill exists and is invocable.** The reconcile procedure is one skill, PKB lint validates the new frontmatter fields, a handful of cases have been worked end-to-end by hand.
- **M2 — Forward sweeps adopted.** The engagement and batch contexts both reach the skill, and no other skill carries closure-loop logic of its own. DRY audit clean.
- **M3 — Reverse direction adopted at release.** The `dump` and `pull` skills carry the reverse handoff on the release path that already writes the task — reading `closes_issues:` and acting on it there, not by invoking reconcile. No new hooks added.
- **M4 — Backfill run.** One agent session, scope as above. Done.

## Open questions

- Is a cached issue-state snapshot worth keeping, so a sweep does not re-query `gh` for every tracked issue? Resolved separately — not blocking this spec.
- Should `closes_issues` accept cross-repo references like `owner/repo#N`? Default no (single-repo numeric). Revisit if a use case emerges.
