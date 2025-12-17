---
name: add
description: Quick-add a task or checklist item from session context
allowed-tools: Skill
permalink: commands/add
---

Use the Skill tool to invoke the `[[skills/tasks/SKILL.md|tasks]]` skill: `Skill(skill="tasks")`

**Purpose**: Quickly capture action items from the current conversation.

**Workflow**:

1. Review the current session for context about what needs to be done
2. Search existing tasks for related items: `grep -li "keyword" $ACA_DATA/tasks/inbox/*.md`
3. **If related task exists**: Add a checklist item using `task_item_add.py`
4. **If no related task**: Create new task using `task_add.py`

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
