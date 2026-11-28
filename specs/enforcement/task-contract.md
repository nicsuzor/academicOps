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
stated -- per [`durable-capture`](../../plugins/crew/skills/axioms/durable-capture.md) and [`single-source-of-truth`](../../plugins/crew/skills/axioms/single-source-of-truth.md), which
this contract does not restate.

### Mechanisms

- **Premise judgment** -- no longer a standalone gate at `claim_task`. The
  assessment happens earlier, in [`/q`](../../plugins/crew/skills/q/SKILL.md), which places and values
  repo-scoped tasks per [R1](../workflows/graph-valuation.md#3-r1----placement-at-intake-q) under governing component or initiative epics with zero leaf `serves` edges (reserving `serves -> target` links for Strategic Value Carriers). Dispatch surfaces ([`/dispatch`](../../plugins/sara/skills/dispatch/SKILL.md)) trust that rather than re-judging the premise themselves. The crew reifies each task ([`/reify`](../../plugins/crew/skills/reify/SKILL.md)) just before dispatch; a polecat container has no plugins and no PKB access, and receives the reified instructions as its prompt.
- **Task-binding invariant** -- no mutating work without a task bound to the
  session via `claim_task`, never an environment variable naming the task.
  One session claims exactly one task, possibly multiple subtasks of it. In
  interactive sessions, for each new non-casual topic, strictly one outer task on the PKB graph is placed and claimed via `/q` by the internal sub-coordinator (`sub-Ida`) on behalf of the interactive session before substantial work begins (searching open and closed related tasks to resume, reopen, or mint the topic task); the user-facing coordinator strictly delegates and verifies, creating no tasks directly. Downstream workers and delegates below the sub-coordinator never create additional tasks on the graph. Pure lookups, PKB reads/writes, and questions answered in-turn require no task creation and no pull/dump ceremonies (`wf-lookup`). Only Face Ida runs the session handover `/dump`.
- **Consolidated feature-branch PR invariant** -- related work (tasks under a composite parent task, tasks touching overlapping surfaces, or open pull requests grouped in a sweep) gathers on a shared feature branch (`bundle/<slug>` or `feat/<slug>`) and reaches the maintainer as one consolidated pull request into `dev` ([`pr-lifecycle.md`](../workflows/pr-lifecycle.md)). Self-contained changes on constituent `polecat/<slug>` branches undergo the three-lens diff review (strategic fit, rule compliance, and quality) and, on `PASS`, are merged directly into the shared feature branch by the agent without waiting for user approval. Any superseded standalone donor pull request is closed immediately in the same step with a comment linking to the consolidated pull request. Pre-approval review on the consolidated pull request is a compliance description-only check (`wf-rbg`, "is this stupid?"), and the full three-lens combined-diff review runs after user approval and rebase against `dev`.
- **Claim at launch** -- a dispatch whose loss would matter beyond its own
  session has its claim written to the graph before the worker starts: who it
  went to, under which session and surface, and when. A worker in a session
  with the crew installed still calls `claim_task` from inside its session, and
  that is what moves the status; a polecat worker has no PKB access and never
  claims. The launch-time record exists so that a worker which died before ever
  claiming is legible as an unanswered dispatch rather than as work nobody
  picked up. **Cheap read-only probes and pure lookups are exempt** -- nothing is lost by running
  one again, so claiming for them buys graph noise instead of recoverability. Pure
  lookups, PKB reads/writes, and questions require no task creation and no pull or dump ceremony. A
  launch-time claim with no worker claim behind it is precisely the
  never-landed-dispatch signal Sara reviews, requeuing it to `ready`
  where warranted -- `/reconcile` no longer probes or resets claims.
- **Task naming invariant** -- task titles must be brief, descriptive, verb-led statements of a concrete thing to achieve (e.g. `Implement X`, `Verify Y`). A task title or filename never carries a person's name or persona prefix; assignment belongs exclusively in `assigned_to` / `assignee` frontmatter fields. See [`specs/meta/naming-and-decisions.md`](../meta/naming-and-decisions.md).
- **Decisions as graph relationships and groundwork-first decision making** -- un-actionable question tasks are prohibited. An agent given a task or high-value prompt does the groundwork first (settling unknowns from the PKB first, then live GitHub PRs/issues/releases and traces) and makes architectural or route decisions itself; it never leaves actionable agent steps in `inbox` or files a task back to the user without groundwork. Deliverables and releases that have already shipped and been communicated to the user are closed (`done`) without waiting to verify user-side installation; ready next agent steps are placed or promoted to `status: queued` via `/q` for dispatch; and only when agent groundwork and option evaluation are complete (with a reasoned recommendation written in the body) and the item genuinely waits on the user's own decision or host action is the task set to `status: review` (`assignee: user`) so it surfaces in the daily note's `## With you`. Design research tasks evaluate candidate alternatives and choose the recommended route directly to unblock downstream implementation. Tasks requiring review or follow-up are structured as a single task with internal subtasks or as a composite parent task (`type: task`) with child tasks, never as loose siblings under an external parent. Competing candidate options stay inside the body of the scoping task or ADR until chosen (retiring separate unchosen option nodes and `alternative` edges); when chosen, only the selected option is reified into an actionable task under `parent: <scoping_task_id>`. Missing information is modelled as an empirical probe task (`classification: probe`) wired to dependent tasks via standard execution prerequisite `needs: [<probe_task_id>]`. In-turn questions are put directly via `AskUserQuestion`.
- **Worker boundary invariant** -- a worker claimed on a task via `/pull` enriches its claimed task by assembling workflows via `/reify` in-session onto a single combined task body by default when needed, coordinates subagent fan-out and reviews with incremental `git push` checkpoints, and creates/wires repository-scoped follow-up tasks on the graph via `/q` (parented under the governing component or initiative epic with `needs` prerequisites and zero leaf `serves` edges) solely when work explicitly cannot be completed in-session (different repository, different time, or workflow-mandated separate external agent/session).
- **Task body brevity invariant** -- task bodies are strictly concise (50-150 words for atomic tasks at capture), structured around `Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, and `Pointers` ([`specs/meta/naming-and-decisions.md`](../meta/naming-and-decisions.md), [`plugins/crew/agents/pauli.md`](../../plugins/crew/agents/pauli.md)) and expanded by [`/reify`](../../plugins/crew/skills/reify/SKILL.md) into the dispatchable contract (`Ask`, `Goal`, `Context`, `Acceptance`, `Instructions`, `Output`, `Report`, `Appendix: Sources`). Extraneous narrative sections (`Background`, `References`, `Implementation Plan`) and prose task links are prohibited.
- **Graph edge economy invariant** -- setting `parent_id` is already an intrinsic graph edge; redundant wiring between descendants/siblings under the same parent without specific interactions is prohibited.
- **Outcome-oriented task contract invariant** -- task acceptance criteria and instructions define observable end-state conditions and verification criteria rather than implementation mechanisms. `Goal`, `Acceptance`, and `Instructions` must contain zero line numbers, line ranges, or narrow slice prescriptions. Under single-session execution (`/pull`), execution runs Stages 1-4 (design, subagent dialectical review, build, and PR verification) in one combined repo-scoped task body by default, keeping subagent reviews, incremental `git push` checkpoints, and PR verification inside the container session rather than requiring separate Stage 1 Design / Stage 2 Build / QA child tasks.
- **Brief and stage satisfiability invariant** -- task acceptance criteria, report requirements, and delegation briefs must be bounded strictly to artifacts and state produced by the assigned worker before release; agent responsibility ends when the release or deliverable is shipped and the user is informed (or a closed-loop delivery task is wired). Downstream pipeline outcomes (such as pull request URLs from subsequent workers, merged code branches, decisions delegated to future stages, or proof of the user's post-release acts such as installing, pulling, or deploying a shipped release) must never be demanded of early-stage workers, dispatchers, or planning agents.
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
  its ask id. A worker whose deliverable is a PR opens the PR as a draft (`gh pr create --draft`), releases its task `done` once the draft PR is open with branch and `pr_url` recorded and local tests verified, and exits; releasing `done` immediately unblocks dependent follow-ups (QA, review, deploy) on the task graph, and the PR goes ready for review (`gh pr ready`) only after the independent check passes; `partial` is reserved strictly for the worker's own unfinished acceptance items, never for waiting to prove the user installed, pulled, or deployed a shipped release. Only silent, undisclosed
  abandonment is garbage-collected (H10): incentive-first, this machinery is the
  backstop, not the mechanism agents are expected to lean on. Its floor is the
  task server predicate -- the contract is only as strong as that floor.
  The completion claim meets the [evidence contract](evidence-contract.md).
  Its required fields are checked for presence only, and only on tasks created
  after the check shipped.
