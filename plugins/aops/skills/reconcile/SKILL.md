---
name: reconcile
description: The return channel. Establish what is actually true about work the graph still claims is in flight and about work that finished while nobody was watching, write those facts back, and return the tasks a landed wave touched to `inbox` for re-planning. Truth maintenance only — it never certifies work complete on its own judgment, never prunes, and never scores, and it cancels only on affirmative evidence — a decision a person already recorded, a referent deleted, a merge that mooted the question, a premise falsified — never on age. Fires on engagement after an absence, inside the consolidation cycle, and on demand.
---

# Reconcile

The graph is a set of claims about work, and a claim outlives the session that
made it. A worker dies mid-task and its claim sits `in_progress` forever. A pull
request merges unwatched and the task it closes never moves. A task's acceptance
criteria name files that were renamed away a fortnight ago. You establish what is
**actually** true, and you write that back.

This is the only place the reconcile procedure lives. Other skills invoke it;
none of them re-implements it. What it governs is tasks and the pull requests
they resolve against.

## What you are

**A fact-writing channel, and nothing else.** Every write you make is something
you observed: a pull request merged, a branch went quiet, a named file no longer
exists, a person wrote a close reason. That is the whole of your authority.

- You **never certify work complete on your own judgment.** Where a `done` is
  right, it is because an observable criterion was met or a person said so —
  never because a task is old, quiet, duplicative, or inconvenient.
- You **do cancel, and only on affirmative evidence.** Cancelling is a different
  act from completing: it asserts the work is no longer wanted or no longer
  possible, never that anyone performed it. Two kinds of evidence license it,
  and nothing else does: **a decision a person already made and recorded**,
  which you read rather than reach (§4); and **a world-fact you established** —
  the thing it acts on was deleted, a merge mooted its question, its premise is
  false (§5). Never elapsed time, never a quiet worker, never a lookup you could
  not resolve.
- You **never re-open or second-guess a decision a person has already recorded.**
  A decision already taken — a merged pull request, an explicit close, a
  recorded sign-off — is settled. You record the fact as observed reality and
  delete any stale in-body instruction the decision overtook; you never
  adjudicate whether the decision was right, premature, or contrary to prior
  notes.

## 1 — Read the graph, claims included

`pkb__list_tasks` (maybe hosted under the `services` MCP server: `mcp__services__pkb__list_tasks`) over **every non-terminal status** the PKB MCP schema declares —
that schema is the source, never a list inlined here. Later steps read and write
across the whole of that set, so a sweep that loads only the statuses which look
in flight reports itself complete while skipping whole classes of work.

Then read the **claim** on each. A status by itself is not a claim; the assignee
and the session are what make it one, and they are what you check.

Filter the slice before you pull it. Narrow by status or project, take the
default markdown format, and repeat until the whole set is covered — many narrow
calls, never one wide one.

### Task Status Reconciliation

Evaluate each non-terminal task in `in_progress`, `review`, or `merge_ready` status individually to verify its actual state against reality:

- Check whether active work is still occurring, whether work was completed, or whether an associated PR was merged or closed.
- Update the task's status in the PKB to accurately reflect reality (e.g., mark as `done`, return to `inbox`, or set to `ready`).

## 2 — Probe every suspect claim, then confirm it or requeue it

A claim is **suspect** when the session behind it is plausibly over: nothing
written to the task since it was taken, and enough time gone that a live worker
would have said something. Suspect is a reason to probe. It is never a verdict.

**Status is not liveness evidence.** A task's status in the graph is not a reading of the worker or container. For detached dispatches that emit no harness completion signal, 'still running' and 'not finished yet' are assumptions rather than facts. The status is not one of those signals, and there is no completion signal to wait for.

**Probe the claim's own evidence trail.** Only the claim's own leavings count —
writes to the task record since the claim, commits on the branch it recorded,
activity on its pull request. Silence somewhere the worker was never going to
write is not evidence of anything.

- **Live** — something moved. Leave the claim where it is and say what you saw.
- **Dead** — nothing moved anywhere the worker would have written. Requeue it:
  set it back to `ready`, and record on the task who held the claim, when it was
  taken, and what you probed to conclude it was abandoned. `ready`, never
  `queued` — releasing work for dispatch is the user's gate, not yours.

**Never silently close an abandoned claim, and never cancel one on age.** A
requeue is reversible and legible; a close is neither, and a claim you closed
because its worker went quiet is work you deleted.

## 3 — Fold in what finished while nobody was watching

**Bound this step before you run it.** The window is whatever your caller gave
you; absent one, choose a bound, and either way state it in your result so the
next sweep knows where you stopped. An unbounded scan reported as a completed one
is the failure here — say what you covered, not that you covered everything.

