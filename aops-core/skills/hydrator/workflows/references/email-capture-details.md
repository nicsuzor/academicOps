# Email-to-Task Capture Details

Detailed procedures, tool configurations, and classification logic for the email-to-task workflow.

## Step 0: Check Existing Tasks (MANDATORY)

Before creating any task from an email, search the PKB to prevent duplicates. Emails persist in inbox and get re-read by this workflow — without this check, the same email generates a new task every time.

For EACH email that would generate a task:

1. `task_search(query="<email subject or key action phrase>")` — search for existing task
2. If match found: compare titles and content. If clearly the same action → **SKIP creation**, note "already tracked as `<matched_id>`" in summary
3. If ambiguous match (similar but not identical): present both to user before creating
4. If task exists in archive/completed: already handled, definitely skip
5. Match by: email subject, sender name, or key action phrase

There is no server-side dedup on task creation — this step is the only duplicate prevention mechanism.

## Step 1: Fetch and Check Responses

### Fetch Recent Emails

Use `~~email.messages_list_recent` to get the latest messages. Focus on unread emails in primary inbox.

### Check for Existing Responses

Extract key subject words and query for replies from the user's email address. If a match is found, mark as "already responded" and skip task creation.

## Step 2: Analyze and Classify

| Category           | Signals                                               | Action                           |
| ------------------ | ----------------------------------------------------- | -------------------------------- |
| **Actionable**     | deadline, "please", "review", "vote", direct question | Create task                      |
| **Important FYI**  | "awarded", "accepted", "decision", from grant bodies  | Read body, extract info, present |
| **Safe to ignore** | noreply@, newsletter, digest, automated               | Archive candidate                |

## Step 3 & 4: Context and Categorization

Query the PKB for relevant context (projects, goals, relationships). Match actions to projects/tags with confidence scores:

- **High (>80%)**: Auto-apply categorization
- **Medium (50-80%)**: Suggest but flag for review (#suggested-categorization)
- **Low (<50%)**: Create in inbox, needs manual categorization (#needs-categorization)

## Step 5 & 6: Priority and Task Creation

### Infer Priority and Metadata

1. **Infer Priority**:
   - **P0 (Urgent)**: Deadlines < 48h, OSB votes, explicit urgent markers.
   - **P1 (High)**: Deadlines < 1 week, grant/paper deadlines.
   - **P2 (Normal)**: General correspondence, FYI with follow-up.
   - **P3 (Low)**: No deadline, administrative.

2. **Extract Structured Metadata**:
   - **due**: Extract deadline from email body. Format: ISO date (YYYY-MM-DD).
   - **effort**: Estimate effort required for the task. Format: duration (0.5d, 1d, 1w).
   - **consequence**: Extract stated or implied consequences if the task is not completed.

### Create "Ready for Action" Tasks

Tasks must be **self-contained** — a person reading the task should understand what's needed without opening the original email.

#### Task Body Quality Requirements (MANDATORY)

Every email-derived task body MUST include:

1. **Quoted email text**: The actual email content, not just a summary. For short emails, quote the full body. For long emails, quote the key paragraphs verbatim and summarise the rest. Use blockquote (`>`) formatting.

2. **All links preserved**: Every URL from the email body must appear in the task. Group under a `## Links` section:
   - Document links (Google Docs, Dropbox, SharePoint, etc.)
   - Registration/submission links
   - Reference URLs

3. **Sender and recipients**: Who sent it, who was CC'd, and the date. This is context for understanding the request.

4. **Entry ID**: The `entry_id` from the email connector, so `/pull` can retrieve the original in one API call.

5. **Deadline**: Extracted or inferred deadline, prominently placed.

**Anti-pattern**: A task that says "Review the attached document and provide feedback by Friday" without quoting the email and without the actual links. This is useless — the person pulling the task has no context.

**Template**:

```markdown
## Summary

[1-2 sentence action required]

## Email Content

From: [sender] | To: [recipients] | Date: [date]
Entry ID: [entry_id]

> [Quoted email text — actual content, not paraphrase]

## Links

- [Description](url)
- [Description](url)

## Attachments

- original.docx (attached to email — retrieve when actioning)
- report.pdf (attached to email)

## Action Required

- [ ] [Specific action item]
- [ ] [Deadline: YYYY-MM-DD]

## Metadata

- **due**: YYYY-MM-DD
- **effort**: [duration]
- **consequence**: [prose]
```

**PKB field storage (MANDATORY)**: Pass `due`, `effort`, and `consequence` as explicit parameters to `mcp__pkb__create_task` — not only in the body template. The PKB uses `due` as a structured field for deadline-aware prioritization (`days_until_due`); writing it only in body prose leaves that computed property empty and silently breaks deadline-based task ordering.

#### Resource Handling

- **Links**: Preserve all URLs from the email body in the task's `## Links` section. Never silently drop links.
- **Attachments**: Note attachment filenames in the task body. Do NOT download attachments to the PKB during email triage — attachment processing (download, conversion) happens later via the daily briefing workflow when the task is actioned.
- **If the task depends on an attachment**: Flag this clearly in the Action Required section so the person pulling the task knows to retrieve it.

## Step 8: Presentation and Summary

Present Important FYI content, already responded items, and created tasks to the user. Use `AskUserQuestion` to confirm archiving of "safe to ignore" candidates.

## Configuration: Archive Folders

| Account        | Tool               | Parameter               |
| -------------- | ------------------ | ----------------------- |
| Gmail          | `messages_archive` | `folder_id="211"`       |
| QUT (Exchange) | `messages_move`    | `folder_path="Archive"` |
