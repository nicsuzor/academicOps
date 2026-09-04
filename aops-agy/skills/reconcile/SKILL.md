---
name: reconcile
description: Truth maintenance over the task graph — establish what is actually true about work the graph still claims is in flight and about work that landed while nobody was watching, write those facts back, and return the tasks a landed wave touched to `inbox` for re-planning. Fires on engagement after an absence, inside the consolidation cycle, and on demand — "reconcile the graph", "what is actually still running", "catch up on the PRs that merged", "clear out the stale in_progress claims", "sweep for abandoned work". Not a planner, a reviewer, or a pruner — it never certifies work complete on its own judgment, never prunes, never scores, never re-plans, and cancels only on affirmative evidence, never on age.
---

# Reconcile

You write facts. Every write is something you observed: a pull request merged, a
branch went quiet, a named file no longer exists, a person recorded a reason.
That is the whole of your authority. The standing limits on it are in **Must
not** at the end of this file, and they bind every step below.

## 1 — Load the graph, claims included

Call `pkb__list_tasks` (hosted under the `services` MCP server as
`mcp__services__pkb__list_tasks`) over **every** non-terminal status the PKB MCP
schema declares. Read that status set off the schema, never off a list inlined
here: a sweep that loads only the statuses which look in flight reports itself
complete while skipping whole classes of work.

Filter the slice before you pull it — narrow by status or project, take the
default markdown format, and repeat until the set is covered. Many narrow calls,
never one wide one.

Then read the **claim** on each. A status by itself is not a claim; the assignee
and the session make it one, and they are what you check.

## 2 — Probe every suspect claim, then confirm it or requeue it

A claim is **suspect** when the session behind it is plausibly over: nothing
written to the task since it was taken, and enough time gone that a live worker
would have said something. Suspect licenses a probe, never a verdict.

Status is not liveness. It is not a reading of the worker or the container, and
a detached dispatch emits no harness completion signal — so "still running" is
an assumption, not a fact, and there is nothing to wait for.

Probe the claim's own leavings and nothing else: writes to the task record since
the claim, commits on the branch it recorded, activity on its pull request.
Silence somewhere the worker was never going to write is evidence of nothing.

- **Live** — something moved. Leave the claim where it is and say what you saw.
- **Dead** — nothing moved anywhere the worker would have written. Set it back
  to `ready` and record on the task who held the claim, when it was taken, and
  what you probed. `ready`, never `queued`: releasing work for dispatch is the
  user's gate. Requeue an abandoned claim, never close or cancel it — a requeue
  is reversible and legible, and a claim closed because its worker went quiet is
  work you deleted.

## 3 — Fold in what finished while nobody was watching

Bound this step before you run it. The window is whatever your caller gave you;
absent one, choose a bound. State it in your result either way, so the next
sweep knows where you stopped.

Match each pull request closed inside that window to a task, in this order:

1. a `pr_url` already on the task;
2. a task id in the pull request body;
3. the head branch matching the task's recorded branch;
4. a head branch prefixed `polecat/` (`polecat/dispatch-<task-id>`,
   `polecat/run-<slug>`). The prefix proves **provenance** — an automated
   polecat run, not parallel human work — but it encodes the session or task
   name, not a unique attempt id, so repeated dispatches share it and it
   identifies neither the attempt nor a live container;
5. the title matching the task title whole-word, ignoring conventional-commit
   prefixes.

A reverse match on distinctive title substrings is surfaced as _likely closed
by_ and **never auto-completes**.

- **Merged** → write the facts first: the pull request, the merge date, the
  branch. A merge is settled — record it and move on. Delete any in-body
  instruction it overtook (a "DO NOT MERGE" note) rather than preserving it as a
  conflict.

  Then re-read the task's acceptance criteria against the merged artifact:
  - every criterion **observably** met → complete it;
  - the merge settled or mooted the task's own question rather than performing
    it — the fork it existed to decide is now decided on the ground → cancel it
    on that evidence (§5), never complete it;
  - any criterion unmet, or met only on a reading that takes judgment → leave
    the task open, quote the unfulfilled criterion, and return the task to
    `inbox` (§7), reported as remaining work and never as an objection to the
    merge.
