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
allowed-tools: Task, Read, Grep, Skill, AskUserQuestion
permalink: commands/email
---

# /email - Email-to-Task Capture

Process the email inbox to extract actionable items and FYIs, creating structured tasks/records in the PKB. Follow the **[[workflows/email-capture]]** workflow — it carries the mandatory guardrails (dedup-before-create via `task_search`, parent linkage, quoted text + entry_id + sender/date). When invoked with `--daily`, return the three sections below for `/daily` to integrate.

## Output Expectations

- **Actionable Emails**: Create self-contained tasks in the PKB. Include sender/recipients/date, the email text quote, all links, and structured metadata (due date, effort estimation, and consequence).
- **FYI Items**: Summarize key threads with verbatim quotes of essential content.
- **Archive Candidates**: List items that can be safely archived.
