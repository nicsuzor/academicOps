---
name: pull
type: command
category: instruction
description: Pull a task from queue, claim it (mark in_progress), and mark complete when done
triggers:
  - "pull task"
  - "get work"
  - "what should I work on"
  - "next task"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Task, Bash, Read, Grep, Skill, AskUserQuestion, mcp__pkb__get_task, mcp__pkb__get_task_children, mcp__pkb__list_tasks, mcp__pkb__update_task, mcp__pkb__complete_task, mcp__pkb__release_task
permalink: commands/pull
---

# /pull - Pull, Claim, and Complete a Task

**Purpose**: Get a task from the dispatch queue (status `queued`), claim it (mark status `in_progress`), and mark it complete when finished.

## Workflow

### Step 1: Get and Claim a Task

Per [[../skills/remember/references/TAXONOMY.md]] §Status Values: agents pull only from `queued` (the human-gated dispatch queue). Tasks in `ready` are decomposed-but-unapproved and MUST NOT be claimed here — the user promotes `ready` → `queued` manually.

1. **List queued tasks**: Call `mcp__pkb__list_tasks(status="queued", limit=10, format="json")` to find dispatchable tasks. The PKB ranks results by composite `focus_score`, which embeds lexicographic severity (SEV4 dominates), priority, downstream weight, deadline urgency, stakeholder waiting, and decay — see [[multi-parent]] §7 for the canonical model.
2. **Select task**: Pick the highest-`focus_score` task in the returned list. Do NOT rank by `urgency`, `downstream_weight`, or any single component directly — those are visible in metadata for filter/debug only; ranking always goes through `focus_score`. See [Priority Labels in TAXONOMY.md](../skills/remember/references/TAXONOMY.md#priority-labels-p0p4) for canonical label definitions (P0 = highest).
3. **Claim task**: Call `mcp__pkb__update_task(id="<task-id>", status="in_progress", assignee="polecat")` to claim it.

**If a specific task ID is provided** (`/pull <task-id>`):

1. Call `mcp__pkb__get_task(id="<task-id>")` to load it.
2. If the task has children (leaf=false), navigate to the first queued leaf subtask instead.
3. If the task is already `in_progress`, skip claim and proceed directly to Step 1.5.
4. Otherwise, claim with `mcp__pkb__update_task(id="<task-id>", status="in_progress", assignee="polecat")`.

**If no tasks are queued**:

- Check active/inbox tasks for any that can be worked on.
- If none exist, report and halt.

### Step 1.5: Inject Soft Dependency Context (Advisory)

After claiming, check if the task has `soft_depends_on` relationships:

1. Read the task's `soft_depends_on` array
2. For each soft dependency ID:
   - Call `mcp__pkb__get_task(id="<soft-dep-id>")`
   - If status is `done`, extract the task body for context
   - If status is NOT done, log: "Soft dependency <id> not yet complete - proceeding without context"
3. Present completed soft dependency context before execution:

```markdown
## Soft Dependency Context (Advisory)

The following completed tasks provide informational context for this task:

### [<soft-dep-id>] <title>

<body excerpt or summary>

---
```

**Important**: Soft dependencies are ADVISORY only:

- Reading them is recommended but not mandatory
- Missing/incomplete soft deps do NOT block task execution
- Context injection helps but agent can proceed without it

### Step 1.7: Specialist Agent Dispatch (Pre-EXECUTE Short-Circuit)

If the claimed task — or its parent epic — has an `assignee` that names a specialist sub-agent, the main agent MUST dispatch via the Agent tool. Do NOT fall through to Step 2 / Step 3A and execute inline.

**Specialist namespaces** (match against `assignee`):

- `aops-core:<name>` → dispatch with `subagent_type="<name>"` (strip the `aops-core:` prefix)
- `aops-cowork:<name>` → dispatch with `subagent_type="<name>"` (strip the `aops-cowork:` prefix)
- `polecat` (bare name) → dispatch with `subagent_type="polecat"`

Known specialist names include `marsha`, `rbg`, `pauli`, `james`, `jr`, `qa`, `enforcer`, `polecat`. Any value matching the namespace patterns above is treated as a specialist regardless of whether the bare name is recognised — the namespace itself is the trigger.

**Dispatch:**

```
Agent(
  subagent_type="<bare-agent-name>",
  prompt="<self-contained brief: task ID, title, body, acceptance criteria, file paths in scope>"
)
```

The brief must be self-contained — the dispatched agent will not have this session's context. Include the task ID, title, full body, acceptance criteria, and any file paths in scope.

After dispatch, **HALT** the main agent. Do NOT continue to Step 2. The specialist owns execution and completion.

If `assignee` is `null`, `nic`, missing, or anything not matching the namespaces above, continue to Step 2 normally.

### Step 2: Assess Task Path - EXECUTE or TRIAGE

After claiming, determine whether to execute immediately or triage first.

#### EXECUTE Path (all must be true)

Proceed with execution when:

- **What**: Task describes specific deliverable(s)
- **Where**: Target files/systems are known or locatable within 5 minutes
- **Why**: Context is sufficient for implementation decisions
- **How**: Steps are known or determinable from codebase/docs
- **Scope**: Estimated completion within current session (or a bounded phase of a multi-session task)
- **Blockers**: No external dependencies (human approval, external input, waiting)

→ Proceed to Step 3: Execute

**Multi-phase tasks**: If the task has multiple phases but one phase can be completed this session, proceed with EXECUTE for that phase. Update the task body with progress before finishing. The task stays `in_progress` for the next session to pick up.

#### TRIAGE Path (any is true)

Triage instead of executing when:

- Task requires human judgment/approval
- Task has unknowns requiring exploration beyond this session
- Task is too vague to determine deliverables
- Task depends on external input not yet available
- Task exceeds session scope

→ Proceed to Step 3: Triage

### Step 3A: Execute (EXECUTE Path)

Follow the task's workflow or use standard execution pattern:

1. Read task body for context and acceptance criteria
2. Implement the changes (if dogfooding, follow the [[dogfooding]] workflow alongside execution)
3. **Verify with independent evidence** (see Step 3A.V below)
4. Run tests if applicable
5. Commit changes
6. Complete task (see Step 4)

### Step 3A.V: Verification Loop (P#103)

Before proceeding to commit, verify the work produces **independent evidence** of correctness. Verification depth scales with complexity:

**Simple tasks** (typo, config change, single-file edit):

- Run tests. If they pass, proceed.

**Standard tasks** (feature, refactor, straightforward bug):

- Run tests AND manually verify the change does what the acceptance criteria require.

**Complex tasks** (concurrency bugs, multi-component fixes, inherited work from other sessions):

- Independently trace the causal chain: what was broken → why → does this fix address the actual mechanism?
- Do NOT trust prior documentation at face value. Re-derive the conclusion from code.
- If inheriting work: the previous session's analysis is a hypothesis, not a fact. Verify it.

**QA loop**: If verification reveals gaps or doubts, loop back to step 2. Do NOT proceed to commit with unresolved questions. This loop is the difference between "tests pass" and "fix is correct."

### Step 3A.1: Execute Spike/Learn Tasks

For tasks with `type: learn`:

1. **Investigate** per task instructions
2. **Write findings to task body** - Use `mcp__pkb__append(id="<task-id>", content="...")` to record findings
3. **Summarize in parent epic** - Read parent, append to "## Findings from Spikes"
4. **Apply learnings to framework** - Before creating follow-up tasks, check if findings warrant direct changes to framework files (HEURISTICS.md, skill prompts, specs). Knowledge files alone are insufficient — if a learning points to a process improvement, change the process.
5. **Decompose actionable items** - Create subtasks for remaining work that can't be done in this session. Resolve parent per [[references/hierarchy-quality-rules]]:
   ```
   mcp__pkb__create_task(
     id="<spike-id>",
     project="<project>",
     parent="<resolved-parent-id>",
     children=[
       {"title": "[Fix] Issue 1", "type": "task", "body": "Context from spike..."},
       {"title": "[Fix] Issue 2", "type": "task", "body": "Context from spike..."}
     ]
   )
   ```
6. **Completion loop (P#109)** - Create a verify-parent task that depends on all subtasks just created. This task confirms the spike's parent goal was fully addressed after implementation.
7. **Complete the spike** - Decomposition IS completion for learn tasks (per P#71, P#81)

### Step 3A.2: Commit Before Completion

Before marking task complete, verify work is committed:

1. Run `git status` - should show no uncommitted changes to tracked files
2. If uncommitted changes exist:
   - Stage relevant files: `git add <files>`
   - Commit with task context: `git commit -m "feat(<area>): <task summary>"`
3. Only after commit succeeds, proceed to Step 4

**Enforcement**: Do NOT call `release_task()` until commit is verified.

### Step 3B: Triage (TRIAGE Path)

Take appropriate action based on what's needed:

#### Option A: Assign to Role

If task needs specific expertise or human judgment:

```
mcp__pkb__update_task(
  id="<task-id>",
  updates={"assignee": "<role>"}  # e.g., "nic", "polecat"
)
```

**Role assignment logic:**

- `assignee="nic"` - Requires human judgment, strategic decisions, or external context
- `assignee="polecat"` - Can be automated but needs clarification on scope/approach
- Leave unassigned if role unclear

Note: Use `mcp__pkb__update_task` (not `mcp__plugin_aops-core_tasks`) for assignee support. Don't set status to "blocked" - just assign.

#### Option B: Decompose into Subtasks

If task is too large but scope is clear:

**Architecture checkpoint (required for >3 subtasks)**: Before creating subtasks, present the architectural approach to the user — what you plan to build, how (agent prompts vs code, which patterns), and key tradeoffs. Do NOT create subtasks until the approach is confirmed. Premature decomposition before the design is stable creates waste (P#72).

```
mcp__pkb__create_task(
  id="<parent-id>",
  project="<project>",
  parent="<resolved-parent-id>",
  children=[
    {"title": "Subtask 1: [specific action]", "type": "action", "order": 0},
    {"title": "Subtask 2: [specific action]", "type": "action", "order": 1},
    {"title": "Subtask 3: [specific action]", "type": "action", "order": 2}
  ]
)
```

**Completion loop (P#109)**: After creating all subtasks, create one additional verify-parent task:

```
mcp__pkb__create_task(
  title="Verify: [parent goal] fully resolved",
  parent="<parent-id>",
  depends_on=["subtask-1-id", "subtask-2-id", "subtask-3-id"],
  assignee=null,
  body="Return to original problem. Confirm goal is met or iterate."
)
```

**Subtask explosion heuristics:**

- Each subtask should pass EXECUTE criteria (15-60 min, clear deliverable)
- Break by natural boundaries: files, features, or dependencies
- Order subtasks logically (dependencies first)
- Don't over-decompose: 3-7 subtasks is ideal
- If > 7 subtasks needed, create intermediate grouping tasks

#### Option C: Block for Clarification

If task is fundamentally unclear:

```
mcp__pkb__update_task(
  id="<task-id>",
  updates={"status": "blocked", "body": "Blocked: [specific questions]. Context: [what's known so far]."}
)
```

After triaging, **HALT** - do not proceed to execution. The task is now either assigned, decomposed, or blocked.

### Step 4: Finish and Mark Ready for Merge

After successful execution (EXECUTE path only), finalize the task:

#### If in a Polecat Worktree

Detect via: current directory is under `$POLECAT_HOME/polecat/`

Run `polecat finish` via Bash:

```bash
polecat finish
```

This command:

1. Auto-commits any uncommitted changes (safeguard)
2. Pushes the branch to origin
3. Attempts to create/update a PR (best-effort; requires GitHub CLI `gh` and may fail without aborting)
4. Sets task status to `merge_ready` (even if PR creation/update fails)

The PR review pipeline handles merge via GitHub auto-merge when a PR exists and is configured appropriately.

#### If NOT in a Polecat Worktree

For tasks executed outside the polecat worktree system (e.g., direct `/pull` in a normal repo), use:

```
mcp__pkb__release_task(id="<task-id>", status="done", summary="What was done and outcome")
```

If you filed a PR, use `merge_ready` instead:

```
mcp__pkb__release_task(id="<task-id>", status="merge_ready", summary="What was done", pr_url="https://...")
```

This captures what was done so work history is never lost.

**Fallback**: If `mcp__pkb__release_task` is not available, use `mcp__pkb__update_task(id="<task-id>", updates={"status": "done"})` or `mcp__pkb__complete_task(id="<task-id>")`.

**Note**: TRIAGE path should halt before reaching Step 4. Only EXECUTE path tasks should be finished.

## Arguments

- `/pull` - Get highest priority queued task from the global dispatch queue
- `/pull <task-id>` - Claim a specific task (or its first queued leaf if it has children)

## Implementation Note

How you execute the task, how you verify it, how you commit/push—those are agent responsibilities, not `/pull` responsibilities. This skill just manages the queue state: get, claim, complete.