- **Closed without merge** → route it (§4). Never re-queue automatically.
- **No match** → surface it. Never invent a task.

Pull requests only; no commit-log scanning. Report the window as covered only
once the writes inside it have succeeded.

**Backstop, ignoring the window.** Sweep every `merge_ready` and `review` task,
oldest first — they rot regardless of when anything closed, and they are not the
same parked state. A `merge_ready` task resolves against its pull request:
merged goes through the criteria check above, closed-without-merge routes to §4,
and **no resolvable pull request at all is anomalous** — surface it, never close
it. A `review` task is parked on a human decision and is **never auto-closed**:
note its pull request's live state where it has one, otherwise surface it as
awaiting a decision so it cannot rot silently.

Also surface: a body claiming release with no pull request recorded; a worker
that ran and recorded that it changed nothing, which returns to `inbox`
annotated with that fact; and three or more sweep reports on one task all
reading closed-without-merge, which is strong evidence the approach keeps
failing and belongs in the routing context.

Where a merge is confirmed but the close is rejected because children are open,
surface it as merge-confirmed, close-blocked, and let it resolve when the child
does. Open children may be legitimate post-merge follow-up, and cascade-closing
destroys real pending work.

If the state this step depends on is absent — as distinct from the PKB being
unreachable — say so explicitly. Never report a step complete when it never had
inputs.

## 4 — Route a pull request closed without merge

Gather the context first: title and body, the last several reviewer comments,
the review state, labels, whether the branch was deleted, and whether the task
already carries repeated closed-without-merge reports.

Then **have an agent read it and classify**. This is a semantic judgment, not a
string match — a "wontfix" label is a signal, not the verdict. You are reading
for **the decision a person already made**, recording it rather than reaching
it. Where the comments carry none clearly, the class is `bad-implementation`,
which files a question rather than closing anything. Exactly one of:

| Class                  | Signal                                                                                    | Action                                                                                                                                                                                                  |
| ---------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **wontfix**            | Clear "do not do this", not-planned, superseded, or the reviewer rejects the goal itself. | Cancel the task, or complete it if a sibling superseded it. Record the pull request and the person's stated reason in the body. File no follow-up.                                                      |
| **bad-implementation** | Wrong approach, design rejected, repeated failure, "needs a rethink", or ambiguous.       | Call `/q` (`/aops:q`) to reposition the task in place under the same parent (returning to `inbox` with updated context on what went wrong and what must change), rather than creating a duplicate task. |
| **retry-as-is**        | Rare. Unrelated infrastructure failure, documented in the comments. Nothing was wrong.    | Re-queue to `inbox`, with the justification written into both the task body and the result.                                                                                                             |

Record the chosen route, the close reason quoted from where you read it, and any
repositioning performed.

## 5 — Staleness, rot, and cancellation

**Aged non-terminal work.** Tasks aged past about ninety days, up to twenty a
sweep. Read the body, then look for completion evidence — sent mail, calendar
entries, commits. Evidence found completes the task with that evidence recorded.
No evidence **flags it for human review**, never auto-cancels: age is not
evidence of irrelevance. Where the evidence tools are unavailable in this
environment, skip the verification and flag the candidates.

**Sent mail, checked per candidate, never swept.** Bound the lookup to the aged
candidate already in hand: search on its title, its task id, and the
correspondents it names — never a mailbox-wide window, and never a second sweep
phase beside this one. Validate the tool before trusting a negative: run one
known-item query first; an unvalidated empty result is "retrieval unreliable
this run," never "no email trace" — a search tool with undocumented
false-negative behaviour makes the two indistinguishable, and reporting the
second when only the first is true has already put a false finding on this
graph once.

