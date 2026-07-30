---
name: dispatch
description: Dispatch and supervise the distributed execution of a task with children — routing each unit to the right worker surface (polecat container, in-session subagent, or agent team) and holding the epic until every unit reaches a terminal state.
agent: "aops-ida:james"
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

**Polecat launch.** The plugin ships the CLI at `${CLAUDE_PLUGIN_ROOT}/polecat/cli.py`. A container emits no completion signal of its own, and a detached session's report reaches nobody. Dispatch every container inside a plain background subagent — the courier — which runs the CLI in the foreground, waits for the container to exit, and returns the harvested result as its own final message. That final message is what the harness delivers back to you.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/polecat/cli.py" run agy -p <project> -t <task-id>
```

The courier's brief must require it to:

- run that command in the foreground — never detached, never under `tmux`, and never spawning subagents of its own;
- take the exit code directly rather than through a pipe, because `cmd | tail` reports the pipe's status and will report success over a container that aborted;
- read the return contract off the task and quote it, rather than summarising its own shell output;
- carry the entire result in its final message, because nothing it says earlier reaches you.

Spawn couriers plainly. A named or teammate-mode spawn returns an idle signal and strands the report where no one reads it.

- `-t <task-id>` seeds `/pull <task-id>` as the container's initial prompt and runs headless, so the worker executes the task and exits. Never add an interactive prompt flag to an autonomous dispatch — that leaves a live container idling at a ready prompt forever, which looks like progress and finishes nothing.
- `-p <project>` is that task's own target repo. Check the task, not the epic — they differ.
- Every path, image, endpoint, and the committing git identity comes from the environment. If one is missing polecat fails loudly; supply nothing yourself.

**Rebuild before a run whose result you intend to certify.** The image carries the plugin code the worker runs, and `make docker-build` builds it from the working tree as it stands — so a certifying run starts from a clean committed tree and a fresh build. Nothing checks this for you. Instruction state does not travel that path at all: project skills, `CLAUDE.md`, and the project rule layer reach the worker from the mounted workspace, so a committed change to those is already live.

## 4. Verify by side-effect

A live session is not success. Exit zero on the launch wrapper is not success. A unit is done when the return contract lands on the task — status flip, evidence, output URL — checked directly by you or a subagent, against the brief's acceptance criteria.

**Then certify it, and record the verdict.** A unit that has landed is not finished until its certification is on the task record. Commission that certification through the review machinery already wired into the graph — the review nodes decomposition emitted as blocking dependencies — and write back the verdict it returns. Reach each node through the agent that owns the skill it names: `strategic-review` is yours to run; `verify` is marsha's, so you commission her rather than invoke it. Executing those nodes _is_ certification at completion; standing a second review beside them gives you two paths and one of them unread.

**You cannot certify from a context that cannot spawn.** Commissioning a review means deploying reviewers, so check that you hold the surface before you take this on. If you do not, hand the unit to a context that does and say so — never read the artifact yourself and call that the verdict. A gate that returns neither a verdict nor a failure is the one outcome this step must not produce.

Quality assurance inside the unit is the worker's business, and the judgment is the reviewer's; substitute your own certification for neither. Never relay a worker's own "confirmed" as fact — commissioning the review and recording what it returns is the whole of your part in it.

## 5. Watch for exits, do not poll

The courier's completion notification is the signal. Wait on it — never a sleep loop, and never a poll against the container. When one lands: verify its side-effect, re-read the graph for whatever that unblocked, dispatch that. Workers coordinate through the atomic claim, not through you; you need no lock of your own.

A courier that returns an acknowledgement instead of a result has failed its brief, whatever the container did. Send it back.

## 6. React to what comes back

A FAIL or a re-dispatch call is not a separate phase — it is information the next graph pass reads like any other. Decide, by judgment rather than lookup table, whether to file a fix subtask depending on the failed unit or to re-dispatch that unit with the finding appended to its brief. Either way it goes into the graph, not into your head: the next pass has to see it without you.
