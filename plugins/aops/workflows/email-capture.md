---
title: Email Task Capture
type: template
category: process
description: Extract a self-contained, actionable task and its reference materials from an email. Select when converting incoming correspondence into a tracked work item. Not for sorting an inbox (use `email-triage`) or drafting outbound responses (use `email-reply`).
tags: [email, communications, task-capture, intake, process]
---

# Process: Email Task Capture

Extract structured task specifications, deadlines, and context from communications.

## 1. Context and Artifact Extraction

- Extract full text, sender details, date, thread history, and attachments from `<email-message>`.
- Download and store referenced documents or files in the workspace or task scratchpad.

## 2. Requirement and Constraint Identification

- Identify explicit action items, deliverables, and success criteria requested by the sender.
- Extract hard constraints: deadlines, stakeholder requirements, target formats, and dependencies.

## 3. Task Formulation

- Compose task title, background, and machine-checkable acceptance criteria.
- Attach verbatim quotes and file pointers to input artifacts.
- Run duplicate check against existing tasks to attach to matching work rather than duplicating.

## 4. Graph Attachment and Handover

- Attach newly created task to appropriate parent epic or backlog.
- Set task status to ready and notify operator or downstream planner.
