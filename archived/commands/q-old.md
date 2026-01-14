---
name: q
category: instruction
description: Queue a task for later execution
allowed-tools: Task, Skill, mcp__memory__store_memory
permalink: commands/q
---

# /q - Queue for Later

Use the Skill tool to invoke the `[[skills/tasks/SKILL.md|tasks]]` skill: `Skill(skill="tasks")`

**Purpose**: Capture a task for later execution.

## Workflow

1. Review the current session for context about what needs to be done
2. Search existing tasks via semantic search: `mcp__memory__retrieve_memory(query="tasks related to [topic]")`
3. **If related task exists**: Add a checklist item using `task_item_add.py`
4. **If no related task**: Create a new task using `task_add.py`
5. DO NOT execute. Task will be queued for execution later.

### Scripts

- Add checklist item: `cd $AOPS && uv run python skills/tasks/scripts/task_item_add.py "task-id.md" --item "Description"`
- Create new task: `cd $AOPS && uv run python skills/tasks/scripts/task_add.py --title "Title" --slug "my-task" --priority P2`

### Key rules

- Always check for existing related tasks first (avoid duplicates)
- Use checklist items for sub-actions within a larger task
- Keep task titles concise, put details in body or checklist
