---
id: enforcement-task-contract
title: In-Session Enforcement -- The Work-Unit Contract
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

# In-Session Enforcement -- The Work-Unit Contract

## aops -- Work-unit loop (the task contract)

Operative from `claim_task` -> `release_task`. That pair is the contract for
a single agent session's single unit of work: one claimed unit, released under
contract.

**The unified worker contract -- this is its canonical home; other docs link
here.** Any fully-spec'd task -- including one with children; an "epic" is just
a task with children, no special machinery -- can be claimed by any worker on
an appropriate execution surface (polecat container, in-session subagent, agent team).
Tasks requiring repository code modifications, sweeping code greps, or expensive
test suite execution belong strictly in isolated polecat containers, never in
interactive coordinator sessions. Workers use every harness feature they have,
and with that comes the obligation to demonstrate compliance and QA internally --
how is the worker's business. The return contract: **evidence + an output URL,
written to the shared task record.** One deliverable per claimed task, never a spray
of per-child PRs the principal reviews individually. Task scope is one project/repo.
Sync-wait versus fire-and-forget is a dispatch-time cadence choice, not a contract
difference.

**The task graph is the sole source of truth for completion.** `release_task` /
`complete_task` is the authoritative completion claim; a prose "done" that
never moves task state is cheap talk. Enforcement binds to the claim act, not
to the session, so it holds regardless of session class. Completion is not a
claim -- it is a claim carrying verification: the release carries
independent-verification evidence bound to the artifact state of the work.

**A task body carries no history or meta-commentary.** It is a checklist of
work to be done, rewritten in place as items complete -- an item is ticked only
with evidence of that item itself; any other item stays unticked with its limit
stated -- per [`durable-capture`](../../plugins/rbg/skills/axioms/durable-capture.md) and [`single-source-of-truth`](../../plugins/rbg/skills/axioms/single-source-of-truth.md), which
this contract does not restate.

### Mechanisms