For each pull request closed inside that window, match it to a task by, in order: a
`pr_url` already on the task; a task id in the pull request body; the head branch
matching the task's recorded branch; a head branch with prefix `polecat/` (e.g.
`polecat/dispatch-<task-id>` or `polecat/run-<slug>`), where the prefix proves
**provenance** (the PR was generated by an automated polecat run, ruling out
parallel human work) but note its **limit**: the branch encodes the session/task
name, not a unique attempt ID, so multiple dispatches of the same task share the
same branch name and it does not identify which attempt or prove container
liveness; the title matching the task title whole-word, ignoring
conventional-commit prefixes. A reverse match on distinctive title substrings is
surfaced as _likely closed by_ and **never auto-completes**.

- **Merged** → write the facts first: the pull request, the merge date, the
  branch. A merged pull request is settled: record the merge as a fact against
  the task and move on. Never raise a merged pull request as an open question,
  never propose revert/ratify/let-stand adjudication, and never characterise a
  merge as premature, wrong-base, or contrary to a note on the node. Delete any
  stale in-body instruction the merge has overtaken (e.g. "DO NOT MERGE") —
  remove it; do not preserve it as a conflict or escalate it.

  Then re-read the task's acceptance criteria against the merged artifact:
  - Every criterion **observably** met → complete it.
  - Merged in a way that settles or moots the task's own question rather than
    performing it — the fork it existed to decide is now decided on the ground →
    cancel it on that evidence (§5), never complete it.
  - Any criterion unmet, or met only on a reading that takes judgment → leave
    the task open, report the unfulfilled criterion quoted, and return the task
    to `inbox` for re-planning (§7). Report _what is left to do_ as remaining
    work, never as an objection to the merge. Surface, do not block, and do not
    resolve the judgment yourself: an acceptance criterion that needs
    interpreting is exactly the case this channel does not decide.
- **Closed without merge** → route it (§4). Never re-queue automatically.
- **No match** → surface it. Never invent a task.

Pull requests only; no commit-log scanning. Report the window as covered only
once the writes inside it have succeeded.

Run a **backstop that ignores the window** over every task in `merge_ready` or
`review`, oldest first — these rot regardless of when anything closed, and they
are not the same parked state. A `merge_ready` task
resolves against its pull request — merged and not yet done goes through the same
criteria check; closed-without-merge routes below; **no resolvable pull request
at all is anomalous** and gets surfaced, not closed. A `review` task is parked on
a human decision and is **never auto-closed**: if it carries a pull request, note
that pull request's live state in what you surface; if it has none, which is the
common case, surface it as awaiting a decision so it cannot rot silently.

Also surface: a body claiming release with no pull request recorded; a worker that
ran and recorded that it changed nothing, which re-queues to `inbox` with an
annotation saying the run happened and produced no work; and three or more
sweep reports on one task all reading closed-without-merge, which is strong
evidence the approach keeps failing and belongs in the routing context.

**Never force a close past open children.** When a merge is confirmed but the
close is rejected because children are open, do not cascade. Open children may be
legitimate post-merge follow-up, and cascade-closing destroys real pending work.
Surface it as merge-confirmed, close-blocked, and let it resolve when the child
does.

If the state this step depends on is absent — as distinct from the PKB being
unreachable — say so explicitly. Never report a step as complete when it never
had inputs.

## 4 — Route a pull request closed without merge

Gather the context first: title and body, the last several reviewer comments, the
review state, labels, whether the branch was deleted, and whether the task
already carries repeated closed-without-merge reports.

Then **have an agent read it and classify**. This is a semantic judgment, not a
string match — a "wontfix" label is a signal, not the verdict. What you are
reading for is **the decision a person already made**; you are recording it, not
reaching it. Where the comments do not clearly carry one, the class is
`bad-implementation`, which files a question rather than closing anything.
Exactly one of:

| Class                  | Signal                                                                                    | Action                                                                                                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **wontfix**            | Clear "do not do this", not-planned, superseded, or the reviewer rejects the goal itself. | Cancel the task, or complete it if a sibling superseded it. Record the pull request and the person's stated reason in the body. File no follow-up.                 |
| **bad-implementation** | Wrong approach, design rejected, repeated failure, "needs a rethink", or ambiguous.       | Cancel the original. File a sibling investigation task under the same parent, softly depending on the original, saying what went wrong and what must change first. |
| **retry-as-is**        | Rare. Unrelated infrastructure failure, documented in the comments. Nothing was wrong.    | Re-queue to `inbox`, with the justification written into both the task body and the result.                                                                        |

