---
name: email
description: This skill provides expertise for interacting with Outlook email via
  MCP tools. Use when agents or subagents need to fetch, read, list, or search emails.
  Includes email triage patterns, signal detection (urgent/deadlines), and filtering
  guidelines. Does NOT handle task extraction (use tasks skill for that).
permalink: aops/skills/email/skill
---

# Email: Outlook MCP Expertise

## Overview

This skill provides the single point of expertise for interacting with Microsoft Outlook email using MCP (Model Context Protocol) tools. It documents HOW to use the `mcp__outlook__*` tools for fetching, reading, listing, and searching emails.

**Agents and subagents should use this skill** (not implement email handling themselves) to ensure consistent email interactions across the system.

## Outlook MCP Tools Reference

The Outlook MCP server provides these tools (all prefixed with `mcp__outlook__`):

- **`mcp__outlook__messages_index`** - Overview of inboxes and folders
- **`mcp__outlook__messages_list_recent`** - List recent emails
- **`mcp__outlook__messages_get`** - Read specific email content
- **`mcp__outlook__messages_query`** - Search emails with filters

## Core Email Operations

### 1. Get Inbox Overview

To see inbox status and available folders:

```python
mcp__outlook__messages_index()
```

This returns:
- Total message counts per folder
- Unread counts
- Available folders

### 2. List Recent Emails

To retrieve recent emails from inbox:

```python
mcp__outlook__messages_list_recent(
    folder="inbox",      # Optional: "inbox" (default), "sent", "drafts", etc.
    limit=20             # Optional: number of messages to return (default: 20)
)
```

Returns list of emails with:
- `entry_id` - Unique identifier for retrieving full content
- `subject` - Email subject line
- `from` - Sender information
- `received_date` - When email was received
- `is_read` - Read status
- `has_attachments` - Whether email has attachments

### 3. Read Email Content

To retrieve full content of a specific email:

```python
mcp__outlook__messages_get(
    entry_id="...",      # Required: from messages_list_recent
    format="text"        # Optional: "text" (default) or "html"
)
```

Returns:
- Full email body (plain text or HTML)
- All metadata (subject, from, to, cc, date)
- Attachment information

### 4. Search Emails

To search for specific emails:

```python
mcp__outlook__messages_query(
    query="subject:conference",  # Search query
    folder="inbox",              # Optional: folder to search
    limit=50                     # Optional: max results
)
```

**Query syntax examples**:
- `subject:conference` - Search in subject
- `from:alice@example.com` - Search by sender
- `received>2025-10-01` - Date filtering
- Can combine with AND/OR operators

## Email Triage Patterns

### Priority Signal Detection

When processing emails, use these signals to assess importance:

**From/Sender signals**:
- From supervisor → likely high priority
- From collaborator → medium priority (check deadline)
- From admin → usually low priority unless time-sensitive
- Conference/journal → check deadlines

**Subject signals**:
- "Urgent" or "ASAP" → high priority
- "Reminder" → check deadline date
- "RE:" or "FW:" → check thread context
- Conference/deadline keywords → extract dates

**Content signals** (after reading):
- Explicit deadlines ("by Friday", "due Nov 15")
- Meeting requests ("can we meet")
- Review requests ("please review")
- Action items ("could you", "need your")

### Filtering Workflow

**Academic/Work vs Noise**:

1. **High signal** (worth presenting to user):
   - From known academic contacts
   - Conference/journal submissions
   - Meeting requests
   - Collaboration invites
   - Student communications
   - Administrative deadlines

2. **Low signal** (can usually skip):
   - Marketing/promotional
   - Automated notifications (unless actionable)
   - Newsletters (unless explicitly relevant)
   - Social media notifications

3. **When uncertain**: Present to user with context

### Batch Processing Pattern

When checking email (e.g., via `/email` command):

1. **List recent** (20-50 messages):
   ```python
   messages = mcp__outlook__messages_list_recent(limit=30)
   ```

2. **Filter by signal**:
   - Unread messages
   - From known senders
   - Subject keywords matching research/work

