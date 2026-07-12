# Email-to-Task Capture Details

Detailed procedures, tool configurations, and classification logic for the email-to-task workflow.

## Step 0: Check Existing Tasks

Before fetching emails, check existing tasks to prevent duplicates. Emails persist in inbox and get re-read by this workflow.

- If task exists in inbox: Skip creating, note in summary
- If task exists in archive: Already completed, definitely skip
- Match by: email subject, sender name, or key action phrase

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

### Infer Priority

- **P0 (Urgent)**: Deadlines < 48h, OSB votes, explicit urgent markers.
- **P1 (High)**: Deadlines < 1 week, grant/paper deadlines.
- **P2 (Normal)**: General correspondence, FYI with follow-up.
- **P3 (Low)**: No deadline, administrative.

### Create "Ready for Action" Tasks

Tasks must include structured summaries, detected resources (attachments/links), and clear action items.

#### Resource Processing

- **Attachments**: Download to designated directory.
- **Linked Docs**: Scan body for Google Docs/Dropbox/etc. links and download/convert.
- **Conversion**: Use pandoc to convert `.docx` to markdown.

## Step 8: Presentation and Summary

Present Important FYI content, already responded items, and created tasks to the user. Use `AskUserQuestion` to confirm archiving of "safe to ignore" candidates.

## Configuration: Archive Folders

| Account        | Tool               | Parameter               |
| -------------- | ------------------ | ----------------------- |
| Gmail          | `messages_archive` | `folder_id="211"`       |
| QUT (Exchange) | `messages_move`    | `folder_path="Archive"` |
