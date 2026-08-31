---
title: Email Triage
type: template
category: process
description: Classify incoming messages into actionable triage buckets (Task, FYI, Skip, Uncertain). Select when scanning an inbox or communication stream to separate actionable tasks from informational updates. Not for drafting replies (use `email-reply`) or deep task extraction (use `email-capture`).
tags: [email, communications, triage, inbox, process]
---

# Process: Email Triage

Intake and sorting procedure to classify incoming messages into actionable categories.

## 1. Message Ingestion and Scope

- Retrieve unread or target messages from `<inbox-source>`.
- Batch messages into manageable inspection slices.

## 2. Classification

- For each message, evaluate sender, subject, body, and attachments against four triage categories:
  - **Task**: Requires action, code changes, or deliverables.
  - **FYI**: Informational updates, meeting notes, status reports. No response or action required.
  - **Skip**: Automated notifications, marketing, spam, or obsolete threads.
  - **Uncertain**: Requires human clarification or policy determination.

## 3. Action Dispatch

- Forward **Task** items to `email-capture` to formulate structured work items.
- Mark **Skip** items for archive or deletion.
- Log **FYI** items to reference notes where relevant.
- Aggregate **Uncertain** items for operator review.

## 4. Triage Summary

- Emit a concise summary table listing message count per bucket and routed tasks.
