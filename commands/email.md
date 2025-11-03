---
name: email
description: Check email, automatically update task database, and present digest
---

# Email Management

Launch the task-manager agent to check email and update task database.

The task-manager agent will:
- Fetch recent emails from configured accounts (using email skill)
- Extract actionable tasks (using tasks skill)
- Update existing tasks if emails provide new information
- Present digest of new/updated tasks and important FYI information
- Propose emails to archive (with confirmation)
