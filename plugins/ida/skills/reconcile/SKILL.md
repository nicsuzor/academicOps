---
name: reconcile
description: Truth maintenance over the task graph -- verification of claimed evidence on done tasks, pull request matching, scope checks, next-task assurance for unfinished work, and world-fact cancellations. Two modes -- `check`, the short pass a supervisor runs over the tasks it names; `sweep`, the long graph-wide pass that runs as a scheduled run. Exclude for worker-level task completion (workers mark done after /pull).
---

# Reconcile

Truth maintenance over the task graph. Reconcile evaluates claimed evidence, verifies scope, matches pull requests, routes failed checks, and ensures every unfinished piece of work has a next task. It does not claim to be the sole writer of `done`; workers with PKB access mark their tasks `done` after `/pull`.

Two modes share the rules below and differ in what they read:

| Mode    | Invocation                      | Run by                              | Reads                                        |
| ------- | ------------------------------- | ----------------------------------- | -------------------------------------------- |
| `check` | `/ida:reconcile check <ids>`    | A supervisor, in its own session    | The named tasks and the PRs they record      |
| `sweep` | `/ida:reconcile sweep [window]` | A scheduled run, never a supervisor | Every non-terminal task and PR in the window |

A bare `/ida:reconcile` runs `check`; `sweep` runs only when named.

## Check

The short pass. A supervisor runs it on work that has come back, so it stays small enough to run without leaving the supervisor's session.

1. **Input**: The task IDs the caller names -- typically the tasks it dispatched that have come back as `done`, `review` or `partial`.
2. **Read each task** and the pull request it records (`pr_url`, or its recorded branch), addressed directly; do not search for PRs the task does not name. A PR the task records that closed without merge is the check's to surface for routing, as the sweep's pull-request step does.
3. **For a task marked `done`**, run the per-task checks below. For any other status, apply the row of the status table that its own record decides.
4. **Set the status** each task's evidence supports, under Settle Decisions Before Escalation and Failed-Check Outcome.
5. **Leave the rest to the sweep.** Check reads no task it was not handed: it does not list the graph, match PRs that name no task, mint or re-queue next tasks, demote dependents or siblings, or cancel on world-facts. Anything of that kind it notices it appends to the handed task's body under `## For the next sweep` -- one line each, naming the task ID affected and the evidence -- and lists in its result.

## Sweep

The long pass. It reads the whole active graph, so it runs as a scheduled run -- asynchronous and detached, its result recorded on the graph -- and never in a supervisor's session.

**How a scheduled run invokes it**: a task whose body directs `/ida:reconcile sweep`, naming its window, is dispatched like any other work (`/reify` → `/dispatch`). The worker that claims it with `/pull` runs the sweep and releases the task with the Output Contract as its release note. The consolidation cycle's data-quality stage runs it the same way. A supervisor that wants a sweep dispatches one; it does not run it in-session.

**Window**: the one the task names; with none, everything since the previous sweep's recorded result. Report the window covered.

1. **Load tasks**: Read non-terminal tasks across active statuses, plus tasks marked `done` within the sweep window.
2. **Check each task** as Check does, over every task loaded, not only those a caller named.
3. **Reconcile pull requests**: Match open and closed pull requests to tasks by structured identifiers (`pr_url`, task ID in PR body or branch, recorded branch, `polecat/` prefix, exact title).
   - **Merged PRs**: Confirm `status: done` on observed merged PRs.
   - **Closed without merge**: Surface for routing if unsure how to update the corresponding task.
4. **Cancel on world-facts**: Cancel tasks only on affirmative evidence recorded in the node body:
   - _Referent destroyed_: Target artifact was deleted, verified across checkouts and refs.
   - _Superseded by merge_: Merged PR mooted or settled the task's question.
   - _Premise falsified_: Named assumption or precondition no longer holds.
5. **Assure next tasks**: Give each unfinished piece of work a next task, per Next-Task Assurance.
6. **Demote affected tasks**: Set unblocked dependents, siblings of landed work, rot (>14d in `ready`/`queued`), and invalidated assumption nodes to `status: inbox` with explanatory annotations. Do not send failed `done` tasks to inbox. Do not demote a task that is the only next task for unfinished work (see Next-Task Assurance). Surface a stale one in the sweep's result instead.
7. **Take up check leftovers**: Act on each `## For the next sweep` line on tasks in the window (`pkb.search(query="For the next sweep")`), then strike it through with the outcome.

## Per-Task Checks

### Principal Closures vs. Worker Delegations