Record the chosen route, the close reason quoted from where you read it, and any
node created.

## 5 — Staleness, rot, and cancellation

**Aged non-terminal work.** Tasks aged past about ninety days, up to twenty a
sweep. Read the body, then look for completion evidence — sent mail, calendar
entries, commits. Evidence found means complete the task with the evidence
recorded. No evidence means **flag for human review**, never auto-cancel: age is
not evidence of irrelevance. Where the evidence tools are unavailable in this
environment, skip the verification and flag the candidates.

**Artifact rot.** For `ready` and `queued` tasks aged past about a fortnight,
verify that the files and symbols the task's criteria name still exist where they
claim to. Rot triggers a write; age alone does not. Which write depends on what
you established: a referent you have shown was **deleted** cancels the task
(below); a referent you merely failed to find where the task said it would be is
a **demotion** to `inbox` with an annotation saying exactly what no longer
resolves (§7).

**The Two-Step Mutation Contract.** Whenever performing a demotion to `inbox` or a cancellation:

1. **Body write**: Write the annotation or evidence into the node body via `pkb__append` or `pkb__update_body`.
2. **Frontmatter mutation**: Explicitly mutate the frontmatter `status` via `pkb__update_task(id="<task-id>", updates={"status": "inbox"|"cancelled"})`.
3. **Readback verification**: Immediately read back via `pkb__get_task(id="<task-id>")` to verify `frontmatter.status` matches the intended state.
   _(Never rely on body appends or batch update tools to mutate frontmatter status — body tools touch only markdown prose, and `pkb__batch_update` drops status payloads.)_

**Cancel on a world-fact.** These are the unattended triggers — the ones where
no person has spoken and you establish the fact yourself. They sit alongside the
person-decision route §4 already carries; they do not replace it. Cancel a task
when one of these is established:

1. **Referent destroyed.** The file, skill, agent, feature, or interface the task
   acts on was _deleted_, not relocated. A failed lookup does not establish
   deletion. Search across every relevant checkout and every relevant ref, by
   exact path, by path-tail, and by basename, before concluding a thing is gone.
   The ref universe is the one the task itself implies — the repositories and
   branches its criteria name, plus the default branch of each. Where you cannot
   establish what that set even is, you have not established deletion: demote.
2. **Superseded by merge.** The gating pull request merged in a way that resolves
   or moots the task's own question (§3).
3. **Premise falsified.** A condition the task explicitly assumed — named in its
   `## Assumptions`, stated as a precondition, or carried by the gate it names —
   no longer holds. An acceptance criterion that is merely **unmet** is not this:
   an outcome nobody has delivered yet is ordinary incomplete work, and the task
   stays open (§3).

**Never cancel on** age or staleness alone; absence of recent activity, or a
worker gone quiet; a missing path that appears only in narrative, provenance, or
`## Source` prose rather than in the acceptance criteria or the work itself; or
any case where relocation and deletion could not be told apart. Where you are
uncertain, demote and annotate — for the uncertain case that remains the correct
answer, and unlike a cancellation it costs nothing to be wrong about.

**Every cancellation carries its evidence in the node body**, matched to the
trigger that fired, and no trigger's burden is imposed on another:

- **A person's decision (§4)** — the pull request, and their stated reason
  quoted from where you read it.
- **Referent destroyed** — the path, plus the commit or ref that shows the
  deletion, plus how you distinguished deletion from relocation: which
  checkouts, refs, and name forms you searched.
- **Superseded by merge** — the pull request number and its merge timestamp.
- **Premise falsified** — the assumption quoted from the node, and the fact that
  falsifies it.

A cancellation nobody can audit from the node is one you do not make.

**Never re-open a settled decision.** When a task is cancelled because a person
already decided or because a pull request merged, that decision is settled.
Reconcile records the fact, deletes any stale instruction or note that the
decision overtook, and moves on. It never re-opens the decision, never files
follow-up questions asking whether to revert, ratify, or let stand, and never
treats the settled outcome as an unresolved controversy. Where a world-fact
cancellation under premise falsification or referent deletion leaves an
unanswerable ambiguity, record the observed fact on the node and return unblocked
dependents to `inbox` (§7); §4 is the standing exception for filing an
investigation on a recorded rejection.

## 6 — Route the completed-but-uncertified

A unit whose work landed but whose record carries no certification verdict is not
done. These sit at `done` — terminal, and so outside the set step 1 loaded — so
this step needs its own read: the units closed inside your window, checked for a
verdict on the record. After an absence it is the largest thing a sweep finds,
and it is the one finding that cannot sit in a report: collect these and hand them onward to the
dispatcher, which commissions the review machinery and records its verdict on the
task record.

