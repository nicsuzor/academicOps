---
id: release-as-done-lifecycle
title: Release-as-Done Task Lifecycle and Retirement of Agent Review Status
status: ready
type: spec
tags: [enforcement, lifecycle, task-contract, workflow, dispatch, reconcile]
---

# Release-as-Done Task Lifecycle and Retirement of Agent Review Status

This specification establishes the architectural standard and structural lifecycle rules for task completion across the framework:

1. **Worker Release-as-Done Rule:** Every worker completing its assigned deliverable (including pull request deliverables) releases its task as `status: done` upon verifying local checks, pushing the branch, opening the PR, and recording deliverable evidence. Automated agents and workers are strictly forbidden from releasing tasks as `review`.
2. **Autonomous Dispatch QA-Gating Invariant:** Dependent QA and review tasks wire a hard `needs` dependency on the implementation task. Because the implementation task releases as `done`, graph dependencies unblock immediately, allowing `/dispatch` to launch independent review and verification workers without human intervention or execution deadlocks.
3. **Reconcile Active Review Transition & Legacy Sweep:** When `/reconcile` processes an agent task sitting in `status: review`, it transitions the task to `done` whenever a review or QA task covers it, or if its pull request deliverable is in place; it evaluates remaining cases against concrete evidence, and sweeps legacy tasks at `review` to unblock trapped graph dependencies. Tasks placed in `review` directly by the user are respected as manual holds and left untouched.
4. **Scope of the `review` Status:** `review` is retained in the underlying taxonomy solely as a manual parking state for the human principal ("the user"). No agent instruction, template, or automated worker is permitted to set or release tasks into `review`.

## 1. User Stories

### US-1: Autonomous Task Handoff Without Graph Deadlocks

As an execution coordinator and dispatch supervisor, I want workers delivering completed pull requests to release their tasks as `done`, so that downstream QA and verification tasks unblock autonomously on the dependency graph.

- **AC-1.1**: Given a worker executing a task whose deliverable is a pull request, when the worker pushes the branch, opens the PR, verifies local tests pass, and updates acceptance evidence, then the worker releases the task as `status: done` with `pr_url` and branch recorded on the task record.
- **AC-1.2**: Given an implementation task with a downstream `QA: <title>` child task wired with `needs: [<implementation_task_id>]`, when the implementation worker releases `done`, then the dependency is satisfied in the graph engine and the QA task transitions from blocked to ready (`ready: true`, `status: queued`).
- **AC-1.3**: Given an automated worker completing a task via `/ida:pull`, when it releases the task, then it releases `status: done` (or `status: partial` if incomplete) and never releases `status: review`.

### US-2: Automated Dispatch of Unblocked Review Tasks

As the `/dispatch` engine, I want clear readiness criteria based on upstream `done` states, so that queued QA workers are dispatched immediately upon upstream deliverable completion.

- **AC-2.1**: Given a queued QA task whose prerequisite implementation task has released as `done`, when `/dispatch` evaluates candidate tasks, then it identifies the QA task as fully unblocked and ready for immediate dispatch.
- **AC-2.2**: Given a completion event from a primary worker (`[polecat-exit] status=done`), when `/dispatch` processes the event, then it immediately checks downstream dependents whose `needs` edges are satisfied and dispatches eligible ready tasks.

### US-3: Truth Maintenance Over Tasks in Review

As the `/reconcile` truth maintenance pass, I want clear deterministic rules for resolving tasks sitting in `review`, so that tasks covered by review workflows or finished PRs transition to `done` and legacy tasks are cleared from the graph.

- **AC-3.1**: Given an agent task currently in `status: review` that is covered by an active or completed review or QA task (where a review task carries `needs` or `depends_on` pointing to the task), when `/reconcile` evaluates the task, then it immediately mutates its status to `done`, resolving blocking edges for dependent tasks.
- **AC-3.2**: Given an agent task currently in `status: review` where no review or QA task covers it, but a valid open pull request is recorded on the task, when `/reconcile` evaluates the task, then it mutates the task status to `done` and, if the PR risk tier warrants independent review, mints/queues a `QA: <title>` follow-up task with `needs: [<task_id>]`.
- **AC-3.3**: Given an agent task currently in `status: review` with no pull request and no covering review task, when `/reconcile` evaluates the task, then it verifies recorded evidence: if all acceptance criteria are met with verifiable evidence, it mutates status to `done`; if incomplete agent work remains, it transitions to `queued` (or `partial`); if a principal decision is required, it sets `partial` with the decision in `reason` and escalates to the daily note `## With you`.
- **AC-3.4**: Given tasks currently sitting in `status: review` on the graph, when `/reconcile` runs its sweep, then all qualifying agent tasks are updated to `done`, eliminating false dependency blocks across active projects.
- **AC-3.5**: Given a task explicitly held in `status: review` by the user (`assignee: user`), when `/reconcile` evaluates the task, then it preserves the user's manual hold and does not mutate the status.

### US-4: Definite Status Vocabulary Boundary

As a framework architect and reviewer, I want the status taxonomy to clearly delimit the semantics of `review`, so that agents never conflate automated verification with human holding states.

