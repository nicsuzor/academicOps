---
id: email-reply
category: operations
bases: [base-task-tracking]
---

# Email Reply

Draft email replies. Agent drafts, user sends.

## Routing Signals

- Task title starts with "Reply to"
- Email task created by /email skill

## Pre-Requisites

1. Load user voice from [[STYLE.md]]
2. If scheduling: check calendar availability

## Unique Steps

1. Retrieve original email (entry_id or search)
2. Draft using user's voice
3. Create draft via messages_reply (**never send**)
4. Task stays `active` until user confirms sent

## Complexity Routing

| Type                   | Action         |
| ---------------------- | -------------- |
| Simple ack             | Direct reply   |
| Scheduling, requests   | Agent drafts   |
| Sensitive, negotiation | Block for user |
