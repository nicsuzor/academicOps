---
name: email
description: Extract action items from emails and create tasks automatically with context-aware categorization
allowed-tools: Skill
permalink: commands/email
---

Use the Skill tool to invoke the `[[skills/tasks/SKILL.md|tasks]]` skill: `Skill(skill="tasks")` - then follow the email-task-capture workflow documented within.

**Workflow**: Extract action items from recent emails, categorize using bmem context, and create properly structured tasks.

**What you'll do**:

1. Fetch recent emails via Outlook MCP (default: 20 emails)
2. Analyze each for actionable items (deadlines, review requests, decisions needed)
3. Query [[skills/bmem/SKILL.md|bmem]] for context to categorize actions (projects, tags, priority)
4. Create tasks via task scripts with full email metadata linking
5. Present summary of tasks created with confidence scoring

**Optional: Bulk archive safe emails**

After task extraction, offer to clean up obvious non-actionable emails:

1. Identify safe-to-archive candidates: newsletters, travel alerts, auto-replies, quarantine digests, TOS updates, spam
2. Present in batches of 4 using `AskUserQuestion` with `multiSelect: true`
3. Frame as "mark any to KEEP" (default = archive)
4. Archive all unmarked emails via `messages_move` to Archive folder

**Example triggers**:

- "check my email for tasks"
- "process emails"
- "any new tasks from email?"
- "email triage"
- "clean up my inbox" (triggers bulk archive flow)

**Backend**: Uses task_add.py scripts (gracefully degrades if MCP unavailable)

**Outputs**: Summary of created tasks with categorization confidence, ready for review in task inbox
