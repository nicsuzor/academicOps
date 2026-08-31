---
title: "Sleep Cycle: Periodic Consolidation Agent"
type: spec
status: draft
created: 2026-03-09
task: aops-6e05d69a
tags:
  - memory
  - consolidation
  - architecture
---

# Sleep Cycle: Periodic Consolidation Agent

## What runs today

`templates/github-workflows/sleep-cycle.yml` ships and installs into the brain
repo (`$ACA_DATA`) as a `workflow_dispatch` job — operator-triggered, not
scheduled. It checks out the brain repo, academicOps, and the sessions repo,
then launches a Claude agent under a 30-minute job timeout with a 25-minute
agent budget and a per-phase batch limit (default 100).

The procedure that agent follows lives in the `remember` skill —
[`plugins/aops/skills/remember/SKILL.md`](../../plugins/aops/skills/remember/SKILL.md)
(maintenance mode) and
[`references/consolidation.md`](../../plugins/aops/skills/remember/references/consolidation.md),
which owns the stage list, batch limits, extraction tests, and defect classes.
This document is the rationale behind that workflow, not a second copy of it;
nothing here restates a stage.

There is no separate `sleep` skill. `/daily`, `/session-insights`, `/audit`,
`/planner`, `/qa`, `/briefing-bundle`, and `/process-bundle` — the supervised
counterparts this design hands its judgment calls to — do not exist in this
repository. Every "stage for supervised review" below therefore currently has
no named receiver, which is the design's largest open hole.

## Problem

Capture works. Retrieval does not. Tasks, session logs, and daily notes are
write-optimised: an agent asking "how does X work?" finds five scattered task
bodies and no synthesised answer, so it either reconstructs from fragments —
slowly, and with errors — or misses the answer entirely.

The gap is **consolidation**: turning accumulated episodes into current-state
knowledge agents actually retrieve.

Synthesising eagerly does not close it. Most captured knowledge is never
retrieved, so upfront synthesis produces moldy documents — permanent notes with
no reader, drifting out of date silently. Promotion has to be pulled by demand,
not pushed by capture.

## Design principles

1. **Every promoted document names its consumer.** A knowledge doc without a
   reader rots. If an insight maps to no consumer in the table below, it stays
   in its episode — git history preserves it.
2. **Consolidation, not synthesis.** The output is updated current-state docs,
   search results, and framework files. Not essays.
3. **Offline batch.** Like sleep consolidation: replay recent episodes, extract
   patterns, update long-term stores, without interrupting active work.
4. **Promotion is use-case-driven, and judged, not scored.** The question is
   always whether a specific reader would be better off — an agent starting
   fresh, a recurring question that keeps being reconstructed, an existing doc
   this contradicts or extends. There is no numeric bar. One retrieval failure
   is stronger signal than ten routine mentions.
5. **Unsupervised execution, supervised judgment.** The cycle runs unattended,
   so it executes mechanical work autonomously and _stages_ everything else for
   a supervised session. The cycle does the legwork; a human or supervised agent
   makes the call.
6. **Idempotent and incremental.** Two runs produce one result. Each run
   processes only what is new since the last.
7. **One cycle, time-bounded.** Phases run in order and the agent exits cleanly
   when the budget is spent. No "nap" versus "deep" modes — two modes buy
   nothing and cost a scheduling decision on every run.
8. **Agents, not orchestrators.** There is no Python driver. The workflow
   launches an agent that works through phases using judgment; deterministic
   scripts cannot make these calls.

## Named consumers

| Consumer        | Reads                                     | Promotion trigger                     |
| --------------- | ----------------------------------------- | ------------------------------------- |
| Session start   | `MEMORY.md`, `CLAUDE.md`, env             | Agent behaviour patterns, conventions |
| PKB search      | `knowledge/`, `memories/`                 | Recurring questions with no answer    |
| Framework files | index files, specs, axioms                | Framework behaviour changes           |
| Daily note      | Focus section, task tree, recommendations | Task status, project progress         |
| Task graph      | Task frontmatter, dependencies            | Status, completion, blocking changes  |

## Constraints on the cycle

**Session insights feed it, and are specified elsewhere.** Backfilling
per-session insight JSON is the cycle's first phase; the extraction contract is
[session-insights-prompt.md](session-insights-prompt.md) and the pipeline
metrics are [session-insights-metrics-schema.md](session-insights-metrics-schema.md).

**Data quality precedes structural work.** Graph maintenance operates on orphan
counts, flat-task counts, and container sizes. With hundreds of duplicates and
stale items in the graph those metrics measure nothing, and the gardener
rearranges garbage into neater piles. Deduplicate and verify staleness first.

**Exhaust available evidence before escalating.** Completion can usually be
proven from sent mail, calendar, git history, or the PKB itself. Verify
autonomously; escalate only genuinely ambiguous cases, or review lists grow
faster than anyone clears them. On CI the mail and calendar servers are absent,
so staleness verification degrades to flagging candidates — never to guessing.

**Age is not staleness.** The cycle must never cancel or delete a task on age or
inactivity alone. Only irrelevance justifies cancellation, and that is a human
judgment. The cycle surfaces candidates; it does not act on them.

**Governance documents are never auto-updated.** Mechanical indices refresh in
place. Axioms, vision, and heuristics changes go out as a PR describing what
changed and why it matters, so the qualitative decision stays with the human.

## Output must not auto-merge

Consolidation output is knowledge of uncertain quality, and everything
downstream reads it. So the cycle splits its writes:

- **Mechanical work** — deduplication, index refresh, graph maintenance, brain
  sync — commits directly. It is deterministic and independently verifiable.
- **Knowledge work** — new notes, synthesis, MOCs — goes to a branch
  `sleep/consolidation-YYYY-MM-DD-HHMM` and opens a PR, reviewed before merge.

**Quality criteria are discovered, not designed.** The review criteria for
consolidation output cannot be written in advance; they come from reviewing real
output and learning what separates good from bad. Design the review after
dogfooding it.

**Graduation path.** A human reviews every consolidation PR at first. Auto-merge
is earned by sustained evidence of quality across many cycles, one step at a
time — reviewer auto-approves and human sees only rejections, then full
autonomy.

## Anti-patterns

- **Over-promotion.** A knowledge doc per observation. Routine details that
  improve no reader's retrieval do not need one.
- **Moldy docs.** Creating a doc with no maintenance path. Every promoted doc
  must be re-checkable by the staleness sweep.
- **Briefing creep.** The cycle presents nothing to a user. It updates stores
  that other tools read.

## Acceptance

- A session transcript with no summary gets one after a cycle.
- An active task with a vague title and empty body is flagged, not deleted.
- A new skill file appears in the mechanical indices after a cycle.
- A change to a governance document arrives as a PR, never a direct commit.
- Every successful cycle ends with a commit to the brain repo.
- The agent exits cleanly inside its budget and writes a summary to
  `$GITHUB_STEP_SUMMARY`, halt count first.

## Open questions

1. **Who receives staged candidates?** No supervised skill exists to hand them
   to. Until one does, promotion candidates have nowhere to land.
2. **How are retrieval failures detected?** They are the strongest promotion
   signal and the cycle cannot currently see them. Session insights are one
   source, but only after post-session processing.
3. **Stale doc: update, archive, or delete?**
4. **Cadence.** The workflow is dispatch-only. Whether a schedule is right, and
   at what interval, is untested.
