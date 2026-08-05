---
name: dispatch
description: Coordinator-side pathway to a worker surface — a supervised in-session team or an isolated polecat container. The mandatory route to `polecat run`; a raw invocation outside this skill bypasses the delivery-guard and image-freshness obligations below.
---

# Dispatch

Assign eligible tasks to workers and return. You never do the work, and you make
no planning decisions — those are out of scope and belong upstream.

**Quick failures are high-value information.** If a task cannot be dispatched,
report the problem; do not investigate alternatives. Partial completions are
routine — do what you can and name what you could not.

**Payload boundary.** Send child workers only target task IDs and explicit delta
inputs, never raw context.

## 1. Read the graph, and dispatch blockers and children first

**Eligible** = fully specified · `queued` · dependencies met · children completed
· inside the hierarchy you were given.

- A task with an unmet dependency is not dispatchable this pass.
- A task with internal subtasks is dispatched whole, or not at all.
- Dispatch eligible tasks in parallel, sequentially only where a dependency or an
  overlapping surface forces it.
- Return ineligible tasks intact for the next pass — do not modify them.
- **Do not stray.** A dependency outside the epic's hierarchy blocks you: halt
  and return what you completed.

A dependency whose own record shows the awaited work already done, but whose
status has not been advanced, is **not** met. Report the contradiction and move
on; resolving it is a planning decision.

## 2. Check image freshness before the first launch

A container runs the framework baked into its image, not the tree you are
sitting in. A stale image silently runs old skills, hooks and `lib/`, and its
output looks like a current-code result.

```bash
docker image inspect "$POLECAT_IMAGE" --format '{{.Created}}'
```

Compare against the last build of the tree the work targets. If the image
predates changes the task depends on, say so in your report and dispatch anyway
only if the task does not touch the drifted surface. Never rebuild here.

## 3. Choose a mode, then launch under tmux either way

Every launch runs inside a **named detached tmux session**, whichever mode you
pick. The session name and `-s` must match, so the tmux session, the host log
directory and the workspace all carry one identifier and you interact with a
worker the same way in both modes.

`polecat run` is a **foreground** command — `docker run --rm`, no detach flag.
It does not return a container ID, and its exit code is the run's outcome, not a
launch receipt. tmux, not polecat, is what makes a dispatch asynchronous.

```bash
NAME="dispatch-<task-id>"
tmux new-session -d -s "$NAME" \
  "uv run python3 '${CLAUDE_PLUGIN_ROOT}/polecat/cli.py' run agy -p <project> -t <task-id> -s $NAME"
```

- `-t <task-id>` seeds `/pull <task-id>` and runs headless, so the worker
  executes the task and exits. **Never add an interactive prompt flag to an
  autonomous dispatch** — that leaves a container idling at a ready prompt
  forever, which looks like progress and finishes nothing.
- `-p <project>` is the task's own target repo. Read it off the task, not the
  parent; they differ more often than you would expect.
- Use `-p <project>`, never `-d` with a linked git worktree — `-d` mounts the
  path as given, and a worktree's `.git` points outside the mount, so every git
  command in the container fails.
- Every path, image, endpoint, and the committing git identity comes from the
  environment. If one is missing polecat fails loudly — supply nothing yourself.

To dispatch to a remote docker host, run the whole tmux invocation there — the
tmux session must live beside the docker daemon, not on your side of the link:

```bash
ssh "$POLECAT_HOST" "tmux new-session -d -s $NAME '<the launch command above>'"
```

Interaction is identical in both modes; the mechanics and their gotchas are in
[`specs/polecat/tmux-interactive-driving.md`](../../../../specs/polecat/tmux-interactive-driving.md).

### Fire-and-forget

The default for a queue you are working through. Launch, confirm the tmux
session exists, and move to the next task.

```bash
tmux has-session -t "$NAME" && echo "dispatched: $NAME"
```

That check is the whole of your launch evidence. **Do not wait, do not poll, do
not attach.** The result arrives on the task record.

**What this mode gives up.** For a seeded `agy` dispatch, polecat runs a
delivery guard: after the container exits it confirms the agent's transcript
actually shows the task id, retries once if not, and refuses to report success
on an unverified seed. That verdict is written to a tmux pane nobody reads. A
fire-and-forget dispatch is therefore **not evidence the task was worked** —
only that a container started. Reap it later (§4) or let the task record speak.

### Synchronous

Use when you must know the outcome before your next decision — a single task, a
dependency the rest of the pass hangs on, or a run you intend to record a status
for. Launch as above, then wait on the session rather than on a fixed timer:

```bash
while tmux has-session -t "$NAME" 2>/dev/null; do sleep 30; done
```

**Never cap the wait with a timeout you are willing to enforce.** Killing the
command kills a healthy worker mid-edit, orphans its uncommitted work in the
host workspace, and can leave a claimed task with no one working it. If you
cannot afford to wait, you wanted fire-and-forget.

On completion you have a real verdict — the delivery guard has run — so you may
record status on the task record. Record what the run evidences and nothing
more: a clean exit with a confirmed seed is not a claim the work is correct or
complete.

## 4. Reap and report

For every fire-and-forget dispatch you are asked to account for, read the
durable state — never the pane, which dies with the session:

```
$AOPS_SESSIONS/logs/<YYYYMMDD>/<session-id>/<project>/
```

A dispatch that ended without reaching a terminal state leaves uncommitted work
on `polecat/<session-id>` in its host workspace. Name it on the task record so
the next pass does not silently redo it. Never integrate it here.

Return immediately:

- Each task dispatched: task ID, title, session name, and **which mode** — a
  fire-and-forget report claims a launch, a synchronous one claims an outcome.
- Each failed dispatch: task ID and reason.
- The **count** of ineligible and undispatched tasks — not a list of them — and
  how many of those should become eligible next pass if every running container
  succeeds.
