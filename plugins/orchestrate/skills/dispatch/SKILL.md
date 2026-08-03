---
name: dispatch
description: Coordinator-side pathway to a worker surface — a supervised in-session team or an isolated polecat container. The mandatory route to `polecat run`; a raw invocation outside this skill bypasses the delivery-guard and image-freshness obligations below.
agent: "james"
---

# Dispatch

Assign eligible tasks to workers and return. You never do the work, and you make
no planning decisions — those are out of scope and belong upstream.

**Confirming a launch is not waiting for a result.** These are different acts and
only one of them is forbidden:

- **Startup confirmation — required, once.** A dispatch that silently failed to
  start is indistinguishable from one running well, so you check once that the
  container exists, and that check is bounded.
- **Completion polling — never.** A container emits no completion signal of its
  own, and its result arrives on the task record, not back through you. Waiting
  on one blocks the dispatcher for the length of the work it just delegated.

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

## 2. Dispatch whole tasks, asynchronously, by task ID

```bash
uv run python3 "${CLAUDE_PLUGIN_ROOT}/polecat/cli.py" run agy -p <project> -t <task-id>
```

- `-t <task-id>` seeds `/pull <task-id>` and runs headless, so the worker
  executes the task and exits. **Never add an interactive prompt flag to an
  autonomous dispatch** — that leaves a container idling at a ready prompt
  forever, which looks like progress and finishes nothing.
- `-p <project>` is the task's own target repo. Read it off the task, not the
  parent; they differ more often than you would expect.
- Prefix with `ssh $POLECAT_HOST -c ...` to dispatch to a remote docker host.
- Every path, image, endpoint, and the committing git identity comes from the
  environment. If one is missing polecat fails loudly — supply nothing yourself.

Polecat returns the container ID on success. Then confirm startup once, and only
once:

```bash
docker ps -a --filter "name=<polecat_id>"
```

If polecat itself failed, or the container is absent, mark the task failed
immediately with a succinct reason on its record.

## 3. Return immediately

- Each task dispatched: task ID, title, container ID.
- Each failed dispatch: task ID and reason.
- The **count** of ineligible and undispatched tasks — not a list of them — and
  how many of those should become eligible next pass if every running container
  succeeds.