Reconcile audits _agent and worker_ completion claims. Closures made directly by the user/principal (e.g. cancelled or marked done on the dashboard, in UI, or via direct user directives) are self-authorizing and presumed intentional.

- **No completion receipts for user closures**: Reconcile must never demand worker completion receipts, release summaries, or audit notes for tasks closed directly by the user.
- **Never flag user closures as defects or anomalies**: A user closure must never be flagged as "closed without an outcome", "dropped with no reason given", or an unverified anomaly, and must never be demoted or escalated to `review` or `inbox` unless affirmative evidence on the record proves an unintentional error.

### Worker Delegations

For a worker task marked `done`:

- **Pull request matching**: Unconditionally recognize merged PRs; inspect unmerged or closed PRs.
- **Facial sufficiency of claimed evidence**: Read each piece of claimed evidence in the worker's report against the task's literal acceptance criteria. Verify whether the evidence is facially sufficient to prove the criteria were met. Asserting that tests passed is sufficient for a worker's completion claim; full substantive QA is handled independently.
- **Scope check**: Verify that the delivered work and touched files respected the task's specified boundaries and did not expand beyond authorized scope.

## Set the Status on Each Task

Every task this sweep reads leaves it in the one status that matches its evidence. A status that no longer describes the task is a defect you fix in the same pass:

| Task is in            | Evidence on the record                                                               | Set it to                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `done` (user closure) | Direct closure by user/principal (dashboard, UI, direct directive)                   | `done` (unchanged, exempt from completion receipts)                                                   |
| `done` (worker)       | Claimed evidence passes facial sufficiency and scope                                 | `done` (unchanged)                                                                                    |
| `done` (worker)       | Fails either check and cannot be remedied in-session                                 | `review`, per Failed-Check Outcome                                                                    |
| any open              | Its PR is merged and its acceptance criteria are met                                 | `done`                                                                                                |
| `review`              | The body names a decision escalated for review that is still open                    | Settle it per Settle Decisions Before Escalation; leave it in `review` only if it requires escalation |
| `review`              | The work is claimed complete and no decision is escalated (parked for merge or QA)   | Judge it as a `done` claim: `done` if it passes, else stays `review` per Failed-Check Outcome         |
| `review`              | Agent work remains and no decision is escalated (parked on a tool, blocker or retry) | `queued` if the task was queued before its claim; otherwise `inbox`                                   |
| `in_progress`         | No live claim: unmodified for more than 24 hours                                     | `queued`                                                                                              |
| `partial`             | Increment delivered and a live follow-up task carries the remainder                  | `partial` (unchanged)                                                                                 |
| any open              | A world-fact trigger fired                                                           | `cancelled`, per the sweep's world-fact step                                                          |

- **`review` means waiting on an escalated decision.** Leave a task there only when the body names a decision that must be escalated under Settle Decisions Before Escalation. Agent work never waits in `review`.
- **`queued` stays an escalated gate.** Set `queued` only to restore a promotion already made during review: a stuck `in_progress` task, or a `review` task parked after a queued claim. Never promote `inbox` or `ready` work to `queued`.
- **Use only the statuses in the table.** Never write `merge_ready` or any other status the table does not name.

## Settle Decisions Before Escalation

Every open escalated decision becomes a line of work for a higher-tier reviewer, so settle it yourself first. The reviewer has delegated their open decisions to you; this applies to each `review` task that names one and to each escalation you are about to write.

A decision must be escalated only when one of these holds:

- **Unrecorded fact**: the answer turns on something only the reviewer knows that the record does not hold -- external preferences, unrecorded health or relationships, or off-graph state.
- **External commitment**: acting on it speaks or commits outside the graph, spends money, or cannot be undone.
- **Reserved field**: it sets a reserved field, such as `intent`, and no ruling on record covers the case.

Pull-request base, merge readiness, style commits, review depth, sequencing, tool choice and security hygiene meet none of these; rule on them.

To rule:

1. Search the record for rulings and stated positions on the question and apply them. Where none applies, take the reversible option that keeps work moving.
2. Append a `Ruled without escalation` entry to the task body: the ruling, its reason with a citation, and that it may be reversed by a reviewer.
3. Set the status the ruling leaves: `done` if it closes the task, otherwise the agent-work-remains row above.

A decision the body shows already made is not open: cite where it was made and apply the row it leaves.

For a decision that must be escalated, reduce it to the single question that must be answered, answerable in one line, and write that question with the default you would take to the task's `reason`. Name which test kept it.

## Next-Task Assurance

Sweep only.

Each unfinished piece of work must leave a next task that someone can pick up. Here, "unfinished" means one of:

