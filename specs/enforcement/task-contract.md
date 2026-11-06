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
any surface (polecat container, in-session subagent, agent team). Workers use
every harness feature they have, and with that comes the obligation to
demonstrate compliance and QA internally -- how is the worker's business. The
return contract: **evidence + an output URL, written to the shared task record.**
One deliverable per claimed task, never a spray of per-child PRs the principal
reviews individually. Task scope is one project/repo. Sync-wait versus
fire-and-forget is a dispatch-time cadence choice, not a contract difference.

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

### Canonical Task Status Table

The framework recognises exactly twelve (12) canonical task statuses. This table is the single source of truth for status definitions and authority across the framework.

| Status | Meaning | Who May Set It |
| :- | :- | :- |
| `inbox` | Untriaged intake capture; default initial state with unknown priority, scoping, and readiness. | PKB engine default on task creation (`create_task` / `/q`), or `/reconcile` (demoting stalled/invalidated tasks). |
| `ready` | Decomposed leaf task with all hard blockers (`depends_on`) resolved, ready for reification and dispatch. | PKB engine (computed graduation when leaf + no unmet blockers + AC), or human/planner at creation. |
| `queued` | Explicitly promoted and reified dispatch gate; bound to executor and workflow, awaiting immediate worker execution. | User (by requesting work or promoting via `/wf-dispatch-queue`), or `/reify` (Pauli) when binding a node next to run. Automated workers never set `queued` on un-asked work. |
| `in_progress` | Actively claimed and being executed in an active human or agent session. | Executing worker or agent via `pkb_claim_task` (or `update_task(status="in_progress")`). |
| `done` | Cleanly completed deliverable meeting all acceptance criteria with verifiable evidence (at worker level: PR filed; at epic/PR-tracking level: PR merged). | Executing worker on PR open / deliverable completion via `pkb_release_task` (`/dump`), or `/reconcile` on observed PR merge. |
| `partial` | Legitimately stopped at a scope seam, missing tool, external blocker, or context boundary before all ACs were met. | Executing worker via `pkb_release_task` (`/dump`), with required non-empty `reason` documenting unfinished items. |
| `failed` | Terminal failure or check failure (e.g. QA check or review lens rejected deliverable) that cannot be completed in this task. | Executing worker or QA/verifier via `pkb_release_task` (`/dump`), with required non-empty `reason` documenting failure evidence and root cause. |
| `cancelled` | Explicitly dropped, withdrawn, or superseded; will not be done. | User, or supervisor / `/reconcile` on verified obsolescence / user instruction ("drop X"), with required non-empty `reason`. |
| `review` | Manual human hold applied directly by the user for inspection, sign-off, or approval. | User only (`assignee: user`). Automated agents and workers are strictly prohibited from setting or releasing `review`. |
| `paused` | Intentionally suspended mid-flight with explicit intent to resume later. | User or interactive supervisor during session hold or interruption. |
| `someday` | Parked aspirational idea or backlog item; differs from `inbox` by explicit intentional deferral. | User or planner (`/strategize`). |
| `archived` | Non-actionable historical record or retired knowledge document retained in place, hidden from default search and hydration. | Knowledge base custodian (`pauli`) or `/reconcile` under the archive-vs-delete test. (Not used for active task workflows). |

#### Computed and Deprecated States (Not Stored Task Statuses)

- **`blocked`**: A computed graph condition (`is_blocked: true`), never a stored status. Expressed exclusively via `depends_on` edge to an uncompleted prerequisite task.
- **`merge_ready`**: Deprecated/invalid legacy token, not in use. Replaced by the release-as-done lifecycle.

#### Disambiguating `done` Semantics: Worker Deliverable vs Reconcile PR Merge

To permanently prevent ambiguity where a PR is open without merge and agents might question whether status should be `done` or `review`:

1. **Worker Implementation Tasks**: The worker's deliverable is the opening of the pull request, local test passing, and recording `pr_url` and branch on the task record. Under this contract, the worker releases `done` upon PR creation. This immediately satisfies `needs` dependencies on the graph, unblocking downstream QA and review tasks to run autonomously without waiting for human merge.
2. **PR-Tracking Tasks and Parent Epics**: Where a task or epic represents the landing of the PR into the target base branch, the deliverable is the merged commit. `/reconcile` monitors open PRs and transitions the tracking task or parent epic to `done` upon observing the merged PR on GitHub. Reconcile never reverts an open-PR worker task to `review`.

### Mechanisms

