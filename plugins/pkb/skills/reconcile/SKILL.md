---
name: reconcile
description: Establish what is actually true about work the graph still claims is in flight, and about work that finished while nobody was watching. Probes stale claims and requeues the dead ones, folds in merged and closed pull requests, and routes completed-but-uncertified units onward for certification. Fires on engagement after an absence, inside the consolidation cycle, and on demand.
agent: "aops-pkb:pauli"
---

# Reconcile

The graph is a set of claims about work, and a claim outlives the session that
made it. A worker dies mid-task and its claim sits `in_progress` forever. A pull
request merges unwatched and the task it closes never moves. A task's acceptance
criteria name files that were renamed away a fortnight ago. You establish what is
**actually** true, and you write that back.

This is the only place the reconcile procedure lives. Other skills invoke it;
none of them re-implements it. What it governs is tasks and the pull requests
they resolve against. Issue-tracker closure in the other direction — a task's
completion resolving an issue — belongs to the release path, not here.

## Contexts

One procedure. The context sets the input subset — never the steps.

| Context        | Input subset                                                                              |
| -------------- | ----------------------------------------------------------------------------------------- |
| **Engagement** | The absence window: claims taken before it, pull requests closed during it.               |
| **Batch**      | The consolidation cycle's window, at that cycle's pacing.                                 |
| **On demand**  | Everything: every non-terminal task, every pull request closed since the recorded cursor. |

The reverse direction — a task completing, and what its completion resolves on
the issue tracker — belongs to the session-exit skill that releases the task, not
here.

## 1 — Read the graph, claims included

`list_tasks` over **every non-terminal status** — the actionable set as
[the taxonomy](../graph-maintenance/references/taxonomy.md) defines it, which is
the source; never a copy of the list inlined here. Not only the statuses that look
in flight: §3 resolves `merge_ready` and `review`, §5 reads `ready` and `queued`
for rot and the parked statuses for age, and §2 and §4 write back to `ready` and
`inbox`, which the next sweep has to be able to see. A sweep that loads a subset
reports itself complete while silently skipping whole classes of work.

Then read the **claim** on each: who holds it, under which session, and when it
was taken — the `Dispatched:` record a dispatch surface writes at launch, and the
assignee and session on the task itself. A status by itself is not a claim. The
assignee and the session are what make it one, and they are what you check.

Filter the slice before you pull it. An unfiltered `list_tasks` on a mature graph
spills to a temp file, and then you have lost the turn rather than gained the
data. Narrow by status or project, take the default markdown format, and repeat
until the whole set is covered — many narrow calls, never one wide one.

## 2 — Probe every suspect claim, then confirm it or requeue it

A claim is **suspect** when the session behind it is plausibly over: nothing
written to the task since it was taken, and enough time gone that a live worker
would have said something. Suspect is a reason to probe. It is never a verdict.

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

**The cursor** is the timestamp the last completed sweep recorded on its own
result, and it is the only thing that bounds this step. Read it before you start;
where a caller handed you a window instead, that window is the cursor for this
run. Where neither exists — a first sweep, or a result you cannot find — say so
in what you emit and bound the step yourself by the oldest claim you loaded,
rather than treating an unbounded scan as a completed one.

For each pull request closed since the cursor, match it to a task by, in order: a
`pr_url` already on the task; a task id in the pull request body; the head branch
matching the task's recorded branch; the title matching the task title
whole-word, ignoring conventional-commit prefixes. A reverse match on distinctive
title substrings is surfaced as _likely closed by_ and **never auto-completes**.

- **Merged** → re-read the task's acceptance criteria against the merged artifact
  before closing. Every criterion clearly met → complete it, recording the pull
  request and the date. Any criterion unmet or needing judgment → leave it and
  surface the criterion, quoted. Surface, do not block.
- **Closed without merge** → route it (§4). Never re-queue automatically.
- **No match** → surface it. Never invent a task.

Pull requests only; no commit-log scanning. The cursor advances only after the
writes succeed.

Run a **cursor-independent backstop** over every task in `merge_ready` or
`review`, oldest first. These are not the same parked state. A `merge_ready` task
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
string match — a "wontfix" label is a signal, not the verdict. Exactly one of:

| Class                  | Signal                                                                                    | Action                                                                                                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **wontfix**            | Clear "do not do this", not-planned, superseded, or the reviewer rejects the goal itself. | Cancel the task, or complete it if a sibling superseded it. Record the pull request and the reason in the body. File no follow-up.                                 |
| **bad-implementation** | Wrong approach, design rejected, repeated failure, "needs a rethink", or ambiguous.       | Cancel the original. File a sibling investigation task under the same parent, softly depending on the original, saying what went wrong and what must change first. |
| **retry-as-is**        | Rare. Unrelated infrastructure failure, documented in the comments. Nothing was wrong.    | Re-queue to `inbox`, with the justification written into both the task body and the result.                                                                        |

Record the chosen route, the close reason, and any node created.

## 5 — Staleness and rot

**Aged non-terminal work.** Tasks aged past about ninety days, up to twenty a
sweep. Read the body, then look for completion evidence — sent mail, calendar
entries, commits. Evidence found means complete the task with the evidence
recorded. No evidence means **flag for human review**, never auto-cancel: age is
not evidence of irrelevance. Where the evidence tools are unavailable in this
environment, skip the verification and flag the candidates.

**Artifact rot.** For `ready` and `queued` tasks aged past about a fortnight,
verify that the files and symbols the task's criteria name still exist where they
claim to. Where they have rotted, demote the task to `inbox` with an annotation
saying so, and re-decompose. Rot triggers demotion; age alone does not.

## 6 — Route the completed-but-uncertified

A unit whose work landed but whose record carries no certification verdict is not
done. After an absence it is the largest thing a sweep finds, and it is the one
finding that cannot sit in a report: collect these and hand them onward to the
dispatcher, which commissions the review machinery and records its verdict on the
task record.

You certify none of them yourself. You did not do the work and you are not the
reviewer, and a worker's own "confirmed" on a task record is a claim, not a
verdict — read it as one more thing needing certification.

## 7 — Emit one result

One synthesized result for whoever called you, whatever the sweep touched. Never
a per-task feed: a caller who has to read twenty rows to find the two that matter
has been handed your sweep instead of its outcome.

Lead with what needs a person's decision, then what you changed, then what you
found and deliberately left alone. Name ids for everything completed, requeued,
demoted, routed, or surfaced — a bare count is not checkable. Close with the one
thing the next sweep should pick up, and with the timestamp this sweep reached:
that is the cursor the next one reads, and a sweep that does not record it makes
the next one unbounded.

## Must not

- Close, cancel, or complete anything because it is old, quiet, or inconvenient.
  Age is a candidacy signal and nothing more.
- Promote work into `queued`. That gate is the user's.
- Certify work, or relay a worker's self-report as a certification verdict.
- Decide by pattern where prose is what decides. Mechanical matching is for
  structured surfaces only — a frontmatter field, a recorded branch, a pull
  request's own structured references. Anywhere the answer lives in prose, read
  it, or hand that one question to an agent that will.
- Re-implement this procedure inside another skill, or run a second sweep beside
  it.

## Fitness test

From your result alone — without opening the graph — the caller can say which
in-flight claims are still live and why, what you changed and on which ids, and
what is now waiting on a person. If any of those three needs re-deriving, the
sweep is not done.
