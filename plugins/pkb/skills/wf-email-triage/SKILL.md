---
id: wf-email-triage
kind: obligation
permalink: wf-email-triage
requires: [task-tracking]
category: email
description: Reusable email triage obligation component for classifying incoming communications into Task, FYI, Skip, or Uncertain with priority inference.
version: 1.0.0
---

# Obligation Workflow Component: Email Triage (`wf-email-triage`)

## Overview

The `wf-email-triage` component is a reusable obligation workflow template for triaging incoming emails. It enforces classification, priority inference, duplicate detection, sent mail verification, and task creation via `[[task-tracking]]`.

## Preconditions

Before classifying any email:

1. **Check Sent Mail**: Verify whether a response has already been sent. If a reply exists, classify as **Skip**.
2. **Check Existing Tasks**: Prevent duplicate task creation for emails that have already been triaged.

## Classification Rules

Each email MUST be assigned exactly one classification:

| Class         | Signals & Indicators                                                                 | Mandatory Action                   |
| ------------- | ------------------------------------------------------------------------------------ | ---------------------------------- |
| **Task**      | Action requested, "please review", decisions needed, deadlines, calendar invitations | Create task with [[task-tracking]] |
| **FYI**       | Informational updates ("awarded", "approved"), status reports, thank-yous            | Archive / Mark read                |
| **Skip**      | automated (noreply@), newsletters, promotional, already replied to                   | Archive / Mark read                |
| **Uncertain** | Ambiguous context, unknown sender, complex multi-part request                        | Prompt user for guidance           |

## Priority Inference Engine (for Task items)

- **P0 (Urgent)**: Contains "URGENT" / "CRITICAL" in subject/body, or explicit deadline within 48 hours.
- **P1 (High)**: Deadline within 1 week, or explicit request from key collaborator/stakeholder.
- **P2 (Normal)**: Deadline within 2 weeks, or standard request.
- **P3 (Low)**: No deadline specified, administrative or low-impact task.

## Post-Triage & Task Tracking

- For all items classified as **Task**:
  - Compose a task record following `[[task-tracking]]`.
  - Set priority according to the priority inference rules.
  - Link original message context (sender, date, subject, thread reference).
- Complete triage sweep and report summary of actions taken (Tasks created, FYI archived, Skip count, Uncertain items requiring decision).
