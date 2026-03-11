---
name: process-bundle
type: skill
category: instruction
description: Process annotated briefing bundle — execute decisions, stage email drafts, create tasks from annotations. Never auto-sends email.
triggers:
  - "process bundle"
  - "process annotations"
  - "execute bundle decisions"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
allowed-tools: Read,Bash,Grep,Edit,Write,~~email,~~calendar,~~pkb
version: 0.1.0
permalink: skills-process-bundle
---

# Process Bundle Skill

Process a briefing bundle that Nic has annotated. Scan for `<!-- @nic: -->` annotations, execute the corresponding action for each, and append a processing receipt.

## CRITICAL BOUNDARY

**This skill executes decisions. It does NOT generate bundles.**

- Email drafts are staged in Outlook as drafts -- **never auto-sent**
- Task status changes are written to PKB
- Each action is logged in the processing receipt
- If an annotation is ambiguous, log it as `needs_clarification` and skip

## Invocation

```
/process-bundle         # Process today's bundle
/process-bundle DATE    # Process a specific date's bundle (YYYYMMDD)
```

## Pipeline

### 1. Locate bundle

```python
# Today's bundle by default
bundle_path = f"$ACA_DATA/daily/{date}-bundle.md"
```

If the bundle doesn't exist, HALT: "No bundle found for {date}. Run /bundle first."

### 2. Scan for unprocessed annotations

Find all `<!-- @nic: -->` annotations that do NOT have a matching `<!-- @claude -->` response immediately after them.

```bash
Grep(pattern="<!--\\s*@nic:", path=bundle_path, output_mode="content", -C=2)
```

Filter out annotations that already have a `<!-- @claude YYYY-MM-DD: -->` response on the next line.

### 3. Process each annotation

For each unprocessed annotation, determine the action type and execute:

| Annotation                           | Action                                                                                                                            |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `<!-- @nic: approved -->`            | Execute the recommended action from the coversheet. Update task status in PKB.                                                    |
| `<!-- @nic: send -->`                | Stage the draft email in Outlook using `messages_reply` or `messages_create_draft`. Use the `In-Reply-To` entry_id for threading. |
| `<!-- @nic: send as edited -->`      | Read the (edited) draft text from the bundle. Stage in Outlook with the edited content.                                           |
| `<!-- @nic: decline -->`             | Execute the alternative/opposite action. Update task in PKB.                                                                      |
| `<!-- @nic: defer to YYYY-MM-DD -->` | Update task due date in PKB. No email action.                                                                                     |
| `<!-- @nic: noted -->`               | No action needed. Mark as processed.                                                                                              |
| `<!-- @nic: task: [title] -->`       | Create a new PKB task with the given title. Infer project from the FYI section context.                                           |
| `<!-- @nic: cancel -->`              | For carryover items: update task status to cancelled in PKB.                                                                      |
| `<!-- @nic: act -->`                 | For carryover items: move to today's active work. Update task status to in_progress.                                              |
| `<!-- @nic: [freeform] -->`          | Interpret the annotation. If clear enough to act, execute. If ambiguous, log as `needs_clarification`.                            |

#### Processing rules

1. **One annotation at a time, sequentially.** Process in document order (top to bottom).
2. **Log every action.** After processing each annotation, add a `<!-- @claude YYYY-MM-DD: [action taken] -->` response immediately after the `@nic` annotation.
3. **Fail-safe on email.** If `messages_reply` or `messages_create_draft` fails, log the error and continue. Never retry silently.
4. **Verify task IDs.** Before updating a task, verify it exists with `get_task`. If not found, log as `task_not_found` and skip.
5. **Never auto-send email.** All email actions create drafts only. Log the draft entry_id in the receipt.

### 4. Build processing receipt

After all annotations are processed, append a receipt table to the bundle:

```markdown
---

## Processing Receipt

Processed: YYYY-MM-DD HH:MM

| # | Section   | Item             | Annotation          | Action Taken                  | Status                |
| - | --------- | ---------------- | ------------------- | ----------------------------- | --------------------- |
| 1 | Decisions | [title]          | approved            | Task [id] updated to done     | ✅                    |
| 2 | Emails    | Reply: [subject] | send                | Draft staged (entry_id: [id]) | ✅                    |
| 3 | FYI       | [headline]       | task: Review X      | Task [id] created             | ✅                    |
| 4 | Decisions | [title]          | defer to 2026-03-15 | Task [id] due date updated    | ✅                    |
| 5 | Carryover | [item]           | [freeform]          | --                            | ⚠️ needs_clarification |
```

Status indicators:

- ✅ Successfully processed
- ⚠️ Needs clarification or partial failure
- ❌ Failed (with error description)

### 5. Summary output

Print to terminal:

```
Bundle processed: daily/YYYYMMDD-bundle.md
N annotations processed: N✅ N⚠️ N❌
Emails staged: N drafts
Tasks updated: N
Tasks created: N

Items needing clarification:
- #5: [freeform annotation text] -- couldn't determine action
```

## Error Handling

| Failure                       | Behaviour                                         |
| ----------------------------- | ------------------------------------------------- |
| Bundle not found              | HALT: "No bundle found for {date}"                |
| No unprocessed annotations    | Print "No pending annotations" and exit           |
| Outlook unavailable           | Skip email actions, log all as ⚠️, note in summary |
| PKB unavailable               | Skip task actions, log all as ⚠️, note in summary  |
| Task ID not found             | Log as ⚠️ `task_not_found`, continue               |
| Ambiguous freeform annotation | Log as ⚠️ `needs_clarification`, continue          |
| Email staging fails           | Log as ❌ with error, continue                    |

## Idempotency

Processing is idempotent. Re-running `/process-bundle` on the same bundle will:

1. Find only annotations without `<!-- @claude -->` responses
2. Skip already-processed annotations
3. Append a new receipt section (not overwrite the previous one)

This means it's safe to run multiple times if processing was interrupted.