- **Premise judgment** -- no longer a standalone gate at `claim_task`. The
  assessment happens earlier, in [`/q`](../../plugins/ida/skills/q/SKILL.md) and [`/reify`](../../plugins/ida/skills/reify/SKILL.md): `/q` places and values the
  work per [R1](../workflows/graph-valuation.md#3-r1----placement-at-intake-q), and `/reify` composes the dispatchable task with its workflow, acceptance criteria, and QA follow-up. Dispatch surfaces ([`/pull`](../../plugins/ida/skills/pull/SKILL.md), [`/dispatch`](../../plugins/ida/skills/dispatch/SKILL.md)) trust that rather
  than re-judging the premise themselves.
- **Task-binding invariant** -- no mutating work without a task bound to the
  session via `claim_task`, never an environment variable naming the task.
  One session claims exactly one task, possibly multiple subtasks of it. In
  interactive sessions, for each new non-casual topic, strictly one outer task on the PKB graph is placed and claimed via `/q` by the internal sub-coordinator (`sub-Ida`) on behalf of the interactive session before substantial work begins (searching open and closed related tasks to resume, reopen, or mint the topic task); the user-facing coordinator strictly delegates and verifies, creating no tasks directly. Downstream workers and delegates below the sub-coordinator never create additional tasks on the graph. Pure lookups, PKB reads/writes, and questions answered in-turn require no task creation and no pull/dump ceremonies (`wf-lookup`). Only Face Ida runs the session handover `/dump`.
- **Bundled PR invariant under epics** -- when tasks execute under a parent task marked `bundle_pr: true` or under an active epic (`type: epic`), workers commit directly to the designated epic branch (`polecat/<epic-id>` or `topic/<slug>`) and do not open detached pull requests against `dev`. All changes and review records bundle into the epic's consolidated pull request for cohesive user review. Standalone tracking PRs are marked superseded and closed upon consolidation.
- **Claim at launch** -- a dispatch whose loss would matter beyond its own
  session has its claim written to the graph before the worker starts: who it
  went to, under which session and surface, and when. The worker's own
  `claim_task` still happens from inside its session and is what moves the
  status; the launch-time record exists so that a worker which died before ever
  claiming is legible as an unanswered dispatch rather than as work nobody
  picked up. **Cheap read-only probes and pure lookups are exempt** -- nothing is lost by running
  one again, so claiming for them buys graph noise instead of recoverability. Pure
  lookups, PKB reads/writes, and questions require no task creation and no pull or dump ceremony. A
  launch-time claim with no worker claim behind it is precisely the
  never-landed-dispatch signal Sara reviews, requeuing it to `ready`
  where warranted -- `/reconcile` no longer probes or resets claims.
- **Task naming invariant** -- task titles must be brief, descriptive, verb-led statements of a concrete thing to achieve (e.g. `Implement X`, `Verify Y`). A task title or filename never carries a person's name or persona prefix; assignment belongs exclusively in `assigned_to` / `assignee` frontmatter fields. See [`specs/meta/naming-and-decisions.md`](../meta/naming-and-decisions.md).
- **Decisions as graph relationships and groundwork-first decision making** -- un-actionable question tasks are prohibited. An agent given a task does the groundwork and makes the decision itself; it never files the task back to the user as their decision (`assignee: user`) unless the user explicitly asked to decide it themselves (tg 1013). Design research tasks evaluate candidate alternatives and choose the recommended route directly to unblock downstream implementation. Tasks requiring review or follow-up are structured as a single task with internal subtasks or as a dedicated epic with child tasks, never as loose siblings under an external parent. Competing candidate options stay inside the body of the scoping task or ADR until chosen (retiring separate unchosen option nodes and `alternative` edges); when chosen, only the selected option is reified into an actionable task under `parent: <scoping_task_id>`. Missing information is modelled as an empirical probe task (`classification: probe`) wired to dependent tasks via standard execution prerequisite `needs: [<probe_task_id>]`. In-turn questions are put directly via `AskUserQuestion`.
- **Worker state-only invariant** -- a worker executing a task may only mutate that task's own state (checking off acceptance criteria, recording verifiable evidence, transitioning status). Workers never inspect or modify edges across other tasks, compute reverse graph dependencies, or mint follow-up verification tasks. Unblocking, dependency resolution, and sequencing belong exclusively to the graph engine and dispatcher.
- **Task body brevity invariant** -- task bodies are strictly concise (50-150 words for atomic tasks at capture), structured around `Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, and `Pointers` ([`specs/meta/naming-and-decisions.md`](../meta/naming-and-decisions.md), [`plugins/ida/agents/pauli.md`](../../plugins/ida/agents/pauli.md)) and expanded by [`/reify`](../../plugins/ida/skills/reify/SKILL.md) into the dispatchable contract (`Ask`, `Goal`, `Context`, `Acceptance`, `Instructions`, `Output`, `Report`, `Appendix: Sources`). Extraneous narrative sections (`Background`, `References`, `Implementation Plan`) and prose task links are prohibited.
- **Graph edge economy invariant** -- setting `parent_id` is already an intrinsic graph edge; redundant wiring between descendants/siblings under the same parent without specific interactions is prohibited.
- **Outcome-oriented task contract invariant** -- task acceptance criteria and instructions define observable end-state conditions and verification criteria rather than implementation mechanisms. `Goal`, `Acceptance`, and `Instructions` must contain zero line numbers, line ranges, or narrow slice prescriptions. Reification of multi-file or architectural changes under `wf-code-task-base` preserves a distinct Stage 1 (Design) task preceding Stage 2 (Build).
- **Brief and stage satisfiability invariant** -- task acceptance criteria, report requirements, and delegation briefs must be bounded strictly to artifacts and state produced by the assigned worker before release. Downstream pipeline outcomes (such as pull request URLs from subsequent workers, merged code branches, or decisions delegated to future stages) must never be demanded of early-stage workers, dispatchers, or planning agents.
- **Full-context file inspection invariant** -- workers must read target repository files in full before executing edits. Keyhole line-slice reads (`read_file` with narrow line windows around advisory line hints) in isolation without prior whole-file context are strictly prohibited; advisory line hints are starting pointers only. Files exceeding single-page tool limits are inspected via sequential discovery before editing.
- **Change-only, single-flight recurring runs invariant** -- every recurring job handles only what changed since its last completed run (`since: <cursor>`), stops immediately when nothing changed, and never starts while another run of the same job is going. Cursors are stored in authoritative state records or document frontmatter; active in-progress markers enforce single-flight concurrency.
- **Bounded helper invariant** -- subagent helpers are kept bounded: related operations batched into single turns, and no helper left idle on background work past the 5-minute prompt cache lifetime. On agent-idle hooks and task boundaries, agents are encouraged to evaluate whether a helper has run too long and cull it, dispatching fresh subagents for unrelated tasks.
- **Evidence contract** -- at `release_task` / `complete_task`; the completion
  claim must carry independent-verification evidence bound to artifact state,
  or a stated failure reason. **This is the primary enforcement point.**
  Framed to agents as "land the plane" -- commit -> push -> `release_task` with
  either a completion claim (`done`) or a `partial` handback per
  [spec-partial-work-tight-loop-delivery.md](../polecat/spec-partial-work-tight-loop-delivery.md#the-partial-terminal-state)
  (the existing terminal status in the canonical taxonomy -- a partial handback
  is a legal terminal outcome, not a failure; that spec owns partial
  semantics, which this bullet does not restate). `/pull` mandates invoking
  `/dump` for the final handover and for logging results at the end of every
  job, whatever its release status (`done`, `partial`, `failed`,
  `cancelled`, or `in_progress`), and `/dump`'s `release_task` body update
  includes a report argument (per [`premise-check`](../../plugins/ida/skills/premise-check/SKILL.md))
  whose conclusion answers each original direction given or question posed by
  its ask id. A worker whose deliverable is a PR opens the PR as a draft (`gh pr create --draft`), releases its task `done` once the draft PR is open with branch and `pr_url` recorded and local tests verified, and exits; releasing `done` immediately unblocks dependent follow-ups (QA, review, deploy) on the task graph, and the PR goes ready for review (`gh pr ready`) only after the coordinator's independent check passes; `partial` is reserved strictly for the worker's own unfinished acceptance items. Only silent, undisclosed
  abandonment is garbage-collected (H10): incentive-first, this machinery is the
  backstop, not the mechanism agents are expected to lean on. Its floor is the
  task server predicate -- the contract is only as strong as that floor.
  The completion claim meets the [evidence contract](evidence-contract.md).
  Its required fields are checked for presence only, and only on tasks created
  after the check shipped.
