---
name: work
category: instruction
description: Enter collaborative mode for a task (human-led execution)
allowed-tools: Task, Bash, Read, Grep, Skill, AskUserQuestion
permalink: commands/work
---

# /work - Collaborative Task Execution

**Purpose**: Claim a task and enter a collaborative loop where the human directs and the bot assists.

## Workflow

### Step 1: Resolve and Claim Task

1.  **Resolve ID**:
    *   **If ID provided** (`/work <id>`): Use that ID.
    *   **If no ID**: Call `mcp__plugin_aops-tools_task_manager__list_tasks(assignee="nic", status="active", limit=1)` to find the user's top priority task.
        *   If none found, fall back to `list_tasks(status="active", limit=1)` (highest priority global task).
2.  **Claim**: Call `mcp__plugin_aops-tools_task_manager__update_task(id="<task-id>", status="in_progress")`.
    *   **Crucial**: Do NOT change the assignee to `bot`. If unassigned, you may optionally assign to `nic` if the user confirms, but otherwise leave the assignee field alone to indicate human ownership.

### Step 2: Context Injection

1.  **Load Task**: Call `mcp__plugin_aops-tools_task_manager__get_task(id="<task-id>")`.
2.  **Present Summary**:
    Display a concise summary to anchor the session:
    ```markdown
    # 🤝 Collaborative Mode: <Task Title> (<ID>)

    **Goal**: <Brief summary of task body>
    **Context**: <Any relevant soft dependencies or parent context>
    ```

### Step 3: Await Direction

**Do NOT auto-execute the task.**

Instead, yield control to the user with a question:
> "Task claimed and context loaded. How would you like to approach this?"

### Step 4: Collaborative Execution (The Session)

For the remainder of the session:
- **User leads**: User provides high-level direction ("Explore this", "Draft that").
- **Bot assists**: Agent performs the work (coding, searching, analyzing).
- **Checkpoints**: Agent should confirm understanding before expensive operations.

### Step 5: Explicit Completion

Do NOT complete the task (`complete_task`) until the user explicitly commands it (e.g., "We're done", "Mark it complete").

When commanded to complete:
1.  **Verify**: Ensure clean git state (`git status`) and passing tests.
2.  **Complete**: Call `mcp__plugin_aops-tools_task_manager__complete_task(id="<task-id>")`.
