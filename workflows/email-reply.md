# Email Reply Workflow

Drafting email replies for tasks created by `/email`. Agent creates drafts, user sends.

**Used by**: [[commands/pull]] (when task title starts with "Reply to")

## Pre-Requisites

Before drafting any email reply:

1. **Load user voice**: Read `$ACA_DATA/STYLE.md` to understand the user's writing voice, tone preferences, and communication style
2. **Check calendar**: If scheduling-related, call `mcp__plugin_aops-tools_outlook__calendar_list_upcoming(days=14)` to know availability

## Retrieve Original Email

**Primary method** (tasks with `entry_id`):
1. Extract `entry_id` from task body - look for: `**entry_id**: \`<id>\``
2. Retrieve: `mcp__plugin_aops-tools_outlook__messages_get(entry_id="<id>", format="text")`

**Fallback** (legacy tasks without `entry_id`):
1. Extract sender name from task title: "Reply to <name>: ..."
2. Search: `mcp__plugin_aops-tools_outlook__messages_search(person="<name>", limit=10)`
3. Match by subject/context from task body
4. If not found: Update task as `blocked`, report to user

## Draft Reply

1. Draft reply using user's voice from STYLE.md
2. Create draft: `mcp__plugin_aops-tools_outlook__messages_reply(entry_id="<id>", body="<draft>")`
3. Report: "Draft created in Outlook Drafts folder. Please review and send."

**Do NOT send emails directly** - always create drafts for user approval.

## Completion Semantics

| State | Task Status | Action |
|-------|-------------|--------|
| Draft created | `active` | Report draft location, await user |
| Email not found | `blocked` | Update task, explain issue |
| Complex/sensitive | `blocked` | Tag `human`, user drafts manually |
| User confirms sent | `done` | Complete task |

**Key rule**: Task stays `active` until user confirms the email was sent.

## Email Complexity Decision Tree

| Type | Examples | Workflow |
|------|----------|----------|
| Simple | "Thanks!", quick ack | Direct reply, no task needed |
| Medium | Scheduling, requests, questions | Agent drafts, user sends |
| Complex | Sensitive, negotiation, bad news | Tag `human`, user handles |

## Voice Guidelines

When drafting, match the user's voice from STYLE.md:
- Tone (formal/casual)
- Signature preferences
- Common phrases/patterns
- Length preferences (concise vs detailed)

If STYLE.md doesn't exist or lacks email guidance, draft in a professional, friendly tone matching the formality of the original email.
