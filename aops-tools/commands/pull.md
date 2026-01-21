---
name: pull
category: instruction
description: Pull a task from the queue, execute it with hydrator guidance, and complete with session reflection
allowed-tools: Task, Bash, Read, Grep, Skill, AskUserQuestion
permalink: commands/pull
---

# /pull - Pull and Execute a Task

**Purpose**: Pull a ready task from the queue, claim it, execute it with hydrator guidance, and complete with proper session reflection. The counterpart to `/q` (queue).

## Workflow

### Step 1: Find Ready Work

Call `mcp__plugin_aops-core_tasks__get_ready_tasks(project="aops")` to see tasks available for work.

This returns tasks that are:
- Leaves (no children)
- No unmet dependencies
- Status: active or inbox
- Sorted by priority (P0 first)

### Step 2: Claim the Top Task (or Triage if None Ready)

**If user provides a task ID directly via `/pull <task-id>`**:

1. Call `mcp__plugin_aops-core_tasks__get_task(id="<task-id>")` to get task details
2. Check if the task has children (is it a leaf?):
   - If `leaf=true`: Proceed to claim this task directly
   - If `leaf=false` (has children): Navigate to a ready leaf subtask:
     a. Call `mcp__plugin_aops-core_tasks__get_task_tree(id="<task-id>")` to get the full subtree
     b. Find the first ready leaf task in the tree (status: active/inbox, no unmet dependencies)
     c. If no ready leaves exist, report "No ready leaves in subtree for <task-id>. Consider `/pull` to triage."
     d. Claim the ready leaf task (not the parent)

**If no task ID provided** (auto-claim mode):

**If no ready tasks**: Follow this fallback sequence:

1. Call `mcp__plugin_aops-core_tasks__list_tasks(status="active")` to find active tasks that may need triage
2. If none, call `mcp__plugin_aops-core_tasks__list_tasks(status="inbox")` to find inbox tasks needing attention
3. If tasks found in either step, apply TRIAGE path to the highest priority one
4. If truly no tasks exist, report "No actionable tasks" and HALT

**If ready tasks exist**: Auto-claim the first (highest priority) task:

```
mcp__plugin_aops-core_tasks__update_task(id="<task-id>", status="active")
```

### Step 3: Show Claimed Task

Call `mcp__plugin_aops-core_tasks__get_task(id="<task-id>")` to get full task details before proceeding.

### Step 4: Assess Task Path

After reviewing the task, determine which execution path applies:

#### Path 1: EXECUTE
**All criteria must be true:**
- **What**: Task describes specific deliverable(s)
- **Where**: Target files/systems are known or locatable within 5 minutes of search
- **Why**: Context is sufficient to make implementation decisions
- **How**: Steps are known or determinable from codebase/docs
- **Scope**: Estimated completion within current session
- **Blockers**: No external dependencies (human approval, external input, waiting)

**Action**: Proceed to Step 5 (Hydrator) → Execute → Complete.

#### Path 2: TRIAGE
**Any criterion is true:**
- Task requires human judgment/approval
- Task has unknowns requiring exploration beyond this session
- Task is too vague to determine deliverables
- Task depends on external input not yet available
- Task exceeds session scope

**Actions (in order):**
1. **Update status to blocked**: `mcp__plugin_aops-core_tasks__update_task(id="<id>", status="blocked")`
2. **Subtask explosion** (if appropriate): Break into child tasks when:
   - You can identify discrete, actionable steps
   - Each subtask passes EXECUTE criteria independently
   - Each subtask is 15-60 minutes of work
   - The breakdown covers the parent task's scope
   ```
   mcp__plugin_aops-core_tasks__decompose_task(id="<parent-id>", children=[
     {"title": "Subtask 1", "type": "action", "order": 0},
     {"title": "Subtask 2", "type": "action", "order": 1, "depends_on": ["<subtask1-id>"]},
   ])
   ```
3. **If cannot decompose**: Update task body explaining what's blocking
   ```
   mcp__plugin_aops-core_tasks__update_task(id="<id>", status="blocked", body="Blocked: <reason>. Needs strategy review.")
   ```

**After TRIAGE**: HALT. Do not proceed to execution.

#### Mid-Execution Reclassification

If during EXECUTE you hit an unexpected blocker:
1. Stop work
2. Update task with findings: `mcp__plugin_aops-core_tasks__update_task(id="<id>", body="Attempted: X. Blocked by: Y")`
3. Reclassify to TRIAGE path

#### Email Reply Tasks

If task title starts with "Reply to" (email reply task created by `/email`):

1. **Extract entry_id from task body**:
   - Look for line: `**entry_id**: \`<id>\``
   - Parse the ID from the backticks

2. **Retrieve email directly** (if entry_id found):
   ```
   mcp__plugin_aops-tools_outlook__messages_get(entry_id="<extracted-id>", format="text")
   ```

3. **Fallback search** (if entry_id missing - legacy tasks):
   - Extract sender name from title ("Reply to <name>: ...")
   - Search: `mcp__plugin_aops-tools_outlook__messages_search(person="<name>", limit=10)`
   - Match by subject if multiple results

4. **Handle missing email**:
   - If email not found (archived/deleted): Update task as blocked
   - Don't create orphaned drafts

