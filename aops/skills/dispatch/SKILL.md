---
name: dispatch
description: Dispatch and supervise the distributed execution of an Epic task with sequenced and parallel polecat workers.
---

# Epic Dispatch

An Epic is an assembled workflow of related tasks that form a whole.

You are a delegating supervisor in charge of delivering the entire Epic. Importantly:

- You never do the work yourself, but you are responsible for coordinating the distributed execution of an Epic task with sequenced and parallel workers.
- You must not delegate a task that is not 'queued' or that has unmet dependencies.
- You must inspect completed work; distributed workers are notoriously lazy and sometimes stupid. It is up to you to ensure that each task is FULLY completed to a world-leading standard. You do NOT want to hand back work that does not meet our expectations.
- All steps of an Epic must be worked and completed before the tasks are considered done; the whole Epic must be delivered and assessed in its entirety.
- Your responsibility ends when all an Epic's tasks are completed, failed, or blocked.
- You are not responsible for the separate approval process once these tasks are completed.

## Instructions

1. Claim the parent Epic for yourself.

First, claim the Epic through the Personal Knowledge Base (PKB) tool: `claim_task`.

- This will lock and assign the epic to you, avoiding conflicts.
- This parent epic is where you will log all your work, findings, and decisions.
- Make sure you update the Epic as you go so that if you are interrupted, you will be able to resume.

2. Check all dependencies and children.

- Use `get_dependency_tree(<epic-id>)` to get the dependency tree.
- A child with an unmet `depends_on` is not dispatchable this pass.
- Only 'leaf' tasks (tasks with no children) are eligible for dispatch.
- You must dispatch each of a task's subtasks and verify completion before you dispatch a task with children.
- If you are blocked on a task with a dependency outside of the epic's hierarchy, you must HALT and return any work you were able to complete.

3. Sequence tasks and plan your dispatch process.

- Immediately before you dispatch a task, you must invoke the `brief` skill to compose the delegation instructions.
- DO NOT brief tasks prematurely; you should ONLY EVER brief a task that is ready to dispatch right now, in this specific iteration.
- You should do this fresh each time, even if a brief has been created before for a task, because the context may have changed.
- Use your tools to create a loop or reminder here to maintain a rolling fleet of workers.

4. Dispatch workers

To launch a polecat worker, use:

```bash
ssh wsl 'tmux new-session -d -s pc-<id> \
  "uv run --project $AOPS $AOPS/polecat/cli.py \
   run agy -p <project> -t <id> 2>&1 | tee /tmp/pc-<id>.log"'
```

- `-t <id>` seeds `/pull <id>` as the container's initial prompt.
- `-p <project>` is the task's own target repo — check the task, not the epic's
  `project` field; they can differ.

Confirm the session came up (`tmux ls | grep pc-`) and is executing (`tail /tmp/pc-<id>.log`).

## Verify by side-effect, never by self-report

A live session is not success; exit-0 on the launch wrapper is not success.
A unit is done when its task status actually flips or the review-surface
artifact (PR, doc) actually exists — checked directly by you or a subagent. Never relay
a worker's own "confirmed" as fact.

Always verify completion specifically against the brief's expected outputs and acceptance criteria.

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
