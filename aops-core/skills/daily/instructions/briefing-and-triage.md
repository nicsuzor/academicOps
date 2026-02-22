# Daily Note: Briefing and Triage

## 1. Create note

Check `$ACA_DATA/daily/YYYYMMDD-daily.md`.

**Symlink Management (CRITICAL)**: On EVERY invocation, update the `daily.md` symlink to point to today's note. This ensures shortcuts and quick-links remain valid:

```bash
ln -snf daily/YYYYMMDD-daily.md $ACA_DATA/daily.md
```

**If exists**: Skip to section 2. The note is updated in place.

**If missing**: Create from template (see [[references/note-template]]), then:

1. Read the previous working day's daily note
2. Identify task IDs from yesterday's Focus/Carryover sections
3. **Verify each task exists** (Step 1.1 below)
4. Copy "Abandoned Todos" to "## Carryover from Yesterday" section
5. Note overdue items from yesterday's Focus Dashboard

### 1.1: Verify Carryover Tasks (CRITICAL)

**Before including ANY task from yesterday's note in today's carryover:**

```python
for task_id in yesterday_task_ids:
    result = mcp__pkb__get_task(id=task_id)
    if not result["success"]:
        # Task was archived/deleted - EXCLUDE from carryover
        continue
    if result["task"]["status"] in ["done", "cancelled"]:
        # Task completed - EXCLUDE from carryover
        continue
    # Task still active - include in carryover
    carryover_tasks.append(result["task"])
```

**Why this matters**: Tasks archived between daily notes appear as "phantom overdue" items if copied blindly from yesterday's note. Always verify against the live task system.

### 1.2: Load Recent Activity

Read last 3 daily notes to show project activity summary:

- Which projects had work recently
- Current state/blockers per project

## 2. Update daily briefing

### 2.0: Load User Context for Email Classification

Before classifying emails, load domain context to filter by relevance:

```bash
Read $ACA_DATA/CORE.md        # User profile, research focus
Read $ACA_DATA/context/strategy.md  # Active projects and domains
```

**Use this context during classification**: Emails about funding, CFPs, conferences, or opportunities OUTSIDE the user's research domains should be classified as **Skip** (domain-irrelevant), not FYI. The user's domains are visible in strategy.md under "Projects" and "Strategic Logic Model".

### 2.1: Email Triage

Fetch recent emails via Outlook MCP:

```
mcp__outlook__messages_list_recent(limit=50, folder="inbox")
```

**CRITICAL - Check sent mail FIRST**: Before classifying ANY inbox email, you MUST fetch sent mail and cross-reference to avoid flagging already-handled items:

```
mcp__outlook__messages_list_recent(limit=20, folder="sent")
```

**For EACH inbox email**: Compare subject line (ignoring Re:/Fwd: prefixes) against sent mail subjects. If a matching sent reply exists, classify as **Skip** (already handled). This cross-reference is MANDATORY - skipping it causes duplicate task creation.

**Incremental**: Also cross-reference against the existing FYI section in today's note. If an email thread is already summarised there, skip it.

**Classify each email** using [[workflows/triage-email]] criteria (LLM semantic classification, not keyword matching).

### 2.2: FYI Content in Daily Note

**Goal**: User reads FYI content in the daily note itself, not by opening emails.

**Thread grouping**: Group emails by conversation thread (same subject minus Re:/Fwd:). Present threads as unified summaries, not individual emails.

**For each FYI thread/item**, fetch full content with `mcp__outlook__messages_get` and include:

- Thread participants and who said what (if multiple contributors)
- **Actual content**: The key information - quote directly for short emails, summarize for long ones

**Format in briefing**:

```markdown
## FYI

### [Thread Topic]

[Participants] discussed [topic]. [Key content/decision/info].

> [Direct quote if short]

### [Single Email Topic]

From [sender]: [Actual content or summary]
```

**CRITICAL - For each FYI item, IMMEDIATELY after writing it:**

1. **If action required** (feedback, review, response, decision) → `mcp__pkb__create_task()` NOW
   - Include deadline if mentioned or implied
   - **Then add task link to FYI content**: `- **→ Task**: [task-id] Task title`
2. **If links to existing task** → `mcp__pkb__update_task()` with the info
3. **If worth future recall** → `mcp__memory__store_memory()` with tags

Do NOT batch these to a later step. Task creation happens AS you process each email, not after.

**Archive flow (user confirmation required)**:

1. Present FYI content in daily note (complete section 2.2)
2. **DO NOT offer to archive yet** - user needs time to read and process the content
3. **Wait for user signal** - user will indicate when they've read the content (e.g., responds to the briefing, asks a question, or says "ok" / "got it")
4. Only AFTER user has acknowledged the content, use `AskUserQuestion` to ask which to archive
5. Exception: Obvious spam (promotional, irrelevant newsletters) can be offered for archive immediately

**Archiving emails**: Use `messages_move` with `folder_path="Archive"` (not "Deleted Items" - that's trash, not archive). If the Archive folder doesn't exist for an account, ask the user which folder to use.

**Empty state**: If no new FYI emails, leave existing FYI content unchanged.

### 2.3: Verify FYI Persistence (Checkpoint)

Before moving to section 3, verify you completed the inline persistence from 2.2:

- [ ] Each action-requiring FYI has a task created
- [ ] Relevant existing tasks updated with new info
- [ ] High-value FYI items stored in memory

**Rule**: Information captured but not persisted is information lost. Daily note is ephemeral; memory and tasks are durable.

If you skipped any, go back and create tasks NOW before proceeding.