5. **Draft reply workflow**:
   - Check calendar if scheduling request: `mcp__plugin_aops-tools_outlook__calendar_list_upcoming()`
   - Create draft: `mcp__plugin_aops-tools_outlook__messages_reply(entry_id="<id>", body="<draft>")`
   - Task stays `active` - user sends manually
   - Report: "Draft created in Outlook. Task remains active until you send and confirm."

### Step 5: Invoke Hydrator for Execution Plan

**(EXECUTE path only)**

Call the hydrator with the task context to generate an execution plan:

```
Task(
  subagent_type="aops-core:prompt-hydrator",
  model="haiku",
  description="Hydrate claimed task",
  prompt="Generate execution plan for claimed task. Task context:\n\n<task details from get_task>\n\nProvide TodoWrite plan with acceptance criteria, relevant context, and verification steps."
)
```

### Step 6: Execute the Plan

1. **Create TodoWrite** with the hydrator's plan
2. **Work through each item** systematically
3. **Run QA verification** before completion (if code changed)

### Step 7: Handle Follow-up Work

If the task generates follow-up work:

```
mcp__plugin_aops-core_tasks__create_task(
  title="<follow-up title>",
  type="task",
  project="aops",
  priority=2,
  body="Follow-up from <original-task-id>: <context>"
)
```

### Step 8: Complete the Task

```
mcp__plugin_aops-core_tasks__complete_task(id="<task-id>")
```

### Step 9: Record Learnings

If the work produced insights worth preserving:

```
Skill(skill="remember")
```

Use this for:
- Patterns discovered during implementation
- Decisions and their rationale
- Knowledge that will help future work

### Step 10: Commit and Push

```bash
git add -A
git commit -m "<meaningful commit message>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git pull --rebase
git push
```

### Step 11: Session Reflection

End with Framework Reflection (see AGENTS.md "Framework Reflection (Session End)" for template).

## Arguments

- `/pull` - Auto-claim mode: claims highest priority ready task (or halts if none)
- `/pull <task-id>` - Direct mode: if task is a leaf, claims it; if task has children, navigates to and claims the first ready leaf subtask in that tree

## Key Rules

1. **Always claim before working** - Never start work without updating status to active
2. **Always hydrate** - Let the hydrator analyze the task and generate the plan
3. **Always verify** - QA step before completing for code changes
4. **Always record** - Use remember skill for insights worth preserving
5. **Always push** - Work is not complete until `git push` succeeds
6. **Always reflect** - End with Framework Reflection for continuous improvement

## Examples

### Example 1: EXECUTE Path (fully specified task)
```
/pull
```
1. Calls `get_ready_tasks()` → finds `aops-xyz` (P1: Fix authentication bug)
2. Auto-claims: `update_task(id="aops-xyz", status="active")`
3. Gets task details via `get_task(id="aops-xyz")`
4. **Assesses path**: What ✓, Where ✓, Why ✓, How ✓, Scope ✓, No blockers ✓ → **EXECUTE**
5. Hydrator analyzes task, generates TodoWrite plan
6. Agent executes plan, fixes bug
7. Creates follow-up: `aops-abc` for adding tests
8. Completes: `complete_task(id="aops-xyz")`
9. Records learnings via remember skill
10. Commits and pushes
11. Outputs Framework Reflection

### Example 2: TRIAGE Path (needs human input)
```
/pull
```
1. Calls `get_ready_tasks()` → finds `aops-abc` (P1: Book progress checkpoint)
2. Auto-claims: `update_task(id="aops-abc", status="active")`
3. Gets task details → requires human assessment of creative work
4. **Assesses path**: Requires human judgment → **TRIAGE**
5. Updates status: `update_task(id="aops-abc", status="blocked", body="Requires human assessment")`
6. **HALT** - does not proceed to execution

### Example 3: TRIAGE with Subtask Explosion
```
/pull
```
1. Calls `get_ready_tasks()` → finds `aops-def` (P1: Refactor auth system)
2. Auto-claims: `update_task(id="aops-def", status="active")`
3. Gets task details → large scope but decomposable
4. **Assesses path**: Exceeds session scope → **TRIAGE**
5. Decomposes:
   ```
   decompose_task(id="aops-def", children=[
     {"title": "Extract auth middleware", "type": "action", "order": 0},
     {"title": "Add JWT validation", "type": "action", "order": 1},
     {"title": "Update auth tests", "type": "action", "order": 2}
   ])
   ```
6. Parent status updated, subtasks are ready for future `/pull`

### Example 4: Direct Mode with Parent Task (navigates to leaf)
```
/pull aops-def
```
1. `get_task(id="aops-def")` → task has `leaf=false` (has children from earlier decomposition)
2. `get_task_tree(id="aops-def")` → returns tree with 3 children
3. Scans tree for ready leaves → finds "Extract auth middleware" (status: inbox, no deps)
4. Auto-claims the leaf: `update_task(id="aops-def-child1", status="active")`
5. Reports: "Task aops-def has children. Claiming leaf subtask: Extract auth middleware"
6. Proceeds to Step 3 with the leaf task

**If no ready tasks but active tasks exist:**
```
/pull
```
1. `get_ready_tasks()` → no results
2. `list_tasks(status="active")` → finds `aops-ghi` (blocked, needs decomposition)
3. Claims and applies TRIAGE path to `aops-ghi`

**If no actionable tasks:**
```
/pull
```
→ "No actionable tasks. HALT."
