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
allowed-tools: Skill
permalink: commands/email
---

# /email - Email-to-Task Capture

Process the email inbox to extract actionable items and FYIs, creating structured tasks/records in the PKB. Follow the **[[workflows/email-capture]]** workflow.

## Execution

Delegate to the `email` skill:
`Skill(skill="email", args="<user args>")`