- **Premise judgment** -- no longer a standalone gate at `claim_task`. The
  assessment happens earlier, in [`/q`](../../plugins/ida/skills/q/SKILL.md) and [`/reify`](../../plugins/ida/skills/reify/SKILL.md): `/q` places and values the
  work per [R1](../workflows/graph-valuation.md#3-r1----placement-at-intake-q), and `/reify` composes the dispatchable task with its workflow, acceptance criteria, and QA follow-up. Dispatch surfaces ([`/pull`](../../plugins/ida/skills/pull/SKILL.md), [`/dispatch`](../../plugins/ida/skills/dispatch/SKILL.md)) trust that rather
  than re-judging the premise themselves.
- **Task-binding invariant** -- no mutating work without a task bound to the
  session via `claim_task`, never an environment variable naming the task.
  One session claims exactly one task, possibly multiple subtasks of it. This
  is a design invariant the framework holds agents to by convention and
  review, not a code-level blocking check today.
- **Claim at launch** -- a dispatch whose loss would matter beyond its own
  session has its claim written to the graph before the worker starts: who it
  went to, under which session and surface, and when. The worker's own
  `claim_task` still happens from inside its session and is what moves the
  status; the launch-time record exists so that a worker which died before ever
  claiming is legible as an unanswered dispatch rather than as work nobody
  picked up. **Cheap read-only probes are exempt** -- nothing is lost by running
  one again, so claiming for them buys graph noise instead of recoverability. A
  launch-time claim with no worker claim behind it is precisely the
  never-landed-dispatch signal Sara reviews, requeuing it to `ready`
  where warranted -- `/reconcile` no longer probes or resets claims.
- **Task naming invariant** -- task titles must be brief, descriptive, verb-led statements of a concrete thing to achieve (e.g. `Implement X`, `Verify Y`). A task title or filename never carries a person's name or persona prefix; assignment belongs exclusively in `assigned_to` / `assignee` frontmatter fields. See [`specs/meta/naming-and-decisions.md`](../meta/naming-and-decisions.md).
- **Decisions as graph relationships and design gates** -- un-actionable question tasks are prohibited. Design research tasks receive a dedicated decision task assigned to the user (`assignee: user`) to choose an implementation route before downstream implementation can unblock. Tasks requiring review or follow-up are structured as a single task with internal subtasks or as a dedicated epic with child tasks, never as loose siblings under an external parent. Open architectural choices or forks are separated into option nodes wired with `alternative` links to their decision node (with one-sided `depends_on` dependencies on waiting tasks, where choosing an option resolves the decision and cancels competing options) only where those branches are decomposed further; a task that has options to choose between with no commitment to doing anything immediately beyond choosing is created without subtasks or option nodes, keeping the choices and instructions on how to make the decision inside the task. Missing information is modelled as a probe task (`classification: probe`). In-turn questions are put directly via `AskUserQuestion`.
- **Task body brevity invariant** -- task bodies are strictly concise (50-150 words for atomic tasks at capture), structured around `Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, and `Pointers` ([`specs/meta/naming-and-decisions.md`](../meta/naming-and-decisions.md), [`plugins/ida/agents/pauli.md`](../../plugins/ida/agents/pauli.md)) and expanded by [`/reify`](../../plugins/ida/skills/reify/SKILL.md) into the dispatchable contract (`Ask`, `Goal`, `Context`, `Acceptance`, `Instructions`, `Output`, `Report`, `Appendix: Sources`). Extraneous narrative sections (`Background`, `References`, `Implementation Plan`) and prose task links are prohibited.
- **Graph edge economy invariant** -- setting `parent_id` is already an intrinsic graph edge; redundant wiring between descendants/siblings under the same parent without specific interactions is prohibited.
- **Outcome-oriented task contract invariant** -- task acceptance criteria and instructions define observable end-state conditions and verification criteria rather than implementation mechanisms. `Goal`, `Acceptance`, and `Instructions` must contain zero line numbers, line ranges, or narrow slice prescriptions. Reification of multi-file or architectural changes under `wf-code-task-base` preserves a distinct Stage 1 (Design) task preceding Stage 2 (Build).
- **Brief and stage satisfiability invariant** -- task acceptance criteria, report requirements, and delegation briefs must be bounded strictly to artifacts and state produced by the assigned worker before release. Downstream pipeline outcomes (such as pull request URLs from subsequent workers, merged code branches, or decisions delegated to future stages) must never be demanded of early-stage workers, dispatchers, or planning agents.
- **Full-context file inspection invariant** -- workers must read target repository files in full before executing edits. Keyhole line-slice reads (`read_file` with narrow line windows around advisory line hints) in isolation without prior whole-file context are strictly prohibited; advisory line hints are starting pointers only. Files exceeding single-page tool limits are inspected via sequential discovery before editing.
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
  its ask id. A worker whose deliverable is a PR releases its task `done` once the PR is open with branch and `pr_url` recorded, local tests verified, and exits; releasing `done` immediately unblocks dependent follow-ups (QA, deploy) on the task graph; `partial` is reserved strictly for the worker's own unfinished acceptance items. Only silent, undisclosed
  abandonment is garbage-collected (H10): incentive-first, this machinery is the
  backstop, not the mechanism agents are expected to lean on. Its floor is the
  task server predicate -- the contract is only as strong as that floor.
  The completion claim meets the [evidence contract](evidence-contract.md).
  Its required fields are checked for presence only, and only on tasks created
  after the check shipped.
