---
name: pull
category: instruction
description: Pull a task from queue, claim it (mark active), and mark complete when done
allowed-tools: Task, Bash, Read, Grep, Skill, AskUserQuestion
permalink: commands/pull
---

# /pull - Pull, Claim, and Complete a Task

**Purpose**: Get a task from the ready queue, claim it (mark status active), and mark it complete when finished.

## Workflow

### Step 1: Get a Task

Call `mcp__plugin_aops-core_tasks__get_ready_tasks(project="aops", caller="bot")` to get available tasks.

Returns tasks that are:
- Leaves (no children)
- No unmet dependencies
- Status: active or inbox
- Assignee is unset OR assigned to "bot"
- Sorted by priority

**Note**: The `caller="bot"` filter ensures agents only see tasks meant for automation. Tasks assigned to "nic" (human) are filtered out. Unassigned tasks are included for backwards compatibility.

**If a specific task ID is provided** (`/pull <task-id>`):
- Call `mcp__plugin_aops-core_tasks__get_task(id="<task-id>")` to load it
- If the task has children (leaf=false), navigate to the first ready leaf subtask instead

**If no tasks are ready**:
- Check active/inbox tasks for any that can be worked on
- If none exist, report and halt

### Step 2: Claim the Task (Mark Active)

```
mcp__plugin_aops-core_tasks__update_task(id="<task-id>", status="active")
```

That's it. The task is now claimed.

### Step 3: Assess Task Path - EXECUTE or TRIAGE

After claiming, determine whether to execute immediately or triage first.

#### EXECUTE Path (all must be true)

Proceed with execution when:

- **What**: Task describes specific deliverable(s)
- **Where**: Target files/systems are known or locatable within 5 minutes
- **Why**: Context is sufficient for implementation decisions
- **How**: Steps are known or determinable from codebase/docs
- **Scope**: Estimated completion within current session
- **Blockers**: No external dependencies (human approval, external input, waiting)

→ Proceed to Step 4: Execute

#### TRIAGE Path (any is true)

Triage instead of executing when:

- Task requires human judgment/approval
- Task has unknowns requiring exploration beyond this session
- Task is too vague to determine deliverables
- Task depends on external input not yet available
- Task exceeds session scope

→ Proceed to Step 4: Triage

### Step 4A: Execute (EXECUTE Path)

Follow the task's workflow or use standard execution pattern:

1. Read task body for context and acceptance criteria
2. Implement the changes
3. Verify against acceptance criteria
4. Run tests if applicable
5. Commit changes
6. Complete task (see Step 5)

### Step 4B: Triage (TRIAGE Path)

Take appropriate action based on what's needed:

#### Option A: Assign to Role

If task needs specific expertise or human judgment:

```
mcp__plugin_aops-core_tasks__update_task(
  id="<task-id>",
  assignee="<role>",  # e.g., "nic", "bot", "human"
  status="blocked",
  body="Blocked: [what's unclear]. Needs: [what decision/input is required]"
)
```

**Role assignment logic:**
- `assignee="nic"` - Requires human judgment, strategic decisions, or external context
- `assignee="human"` - Generic human tasks (emails, scheduling, etc.)
- `assignee="bot"` - Can be automated but needs clarification on scope/approach
- Leave unassigned if role unclear

#### Option B: Decompose into Subtasks

If task is too large but scope is clear:

```
mcp__plugin_aops-core_tasks__decompose_task(
  id="<parent-id>",
  children=[
    {"title": "Subtask 1: [specific action]", "type": "action", "order": 0},
    {"title": "Subtask 2: [specific action]", "type": "action", "order": 1},
    {"title": "Subtask 3: [specific action]", "type": "action", "order": 2}
  ]
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
mcp__plugin_aops-core_tasks__update_task(
  id="<task-id>",
  status="blocked",
  body="Blocked: [specific questions]. Context: [what's known so far]."
)
```

After triaging, **HALT** - do not proceed to execution. The task is now either assigned, decomposed, or blocked.

### Step 5: Mark Complete When Done

```
mcp__plugin_aops-core_tasks__complete_task(id="<task-id>")
```

Only call this after successful execution (EXECUTE path). TRIAGE path should halt before completion.

## Arguments

- `/pull` - Get highest priority ready task for bot (unassigned or assigned to "bot")
- `/pull <task-id>` - Claim a specific task (or its first ready leaf if it has children)
- `/pull --caller=nic` - Get ready tasks assigned to nic (human) or unassigned

## Implementation Note

How you execute the task, how you verify it, how you commit/push—those are agent responsibilities, not `/pull` responsibilities. This skill just manages the queue state: get, claim, complete.

## Main Session Requirement

**This command must run in the main Claude Code session**, not in worker agents spawned via `Task(subagent_type=...)`.

Worker agents lack MCP tool access. Tasks requiring Outlook (email), Zotero, memory, calendar, or browser automation will fail if executed by workers. See HEURISTICS.md P#77.

For parallel task processing, use the hypervisor pattern with queue filtering to ensure workers only receive MCP-independent tasks (file edits, git operations, code changes).
