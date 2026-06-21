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

## Outlook cold-start — retry, don't restart

The Outlook MCP server is lazy: the **first call after an idle period triggers the Exchange logon (~1 min)**, so the first one or more calls may fail with `The attempt to log on to Microsoft Exchange has failed`. This is the expected cold-start signature, **not** a real auth failure — and `ping` may return `pong` while Exchange is still warming. **Just retry the same call 2–3 times over ~a minute**; it connects on its own. Do NOT restart Outlook or the MCP server (or tell the user to), and do NOT halt on the first error. Only treat it as a genuine failure if retries past ~2 minutes still return that error.

## Output Expectations

- **Actionable Emails**: Create self-contained tasks in the PKB. Include sender/recipients/date, the email text quote, all links, and structured metadata (due date, effort estimation, and consequence).
- **FYI Items**: Summarize key threads with verbatim quotes of essential content.
- **Archive Candidates**: List items that can be safely archived.
