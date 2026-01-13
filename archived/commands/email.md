---
name: email
category: instruction
description: Create "ready for action" tasks from emails - with summaries, downloaded documents, and clear response requirements
allowed-tools: Skill
permalink: commands/email
---

Use the Skill tool to invoke the `[[skills/tasks/SKILL.md|tasks]]` skill: `Skill(skill="tasks")` - then follow the email-task-capture workflow documented within.

**Workflow**: Extract action items from emails and create fully-prepared tasks ready to work on immediately.

**What you'll do**:

1. Fetch recent emails: Call `mcp__outlook__messages_list_recent(limit=20)` - if it works, proceed; if error, HALT and report
2. **Check Sent folder** for existing responses (skip tasks for emails already dealt with)
3. Classify emails: Actionable → Task | Important FYI → Extract info | Safe to ignore → Archive candidate
4. **Read Important FYI email bodies** and extract key information (dates, amounts, outcomes)
5. Query [[skills/remember/SKILL.md|remember]] for context to categorize actions
6. **Create "ready for action" tasks**:
   - Summarize what you need to respond to (not just raw email)
   - Download attachments and linked documents (Google Docs, etc.)
   - Convert documents to markdown for repo storage
   - Store in appropriate location (reviews → `$ACA_DATA/reviews/{sender}/`)
   - Create structured task with summary, response needed, document links, original email
7. **Present all important information to user** (not just subject lines - actual content)
8. Offer bulk archive for safe-to-ignore emails

**Task output format**:

Tasks created include:

- **Context**: Brief who/what/when
- **Summary: What You Need to Respond To**: Primary question + secondary items
- **Response Needed**: Concrete action checklist
- **Associated Documents**: Links to downloaded/converted files
- **Original Email**: Full text preserved at bottom

**Document handling**:

| Classification     | Storage Location                      |
| ------------------ | ------------------------------------- |
| Review/Supervision | `$ACA_DATA/reviews/{sender}/`         |
| Other              | `$ACA_DATA/task-documents/{task-id}/` |

**Example triggers**:

- "check my email for tasks"
- "process emails"
- "any new tasks from email?"
- "email triage"
- "clean up my inbox"

**Backend**: Uses task_add.py scripts (gracefully degrades if MCP unavailable)
