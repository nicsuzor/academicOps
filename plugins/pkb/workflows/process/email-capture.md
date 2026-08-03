---
id: email-capture
kind: process
category: email
description: Extract action items from emails into "ready for action" tasks with summaries, downloaded documents, and clear response requirements
requires: [task-tracking]
pairs-with: [wf-handover]
conflicts: []
recommends: [email-triage]
version: 2.1.0
permalink: workflows-process-email-capture
---

# Process: Email → Task Capture

**When to invoke**: "check my email for tasks", "process emails", "any new
tasks from email?" Heavier than [[email-triage]] — produces a fully-loaded,
ready-to-work task rather than just a classification.

## Steps

1. **Check existing tasks first** — prevent duplicates for emails already
   processed.
2. **Fetch and check responses** — recent emails; skip any already replied to.
3. **Analyze and classify** — Actionable / Important FYI / Safe to ignore.
4. **Context and categorization** — query PKB for project match and confidence.
5. **Infer priority** — P0–P3 per [[email-triage]]'s rules.
6. **Create "ready for action" tasks** — summary, downloaded resources, and a
   clear response requirement, not just a title. Compose [[task-tracking]];
   every task MUST have a `parent` (epic or project).
7. **Present** — show Important FYI content and created tasks to the user.

## Critical Guardrails

- Always check for existing tasks before creating one.
- Verify the email connector by calling it, not by checking config.
- High-confidence auto-categorizes; low-confidence flags for review.
- Fail-fast: halt immediately if the email connector is unavailable.
