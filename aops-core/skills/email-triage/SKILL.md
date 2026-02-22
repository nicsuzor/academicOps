---
name: email-triage
category: instruction
description: Email triage workflow with mandatory archive receipt logging to task body
allowed-tools: Read,Glob,Grep,Edit,Write,TodoWrite,AskUserQuestion,mcp__outlook__messages_list_recent,mcp__outlook__messages_get,mcp__outlook__messages_move,mcp__outlook__messages_search,mcp__pkb__update_task,mcp__pkb__create_task,mcp__memory__retrieve_memory
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
result = mcp__pkb__create_task(
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
mcp__pkb__update_task(
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

**Classification guardrails:**

- Personal invitations requesting participation → classify as **Task** (not FYI)
- Domain mismatches (e.g., medical grants for non-medical projects) → **Skip** or FYI
- Routine newsletters/receipts/automated alerts → usually **Skip**; archive after logging

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
mcp__pkb__update_task(
    id=task_id,
    body=f"| {count} | {email['date']} | {email['from']} | {email['subject']} |"
)
```

**Do NOT batch receipt writes. Each archive operation = immediate receipt append.**

### Step 6: Finalize Receipt Log

After all emails archived, append summary:

```python
mcp__pkb__update_task(
    id=task_id,
    body=f"\nAll {total_count} emails moved to {folder_name} folder."
)
```

## Interactive Supervised Mode

Interactive Supervised Mode is an extension of the standard 6-step workflow for runs where a human is actively supervising (human-in-the-loop). **All of Steps 1–6 still apply**, including the mandatory user checkpoint in Step 4; the rules below are additional guardrails that change *how* you execute those steps when the user is available for real-time review.

### Classification Workflow

1. **Classify first (refines Step 2 + Step 4)**: Before taking any action on emails, complete the full batch classification (Task/FYI/Skip) and present it to the user for review and confirmation. This user review happens at the Step 4 checkpoint, before any archive or move operations.
2. **Noise first (ordering within Steps 3–5)**: After user confirmation of the classification, archive Skip (noise) items first as a quick win, then proceed to process Task and FYI items according to the main workflow.

### Scheduling and Coordination

1. **Never propose dates**: When scheduling is required, use `AskUserQuestion` to present options — never assume dates or availability
2. **Multi-party coordination**: Before drafting coordination emails, ask "who else needs to be contacted?"

### Response Drafting

1. **Long threads (>2 messages)**: Summarise the thread state to the user before drafting a reply
2. **Non-responders**: When someone hasn't replied to a previous email, use a more tentative, warmer tone — not transactional
3. **Draft vs send**: Always confirm whether the user wants to save as draft or send

### Deferred Items

1. **Create task for deferred work**: Any actionable email that won't be handled immediately MUST get a task — never archive an actionable email without creating a task first

## Drafting Email Responses

When drafting responses, follow these requirements:

### Style Guide Prerequisite

**Before drafting ANY response**, load the user's email style guide from memory:

```python
mcp__memory__retrieve_memory(query="email style guide")
```

If no style guide is found, use these defaults:
- Sign-off: "Best" or "Cheers" (never "Best regards" or "Kind regards")
- Tone: Warm, direct, collegial — like talking to a respected peer over coffee
- Structure: Brief paragraphs, personal judgment language ("my intuition is...", "I'm happy to...")
- Avoid: Legal brief structure, numbered lists, formal headings, "I submit that"
- Default to brevity — if it feels like a memo, it's too formal

### Drafting Guardrails

- Apply the Interactive Supervised Mode guardrails above (long threads, non-responder tone, scheduling, draft vs send)
- If email requires action but NOT a reply to sender, do not suggest a response

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
    mcp__pkb__update_task(
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
