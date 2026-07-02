---
name: email
type: skill
category: instruction
description: Email-to-task capture — triage the inbox into actionable tasks, FYI summaries, and archive candidates in the PKB. Owns the Outlook MCP cold-start retry guardrail and dedup/parent-linkage rules. Invoked by /email.
triggers:
  - "process email"
  - "email to task"
  - "handle this email"
  - "triage inbox"
modifies_files: true
needs_task: false
mode: execution
domain:
  - email
allowed-tools: mcp__outlook__*,mcp__pkb__task_search,mcp__pkb__create_task,mcp__pkb__list_tasks,AskUserQuestion
permalink: skills-email
---

# email — Email-to-Task Capture

Process the email inbox to extract actionable items and FYIs, creating structured tasks/records in the PKB. When invoked with `--daily`, return the three sections below for `/daily` to integrate rather than presenting them standalone.

## Outlook cold-start — retry, don't restart

The Outlook MCP server is lazy: the **first call after an idle period triggers the Exchange logon (~1 min)**, so the first one or more calls may fail with `The attempt to log on to Microsoft Exchange has failed`. This is the expected cold-start signature, **not** a real auth failure — and `ping` may return `pong` while Exchange is still warming. **Just retry the same call 2–3 times over ~a minute**; it connects on its own. Do NOT restart Outlook or the MCP server (or tell the user to), and do NOT halt on the first error. Only treat it as a genuine failure if retries past ~2 minutes still return that error.

## Procedure

1. **Fetch & dedup**: Retrieve recent emails via the Outlook MCP tools. Before creating any task, run `mcp__pkb__task_search` on the email subject/key action phrase — if a match exists, skip creation and link to it instead; if ambiguous, ask via `AskUserQuestion`.
2. **Classify**: Categorize each email into Actionable, Important FYI, or Safe to Ignore.
3. **Create tasks**: For each actionable email, create a self-contained task via `mcp__pkb__create_task` with a `parent` epic/project (mandatory linkage), and a body containing the quoted email text, `entry_id`, sender/date, and all links (do not download attachments — link them).
4. **Present summary**: Present the three sections below.

## Output Expectations

- **Actionable Emails**: Self-contained tasks in the PKB. Include sender/recipients/date, the email text quote, all links, and structured metadata (due date, effort estimate, consequence).
- **FYI Items**: Summarize key threads with verbatim quotes of essential content.
- **Archive Candidates**: List items that can be safely archived.
