---
id: email-triage
kind: process
category: email
description: Classify incoming emails into Task/FYI/Skip/Uncertain with priority inference
requires: [task-tracking]
pairs-with: [wf-handover]
conflicts: []
version: 1.0.0
permalink: workflows-process-email-triage
---

# Process: Email Triage

## Critical Precondition

Before classifying any email, **check sent mail first**. If a matching reply
already exists, classify as Skip.

## Classification

One classification per email:

| Class         | Signals                                                      | Action                                   |
| ------------- | ------------------------------------------------------------ | ---------------------------------------- |
| **Task**      | "please review...", decisions needed, deadlines, invitations | Create a task, compose [[task-tracking]] |
| **FYI**       | "awarded", "approved", outcomes, thank-yous                  | Archive                                  |
| **Skip**      | noreply@, newsletters, already replied to                    | Archive                                  |
| **Uncertain** | mixed signals, unknown sender                                | Ask the user                             |

## Priority Inference (for Tasks)

- **P0**: contains "URGENT" or deadline < 48h
- **P1**: deadline < 1 week, or collaborator request
- **P2**: deadline < 2 weeks, or general request
- **P3**: no deadline, administrative

## NOT this template

- Extracting a full task with downloaded attachments/summaries → [[email-capture]]
- Drafting a reply → [[email-reply]]
