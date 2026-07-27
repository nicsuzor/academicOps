---
name: dispatch
description: Dispatch and supervise the distributed execution of a task with children — routing each unit to the right worker surface (polecat container, in-session subagent, or agent team) and holding the epic until every unit reaches a terminal state.
agent: "aops:james"
---

# Dispatch

The mandatory pathway to a polecat container. A raw `polecat run` outside this skill bypasses the dispatch contract.

An epic is just a task with children. You are the supervisor delivering the whole of it: you never do the work, you coordinate sequenced and parallel workers, and your responsibility ends only when every unit is `done`, `partial`, `failed`, or `blocked`. `partial` is a legal, expected handback, not a failure — read it as new graph information, confirm its continue-tasks exist, and route the remainder.

## 1. Claim the epic

Claim it through the knowledge base. That locks it to you and gives you the one place to log findings and decisions. Update it as you go: if you are interrupted, that record is how the next pass resumes.

## 2. Read the graph

Pull the dependency tree. A child with an unmet dependency is not dispatchable this pass.

**Eligibility** = fully specified + queued + dependencies met — regardless of whether it has children. A task with children may go whole to one worker, who owns its internal sequencing and returns **one** deliverable: evidence plus an output URL on the task.

**Consolidate.** If you do route children separately, the workflow must still converge on one deliverable — never a spray of per-child pull requests reviewed individually. This duty is not scoped to one epic: before dispatching anything, check for other ready tasks touching the same file or subsystem, siblings in other epics included, and bundle them into one worker producing one pull request whose body lists every task id, tested together.

A dependency outside the epic's hierarchy blocks you: halt and return whatever you completed.

## 3. Brief, then dispatch

Compose the delegation brief immediately before dispatching — never earlier, and freshly each time even if that task was briefed on an earlier pass, because the context has moved.

Choose a surface and a cadence per task. Cadence is a routing detail; the review shape does not depend on it.

- **In-session subagent** — needed now, mechanical or exploratory, results reconciled in this session.
- **Agent team** — parallel work you supervise to a single reconciled result.
- **Polecat container** — substantial autonomous repo work landing a durable artifact. Higher latency; wrong for anything needed now.

**Polecat launch.** The plugin ships the CLI at `${CLAUDE_PLUGIN_ROOT}/polecat/cli.py`. Launch it detached under `tmux` so the session survives your turn:

```bash
tmux new-session -d -s "pc-<task-id>" \
  "python3 \"${CLAUDE_PLUGIN_ROOT}/polecat/cli.py\" run agy -p <project> -t <task-id>"
```

- `-t <task-id>` seeds `/pull <task-id>` as the container's initial prompt and runs headless, so the worker executes the task and exits. Never add an interactive prompt flag to an autonomous dispatch — that leaves a live container idling at a ready prompt forever, which looks like progress and finishes nothing.
- `-p <project>` is that task's own target repo. Check the task, not the epic — they differ.
- Every path, image, and endpoint polecat needs comes from the environment. If one is missing it fails loudly; supply nothing yourself.

Confirm the session came up and is executing before you treat it as dispatched.

## 4. Verify by side-effect

A live session is not success. Exit zero on the launch wrapper is not success. A unit is done when the return contract lands on the task — status flip, evidence, output URL — checked directly by you or a subagent, against the brief's acceptance criteria.

Quality assurance inside the unit is the worker's business, and independent review is the reviewer's; substitute your own certification for neither. Never relay a worker's own "confirmed" as fact.

## 5. Watch for exits, do not poll

Wait on worker exit through a background-task notification or a monitor on the launch session — never a sleep loop. When one exits: verify its side-effect, re-read the graph for whatever that unblocked, dispatch that. Workers coordinate through the atomic claim, not through you; you need no lock of your own.

## 6. React to what comes back

A FAIL or a re-dispatch call is not a separate phase — it is information the next graph pass reads like any other. Decide, by judgment rather than lookup table, whether to file a fix subtask depending on the failed unit or to re-dispatch that unit with the finding appended to its brief. Either way it goes into the graph, not into your head: the next pass has to see it without you.