- **AC-4.1**: Given the status taxonomy in `tests/policy.toml`, when schema validation checks `valid_statuses`, then `review` is present in the 12-value set for database backwards compatibility.
- **AC-4.2**: Given a task on the graph, when an agent or the user sets `status: review`, then `status: review` is accepted only if set directly by the user (`assignee: user`), and is rejected for automated agent releases.
- **AC-4.3**: Given all framework skills, workflow templates, agent personas, and project rules, when searched for release instructions, then zero instructions tell automated agents to release `status: review`.

## 2. Root Cause & Architectural Rationale

### The Graph Dependency Deadlock

In the personal knowledge base (PKB) and task graph architecture, task dependencies are modeled as directed edges (`needs: [<upstream_id>]` or `depends_on: [<upstream_id>]`). The graph query engine evaluates whether a dependency is satisfied using an exact condition: **an upstream task only unblocks downstream dependents when its status is `done`**.

Under prior instructions:

1. `plugins/ida/skills/pull/SKILL.md` instructed: _"A worker whose deliverable is a PR releases `review` once the PR is open... and exits without waiting for CI, review or merge: the repository merges it, and `/reconcile` writes `done` on the merge"_.
2. Universal finish template `wf-finish.md` instructed: _"Release the task as `review` via `pkb.release_task`, with the PR URL in `pr_url`"_.
3. Universal quick-fix template `wf-quick-fix.md` instructed: _"Release the task: ... As standard handoff status (e.g. `review`)..."_.
4. At the same time, `/reify` minted downstream QA follow-up tasks with `needs: [<primary_task_id>]`.
5. `/dispatch` instructed: _"A QA follow-up stays queued until its hard dependency completes; it is not ready yet"_.

This created a **structural deadlock**:

- The primary worker created the PR, satisfied all its acceptance criteria, and released as `review`.
- Because the status was `review` (not `done`), the PKB graph engine evaluated the QA task's `needs` dependency as **unsatisfied**.
- The QA task remained `blocked`.
- `/dispatch` saw the QA task was blocked and refused to dispatch a worker for it.
- Because no QA worker was dispatched, the PR was never verified or merged.
- Because the PR was never merged, `/reconcile` never observed a merge to transition the primary task to `done`.
- The task sat in `review` permanently, and the QA task sat blocked permanently.

### Principal Determination and Architectural Resolution

The framework principal determined the unified operating rule:
Workers must release finished deliverables as `done`. Automated agents are never told to use `review`. `/reconcile` transitions tasks in `review` to `done` when a review task or PR deliverable covers them.

The resolution:

1. Workers release finished deliverables as `done`. For pull request deliverables, creating the PR, pushing the branch, verifying local tests, and recording verifiable citations on the task fulfills the implementation task's contract.
2. Releasing as `done` immediately satisfies `needs: [<primary_task_id>]` on the graph.
3. The dependent QA task immediately transitions to ready and is picked up autonomously by `/dispatch`.
4. The parent epic remains open until all children (implementation, review, merge) are complete, preserving overall epic-level integrity without deadlocking task-level graph dependencies.

## 3. Comprehensive Target File Audit (AC1)

Every file across skills, workflow templates, agent personas, rules, and specifications that instructs a worker, reviewer, or reconciler which status to release or write is audited below, with exact `file:line` citations, current text, and proposed text.

### 3.1 `plugins/ida/skills/pull/SKILL.md`

- **Line 32:**
  - **Current Text:**
    ```markdown
    Release as `done` or `partial` by default. A worker whose deliverable is a PR releases `review` once the PR is open, with `pr_url` on the record, and exits without waiting for CI, review or merge: the repository merges it, and `/reconcile` writes `done` on the merge, which unblocks dependent work. `partial` is only for the worker's own unfinished acceptance items. Never send a complete deliverable to `partial` because of a dependent check or follow-up.
    ```
  - **Proposed Text:**
    ```markdown
    Release as `done` or `partial` by default. A worker whose deliverable is a PR releases `done` once the PR is open, with `pr_url` and branch recorded on the record, and exits without waiting for CI, review or merge: releasing `done` immediately unblocks dependent QA and review follow-up tasks on the graph. `partial` is reserved strictly for the worker's own unfinished acceptance items. Never release as `review` or send a complete deliverable to `partial` because of a dependent check or follow-up.
    ```

- **Line 36:**
  - **Current Text:**
    ```markdown
    Apart from an open PR awaiting merge, `review` means a worker needs help to finish the task. It is transient, never a waiting state for decisions. Release as `review` only when the worker cannot finish without help from a higher level, recording what help is needed on the record in `reason`. A worker hands back on the record and never addresses or escalates to the user. Any reconcile pass reading a `review` task transitions it immediately.
    ```
  - **Proposed Text:**
    ```markdown
    Never release as `review`. If a worker's own deliverable is incomplete due to an external blocker, missing tool, or scope seam, release as `partial` naming unfinished items and missing evidence in `reason`. When an approval boundary or decision point is reached, file the complete artifact on the record and release as `partial` documenting what decision is needed; never release as `review`.
    ```

- **Line 40:**
  - **Current Text:**
    ```markdown
    Invoke `/dump` at the end of every job, whatever its release status (`done`, `partial`, `review`, `failed`, `cancelled`, or `in_progress`).
    ```
  - **Proposed Text:**
    ```markdown
    Invoke `/dump` at the end of every job, whatever its release status (`done`, `partial`, `failed`, `cancelled`, or `in_progress`).
    ```

### 3.2 `plugins/ida/skills/dump/SKILL.md`