Where a candidate turns up, an agent reads it and answers one structured
question, on the model of §4's pull-request classification: does this message
settle the task's own open question — a completion claim, a go/no-go decision,
or an answer to something the task was explicitly blocked on, never an
incidental mention — returning `settles: bool`, `confidence:
high|medium|low`, and `reason` quoting the decisive phrase. Only `confidence:
high` with `settles: true` writes the fact; `medium`, `low`, or no candidate
found flags it for human review under this paragraph's own rule above, and
never auto-cancels or auto-completes on anything less.

An email-sourced write carries the same evidence a merge carries: the message
reference (a stable id where the tool provides one, otherwise subject, date,
and sender), the date sent, and the excerpt that establishes the fact — quoted,
never paraphrased — plus the confidence and reason returned above. It goes
through the two-step mutation contract below like every other write this step
makes: body, then frontmatter status, then a readback.

**Artifact rot.** For `ready` and `queued` tasks aged past about a fortnight,
verify that the files and symbols the task's criteria name still exist where
they claim to. Rot triggers the write; age alone does not. A referent you have
shown was **deleted** cancels the task; a referent you merely failed to find
where the task said it would be **demotes** it to `inbox`, annotated with
exactly what no longer resolves (§7).

**Cancel on a world-fact.** These are the unattended triggers, where no person
has spoken and you establish the fact yourself. They sit alongside §4's
person-decision route and do not replace it. Cancel when one is established:

1. **Referent destroyed.** The file, skill, agent, feature, or interface the
   task acts on was _deleted_, not relocated. A failed lookup does not establish
   deletion. Search across every relevant checkout and ref — by exact path, by
   path-tail, and by basename — before concluding a thing is gone. The ref
   universe is the one the task itself implies: the repositories and branches
   its criteria name, plus each one's default branch. Where you cannot establish
   what that set even is, you have not established deletion — demote.
2. **Superseded by merge.** The gating pull request merged in a way that
   resolves or moots the task's own question (§3).
3. **Premise falsified.** A condition the task explicitly assumed — named in its
   `## Assumptions`, stated as a precondition, or carried by the gate it names —
   no longer holds. An acceptance criterion that is merely **unmet** is not
   this: an outcome nobody has delivered yet is ordinary incomplete work, and
   the task stays open (§3).

Where relocation and deletion cannot be told apart, or you are otherwise
uncertain, demote and annotate. Unlike a cancellation, a demotion costs nothing
to be wrong about.

**Every cancellation carries its evidence in the node body**, matched to the
trigger that fired, and no trigger's burden is imposed on another:

- **a person's decision (§4)** — the pull request, and their stated reason
  quoted from where you read it;
- **referent destroyed** — the path, the commit or ref that shows the deletion,
  and how you distinguished deletion from relocation: which checkouts, refs, and
  name forms you searched;
- **superseded by merge** — the pull request number and its merge timestamp;
- **premise falsified** — the assumption quoted from the node, and the fact that
  falsifies it.

A cancellation nobody can audit from the node is one you do not make.

Where a world-fact cancellation leaves an unanswerable ambiguity, record the
observed fact on the node and return unblocked dependents to `inbox` (§7). §4
repositions tasks in place rather than filing separate investigation tasks.

### The two-step mutation contract

Every demotion to `inbox` and every cancellation is two writes and a readback:

1. **Body** — write the annotation or evidence with `pkb__append` or
   `pkb__update_body`. These touch markdown prose only.
2. **Frontmatter** — mutate the status explicitly with
   `pkb__update_task(id="<task-id>", updates={"status": "inbox"|"cancelled"})`.
   `pkb__batch_update` drops status payloads silently; never use it here.
3. **Readback** — call `pkb__get_task(id="<task-id>")` immediately and confirm
   `frontmatter.status` is what you intended.

## 6 — Route the completed-but-uncertified

A unit whose work landed but whose record carries no certification verdict is
not done. These sit at `done` — terminal, and so outside the set §1 loaded — so
this step needs its own read: the units closed inside your window, checked for a
verdict on the record.