You certify none of them yourself. You did not do the work and you are not the
reviewer, and a worker's own "confirmed" on a task record is a claim, not a
verdict — read it as one more thing needing certification.

## 7 — Return the affected tasks to `inbox`

**Re-plan when the wave lands.** A merged pull request settles assumptions that
other tasks were built on; a rotted artifact invalidates the criteria that named
it. Neither is yours to re-plan, and both change what should happen next.

Collect the tasks a fact you wrote actually touched:

- what the completed unit's `depends_on` edges unblocked, and its live siblings
  under the same parent;
- anything whose `## Assumptions` names a belief the landed work tested — the
  probe that came back is the case this exists for;
- everything §5 demoted for rot;
- what a §5 cancellation unblocked or invalidated — the cancelled node is
  terminal and does not itself return, but its live siblings and anything whose
  criteria leaned on it do;
- the investigation tasks §4 filed.

Set that whole set back to `inbox`, annotated with the fact that moved it,
using the two-step mutation contract:

1. Append the annotation to the task body (`pkb__append` or `pkb__update_body`).
2. Update the frontmatter status explicitly via `pkb__update_task(id="<task-id>", updates={"status": "inbox"})`.
3. Verify readback immediately with `pkb__get_task(id="<task-id>")`.
   Do NOT use `pkb__batch_update` for status mutations or demotions (it drops status payloads silently).

`inbox` is the signal that a task needs working out again; re-planning is a
separate act, on the user's call, and none of it is yours. You do not re-sort
their assumptions, re-rank their forks, re-cut them, or promote them.

## 8 — Emit one result

One synthesized result for whoever called you, whatever the sweep touched. Never
a per-task feed: a caller who has to read twenty rows to find the two that matter
has been handed your sweep instead of its outcome.

Lead with what needs a person's decision, then what you changed, then what you
found and deliberately left alone, then what you returned to `inbox`. Report
**cancellations as their own category**, never folded in with demotions or
completions: for each, the id, which trigger fired — a person's recorded
decision (§4), referent destroyed, superseded by merge, premise falsified — and
the evidence you wrote to the node for that trigger. Name ids for everything
completed, cancelled, requeued, demoted, routed, surfaced, or handed on — a
bare count is not checkable. Close with the one thing the next sweep should pick
up, and with the window you covered — a result that does not say where you
stopped leaves the next sweep no way to start.

## Must not

- Close, cancel, or complete anything because it is old, quiet, or inconvenient.
  Age is a candidacy signal and nothing more.
- Cancel anything without the evidence its own trigger requires, written into
  the node body (§5) — and, where you claim a referent was destroyed, without
  the deletion-versus-relocation check. Where the two cannot be told apart,
  demote instead.
- Re-open, adjudicate, or second-guess a decision a person has already recorded —
  including merged pull requests (never propose revert/ratify/let-stand, never
  treat a merge as premature, wrong-base, or conflicting with prior notes).
- Append a demotion, rot, or cancellation note to a task's body without also
  mutating its frontmatter `status` via `pkb__update_task`. Leaving a task at
  `status: queued` or `status: ready` while its body says demoted/cancelled is
  strictly forbidden.
- Use `pkb__batch_update` to mutate task statuses or perform demotions (use
  `pkb__update_task` per node and verify with `pkb__get_task`).
- Resolve an acceptance criterion that needs interpreting, or supply the
  judgment a person has not made.
- Prune, restructure, merge, or re-parent anything.
- Write `focus_score`, `intent`, `priority`, or `severity`.
- Promote work into `queued`. That gate is the user's.
- Re-plan: re-sort assumptions, design probes, cut units, or write briefs.
- Certify work, or relay a worker's self-report as a certification verdict.
- Decide by pattern where prose is what decides. Mechanical matching is for
  structured surfaces only — a frontmatter field, a recorded branch, a pull
  request's own structured references. Anywhere the answer lives in prose, read
  it, or hand that one question to an agent that will.
- Re-implement this procedure inside another skill, or run a second sweep beside
  it.
- Modify installed runtime plugin directories (`~/.gemini/config/plugins/`, `~/.claude/plugins/`) directly — framework updates must be made in tracked source checkouts.

## Fitness test

From your result alone — without opening the graph — the caller can say which
in-flight claims are still live and why, what you changed and on which ids, what
you cancelled and on what affirmative evidence, what is now waiting on a person,
and which tasks went back to `inbox` and on what fact. If any of those needs
re-deriving, the sweep is not done.
