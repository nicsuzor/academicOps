---
name: email-triage
category: instruction
description: Email triage workflow with mandatory archive receipt logging to task body
allowed-tools: Read,Glob,Grep,Edit,Write,TodoWrite,AskUserQuestion,mcp__outlook__messages_list_recent,mcp__outlook__messages_get,mcp__outlook__messages_move,mcp__outlook__messages_search,mcp__plugin_aops-core_task_manager__update_task,mcp__plugin_aops-core_task_manager__create_task
version: 1.0.0
permalink: skills-email-triage
---

# Email Triage Skill

Triage inbox emails with MANDATORY archive receipt logging. Receipts are written to task body concurrently during execution, not after.

## CRITICAL: Archive Receipt Requirement

**Every archive operation MUST produce a receipt log in the task body.**

This is non-negotiable. The user cannot audit or revert archive operations without receipts. Writing receipts to scratchpad is UNACCEPTABLE - scratchpad is ephemeral, task body is persistent.

### Receipt Format

```markdown
## Archive Receipt Log (N emails)

| #   | Date       | From             | Subject                             |
| --- | ---------- | ---------------- | ----------------------------------- |
| 1   | 2025-11-19 | Email Quarantine | End User Digest: 7 New Messages     |
| 2   | 2025-11-19 | QUT Travel       | Your Travel (#893940) has concluded |
| ... |            |                  |                                     |

All N emails moved to [Archive Folder] folder.
```

### Concurrent Write Pattern

**WRONG** (batch at end - data loss risk):

```
1. Archive email 1
2. Archive email 2
...
N. Archive email N
N+1. Write all receipts to task body  # If this fails, ALL receipts lost
```

**RIGHT** (concurrent - partial receipt on failure):

```
1. Archive email 1 → immediately append receipt to task body
2. Archive email 2 → immediately append receipt to task body
...
N. Archive email N → immediately append receipt to task body
```

## Workflow

### Step 1: Bind to Task

**MANDATORY**: This skill requires a task to write receipts to.

```python
# Option A: Use existing task
task_id = "<provided-task-id>"

# Option B: Create new task
result = mcp__plugin_aops-core_task_manager__create_task(
    task_title="Email triage: [date range/criteria]",
    type="task",
    project="<project>",
    tags=["email", "triage"]
)
task_id = result["task"]["id"]
```

**If no task is bound, HALT. Do not proceed without a task ID for receipt logging.**

### Step 2: Initialize Receipt Log

Before archiving ANY emails, initialize the receipt table header in the task body:

```python
mcp__plugin_aops-core_task_manager__update_task(
    id=task_id,
    body="""## Archive Receipt Log

| # | Date | From | Subject |
|---|------|------|---------|"""
)
```

### Step 3: Fetch and Classify Emails

Fetch emails based on criteria:

```python
# Recent emails
emails = mcp__outlook__messages_list_recent(limit=50, folder="inbox")

# Or search by criteria
emails = mcp__outlook__messages_search(
    subject="keyword",
    person="sender@example.com",
    is_unread=True
)
```

**Classification categories** (semantic, not keyword-based):

| Category | Description                            | Action              |
| -------- | -------------------------------------- | ------------------- |
| **Task** | Requires action, response, or decision | Create task         |
| **FYI**  | Useful information, no action needed   | Read and archive    |
| **Skip** | Spam, irrelevant, auto-generated noise | Archive immediately |

**Reply-waiting signals** (ALWAYS Task, never FYI):

- "following up", "checking in", "any update", "wanted to touch base"
- "haven't heard back", "just checking", "circling back"
- Questions awaiting answer from a previous thread
- External parties waiting for scheduling, confirmation, or decision
- PhD/collaboration inquiries requesting supervision or meeting

### Step 4: User Checkpoint Before Archive

**MANDATORY**: Get user approval before archiving.

Use `AskUserQuestion` to present:

1. Count of emails per category
2. Sample subjects from each category
3. Confirmation to proceed with archive

```python
AskUserQuestion(
    questions=[{
        "question": "Ready to archive N emails (X Skip, Y FYI)?",
        "header": "Archive",
        "options": [
            {"label": "Archive all", "description": "Proceed with archiving classified emails"},
            {"label": "Review first", "description": "Show me the full list before archiving"},
            {"label": "Cancel", "description": "Do not archive anything"}
        ],
        "multiSelect": False
    }]
)
```

### Step 5: Archive with Concurrent Receipts

**For each email to archive:**

1. Move the email:

```python
mcp__outlook__messages_move(
    entry_id=email["entry_id"],
    folder_path="Archive"  # Or user-specified folder
)
```

2. **IMMEDIATELY** append receipt to task body:

```python
mcp__plugin_aops-core_task_manager__update_task(
    id=task_id,
    body=f"| {count} | {email['date']} | {email['from']} | {email['subject']} |"
)
```

**Do NOT batch receipt writes. Each archive operation = immediate receipt append.**

### Step 6: Finalize Receipt Log

After all emails archived, append summary:

```python
mcp__plugin_aops-core_task_manager__update_task(
    id=task_id,
    body=f"\nAll {total_count} emails moved to {folder_name} folder."
)
```

## Batch Processing (Large Volumes)

For 100+ emails, use chunking per [[workflows/batch-processing]]:

### Chunking Strategy

- **Temporal**: By month (e.g., "Nov 2025", "Dec 2025")
- **Categorical**: By sender domain or type
- **Size-based**: Fixed chunks of 20-50 emails

### Parallel Worker Pattern

Spawn parallel workers, each with the task ID for receipt logging:

```python
Task(
    subagent_type="general-purpose",
    prompt=f"""Process Nov 2025 emails for triage.

    Task ID for receipts: {task_id}

    For EACH email archived, IMMEDIATELY append receipt:
    mcp__plugin_aops-core_task_manager__update_task(
        id='{task_id}',
        body='| N | DATE | FROM | SUBJECT |'
    )

    Classification criteria: [criteria]
    Archive folder: Archive
    """,
    run_in_background=True
)
```

### Worker Receipt Responsibility

**Each worker is responsible for its own receipts.** The supervisor does NOT aggregate receipts after the fact - they are written during execution by each worker.

## Error Handling

| Error                   | Response                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Archive fails mid-batch | Task body contains partial receipt up to failure point - audit trail preserved     |
| Task update fails       | HALT immediately. Log error. Do NOT continue archiving without receipt persistence |
| Outlook unavailable     | HALT. Do not proceed without email access                                          |
| No task bound           | HALT. Create or specify task before any archive operations                         |

## Quality Gates

Before marking triage complete:

- [ ] All archived emails have receipt entries in task body
- [ ] Receipt count matches archive count
- [ ] User approved archive operation
- [ ] Task body contains final summary with total count and folder

## Example Output

Task body after successful triage:

```markdown
# Email triage: QUT inbox (Nov 2025 - Feb 2026)

## Archive Receipt Log (188 emails)

| #   | Date       | From                         | Subject                             |
| --- | ---------- | ---------------------------- | ----------------------------------- |
| 1   | 2025-11-19 | Email Quarantine             | End User Digest: 7 New Messages     |
| 2   | 2025-11-19 | QUT Travel                   | Your Travel (#893940) has concluded |
| 3   | 2025-11-18 | QUT DVC Research             | Read and Publish Agreement Update   |
| ... |            |                              |                                     |
| 188 | 2026-02-01 | alerts-noreply@clarivate.com | Web of Science Alert                |

All 188 emails moved to QUT Archive folder.
```
