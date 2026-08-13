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

## 3. Choose a mode, as long as it is isolated in a container!

### Give the worker enough wall clock

A headless agent that outruns its print timeout is killed mid-work and returns
nothing — the launch looks clean and the task looks untouched. `agy` defaults to
`5m0s`, which is under both tiers, so every dispatch sets its own:

- **Container dispatch: 30 minutes minimum.** Export `POLECAT_PRINT_TIMEOUT=30m`;
  polecat forwards it to the worker's `--print-timeout`.
- **Local invocation: 10 minutes.** Pass `--print-timeout 10m` alongside `-p`.

The value is a **Go duration string** — `30m`, `10m`, `45m` — never a unitless
integer. `agy` rejects `--print-timeout 900000` at flag parse — `missing unit in
duration` — and the worker never starts.

### Local subagent team

**If you are already running inside an isolated container**, do not start a new container for your workers. Instead, you may:

- dispatch using your native tools to a 'subagent team' or `/teamwork-preview`, where you will play an active role as the coordinator of work, delegate verification and iterative development loops, and be responsible for its final delivery stage.
- dispatch background agents directly within your container by calling `agy` or `claude` with a headless prompt (`-p`). You may like to make sure they use their own worktree if you will be running multiple agents in parallel, but you will have to reconcile the changes when they return.

### Polecat (worker containers)

If you are not running within a container, you should use the 'polecat run' command to dispatch a team of workers in an isolated environment.

All dispatches use a standard `polecat run` command wrapped in a detached `tmux` session.

#### 1. Command Template

Define the session identifier and build the launch command:

```bash
NAME="dispatch-<task-id>"
CMD="uv run python3 '${CLAUDE_PLUGIN_ROOT}/polecat/cli.py' run agy -p <project> -t <task-id> -s $NAME"
```

#### 2. Launch (Local vs Remote)

Run the session locally or remotely depending on where the target Docker daemon lives:

- **Local:**

```bash
tmux new-session -d -s "$NAME" "$CMD"
```

- **Remote:**

```bash
ssh "$POLECAT_HOST" "tmux new-session -d -s $NAME '$CMD'"
```

#### 3. Post-Launch Workflow

Choose **one** monitoring approach based on whether you need the result immediately:

- **Fire-and-Forget (Default for task queues):** Confirm dispatch and move on immediately.

```bash
tmux has-session -t "$NAME" && echo "dispatched: $NAME"
```

- **Synchronous (Single task/blocking dependency):** Poll until the session finishes.

```bash
while tmux has-session -t "$NAME" 2>/dev/null; do sleep 30; done
```

#### Critical Rules

- **Match session identifiers:** The `-s` flag must always match the `tmux` session name (`$NAME`).
- **Use `-p <project>` for target repos:** Never use `-d` with a linked git worktree, only full checkouts (worktree `.git` files point outside container mounts and break git commands).
- **No interactive flags:** Never add interactive flags to autonomous dispatches; doing so causes workers to idle at prompts indefinitely.
- **Environment defaults:** Do not pass paths, images, or git credentials manually—Polecat loads these directly from the host environment.
- **Never force-kill synchronous waits:** Killing the wait script can orphan uncommitted work in the host workspace and leave tasks permanently claimed.

## 4. Report

Return:

- Each task dispatched: task ID, title, session name, and **which mode** — a
  fire-and-forget report claims a launch, a synchronous one claims an outcome.
- Each failed dispatch: task ID and reason.
- The **count** of ineligible and undispatched tasks — not a list of them — and
  how many of those should become eligible next pass if every running container
  succeeds.
