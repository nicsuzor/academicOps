---
name: email
description: Extract action items from emails and create tasks automatically with context-aware categorization
permalink: commands/email
---

Invoke the email-task-capture workflow from the tasks skill.

**Workflow**: Extract action items from recent emails, categorize using bmem context, and create properly structured tasks.

**What you'll do**:

1. Fetch recent emails via Outlook MCP (default: 20 emails)
2. Analyze each for actionable items (deadlines, review requests, decisions needed)
3. Query bmem for context to categorize actions (projects, tags, priority)
4. Create tasks via task scripts with full email metadata linking
5. Present summary of tasks created with confidence scoring

**Example triggers**:

- "check my email for tasks"
- "process emails"
- "any new tasks from email?"
- "email triage"

**Full documentation**: [[skills/tasks/workflows/email-capture.md]]

**Backend**: Uses task_add.py scripts (gracefully degrades if MCP unavailable)

**Outputs**: Summary of created tasks with categorization confidence, ready for review in task inbox