- **Line 23:**
  - **Current Text:**
    ```markdown
    - `done`: All acceptance criteria are fully met with verified evidence recorded in the task's Report section: quoted output, `file:line` citations, counts, the specimen run where requested, and the report argument answering each `<task id>/AC<n>` from that evidence. A worker whose deliverable is a PR releases `review` instead (below). An empty, template, or bare-assertion report is released as `partial`.
    ```
  - **Proposed Text:**
    ```markdown
    - `done`: All acceptance criteria are fully met with verified evidence recorded in the task's Report section: quoted output, `file:line` citations, counts, the specimen run where requested, and the report argument answering each `<task id>/AC<n>` from that evidence. When the deliverable is a PR, the worker pushes the branch, opens the PR, records `pr_url` and branch, and releases `done`. An empty, template, or bare-assertion report is released as `partial`.
    ```

- **Line 25:**
  - **Current Text:**
    ```markdown
    - `review`: Either the worker's PR is open and awaits merge by the repository (record `pr_url`; do not wait for CI, review or merge; the reconcile pass writes `done` on the merge), or the worker needs help to finish the task. Help is transient, never a waiting state: a worker hands back on the record, documenting what help is needed in `reason`, and never addresses or escalates to the user. Any reconcile pass reading a `review` task transitions it immediately.
    ```
  - **Proposed Text:**
    ```markdown
    - `review`: Reserved exclusively for manual human holds applied directly by the user. Workers and automated sessions never set or release `review`. If work requires an escalated decision or has incomplete items, release `partial` with documented reason.
    ```

- **Line 58:**
  - **Current Text:**
    ```markdown
    - STATUS: <release status: done | partial | review | failed | cancelled | in_progress>
    ```
  - **Proposed Text:**
    ```markdown
    - STATUS: <release status: done | partial | failed | cancelled | in_progress>
    ```

### 3.3 `plugins/ida/skills/dispatch/SKILL.md`

- **Line 18:**
  - **Current Text:**
    ```markdown
    - A QA follow-up stays queued until its hard dependency completes; it is not ready yet.
    ```
  - **Proposed Text:**
    ```markdown
    - A QA follow-up stays queued until its primary task releases `done`; once the primary task releases `done`, the QA follow-up's `needs` dependency is satisfied and it becomes ready for immediate dispatch.
    ```

- **Line 33:**
  - **Current Text:**
    ```markdown
    `[polecat-exit] task=<task-id> container=<container-name> exit_code=<code|0> status=<review|done|partial|failed> pr_url=<url> duration=<seconds>s`
    ```
  - **Proposed Text:**
    ```markdown
    `[polecat-exit] task=<task-id> container=<container-name> exit_code=<code|0> status=<done|partial|failed> pr_url=<url> duration=<seconds>s`
    ```

- **Line 39:**
  - **Current Text:**
    ```markdown
    - **Review or Done (`status=review` or `status=done`, `exit_code=0`)**: The worker delivered. Trigger `/verify` on the deliverable or `/reconcile` to process the PR and update task state. Read downstream tasks on the graph whose `needs` dependencies are now satisfied, and dispatch any that are ready.
    ```
  - **Proposed Text:**
    ```markdown
    - **Done (`status=done`, `exit_code=0`)**: The worker delivered. Read downstream tasks on the graph (e.g. QA follow-up or review task) whose `needs` dependencies are now satisfied, and dispatch any that are ready. Trigger `/verify` on the deliverable or `/reconcile` as needed.
    ```

### 3.4 `plugins/ida/skills/workflow-library/workflows/wf-finish.md`

- **Lines 25–27:**
  - **Current Text:**
    ```markdown
    - **Tier 2 (Operational Gate)**: Code, workflows, tools, skills, rules, agent definitions, or tests. Reviewer sign-off required; a fresh QA worker independently verifies claims, runs tests, and posts receipts to the PR as a structured review comment. The QA worker does not merge, leaving the PR open for reviewer sign-off. The QA task is released as `done` with the PR URL recorded on the task record so `/reconcile` tracks merge without human wait states. No task rests or releases in `review` for a human merge gate.
    - **Tier 3 (Critical Hazard & Public Gate)**: Host infrastructure, credentials, manuscripts, public releases, or high blast radius. Gated on principal review and merge; agents are forbidden from merging. QA workers independently verify and post receipts, leaving the PR open, and release the QA task as `done`.
    - **Merge**: For verified Tier 1 PRs, QA worker merges upon verified pass. For Tier 2 and Tier 3 PRs, reviewer sign-off merges the PR; QA worker verifies, posts receipts, and leaves the PR open. `/reconcile` writes `done` when the PR merges, which unblocks dependent work.
    ```
  - **Proposed Text:**
    ```markdown
    - **Tier 2 (Operational Gate)**: Code, workflows, tools, skills, rules, agent definitions, or tests. Reviewer sign-off required; a fresh QA worker independently verifies claims, runs tests, and posts receipts to the PR as a structured review comment. The QA worker does not merge, leaving the PR open for reviewer sign-off. The QA task is released as `done` with the PR URL recorded on the task record so `/reconcile` tracks merge without human wait states. No task rests or releases in `review` for a human merge gate.
    - **Tier 3 (Critical Hazard & Public Gate)**: Host infrastructure, credentials, manuscripts, public releases, or high blast radius. Gated on principal review and merge; agents are forbidden from merging. QA workers independently verify and post receipts, leaving the PR open, and release the QA task as `done`.
    - **Merge**: For verified Tier 1 PRs, QA worker merges upon verified pass. For Tier 2 and Tier 3 PRs, reviewer sign-off merges the PR; QA worker verifies, posts receipts, and leaves the PR open. The primary implementation task releases `done` upon PR filing to unblock QA; when the PR merges, the parent epic progresses.
    ```

