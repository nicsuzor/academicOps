---
id: email-reply
kind: process
category: email
description: Draft email replies in the user's voice, checking calendar availability for scheduling — agent drafts, user sends
requires: [task-tracking]
pairs-with: [handover]
conflicts: []
version: 1.0.0
permalink: workflows-process-email-reply
---

# Process: Email Reply

Agent drafts, user sends — never send autonomously.

## Routing Signals

- Task title starts with "Reply to"
- Email task created via [[email-capture]] or [[email-triage]]

## Pre-Requisites

1. Load the user's voice/style reference.
2. If scheduling: check calendar availability first.

## Steps

1. Retrieve the original email (by entry_id or search).
2. Draft using the user's voice.
3. Create a draft via the reply tool — **never send**.
4. Task stays `active` until the user confirms it's sent.

## Complexity Routing

| Type                   | Action                                      |
| ---------------------- | ------------------------------------------- |
| Simple acknowledgment  | Direct reply                                |
| Scheduling, requests   | Agent drafts                                |
| Sensitive, negotiation | Block for the user — draft nothing, flag it |
