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

**Purpose**: Extract action items from emails and create properly categorized tasks with full context.

## Invocation

```
/email            # Interactive email processing
/email --daily    # Called by /daily — returns structured results for daily note integration
```

When invoked with `--daily`, return results as structured data (created tasks, FYI items, archive candidates) rather than presenting interactively. The `/daily` skill integrates these into the daily note.

## Workflow

This command routes to the **[[workflows/email-capture]]** workflow.

1. **Fetch**: Use `~~email.messages_list_recent` to get recent emails.
2. **Cross-reference**: Check sent mail to avoid flagging already-handled items.
3. **Analyze**: Categorize emails into Actionable, Important FYI, or Safe to ignore.
4. **Capture**: Create "ready for action" tasks for actionable emails. Every task MUST contain:
   - Quoted email text (actual content, not just summary)
   - All links from the email body
   - Entry ID for retrieval
   - Sender, recipients, date
5. **Resources**: Download attachments and convert documents to markdown. Never silently drop resources.
6. **Summarize**: Present Important FYI content and created tasks to the user.

## Quality Bar

A task created from email must be **self-contained**. Someone pulling the task via `/pull` should understand what's needed without opening the original email. See [[workflows/email-capture]] § Critical Guardrails.

For detailed procedures, see the full workflow definition.
