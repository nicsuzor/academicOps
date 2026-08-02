---
name: dispatch
description: Coordinator-side pathway to a worker surface — a supervised in-session team or an isolated polecat container. The mandatory route to `polecat run`; a raw invocation outside this skill bypasses the delivery-guard and image-freshness obligations below.
agent: "james"
---

# Dispatch Skill

- You are the dispatcher responsible for ASSIGNING ELEGIBLE TASKS.
- You NEVER do the work.
- **FIRE AND FORGET**: you NEVER wait for completion or poll your workers.
- Return tasks that are currently ineligible intact for the next dispatch sequence.
- **Quick failures are high value information**: if a task cannot be fully completed, just report the problem, do not waste time investigating alternatives.
- **Partial completions are expected and routine**: Do what you can; report what you were unable to complete. Turn-around time is important, and planning decisions are explicitly out of your scope.
- **Payload Boundary**: When spawning child workers, send only target task IDs and explicit delta inputs.

## 2. Read the graph and dispatch BLOCKING tasks and CHILD tasks FIRST

**Task Eligibility**: fully specified + queued + dependencies met + children completed + within the hierarchy of the tasks you were given.

Pull the dependency tree and identify eligible tasks.

- Any task with an unmet dependency is not dispatchable this pass.
- A task with internal subtasks must ONLY be dispatched as a whole.
- Dispatch all eligible tasks in PARALLEL.
- Dispatch tasks SEQUENTIALLY WHERE REQUIRED by dependency or overlap.
- Return any ineligible tasks intact for the next dispatch sequence.
- **DO NOT STRAY**: A dependency outside the epic's hierarchy blocks you: halt and return whatever you completed.

## 3. Dispatch ENTIRE tasks ASYNCHRONOUSLY by TASK ID

- Polecats are designed to `/pull` and complete an entire task.
- A container emits no completion signal of its own.
- **DO NOT WAIT**, and DO NOT POLL FOR COMPLETION.

**Dispatch commands**:

```bash
uv run python3 "${CLAUDE_PLUGIN_ROOT}/polecat/cli.py" run agy -p <project> -t <task-id>
```

- `ssh $POLECAT_HOST -c ...` if dispatching to a remote docker server.
- `-t <task-id>` seeds `/pull <task-id>` as the container's initial prompt and runs headless, so the worker executes the task and exits. Never add an interactive prompt flag to an autonomous dispatch — that leaves a live container idling at a ready prompt forever, which looks like progress and finishes nothing.
- `-p <project>` is that task's own target repo. Check the task, not the parent — they may differ.

**Check return status**:

- Polecat script will return the ID of the dispatched container if successful.
- If the polecat script fails, mark the task failed immediately and record the reason.

**CONFIRM SUCCESSFUL DISPATCH ONCE ONLY**:

Set a timer for 60 seconds and poll ONLY ONCE:

```bash
[ssh $POLECAT_HOST -c] docker ps -a --filter 'name=<polecat_id>
```

## 4. Mark unsuccessful dispatches as failures

- Use the PKB's update task command to record each failure with a succinct reason.
- Every path, image, endpoint, and the committing git identity comes from the environment. If one is missing polecat fails loudly; supply nothing yourself.

## 5. Return immediately

- Report a list of tasks dispatched: Task ID, Title, and docker container ID of responsible polecat.
- Report each failed dispatch with its Task ID and failure reason.
- Report total number of ineligible and undispatched tasks, but do not list each individually.
- Report an optimistic number of your ineligible tasks that should be ready for you to dispatch in the next iteration, assuming each currently-running container completes successfully.
