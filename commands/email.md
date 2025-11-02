---
name: email
description: Check email, automatically update task database, and present digest
---

# Email Management

Invoke the task-manager subagent to:
1. Load strategic database (existing tasks, priorities, context)
2. Fetch recent emails from all accounts (using email skill)
3. Automatically create/update tasks (using tasks skill)
4. Present digest of new/updated tasks and FYI information
5. Propose emails to archive and request confirmation

**This is a shortcut for**: "Check my email and automatically update my task database"

The task-manager will:
- Silently load `$ACADEMICOPS_PERSONAL/data/` (tasks, projects, goals, context)
- Use email skill to fetch emails via Outlook MCP
- Create tasks automatically (no prompting for permission)
- Update existing tasks if email provides new information
- Present summary of changes made
- Suggest emails to archive based on completion/FYI status