- **Line 41:**
  - **Current Text:**
    ```markdown
    4. Release the task as `review` via `pkb.release_task`, with the PR URL in `pr_url` and `reason` stating the PR awaits merge. Do not wait for CI, review or merge. `partial` is only for the worker's own unfinished acceptance items. Workers never create or name follow-up tasks.
    ```
  - **Proposed Text:**
    ```markdown
    4. Release the task as `done` via `pkb_release_task`, with the PR URL in `pr_url` and branch recorded on the task record. Do not release as `review`. Releasing `done` unblocks the downstream QA or review follow-up task on the graph. Do not wait for CI, review or merge. `partial` is reserved strictly for the worker's own unfinished acceptance items. Workers never create or name follow-up tasks.
    ```

### 3.5 `plugins/ida/skills/workflow-library/workflows/wf-quick-fix.md`

- **Line 55:**
  - **Current Text:**
    ```markdown
    - As standard handoff status (e.g. `review`) if fallback to the standard delivery process was triggered prior to delivery.
    ```
  - **Proposed Text:**
    ```markdown
    - As standard handoff status (e.g. `partial` if blocked, or `done` if delivered via standard PR) if fallback to the standard delivery process was triggered prior to delivery. Never release as `review`.
    ```

### 3.6 `plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md`

- **Line 21:**
  - **Current Text:**
    ```markdown
    3. **Push and file the PR** -- push the branch and open a pull request against the base branch, its description mapping each acceptance criterion to the evidence that meets it: a test, a command's output, a fresh agent's run, or a commit. Record the PR URL on the task and release it as `done`.
    ```
  - **Proposed Text:**
    ```markdown
    3. **Push and file the PR** -- push the branch and open a pull request against the base branch, its description mapping each acceptance criterion to the evidence that meets it: a test, a command's output, a fresh agent's run, or a commit. Record the PR URL and branch on the task and release it as `done`. Releasing `done` satisfies the dependency for Stage 4 (Review and verdict).
    ```

- **Line 40:**
  - **Current Text:**
    ```markdown
    or a merge recommendation posted with the review task released as `merge_ready`. Workers never file fix follow-up tasks.
    ```
  - **Proposed Text:**
    ```markdown
    or a merge recommendation posted with the review task released as `done`. Workers never file fix follow-up tasks.
    ```

### 3.7 `plugins/ida/skills/workflow-library/workflows/wf-doc-base.md`

- **Line 19:**
  - **Current Text:**
    ```markdown
    or **mergeable** (clean review, no reviewer changes, checks green: post a merge recommendation and release as `merge_ready`). Do not merge.
    ```
  - **Proposed Text:**
    ```markdown
    or **mergeable** (clean review, no reviewer changes, checks green: post a merge recommendation and release as `done`). Do not merge.
    ```

### 3.8 `plugins/ida/skills/workflow-library/workflows/wf-reconcile.md`

- **Line 2:**
  - **Current Text:**
    ```yaml
    description: Truth maintenance over the task graph -- reconcile merged PRs, move review tasks to reality under the bazaar model, handle failed tasks by deciding next actions from the parent epic, write items reaching the user to today's daily note, record world-fact cancellations, and demote affected tasks to inbox.
    ```
  - **Proposed Text:**
    ```yaml
    description: Truth maintenance over the task graph -- reconcile merged PRs, transition tasks in review to done when covered by review tasks or open PRs, handle failed tasks by deciding next actions from the parent epic, write items reaching the user to today's daily note, record world-fact cancellations, and demote affected tasks to inbox.
    ```