Certify none of them yourself. You did not do the work, you are not the
reviewer, and a worker's own "confirmed" on a task record is one more claim
needing certification. Collect them and hand them onward to the dispatcher,
which commissions the review machinery and records its verdict. This is the one
finding that cannot sit in a report.

## 7 — Return the affected tasks to `inbox`

A merged pull request settles assumptions other tasks were built on; a rotted
artifact invalidates the criteria that named it. Collect the tasks a fact you
wrote actually touched:

- what a completed unit's `depends_on` edges unblocked, and its live siblings
  under the same parent;
- anything whose `## Assumptions` names a belief the landed work tested — the
  probe that came back is the case this exists for;
- everything §5 demoted for rot;
- what a §5 cancellation unblocked or invalidated — the cancelled node is
  terminal and does not itself return, but its live siblings and anything whose
  criteria leaned on it do;
- the tasks §4 repositioned to `inbox`.

Set that whole set to `inbox` under the two-step mutation contract (§5),
annotated with the fact that moved it. `inbox` signals that a task needs working
out again; the re-planning itself is a separate act on the user's call.

## 8 — Emit one result

One synthesized result for whoever called you, whatever the sweep touched — a
caller who has to read twenty rows to find the two that matter has been handed
your sweep instead of its outcome.

Lead with what needs a person's decision, then what you changed, then what you
found and deliberately left alone, then what you returned to `inbox`. Report
**cancellations as their own category**, never folded in with demotions or
completions: for each, the id, which trigger fired — a person's recorded
decision (§4), referent destroyed, superseded by merge, premise falsified — and
the evidence you wrote to the node for that trigger. Name ids for everything
completed, cancelled, requeued, demoted, routed, surfaced, or handed on; a bare
count is not checkable. Close with the one thing the next sweep should pick up,
and with the window you covered.

## Must not

- Certify work complete on your own judgment, or relay a worker's self-report as
  a certification verdict. A `done` is right only where an observable criterion
  was met or a person said so.
- Close, cancel, or complete anything because it is old, quiet, duplicative, or
  inconvenient. Age is a candidacy signal and nothing more.
- Cancel without the evidence its own trigger requires written into the node
  body (§5) — and, where you claim a referent was destroyed, without the
  deletion-versus-relocation check. Where the two cannot be told apart, demote.
- Cancel on a missing path that appears only in narrative, provenance, or
  `## Source` prose rather than in the acceptance criteria or the work itself.
- Re-open, adjudicate, or second-guess a decision a person has already recorded,
  merged pull requests included: never propose revert, ratify, or let-stand, and
  never characterise a merge as premature, wrong-base, or contrary to a note on
  the node.
- Annotate a body with a demotion, rot, or cancellation without also mutating
  the frontmatter `status` via `pkb__update_task`. A task sitting at
  `status: queued` or `status: ready` while its body says demoted or cancelled
  is strictly forbidden.
- Use `pkb__batch_update` to mutate task statuses or perform demotions.
- Resolve an acceptance criterion that needs interpreting, or supply a judgment
  a person has not made.
- Prune, restructure, or merge anything (delegate task repositioning and intake placement to `/q`).
- Write `focus_score`, `intent`, `priority`, or `severity`.
- Promote work into `queued`. That gate is the user's.
- Re-plan: re-sort assumptions, design probes, cut units, or write briefs.
- Decide by pattern where prose is what decides. Mechanical matching is for
  structured surfaces only — a frontmatter field, a recorded branch, a pull
  request's own structured references. Anywhere the answer lives in prose, read
  it, or hand that one question to an agent that will.
- Re-implement this procedure inside another skill, or run a second sweep beside
  it.

## Fitness test

From your result alone — without opening the graph — the caller can say which
in-flight claims are still live and why, what you changed and on which ids, what
you cancelled and on what affirmative evidence, what is now waiting on a person,
and which tasks went back to `inbox` and on what fact. If any of those needs
re-deriving, the sweep is not done.
