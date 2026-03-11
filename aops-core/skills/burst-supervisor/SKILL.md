---
name: burst-supervisor
type: skill
description: Long-running iterative supervisor — dispatch work items to polecat workers across multiple bursts with state recovery.
triggers:
  - "burst supervisor"
  - "burst-supervisor"
  - "iterative supervisor"
  - "long-running supervisor"
modifies_files: true
needs_task: false
mode: batch
domain:
  - operations
---

# Burst Supervisor

Iterative supervisor for long-running workflows. Dispatches work items to polecat workers in small batches across multiple invocations, with full state recovery between bursts.

## Design Philosophy

**State lives in the tracking task body.** The tracking task's body carries structured state as a YAML code block (queue, dispatches, counters) plus a human-readable progress log. PKB strips unrecognized frontmatter fields, so all supervisor state must be in the body. Any agent can resume by reading the task — no external state files needed.

**Dispatch via polecat.** Workers are invoked through `polecat run -t <task-id>`, which provides worktree isolation, agent invocation (Claude or Gemini via `-g`), auto-finish, and transcript capture. The supervisor never calls agent CLIs directly.

**Burst model.** Each invocation processes one burst: check active dispatches, evaluate results, dispatch new items, persist state, halt. Schedule recurring bursts with `/loop 30m /burst-supervisor <tracking-task-id>`.

## Invocation

```
/burst-supervisor <tracking-task-id>           # Resume existing supervisor
/burst-supervisor init <workflow-description>   # Initialize new supervisor
```

## Phase 1: Load State

Read the tracking task:

```
task = mcp__pkb__get_task(id=<tracking-task-id>)
```

Parse the `supervisor` state from the YAML code block in the task body (fenced with `` ```yaml `` ... `` ``` ``). PKB strips unrecognized frontmatter fields, so supervisor state lives in the body, not frontmatter. If no YAML code block with supervisor state exists, this task hasn't been initialized — error and halt.

Key state fields (inside the body YAML block):

- `queue[]` — ordered work items with per-item status
- `active_dispatches[]` — tasks sent to workers, not yet returned
- `config` — burst size, max attempts, worker type
- `plan` — aggregate counters (completed, failed, remaining)

## Phase 2: Check Active Dispatches and Evaluate Results

For each entry in `supervisor.active_dispatches`:

1. **Load worker task**: `mcp__pkb__get_task(id=dispatch.task_id)`
2. **If worker task status is `done` or `merge_ready`**: proceed to evaluation (Phase 2a)
3. **If worker task is still `in_progress`**:
   - Check age: if dispatched > 4 hours ago, treat as stale
   - Stale + attempts exhausted: mark `failed`
   - Stale + retries remaining: set `status=pending`, increment `attempts`
   - Not stale: skip (worker still running)
4. **If worker task status is `active` or `ready`** (never claimed):
   - This means polecat dispatch failed silently. Log warning, set queue item back to `pending`.

### Phase 2a: Evaluate Worker Output

**No code. No regex. No scoring functions.** Evaluation is a semantic judgment call — the supervisor agent reads the worker's output and decides whether it meets the workflow's criteria. This is what agents are good at.

For each completed worker task:

**Step 1: Gather evidence.** Read the actual work product:

- Read the worker task body for any output or notes the worker left
- If the worker modified files (e.g., a spec file), read those files directly using the Read tool
- If the worker created a PR, check the PR diff: `gh pr diff <pr-number>`
- If the worker's branch exists, compare: `git diff main..polecat/<task-id> -- <relevant-files>`

**Step 2: Read the evaluation criteria.** The tracking task body contains an **Evaluation Criteria** section written in plain language. These criteria are workflow-specific — the person who initialized the supervisor wrote them. Examples:

- For a spec audit: "User expectations section exists, each expectation is testable, no aspirational claims about unimplemented features"
- For document review: "Key findings are summarized, recommendations are actionable, no factual errors"
- For email processing: "Task was created with correct metadata, response draft captures the right tone"

Read these criteria. They are the standard — not a checklist to mechanically tick, but guidance for your judgment.

**Step 3: Make the call.** Apply your judgment to the evidence against the criteria. There are three outcomes:

#### ACCEPT

The work meets the criteria. It doesn't need to be perfect — it needs to be good enough that further revision would yield diminishing returns.

```
queue_item.status = "done"
queue_item.result = "accepted"
```

Log in the progress section: `Evaluated {item.id}: ACCEPTED. {one-sentence rationale}`

#### REVISE

