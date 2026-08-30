---
id: email-triage
type: template
kind: process
category: email
description: Classify incoming emails into Task/FYI/Skip/Uncertain
requires: [task-tracking]
pairs-with: [wf-handover]
conflicts: []
version: 1.0.0
permalink: workflows-process-email-triage
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---

> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process: Email Triage

## Critical Precondition

Before classifying any email, **check sent mail first**. If a matching reply
already exists, classify as Skip.

## Immediate PKB task update on discovery

The moment an email reveals new information — arrival of a new commitment, resolution of an existing item (approval granted, invitation declined, request cancelled), or a changed constraint (deadline moved, assignee changed):

1. **Update the target task node immediately**, whatever else the run is doing. Update `status`, `due`, `assignee`, or body notes directly on the task node that gates the work.
2. **Create a task node if none exists** for the commitment or obligation (`pkb__create_task` with a parent). Prose in a document or daily note is not a record.
3. **Do not defer the write** to a wrap-up step, summary, or handback.

## Classification

One classification per email:

| Class         | Signals                                                      | Action                                                                 |
| ------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- |
| **Task**      | "please review...", decisions needed, deadlines, invitations | Create a task node immediately, compose [[task-tracking]]              |
| **FYI**       | "awarded", "approved", outcomes, thank-yous                  | Update gating task node in PKB immediately on discovery; archive email |
| **Skip**      | noreply@, newsletters, already replied to                    | Archive                                                                |
| **Uncertain** | mixed signals, unknown sender                                | Ask the user                                                           |

## NOT this template

- Extracting a full task with downloaded attachments/summaries → [[email-capture]]
- Drafting a reply → [[email-reply]]
