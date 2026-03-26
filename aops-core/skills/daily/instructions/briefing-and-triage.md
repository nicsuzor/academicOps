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

## 2. Email triage (delegate to /email)

**MANDATORY**: Email processing is handled by the `/email` skill, not inline. Invoke it:

```
Skill(skill="email", args="--daily")
```

The `/email` skill handles everything: fetching, sent-mail cross-referencing, classification, task creation with full email content, and duplicate prevention. See [[workflows/email-capture]] for details.

**Why delegate**: Inline email processing leads to shallow task bodies — missing quoted text, no links, no entry_id. The `/email` skill enforces the quality bar defined in [[workflows/email-capture]].

### 2.1: After /email completes

The `/email` skill returns:

- **Created tasks** (actionable emails → tasks with full context)
- **FYI items** (informational emails with content summaries)
- **Archive candidates** (already-handled or low-signal emails)

**Integrate results into the daily note**:

1. **FYI section**: Write FYI items into the daily note's "What Needs Attention" section. The user reads content in the note itself, not by opening emails.

2. **Thread grouping**: Group emails by conversation thread (same subject minus Re:/Fwd:). Present threads as unified summaries, not individual emails.

**Semantic chunking rule**: Each FYI item must be a **single self-contained unit** — either an h3 heading or a list item — with full actual text (selected but verbatim). The PKB indexes daily notes, so each chunk must make sense in isolation without surrounding context.

**Format in briefing**:

```markdown
## FYI

### [Thread Topic]

From [sender] to [recipients], [date]:

> [Verbatim quote of the key content — selected paragraphs, not paraphrase]

[1 sentence summary of what this means / why it matters]

- **→ Task**: [task-id] Task title (if action required)

### [Single Email Topic]

From [sender], [date]:

> [Actual email content — verbatim, not summarised]
```

**Incremental**: Cross-reference against the existing FYI section in today's note. If an email thread is already summarised there, skip it. Preserve any user annotations below existing FYI items.

**Archive flow (user confirmation required)**:

1. Present FYI content in daily note first
2. **DO NOT offer to archive yet** — user needs time to read and process
3. **Wait for user signal** — user will indicate when they've read the content
4. Only AFTER user has acknowledged, use `AskUserQuestion` to ask which to archive
5. Exception: Obvious spam can be offered for archive immediately

**Archiving emails**: Use `messages_move` with `folder_path="Archive"` (not "Deleted Items"). If the Archive folder doesn't exist for an account, ask the user which folder to use.

**Empty state**: If no new emails, leave existing FYI content unchanged and note "No new emails" in terminal output.

### 2.2: Verify FYI Persistence (Checkpoint)

Before moving to section 3, verify:

- [ ] Each action-requiring email has a task created (by `/email`)
- [ ] Each task body contains quoted email text, links, and entry_id
- [ ] FYI items in daily note are self-contained chunks with verbatim email content (not just subject lines)
- [ ] Relevant existing tasks updated with new info

**Rule**: Information captured but not persisted is information lost. Daily note is ephemeral; memory and tasks are durable.

If `/email` missed any actionable items, create tasks NOW before proceeding.