The work has specific, addressable problems. You can articulate what's wrong and what "fixed" looks like. Do not revise for style preferences or minor issues — only for substantive gaps against the criteria.

```
queue_item.status = "pending"
queue_item.result = "revision_needed"
queue_item.attempts += 1
```

Create a new worker task with revision instructions:

```
mcp__pkb__create_task(
    title="[Burst] {workflow}: {item.id} (revision {attempts})",
    parent=<tracking-task-id>,
    project=<project>,
    assignee="polecat",
    body=<revision instructions>
)
```

The revision instructions must include:

- What the previous worker produced (reference the previous task ID)
- What specific problems were found (not vague — quote or reference specifics)
- What "done" looks like for this revision (concrete, assessable)

Log in the progress section: `Evaluated {item.id}: REVISION NEEDED (attempt {N}). {what was wrong}`

Log in the decisions section: `{timestamp}: {item.id} sent for revision — {specific feedback summary}`

#### FAIL (escalate)

The work has fundamental problems that revision won't fix, OR the item has exhausted its retry budget (`attempts >= config.max_attempts`, default 3).

```
queue_item.status = "failed"
queue_item.result = "failed"
```

Add to the **Escalations** section in the tracking task body:

```markdown
### {item.id} — ESCALATED ({timestamp})

**Attempts**: {N}
**Last worker**: {task-id}
**Problem**: {clear description of why this can't be resolved by another worker attempt}
**Recommendation**: {what a human should do — e.g., "rewrite the spec manually", "clarify requirements first"}
```

Log in the progress section: `Evaluated {item.id}: FAILED after {N} attempts. Escalated.`

### Evaluation Principles

These apply regardless of workflow type:

1. **Read the work, not just the metadata.** Don't accept based on task status alone. The worker may have marked itself done without actually completing the work well. Read the actual output.

2. **Judge against the stated criteria, not your own preferences.** The workflow author defined what "good" means. Evaluate against that, not against what you would have done differently.

3. **Be specific in revision feedback.** "Not good enough" is useless. "The user expectations section lists 3 items but none are testable — each should have a clear pass/fail condition" is actionable.

4. **Err toward accepting adequate work.** The goal is throughput on a long queue, not perfection on each item. Accept work that meets the criteria even if you'd do it differently. Reserve revision for substantive gaps.

5. **Escalate early if the approach is wrong.** If a worker's output shows it fundamentally misunderstood the task (not just quality issues), don't waste retry budget. Escalate with a clear note about what went wrong so the human can adjust the worker instructions or handle it manually.

## Phase 3: Dispatch New Work

Calculate available slots:

```
available = config.items_per_burst - len(active_dispatches)
```

For each pending item (up to `available` slots):

### 3a. Create Worker Task in PKB

```
worker_task = mcp__pkb__create_task(
    title="[Burst] {workflow}: {item.id}",
    parent=<tracking-task-id>,
    project=<project>,
    assignee="polecat",
    priority=1,
    body=<rendered worker instructions>
)
```

The worker instructions are rendered from the **Worker Instructions** template in the tracking task body, with `{source}`, `{item.id}`, and any other item-specific variables substituted.

### 3b. Dispatch via Polecat

Invoke each worker through polecat infrastructure:

```bash
# Claude worker (default)
polecat run -t <worker-task-id> -p <project> -c burst-supervisor

# Gemini worker
polecat run -t <worker-task-id> -p <project> -c burst-supervisor -g
```

Use `config.worker_type` to determine the runner:

- `"claude"` or `"claude-cli"` → `polecat run -t <id> -p <project> -c burst-supervisor`
- `"gemini"` or `"gemini-cli"` → `polecat run -t <id> -p <project> -c burst-supervisor -g`

If the burst dispatches multiple items, launch them in parallel using separate Bash tool calls (one per worker). Each `polecat run` is a blocking subprocess that handles the full lifecycle: claim, worktree setup, agent execution, auto-finish.

**Do NOT call `gemini -p`, `claude -p`, or any agent CLI directly.** Always go through `polecat run`.

### 3c. Update Queue State

After dispatch (whether worker completes immediately or is still running):

- Set queue item `status=in_progress`
- Set `worker_task=<worker-task-id>`
- Set `dispatched=<timestamp>`
- Add to `active_dispatches`

## Phase 4: Persist State

Update the tracking task with new state:

### 4a. Update State Counters (Body YAML Block)

```
plan.completed = count(queue where status == "done")
plan.failed = count(queue where status == "failed")
plan.in_progress = count(queue where status == "in_progress")
plan.remaining = count(queue where status == "pending")
burst_count += 1
last_burst = <now>
```

