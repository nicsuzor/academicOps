---
name: email
category: instruction
description: Create "ready for action" tasks from emails
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
