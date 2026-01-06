---
name: add
category: instruction
description: Quick-add a task or checklist item from session context
allowed-tools: Skill
permalink: commands/add
---

Use the Skill tool to invoke the `[[skills/tasks/SKILL.md|tasks]]` skill: `Skill(skill="tasks")`

**Purpose**: Quickly capture action items from the current conversation.

**Workflow**:

1. Review the current session for context about what needs to be done
2. Search existing tasks via semantic search: `mcp__memory__retrieve_memory(query="tasks related to [topic]")`
3. **If related task exists**: Add a checklist item using `task_item_add.py`
4. **If no related task**:
   a. Check: is this atomic or multi-step?
   b. If multi-step, invoke `Skill(skill="task-expand")` for expansion guidance
   c. Apply expansion methodology to generate subtasks with `[effort::]`, `[automatable::]`, `[depends::]` metadata
   d. Create task with `## Checklist` section using `task_add.py`

**Checklist item format** (Obsidian Tasks compatible):

```
- [ ] Action item description
- [ ] Another item 📅 2025-01-15
- [x] Completed item ✅ 2025-01-10
```

**Scripts**:

- Add checklist item: `cd $AOPS && uv run python skills/tasks/scripts/task_item_add.py "task-id.md" --item "Description"`
- Create new task: `cd $AOPS && uv run python skills/tasks/scripts/task_add.py --title "Title" --slug "my-task" --priority P2`

**Key rules**:

- Always check for existing related tasks first (avoid duplicates)
- Use checklist items for sub-actions within a larger task
- Keep task titles concise, put details in body or checklist