- a task marked `done` whose PR is still open, whether draft or ready;
- a task in `partial` or `paused`;
- a task in `in_progress` without a live claim (e.g. from a worker crash);
- a draft PR whose task is waiting on another piece of work.

A piece of work is covered when one of these holds:

- a next task exists and is `queued` or `ready`, or is `in_progress` under a live claim;
- the work waits on a decision from Nic that this sweep's result names (tasks in `review`).

For each piece of work that is not covered:

1. **Find the governing finish template**: the project's `.agents/templates/wf-finish.md` if it exists, otherwise the universal `wf-finish` template in the workflow library. Its QA review rule decides whether the change needs QA. Its Follow-up QA Task Specification gives the shape of the QA task.
2. **Look for an existing next task first**: the task's `follow_up_tasks`, its children, tasks that `depends_on` it, and a task titled `QA: <task title>`. Do not mint a duplicate.
3. **Awaiting QA**: the task is `done` with an open PR, and the finish template requires QA for the change.
   - If no QA task exists, mint one following the template's specification: title, same parent, and `depends_on: [<task-id>]`. Then add its ID to the source task's `follow_up_tasks`.
   - If the QA task exists but sits in `inbox`, set it to `queued`.
   - If the finish template has QA review a PR that is ready for review, and the PR is still a draft, mark it ready with `gh pr ready`.
   - Leave a PR in draft when this skill converted it under a failed check (task in `review`).
4. **Draft awaiting related work**: the PR body, the task's release text, or its `depends_on` edges name another piece of work that must land first.
   - Find the task that carries that work. If none exists, mint one, then wire `depends_on` from the waiting task to it.
   - If that work has landed, check that the draft has picked it up (rebased, or the follow-up commit is on its branch). If it has, the PR now awaits QA; handle it under step 3. If it hasn't, queue the waiting task so a worker finishes the PR.
   - If that work has not landed, and the task that carries it is in an inactive state (`inbox` or `paused`), set it to `queued`.
5. **Partial or paused without a successor**: mint a task for the remaining acceptance criteria, using the release reason as its goal. Add its ID to the source task's `follow_up_tasks`. If the remainder needs Nic's decision first, name that decision in the sweep's result instead.

## Failed-Check Outcome

When a task marked `done` fails the facial sufficiency or scope check:

1. **Remedy before escalation where possible**: A failure remedied before reaching the user (e.g. missing evidence supplied by an independent verification check that passes) is not a failure -- confirm `status: done` citing the remedied evidence.
2. **Escalate unremedied failures**: For failures that cannot be remedied in-session, route the task for ratification or reversal rather than returning it to `inbox`. Set `status: review` and document the exact failure reason and unverified criteria in the task body, with the ratify-or-reverse question reduced to one line per Settle Decisions Before Escalation.
3. **Convert PR to draft with comment**: If a PR was filed, convert it to a draft PR and post an explanatory comment stating which check failed and what the user needs to decide, preventing accidental merge before ratification. Address the PR directly by its URL or repository-qualified reference rather than relying on a local checkout.

## Writes

1. **Cancel on world-facts**: Cancel tasks only on affirmative evidence recorded in the node body:
   - _Referent destroyed_: Target artifact was deleted, verified across checkouts and refs.
   - _Superseded by merge_: Merged PR mooted or settled the task's question.
   - _Premise falsified_: Named assumption or precondition no longer holds.
2. **Demote affected tasks**: Set unblocked dependents, siblings of landed work, rot (>14d in `ready`/`queued`), and invalidated assumption nodes to `status: inbox` with explanatory annotations. Do not send failed `done` tasks to inbox. Do not demote a task that is the only next task for unfinished work (see Next-Task Assurance). Surface a stale one in the sweep's result instead.

## Output Contract

Emit one synthesized result:

1. Rulings made without escalation (task ID, ruling, citation).
2. Decisions escalated for review (task ID, the one-line question, the test that escalated it).
3. Checks failed: Tasks escalated for ratification or reversal (with recorded reasons and PR draft links).
4. Status updates made (task IDs, PR links, verified completions).
5. Sweep only -- unfinished work recovered: next tasks minted or re-queued, and PRs marked ready (task IDs, PR links, evidence that the work had no next task).
6. Sweep only -- cancellations (task ID, trigger fired, verbatim evidence written to body).
7. Sweep only -- tasks demoted to `inbox` (dependents, stale items).
8. Sweep only -- sweep window covered.
9. Check only -- "For the next sweep" (task ID, what was noticed, evidence).
