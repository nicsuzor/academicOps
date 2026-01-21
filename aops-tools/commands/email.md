---
name: email
category: instruction
description: Create "ready for action" tasks from emails - with summaries, downloaded documents, and clear response requirements
allowed-tools: Bash
permalink: commands/email
---

**Workflow**: Extract action items from emails and create tasks ready to work on immediately.

**What you'll do**:

1. Fetch recent emails: Call `mcp__plugin_aops-tools_outlook__messages_list_recent(limit=20)` - if it works, proceed; if error, HALT and report
2. **Check Sent folder** for existing responses (skip tasks for emails already dealt with)
3. Classify emails using [[workflows/triage-email]] criteria: Task → create task | FYI → Extract info | Skip → Archive candidate
4. **Read Important FYI email bodies** and extract key information (dates, amounts, outcomes)
5. Query [[skills/remember/SKILL.md|remember]] for context to categorize actions
6. **Create "ready for action" tasks**:
   - Summarize what you need to respond to (not just raw email)
   - Download attachments and linked documents (Google Docs, etc.)
   - Convert documents to markdown for repo storage
   - Store in appropriate location (reviews → `$ACA_DATA/reviews/{sender}/`)
   - Create task with body containing summary, response needed, document links
7. **Present all important information to user**:
   - **Tasks created**: Table with title, priority, project
   - **FYI emails**: MUST include content summary (key dates, amounts, outcomes, decisions) - NOT just subject/sender metadata
   - **Archived**: List what was archived
8. Archive safe-to-ignore emails (use `mcp__plugin_aops-tools_outlook__messages_list_folders` to find correct archive folder per account - Gmail uses lowercase `archive`, Exchange uses `Archive`)

**Task creation**:

```
mcp__plugin_aops-core_tasks__create_task(
  title="Reply to <sender name>: <subject summary>",
  type="task",
  project="aops",
  priority=2,  # 1-3 for emails
  body="<structured description>"
)
```

Body MUST include (in this order):
- **entry_id**: `<entry_id>` (REQUIRED - enables direct email lookup, must be first line)
- **From**: Sender name and email
- **Date**: When received
- **Context**: Brief who/what/when
- **Summary**: What you need to respond to
- **Response Needed**: Concrete action checklist
- **Associated Documents**: Links to downloaded/converted files (if any)

**CRITICAL**: The `entry_id` line must use exactly this format for parsing:
```
**entry_id**: `000000009A3C5E42...`
```
This enables `/pull` to retrieve the email in 1 API call instead of searching.

**Document handling**:

| Classification     | Storage Location              |
| ------------------ | ----------------------------- |
| Review/Supervision | `$ACA_DATA/reviews/{sender}/` |
| Other              | `$ACA_DATA/documents/`        |

**Example triggers**:

- "check my email for tasks"
- "process emails"
- "any new tasks from email?"
- "email triage"
- "clean up my inbox"

**Backend**: Uses tasks MCP for task creation
