---
name: epic-dispatch
description: Walk an epic's task graph and dispatch every currently-unblocked leaf to a background worker, repeating as workers exit and clear new leaves. Use when an epic has multiple ready subtasks — including decompose's standing pauli/rbg/marsha review tasks — that can advance in parallel. Not for single-task execution (`/pull`) or planning (`/decompose`).
---

# Epic Dispatch

You are advancing an epic's task graph, not working a checklist. `decompose`
already cut the DAG and wired pauli/rbg/marsha as blocking dependencies —
your only job is walking that graph and firing whatever it says is ready.
Architecture is decompose's call; this is dispatch-time judgment only.

## Read edges, not children

`get_dependency_tree(<epic-id>)` — a child list is not ready work. A child
with an unmet `depends_on` is not dispatchable this pass, however it looks in
a flat list. Dispatch only leaves with no unmet dependency.

If a subtask is a **de-risking spike** — its finding could reshape what
comes after it — treat everything downstream as blocked on your judgment of
that finding even where no `depends_on` edge says so yet. Once you've read
the finding, either clear the block or file the edge for real, so the next
pass doesn't need you to remember it.

## Brief and dispatch each ready leaf

For every unblocked leaf, invoke `brief` — it composes the delegation brief,
persists it to the task body, and hands off by task-id reference. This
applies uniformly to review tasks: dispatch pauli/rbg/marsha's tasks the same
way, when their own dependencies clear. Reviewer ≠ executor falls out of
that automatically.

Launch one worker per ready unit:

```bash
ssh wsl 'tmux new-session -d -s pc-<id> \
  "uv run --project ~/src/academicOps ~/src/academicOps/polecat/cli.py \
   run agy -p <project> -t <id> 2>&1 | tee /tmp/pc-<id>.log"'
```

`-t <id>` seeds `/pull <id>` as the container's initial prompt. `-p
<project>` is the task's own target repo — check the task, not the epic's
`project` field; they can differ. Confirm the session came up (`tmux ls |
grep pc-`) and is executing rather than fast-failing (`tail
/tmp/pc-<id>.log`) before moving to the next. For tmux/polecat mechanics
beyond this launch shape (send-keys, log locations, gotchas), see
`specs/polecat/tmux-interactive-driving.md` — don't duplicate it here.

## Verify by side-effect, never by self-report

A live session is not success; exit-0 on the launch wrapper is not success.
A unit is done when its task status actually flips or the review-surface
artifact (PR, doc) actually exists — checked directly by you or a cheap
independent read, per `specs/enforcement/evidence-contract.md`. Never relay
a worker's own "confirmed" as fact.

## Watch for exits, don't poll

Wait on worker exit through a background-task notification or a `Monitor` on
the launch session — never a sleep loop. When one exits: verify its
side-effect, re-read the graph for whatever that unblocked, dispatch that.
Workers coordinate through `claim_task`'s atomic claim, not through you — you
don't need your own lock.

## React to what comes back

A FAIL or re-dispatch call from a review task is not a separate phase — it's
new information the next graph pass reads like any other. If a review found
something, decide (your judgment, not a lookup table) whether to file a fix
subtask wired with `depends_on` back to the failed unit, or re-dispatch the
same unit with the finding appended to its brief. Either way, wire it into
the graph rather than holding it in your head — the next pass has to see it
without you.

## Judgment stays with Nic

A spike finding that reshapes architecture, methodology, or anything
published under his name gets surfaced to him directly — don't auto-dispatch
the next phase off your own reading of it. If a finding needs his call
before anything downstream can proceed, set the blocked task to `review`;
dispatch skips it there until he moves it back to `queued`.
