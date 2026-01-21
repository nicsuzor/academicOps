# Email Reply Workflow

Drafting email replies for tasks created by `/email`. Agent creates drafts, user sends.

**Used by**: pull command (when task title starts with "Reply to")

## Pre-Requisites

1. **Load user voice**: Read `$ACA_DATA/STYLE.md` for writing voice and tone
2. **Check calendar**: If scheduling-related, check upcoming events for availability

## Retrieve Original Email

**Primary**: Extract `entry_id` from task body, fetch with messages_get
**Fallback**: Search by sender name and match by subject

## Draft Reply

1. Draft using user's voice from STYLE.md
2. Create draft via messages_reply (NOT send)
3. Report: "Draft created in Outlook Drafts folder"

**Never send emails directly** - always create drafts for user approval.

## Completion Semantics

| State | Task Status |
|-------|-------------|
| Draft created | `active` (await user) |
| Email not found | `blocked` |
| Complex/sensitive | `blocked`, tag `human` |
| User confirms sent | `done` |

## Complexity Decision Tree

| Type | Examples | Action |
|------|----------|--------|
| Simple | "Thanks!", quick ack | Direct reply, no task |
| Medium | Scheduling, requests | Agent drafts |
| Complex | Sensitive, negotiation | User drafts |
