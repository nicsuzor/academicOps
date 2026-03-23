---
name: email
type: command
category: instruction
description: Create "ready for action" tasks from emails - with summaries, downloaded documents, and clear response requirements
triggers:
  - "process email"
  - "email to task"
  - "handle this email"
modifies_files: true
needs_task: false
mode: execution
domain:
  - email
allowed-tools: ~~email, Task, Read, Grep, Skill, AskUserQuestion
permalink: commands/email
---

# /email - Email-to-Task Capture

**Purpose**: Extract action items from emails and create properly categorized tasks.

## Workflow

This command routes to the **[[workflows/email-capture]]** workflow.

1. **Fetch**: Use `~~email.messages_list_recent` to get recent emails.
2. **Analyze**: Categorize emails into Actionable, Important FYI, or Safe to ignore.
3. **Capture**: Create "ready for action" tasks for actionable emails.
4. **Resources**: Download attachments and linked documents.
5. **Summarize**: Present Important FYI content and created tasks to the user.

For detailed procedures, see the full workflow definition.
