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

Process the email inbox to extract actionable items and FYIs, creating structured tasks/records in the PKB.

```
## Output Expectations

- **Actionable Emails**: Create self-contained tasks in the PKB. Include sender/recipients/date, the email text quote, all links, and structured metadata (due date, effort estimation, and consequence).
- **FYI Items**: Summarize key threads with verbatim quotes of essential content.
- **Archive Candidates**: List items that can be safely archived.
```