3. **Read high-priority** messages only:
   ```python
   for msg in high_priority_messages:
       content = mcp__outlook__messages_get(entry_id=msg.entry_id)
       # Process content
   ```

4. **Present summary** to user with actionable items

## Integration with Other Skills

**Tasks skill**:
- Email skill handles FETCHING emails
- Tasks skill handles CREATING tasks from email content
- Agents should use both: email to fetch → tasks to extract

**Typical workflow**:
1. Agent uses email skill to fetch recent messages
2. Agent reads relevant email content
3. Agent uses tasks skill to create tasks for actionable items
4. Agent presents summary to user

## Email Thread Handling

**CRITICAL**: Outlook email bodies include ENTIRE THREAD HISTORY (quoted messages).

When processing emails:
- Content BEFORE `On [date]...wrote:` or `>` quote markers = CURRENT message
- Everything after = old quoted history
- Use `received` field for dating (NOT dates found in quoted text)
- Extract and summarize CURRENT message only (ignore quoted history)

## Email Processing Constraints

**DO**:
- Fetch and read emails
- Filter/prioritize based on signals
- Present summaries to user
- Extract information for task creation
- Parse email threads to extract CURRENT message only
- Use metadata (received date) not body content for dating

**DO NOT**:
- Archive or delete emails (user controls this)
- Reply to emails (user controls this)
- Move emails between folders (user controls this)
- Process entire mailbox uninvited (fetch recent only)
- Mark emails as read/unread (MCP may not support)
- Present entire email thread history (summarize instead)
- Extract dates from quoted portions of email body

## Common Usage Patterns

### Pattern 1: Check for Urgent Messages

```python
# Get recent unread emails
recent = mcp__outlook__messages_list_recent(limit=20)

# Filter unread with urgency signals
urgent = [msg for msg in recent
          if not msg.is_read
          and ("urgent" in msg.subject.lower()
               or "asap" in msg.subject.lower())]

# Read full content of urgent messages
for msg in urgent:
    content = mcp__outlook__messages_get(entry_id=msg.entry_id)
    # Process...
```

### Pattern 2: Find Deadline-Related Emails

```python
# Search for conference/deadline emails
deadline_emails = mcp__outlook__messages_query(
    query="subject:deadline OR subject:due OR subject:conference"
)

# Read and extract deadline dates
for msg in deadline_emails:
    content = mcp__outlook__messages_get(entry_id=msg.entry_id)
    # Extract dates, create tasks...
```

### Pattern 3: Check Specific Sender

```python
# Search for emails from specific person
supervisor_emails = mcp__outlook__messages_query(
    query="from:supervisor@university.edu",
    limit=10
)

# Process recent messages from supervisor
```

## Best Practices

**DO**:
- Fetch reasonable batch sizes (20-50, not 1000)
- Filter before reading full content (save API calls)
- Use signal detection to prioritize
- Present summaries, not raw dumps
- Check unread messages first

**DON'T**:
- Process entire mailbox (invasive, slow)
- Read every email's full content (expensive)
- Make assumptions about email actions (let user decide)
- Archive/delete without explicit user request
- Spam the user with every email detail

## Quick Reference

**Most common workflow**:

```python
# 1. List recent emails
messages = mcp__outlook__messages_list_recent(limit=30)

# 2. Filter for actionable items
actionable = [msg for msg in messages
              if not msg.is_read
              and is_high_priority(msg)]

# 3. Read high-priority messages
for msg in actionable:
    content = mcp__outlook__messages_get(entry_id=msg.entry_id)
    # Extract tasks, present to user...

# 4. Present summary
# Show: count, important senders, urgent items, action needed
```

## Error Handling

**Common issues**:
- MCP server not configured → Check `config/mcp.json` for `outlook` entry
- Authentication failures → MCP server may need restart
- Rate limiting → Reduce batch sizes, add delays

**Graceful degradation**:
- If MCP unavailable, inform user (don't fail silently)
- If specific email unreadable, skip and continue
- If search fails, try simpler query