### 4b. Append Progress Log to Body

```markdown
### Burst {N} -- {timestamp}

- Checked: {n} dispatches ({accepted} accepted, {revised} revised, {failed} failed)
- Dispatched: {n} new items → {worker_type}
- Progress: {done}/{total} complete, {in_progress} in progress, {remaining} remaining
```

### 4c. Write Back

Use the Edit tool to update the YAML code block in the tracking task body with the new state, and append the progress log below it. For PKB-tracked fields (status, assignee, tags), use `mcp__pkb__update_task`.

## Phase 5: Report and Halt

Output a progress summary to the terminal:

```
Burst {N} complete.
  Queue: {done}/{total} done, {in_progress} in flight, {remaining} pending, {failed} failed
  Active dispatches: {list of task IDs}
```

**If all items are done or failed**: Mark tracking task as `done`. Summarize final results.

**If work remains**: Suggest next burst:

```
Next burst: /burst-supervisor <tracking-task-id>
Schedule: /loop 30m /burst-supervisor <tracking-task-id>
```

**HALT.** Do not loop — each invocation is one burst.

## Init Flow

When invoked with `init`:

1. **Determine workflow**: Read user's description or use a workflow template
2. **Populate queue**: Scan the source (e.g., `ls specs/*.md` for spec-audit) to build the item list
3. **Create tracking task** in PKB with the state schema:

```
mcp__pkb__create_task(
    title="Supervisor: {workflow description}",
    project=<project>,
    parent=<epic-id if applicable>,
    assignee="polecat",
    tags=["supervisor", "long-running"],
    body=<tracking task body with workflow config + empty progress log>
)
```

4. **Initialize state as a YAML code block in the body** (from [[aops-f22cf622]]):
   - `version: 1`
   - `workflow: <name>`
   - `queue: [...]` (populated from scan)
   - `active_dispatches: []`
   - `config: {max_attempts: 3, items_per_burst: 3, worker_type: "claude", review_mode: "auto"}`
   - `plan: {total_items: N, completed: 0, failed: 0, in_progress: 0, remaining: N}`
     PKB strips unrecognized frontmatter fields — state MUST live in the body.

5. **Proceed to first burst** (Phase 2-5)

## Concurrency Guard

On load, check `supervisor.last_burst`. If it was updated < 5 minutes ago AND there are active dispatches, warn:

```
Another supervisor burst may be running (last burst: {timestamp}, {N} active dispatches).
Proceed anyway? [y/N]
```

This is advisory, not a hard lock.

## Tracking Task Body Template

```markdown
# Supervisor: {workflow description}

## Mission

{User-provided description of what this supervisor is doing}

## Workflow Config

### Queue Source

{How to populate the queue, e.g., "Scan specs/*.md, one item per file"}

### Worker Instructions

{Template for what each worker should do. Use {source} and {item.id} as placeholders.}

### Evaluation Criteria

{Checklist the supervisor uses to evaluate worker output}

## Progress

{Burst logs appended here by Phase 4b}

## Decisions

{Supervisor decision log — why items were re-queued, skipped, etc.}

## Escalations

{Items that exceeded max_attempts or need human judgment}
```

## Relationship to Existing Patterns

| Pattern                | Use case                         | Dispatch model                                           |
| ---------------------- | -------------------------------- | -------------------------------------------------------- |
| `polecat swarm`        | Parallel batch, drain queue      | Pull (workers claim from queue)                          |
| `polecat supervise`    | LLM-driven parallel rounds       | Push (supervisor selects + dispatches)                   |
| **burst-supervisor**   | Iterative long-running workflows | Push (supervisor creates tasks + dispatches via polecat) |
| swarm-supervisor skill | Full lifecycle orchestration     | Push (decompose → review → dispatch)                     |

The burst-supervisor is for workflows that process N items iteratively across multiple sessions — spec audits, document reviews, email processing. It creates worker tasks in PKB and dispatches via `polecat run`, giving workers full worktree isolation and autonomous execution.

## Related

- `/pull` — Single task workflow (what each worker runs internally)
- `polecat run` — Single autonomous polecat worker
- `polecat supervise` — LLM-driven parallel dispatch (supervisor_loop.py)
- `swarm-supervisor` — Full lifecycle orchestration skill
- [[aops-f22cf622]] — State schema design
- [[aops-174d3fb9]] — Burst lifecycle design
- [[aops-c83f7a04]] — Result evaluation design
