---
name: email
description: Extract action items from emails and create tasks automatically with context-aware categorization
allowed-tools: Skill
permalink: commands/email
---

Use the Skill tool to invoke the `[[skills/tasks/SKILL.md|tasks]]` skill: `Skill(skill="tasks")` - then follow the email-task-capture workflow documented within.

**Workflow**: Extract action items from recent emails, present important information, and create properly structured tasks.

**What you'll do**:

1. Fetch recent emails via Outlook MCP (default: 20 emails)
2. **Check Sent folder** for existing responses (skip tasks for emails already dealt with)
3. Classify emails: Actionable → Task | Important FYI → Extract info | Safe to ignore → Archive candidate
4. **Read Important FYI email bodies** and extract key information (dates, amounts, outcomes)
5. Query [[skills/remember/SKILL.md|remember]] for context to categorize actions
6. Create tasks via task scripts with full email metadata linking
7. **Present all important information to user** (not just subject lines - actual content)
8. Offer bulk archive for safe-to-ignore emails

**Key behavior: Present before archive**

Before archiving anything, OUTPUT the actual information from Important FYI emails:
- Grant outcomes (amounts, dates, project details)
- Conference acceptances (dates, session info)
- OSB decisions (summaries, links)
- Significant updates affecting user's work

User sees this information directly - no confirmation clicks needed.

**Bulk archive safe emails**

After presenting important info, offer to clean up obvious non-actionable emails:

1. Identify safe-to-archive candidates: newsletters, travel alerts, auto-replies, quarantine digests
2. Present using `AskUserQuestion` with `multiSelect: true`
3. Frame as "mark any to KEEP" (default = archive)
4. Archive all unmarked emails via `messages_move` to Archive folder

**Example triggers**:

- "check my email for tasks"
- "process emails"
- "any new tasks from email?"
- "email triage"
- "clean up my inbox"

**Backend**: Uses task_add.py scripts (gracefully degrades if MCP unavailable)

**Outputs**:
- Important information extracted from FYI emails (presented to user)
- Already-responded emails detected (shown but no task created)
- Tasks created with categorization
- Archive candidates for user confirmation