- **Lines 21–27:**
  - **Current Text:**
    ```markdown
    - **Open PRs**: Read review and check state with `gh pr view <n> --repo <owner/repo> --json state,isDraft,mergedAt,reviewDecision,statusCheckRollup`. `reviewDecision: CHANGES_REQUESTED` or a failing check in `statusCheckRollup` routes the task to `queued` or a follow-up task, never `done` or `review`. Otherwise, a `review` task whose PR is still open is waiting on the repository to merge it; leave it until the PR merges or closes.

    3. **The Review Lifecycle**: Apart from a task waiting on its open PR (step 2), `review` means a worker needs help to finish the task; it is transient, never a waiting state. Under the bazaar model, any pass reading a `review` task owns the outcome in that pass and mints any needed tasks; nothing is deferred to a later sweep or the original dispatcher. Bring the record to reality and take exactly one outcome:
       - `ready` or `queued`: not finished properly, an agent can finish it.
       - `partial` plus a new review task queued for an agent, wired so the source cannot complete before it (source `depends_on` it). Dispatch or queue the review task so it does not sit idle.
       - `done` plus a clean split of partly-finished work (sequencing handled by the epic).
       - `failed`: terminal failure with documented root cause.
         Nothing is left in `review`.
    ```
  - **Proposed Text:**
    ```markdown
    - **Open PRs**: Read review and check state with `gh pr view <n> --repo <owner/repo> --json state,isDraft,mergedAt,reviewDecision,statusCheckRollup`. `reviewDecision: CHANGES_REQUESTED` or a failing check in `statusCheckRollup` routes the task to `queued` or a follow-up task, never `done` or `review`.

    3. **Reconciling Tasks in Review**: Agents never release tasks into `review`. Tasks explicitly held in `review` by the user (`assignee: user`) represent manual inspection holds and are left untouched. For all other tasks in `status: review`:
       - **Covered by a review or QA task**: If an active review or QA task points to the task via graph dependency edges (`needs` or `depends_on` contains the task ID), mutate the task status immediately to `done`. This unblocks dependent tasks on the graph.
       - **Uncovered with an open PR**: If no review or QA task covers the task, but an open pull request is recorded on the task, mutate the task status to `done` and, if the PR risk tier warrants verification, mint/queue a `QA: <title>` follow-up task with `needs: [<task_id>]`.
       - **Uncovered without a PR**: If the task has no PR and no covering review task, verify recorded evidence against acceptance criteria:
         - If criteria are fully satisfied with verifiable evidence: mutate status to `done`.
         - If incomplete agent work remains: transition to `queued` (or `partial` if partly delivered).
         - If principal input is required: transition to `partial` (recording the question in `reason`) and escalate to today's daily note `## With you`.
           No agent task is left in `review`.
    ```

- **Line 56:**
  - **Current Text:**
    ```markdown
    - Must not write `done` on any evidence other than an observed merged PR or a clean finished part of a split task.
    ```
  - **Proposed Text:**
    ```markdown
    - Must not write `done` on any evidence other than an observed merged PR, a clean finished part of a split task, or an agent task in `review` covered by a review/QA task, open PR, or complete verifiable evidence.
    ```

- **Line 57:**
  - **Current Text:**
    ```markdown
    - Must not leave tasks in `review` or route tasks to `review` as a waiting state, except a task whose open PR awaits merge.
    ```
  - **Proposed Text:**
    ```markdown
    - Must not leave agent tasks in `review` or route tasks to `review`; all agent tasks found in `review` must be transitioned immediately.
    ```

### 3.9 `.agents/rules/headless-workers.md`

- **Line 3 (Frontmatter Description):**
  - **Current Text:**
    ```yaml
    description: Headless workers cannot pause interactively or escalate to the user; approval boundaries file artifacts on the record, and review is transient help rather than a decision wait state.
    ```
  - **Proposed Text:**
    ```yaml
    description: Headless workers cannot pause interactively or escalate to the user; approval boundaries file artifacts on the record, and agents are never told to release review.
    ```

- **Lines 11–12:**
  - **Current Text:**
    ```markdown
    - Workers never create or name follow-up tasks, and reports carry no 'Next task' pointer. A worker whose check fails (e.g. QA or review) releases its task as `failed`. When an approval boundary or decision point is reached, the worker files the complete artifact on the record and does not release the task as `done` when dependent implementation work requires an explicit approval decision; it releases on the record (e.g. `partial` or `review` documenting what decision or help is needed in `reason`), without minting follow-up tasks. Sequencing, remediation, and downstream work live in the parent epic and are decided during the reconcile pass.
    - `review` means a worker needs help to finish the task; it is transient and never a waiting state for decisions. If a worker needs help from a higher level, it releases as `review` documenting what help is needed on the record. Any reconcile pass reading a `review` task transitions it immediately.
    ```
  - **Proposed Text:**
    ```markdown
    - Workers never create or name follow-up tasks, and reports carry no 'Next task' pointer. A worker whose check fails (e.g. QA or review) releases its task as `failed`. When an approval boundary or decision point is reached, the worker files the complete artifact on the record and does not release the task as `done` when dependent implementation work requires an explicit approval decision; it releases on the record as `partial` documenting what decision or help is needed in `reason`, without minting follow-up tasks. Sequencing, remediation, and downstream work live in the parent epic and are decided during the reconcile pass.
    - Workers are never told to use or release `review`. If a worker cannot complete work without higher-level help, it releases as `partial` documenting the required assistance in `reason`. Any reconcile pass reading an agent task in `review` transitions it immediately.
    ```

### 3.10 `plugins/ida/agents/sara.md`

- **Line 49:**
  - **Current Text:**
    ```markdown
    - Workers set `in_progress` on claim and `done`, `partial`, or `review` (an open PR awaiting merge, or transient when needing help) on release; learn of completions from polecat-mcp's completion events (`[polecat-exit]`) rather than polling or timers, and never write worker statuses directly.
    ```
  - **Proposed Text:**
    ```markdown
    - Workers set `in_progress` on claim and `done`, `partial`, or `failed` on release; learn of completions from polecat-mcp's completion events (`[polecat-exit]`) rather than polling or timers, and never write worker statuses directly.
    ```

- **Line 50:**
  - **Current Text:**
    ```markdown
    - Run `/reconcile` to audit completion claims, write `done` when a PR merges, transition help `review` tasks immediately, and set read tasks to the status their evidence supports (never reconcile your own work or demand receipts for user closures; remedied failures move to `done`).
    ```
  - **Proposed Text:**
    ```markdown
    - Run `/reconcile` to audit completion claims, write `done` when a PR merges, transition any agent tasks found in `review` to `done` (or `partial`), and set read tasks to the status their evidence supports (never reconcile your own work or demand receipts for user closures; remedied failures move to `done`).
    ```

- **Line 91:**
  - **Current Text:**
    ```markdown
    ├→ review (transient: worker needs help; moved on by reconcile)
    ```
  - **Proposed Text:**
    ```markdown
    ├→ [review retired from worker release; manual human hold only]
    ```

### 3.11 `plugins/ida/skills/verify/SKILL.md`

- **Line 73:**
  - **Current Text:**
    ```markdown
    - STATUS: <release status: done | partial | review | failed | cancelled | in_progress>
    ```
  - **Proposed Text:**
    ```markdown
    - STATUS: <release status: done | partial | failed | cancelled | in_progress>
    ```

### 3.12 `specs/enforcement/task-contract.md`

- **Lines 83–87:**
  - **Current Text:**
    ```markdown
    A worker whose deliverable is a PR releases its task `review` once the PR is open and exits; the repository merges it and `/reconcile` writes `done` on the merge, which unblocks dependent follow-ups (QA, deploy); `partial` is reserved strictly for the worker's own unfinished acceptance items.
    ```
  - **Proposed Text:**
    ```markdown
    A worker whose deliverable is a PR releases its task `done` once the PR is open with branch and `pr_url` recorded, local tests verified, and exits; releasing `done` immediately unblocks dependent follow-ups (QA, deploy) on the task graph; `partial` is reserved strictly for the worker's own unfinished acceptance items.
    ```

### 3.13 `specs/enforcement/workflow.md`

- **Line 35:**
  - **Current Text:**
    ```markdown
    When a task's deliverable is a pull request, the worker opens the PR, records `pr_url`, and releases the task as `review` without waiting for CI or merge; when the repository merges the PR, `/reconcile` transitions the task to `done`, unblocking dependent follow-ups.
    ```
  - **Proposed Text:**
    ```markdown
    When a task's deliverable is a pull request, the worker opens the PR, records `pr_url` and branch, and releases the task as `done` without waiting for CI or merge; releasing `done` immediately unblocks dependent follow-ups (such as independent QA tasks); when the repository merges the PR, the parent epic progresses.
    ```

- **Line 78:**
  - **Current Text:**
    ```markdown
    In all non-PR tasks, worker self-release to `done` remains standard upon fulfilling the frozen acceptance criteria; workers are not held in `review` awaiting a downstream gate.
    ```
  - **Proposed Text:**
    ```markdown
    Across all tasks (both PR and non-PR tasks), worker self-release to `done` is standard upon fulfilling the frozen acceptance criteria; workers are never held in `review` awaiting a downstream gate.
    ```

### 3.14 `specs/enforcement/enforcement.md`

- **Lines 143, 146, 152:**
  - **Current Text:**
    ```markdown
    Under headless worker and review lifecycle rules, QA tasks complete as `done` with the PR URL recorded on the task record so that `/reconcile` tracks merge without human wait states; no task rests or releases into `review` for human merge gates.
    Worker self-release to `done` is preserved across all non-PR tasks: when a worker satisfies all frozen acceptance criteria with concrete verifiable evidence recorded in its handback report, it releases the task directly to `done`. Non-PR workers are not forced into `review` awaiting external verification.
    ```
  - **Proposed Text:**
    ```markdown
    Under headless worker and review lifecycle rules, both implementation workers and QA workers complete as `done` with the PR URL recorded on the task record so that `/dispatch` unblocks QA immediately and `/reconcile` tracks merge without human wait states; no task rests or releases into `review` for human merge gates.
    Worker self-release to `done` applies across all tasks (PR and non-PR): when a worker satisfies all frozen acceptance criteria with concrete verifiable evidence recorded in its handback report, it releases the task directly to `done`. Workers are never forced into `review` awaiting external verification.
    ```

### 3.15 `specs/workflows/reconcile.md`

- **Lines 22–30:**
  - **Current Text:**
    ```markdown
    | Gap | State |
    | - | - |
    | GH issue closed via `Closes #N` → PKB task carrying `gates_on` for it | Not built -- forward-issue leg, below |
    | Closed-not-merged PR that was legitimately superseded | Built |
    | Failed tasks from workers (e.g. QA or review failures) → next actions decided from parent epic | Built |
    | Multi-part task / verbatim note request partially resolved by merged PR → itemize completed vs incomplete elements | Built |
    | Manual `gh issue close` with `state_reason: not_planned` or `duplicate` | Not built -- forward-issue leg, below |
    | PKB task done → GH issue comment/close beyond the native `Closes #N` commit convention | Not built -- reverse direction, M3 |
    ```
  - **Proposed Text:**
    ```markdown
    | Gap | State |
    | - | - |
    | GH issue closed via `Closes #N` → PKB task carrying `gates_on` for it | Not built -- forward-issue leg, below |
    | Closed-not-merged PR that was legitimately superseded | Built |
    | Failed tasks from workers (e.g. QA or review failures) → next actions decided from parent epic | Built |
    | Multi-part task / verbatim note request partially resolved by merged PR → itemize completed vs incomplete elements | Built |
    | Task in `review` covered by a review/QA task, open PR, or complete evidence | Built -- transitioned to `done` |
    | Manual `gh issue close` with `state_reason: not_planned` or `duplicate` | Not built -- forward-issue leg, below |
    | PKB task done → GH issue comment/close beyond the native `Closes #N` commit convention | Not built -- reverse direction, M3 |
    ```

### 3.16 `specs/ENFORCEMENT-MAP.md`

- **Line 69:**
  - **Current Text:**
    ```markdown
    | [Non-PR QA Child Rule](enforcement/workflow.md#risk-scaled-review-depth) -- `/reify` mints a separate `QA: <task>` child for non-PR tasks only where the composed workflow warrants an independent verification check; worker self-release to `done` is preserved across all non-PR tasks. | instructions, process | imperative, required gate | `specs/enforcement/workflow.md:77`, `specs/agents/reify.md:47-51`, `specs/enforcement/enforcement.md#non-pr-task-verification-and-lifecycle`: Mints separate QA child task only when the workflow warrants another check (e.g. replication, qualitative audits, high-impact specs); straightforward non-PR workflows mint no QA child; workers self-release to `done` upon meeting frozen acceptance criteria without being held in `review`. Observation: Workflow composition at reification mints independent QA tasks for empirical and high-impact non-PR workflows while preserving worker self-release to done on standard tasks without review deadlocks. |
    ```
  - **Proposed Text:**
    ```markdown
    | [Release-as-Done & QA Autonomous Unblocking](enforcement/release-as-done-lifecycle.md) -- Workers release finished deliverables (including PRs) as `done`; agents are forbidden from releasing `review`; dependent QA tasks unblock autonomously upon upstream `done`. | instructions, structural, process | imperative, required gate | `plugins/ida/skills/pull/SKILL.md:32`, `dump/SKILL.md:23`, `dispatch/SKILL.md:18,39`, `wf-finish.md:41`, `wf-code-task-base.md:21`, `.agents/rules/headless-workers.md:11-12`: Mandates release as `done` upon deliverable existence, PR creation, and passing local checks; forbids agent release to `review`; downstream QA tasks unblock on `needs` when upstream is `done`; `/reconcile` transitions legacy `review` tasks covered by review/QA tasks to `done`. |
    ```

## 4. /dispatch QA-Gating Rule Specification (AC2)

### The Operative Gating Rule

> **QA-Gating Invariant:**
> A downstream QA or verification follow-up task (`QA: <primary task title>`) connects to its primary implementation task via a hard `needs` dependency edge (`needs: [<primary_task_id>]`).
> The PKB graph query engine evaluates this dependency strictly against completion: the dependency is satisfied **if and only if the primary task status is `status: done`**.
> Once the primary worker pushes the branch, opens the pull request, verifies local checks, and releases the task as `done`, the dependency is satisfied immediately.
> The QA follow-up transitions from blocked to ready (`status: queued`, `ready: true`) and becomes immediately eligible for dispatch.

### Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    participant D as /dispatch
    participant W as Primary Worker
    participant G as PKB Task Graph
    participant Q as QA Worker

    Note over D,G: Primary Task is queued; QA Task has needs: [Primary] (blocked)
    D->>W: Launch Primary Worker (/ida:pull <primary-id>)
    W->>G: claim_task -> status: in_progress
    W->>W: Implement code, pass tests, push branch, open PR
    W->>G: release_task(status: done, pr_url, branch, evidence)
    Note over G: Primary Task is DONE.<br/>needs edge for QA Task is SATISFIED.<br/>QA Task becomes ready: true!
    W->>D: polecat-exit (status=done)
    D->>G: Query ready tasks whose dependencies are satisfied
    G-->>D: Returns QA Task (ready: true)
    D->>Q: Launch QA Worker (/ida:pull <qa-id>)
    Note over Q: QA Worker runs in clean context, verifies PR, and releases done!
```

### Prohibited Behaviors

- `/dispatch` must never require manual promotion, human sign-off, or supervisor intervention to move a queued QA task from blocked to ready once its primary releases `done`.
- Workers must never release `review` or `partial` when the primary PR deliverable is complete, as this leaves the QA task blocked.

## 5. /reconcile Step for `review` Tasks Specification (AC3)

### The Reconcile Resolution Algorithm

When `/reconcile` (or `wf-reconcile`) executes its sweep, it reads all tasks currently carrying `status: review` and executes the following deterministic procedure:

```
For each task T where T.status == "review":

  1. CHECK FOR USER MANUAL HOLD:
     If T.assignee == "user":
       Leave T in status: review (manual user hold preserved per wf-reconcile.md:17).
       Continue to next task.

  2. CHECK FOR COVERING REVIEW OR QA TASK VIA GRAPH EDGES:
     Else if there exists an active task R on the graph such that:
       (R.needs contains T.id OR R.depends_on contains T.id)
     Then:
       Mutate T.status -> "done"
       Log: "Reconciled review task T to done: covered by dependent review task R"
       Continue to next task.

  3. CHECK FOR DELIVERED PULL REQUEST:
     Else if T.pr_url is non-empty AND T.pr_url points to an active pull request:
       Mutate T.status -> "done"
       If T warrants independent QA under risk taxonomy AND no QA task exists:
         Mint QA child under T.parent: Title="QA: " + T.title, needs=[T.id], status="queued"
         Log: "Reconciled review task T to done on open PR; minted dependent QA follow-up"
       Else:
         Log: "Reconciled review task T to done on open PR"
       Continue to next task.

  4. CHECK RECORDED EVIDENCE AGAINST ACCEPTANCE CRITERIA:
     Else:
       Read T.body acceptance criteria and ## Report.
       If all acceptance criteria are marked (- [x]) with verifiable pinpoint citations:
         Mutate T.status -> "done"
         Log: "Reconciled review task T to done: verifiable evidence satisfies criteria"
       Else if incomplete agent work remains:
         Mutate T.status -> "queued" (or "partial" if partial increment delivered)
         Log: "Reconciled review task T to queued/partial: incomplete agent work"
       Else if an escalated human decision is required:
         Mutate T.status -> "partial" with question in T.reason
         Escalate to today's daily note under "## With you"
         Log: "Reconciled review task T to partial: escalated decision required"
```

### Resolution of Tasks Sitting at `review` Today

Tasks currently sitting in `status: review` across the task graph are resolved on the next reconcile sweep:

1. `/reconcile` sweeps all tasks at `status: review`.
2. Tasks assigned to the user (`assignee: user`) remain in `status: review` as intentional manual holds.
3. For all agent tasks that represent delivered PRs with associated QA tasks or open PRs, `/reconcile` immediately transitions the task to `status: done`.
4. Transitioning these tasks to `done` immediately resolves the `needs` edges for their dependent child tasks (unblocking downstream build and QA tasks).
5. No agent task is left in `review`.

## 6. Status Vocabulary Analysis & Scope of `review` (AC4)

### Retention in Policy Taxonomy

The canonical 12-value status vocabulary defined in `tests/policy.toml` and mirrored in the PKB schema is:

```toml
valid_statuses = [
  "inbox",
  "ready",
  "queued",
  "in_progress",
  "review",
  "done",
  "paused",
  "someday",
  "cancelled",
  "partial",
  "failed",
]
```

`review` **remains a valid status string in the underlying database schema and taxonomy**. Retaining it in `valid_statuses` is necessary to:

1. Prevent database migration failures or schema validation errors against historic task records and git commit trees.
2. Allow `/reconcile` to query tasks carrying `status: review` during truth maintenance sweeps without schema rejection.

### The Single Permitted Case for `review`

> **The Single Case Rule:**
> `status: review` is reserved **exclusively** for a manual holding state applied directly by the human principal ("the user").
> If the user explicitly moves a task into `review` in the PKB console or editor to hold it for personal manual inspection, that status is respected as intentional human action and left untouched by automated reconcile sweeps.

### Absolute Prohibition on Agent Use

> **Agent Prohibition:**
> Automated agents, polecat workers, subagents, and skills (`pull`, `dump`, `dispatch`, `reify`, `verify`) are **strictly prohibited** from releasing or setting `status: review`.
> No prompt, skill, rule, or workflow template shall instruct an agent to release or transition a task into `review`.
> When an agent finishes its deliverable, it releases `status: done`.
> When an agent encounters a blocker, scope seam, or approval boundary, it releases `status: partial` (or `status: failed` on verification failure) with full evidence in `reason`.

## 7. Enforcement Pyramid Analysis

Following [`specs/enforcement/enforcement.md`](enforcement.md), the change is evaluated across the pyramid tiers:

| Tier | Mechanism | Implementation in this Change |
| :- | :- | :- |
| **Level 1: Instructions** | Skill and workflow markdown instructions | Update `pull/SKILL.md`, `dump/SKILL.md`, `dispatch/SKILL.md`, `wf-finish.md`, `wf-quick-fix.md`, `wf-code-task-base.md`, `wf-doc-base.md`, `wf-reconcile.md`, `headless-workers.md`, and `sara.md` to mandate `release_task(status: done)` and eliminate instructions directing agents to use `review`. |
| **Level 2: Context / Prompts** | Reconcile and dispatch operational context | `/dispatch` checks for `status: done` to unblock `needs` edges; `/reconcile` checks for covering QA tasks and transitions `review` to `done`. |
| **Level 3: Structural** | Graph edge dependency resolution | PKB graph query engine evaluates `needs: [<id>]` as satisfied when upstream status is `done`. Unblocks downstream QA dispatch without polling. |
| **Level 4: Mechanical Gates** | Tool input validation | PKB tool `pkb_release_task` already requires `summary` and ticked acceptance criteria for `status: done`. Future escalation could soft-deny `status: review` when caller is an automated agent session. |

Defaulting to Level 1 (Instructions) and Level 3 (Structural graph dependencies) is sufficient to fix the deadlock immediately without adding heavyweight runtime hooks or fragile wrappers.

## 8. Implementation & Verification Protocol

### Outcome-Level Criteria for Build Stage

The subsequent implementation change must satisfy:

1. **Instruction Parity:** All identified file locations in skills, workflows, agent personas, rules, and specifications are updated to reflect the release-as-done rule and the single-case scope of `review`.
2. **Dispatch Unblocking:** Given a primary task with a downstream QA task, completing the primary task with `status: done` leaves the QA task in `ready: true`, dispatchable by `/dispatch` without human intervention.
3. **Reconcile Drain:** Running `/reconcile` sweeps any agent task sitting in `status: review` covered by a review task or PR and transitions it to `status: done`, while leaving user-assigned manual holds in `review`.
4. **Test Suite Green:** All existing tests in `tests/` pass (`uv run pytest`), ensuring zero regression in policy validation or hook handling.
