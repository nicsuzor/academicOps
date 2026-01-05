---
name: email-task-capture
description: Extract action items from emails and create "ready for action" tasks with summaries, downloaded documents, and clear response requirements
permalink: skills/tasks/workflows/email-capture
tags: [workflow, email, task-capture, automation, memory, documents]
version: 2.0.0
phase: 2
backend: scripts
---

# Email → Task Capture Workflow

**Purpose**: Automatically extract action items from emails and create properly categorized tasks with full context linking.

**When to invoke**: User says "check my email for tasks", "process emails", "any new tasks from email?", or similar phrases indicating email-to-task workflow.

**Backend**: Pluggable - uses task scripts (Phase 1-2) or Tasks MCP (Phase 3+). Falls back gracefully if primary backend unavailable.

## Core Workflow

### Step 0: Check Existing Tasks (MANDATORY FIRST)

**Before fetching emails**, check existing tasks to prevent duplicates. Emails persist in inbox and get re-read by this workflow.

**Use memory server semantic search** (preferred over grep):
```
mcp__memory__retrieve_memory(query="email subject keywords")
```

**Fallback to file search if memory server unavailable**:
```bash
# Search inbox tasks
grep -li "SEARCH_TERM" $ACA_DATA/tasks/inbox/*.md

# Search archived tasks (already completed)
grep -li "SEARCH_TERM" $ACA_DATA/tasks/archived/*.md
```

**When duplicate detected**:
- If task exists in inbox: Skip creating, note in summary
- If task exists in archive: Already completed, definitely skip
- Match by: email subject, sender name, or key action phrase

**Why this matters**: Emails stay in inbox after task creation. Without this check, the same email creates duplicate tasks every time the workflow runs.

### Step 1: Fetch Recent Emails

**CRITICAL**: To check if Outlook MCP is available, CALL THE TOOL. Do NOT investigate config files, check `ListMcpResourcesTool`, or grep for settings. Just invoke the tool - if it works, proceed; if it errors, HALT.

**Tool**: `mcp__outlook__messages_list_recent`

**Parameters**:

```json
{
  "account": "n.suzor@qut.edu.au", // Optional: specific account or null for all
  "limit": 20 // Optional: number of messages (default 50)
}
```

**Example invocation**:

```json
{
  "tool": "mcp__outlook__messages_list_recent",
  "parameters": {
    "account": null,
    "limit": 20
  }
}
```

**Returns**: List of messages with `subject`, `from_name`, `from_email`, `received`, `body`, `entry_id`, `has_attachments`

**Key filters**:

- Focus on action-oriented emails (not newsletters, notifications)
- Prioritize unread emails in primary inbox
- Limit to manageable batch (10-20 emails per check)

### Step 1.5: Check for Existing Responses

For emails that look actionable, check if user has already responded (indicating the matter may be dealt with).

**Tool**: `mcp__outlook__messages_query_subject_contains`

**Process**:
1. Extract key subject words (strip "Re:", "Fwd:", "FW:" prefixes)
2. Query: `messages_query_subject_contains(term="[key subject words]", limit=5)`
3. Filter results where `from_email` contains user's email address (n.suzor@qut.edu.au or nic@suzor.net)
4. If match found: mark as "already responded"

**Already responded emails**:
- Skip task creation
- Still present to user: "Already responded: [subject] - you replied [date]"
- Include in summary so user sees it was detected

**Limitation**: Won't catch replies with heavily modified subjects or forwarded threads. Good enough for common case.

**Example**:
```
Incoming: "[ACTION REQUIRED] OSB Cycle 38 Vote"
Query: messages_query_subject_contains(term="OSB Cycle 38 Vote")
Found: "Re: [ACTION REQUIRED] OSB Cycle 38 Vote" from n.suzor@qut.edu.au
Result: Mark as already responded, skip task creation
```

### Step 2: Analyze and Classify Each Email

For each email, classify into one of three categories:

#### Category A: Actionable (Create Task)

**High-signal action indicators**:

- Explicit requests: "Please review...", "Can you...", "Need your..."
- Deadlines: "by Friday", "due Nov 15", "before the meeting"
- Decision points: "Your vote on...", "Approve/reject...", "Sign off on..."
- Scheduling: "Confirm attendance", "RSVP", "Book travel"
- Review requests: "Feedback needed", "Please comment", "Review attached"

**Context clues**:

- Email from known collaborators/supervisors (check from_email)
- Subject keywords: ACTION, URGENT, REVIEW, VOTE, DEADLINE, TODO
- Body markers: numbered lists, bullet points with tasks
- Questions directed at recipient

#### Category B: Important FYI (Read Body, Extract Info, Present to User)

**Signals for Important FYI** (not actionable, but user needs to see the info):

- Contains: "awarded", "accepted", "approved", "decision", "published", "outcome"
- From: OSB, ARC, SNSF, or other grant/research bodies
- Subject: conference acceptance, publication notification, funding outcome
- Significant deadline changes or policy updates affecting user's work

**For Important FYI emails**:
1. Read full body: `mcp__outlook__messages_get(entry_id, format="text")`
2. Extract key information (dates, amounts, outcomes, decisions, links)
3. Store for presentation before archiving

**Extract for Important FYI**:
```
{
  "category": "important_fyi",
  "subject": "Original subject",
  "from": "Sender name",
  "key_info": "1-3 sentence summary of the important information",
  "details": "Specific dates, amounts, links, or action items mentioned"
}
```

#### Category C: Safe to Ignore (Archive Candidate)

**Signals for safe-to-ignore**:

- From: noreply@, newsletter@, quarantine@, digest
- Subject: "Weekly digest", "Newsletter", "Update", travel alerts
- Automated notifications without specific action required
- Generic mass communications (CFPs to mailing lists, webinar invites)

**Safe to ignore emails**: Add to archive candidates list, present to user with "mark any to KEEP" option.

#### Classification Summary Table

| Category | Signals | Action |
|----------|---------|--------|
| **Actionable** | deadline, "please", "review", "vote", direct question | Create task |
| **Important FYI** | "awarded", "accepted", "decision", from grant bodies | Read body, extract info, present |
| **Safe to ignore** | noreply@, newsletter, digest, automated | Archive candidate |

**Extract for actionable items**:

```
{
  "title": "Concise action description (50 chars max)",
  "body": "Full context from email body (relevant paragraphs)",
  "deadline": "Extracted deadline (ISO format) or null",
  "raw_text": "Original email excerpt containing this action"
}
```

### Step 3: Gather Context from Memory Server

For each extracted action, query **memory server** for relevant context.

**Tool**: `mcp__memory__retrieve_memory`

**Parameters**:

```json
{
  "query": "search terms from email" // Required: search query string only
}
```

**Example invocation**:

```json
{
  "tool": "mcp__memory__retrieve_memory",
  "parameters": {
    "query": "OSB vote content removal oversight board"
  }
}
```

**Query construction**:

- Email subject line
- Sender name/email
- Key terms from action description

**Extract from memory**:

- **Projects**: Active projects matching email content
- **Goals**: Related strategic goals
- **Relationships**: Sender importance/collaboration history
- **Patterns**: Similar past tasks, typical categorizations

**Example**:

```
Email subject: "OSB Cycle 38 Vote - Content removal case #2024-123"
Memory query: "OSB vote content removal oversight board"
Returns: project: oversight-board, tags: [osb, vote, content-moderation]
```

### Step 4: Categorize with Confidence Scoring

Match actions to projects/tags with confidence scores:

**High confidence (>80%)**: Auto-apply categorization

- Strong project keyword match in memory
- Known sender-project association
- Clear deadline signals priority

**Medium confidence (50-80%)**: Suggest but flag for review

- Partial keyword match
- Unknown sender but clear topic
- Add tag: `#suggested-categorization`

**Low confidence (<50%)**: Create in inbox, needs manual categorization

- Ambiguous content
- No memory matches
- Add tag: `#needs-categorization`

**Categorization criteria**:

| Signal                                  | Project Match   | Priority Inference | Tags                         |
| --------------------------------------- | --------------- | ------------------ | ---------------------------- |
| "OSB vote", sender from oversight board | oversight-board | P0 (urgent)        | osb, vote, urgent            |
| "Review PhD thesis", academic sender    | phd-supervision | P1 (high)          | review, thesis, academic     |
| "Travel confirmation", booking service  | personal        | P3 (low)           | travel, admin                |
| "Feedback on draft", unknown sender     | inbox           | P2 (normal)        | needs-categorization, review |

### Step 5: Infer Priority

Determine priority (P0-P3) from email signals:

**P0 (Urgent)**:

- Explicit "URGENT", "ACTION REQUIRED" in subject
- OSB votes (strict deadlines)
- Deadline within 48 hours
- High-importance sender (OSB, department head)

**P1 (High)**:

- Deadline within 1 week
- Review requests from collaborators
- Meeting prep required
- Grant/paper deadlines

**P2 (Normal)**:

- Deadline within 2 weeks
- General correspondence
- FYI with follow-up needed
- Unclear urgency signals

**P3 (Low)**:

- No deadline
- Administrative tasks
- Travel confirmations
- Newsletter follow-ups

### Step 6: Create "Ready for Action" Tasks

Tasks should be ready to work on immediately - not just raw email captures. This step creates fully-prepared tasks with summaries, downloaded documents, and clear action items.

#### 6a. Summarize the Email

Read the full email and generate a structured summary:

1. **What the sender is asking for** (primary question/request)
2. **Secondary items** to address
3. **Concrete response actions** needed

This is natural LLM capability - read, understand, summarize.

#### 6b. Detect Resources

Identify documents that should be downloaded:

**Attachments**: Check `has_attachments` field from email response.

**Linked documents**: Scan email body for document URLs:
- `docs.google.com/document/*`
- `drive.google.com/*`
- `dropbox.com/*`
- `sharepoint.com/*`
- Direct file links (`.pdf`, `.docx`, `.xlsx`)

**Filter out noise**: Ignore signature links, unsubscribe links, tracking pixels, social media.

#### 6c. Download Resources

Use appropriate tool for each resource type:

**Email attachments**:
```
mcp__outlook__messages_download_attachments(
  entry_id="...",
  download_dir="$ACA_DATA/reviews/{sender}/"  # or task-documents/{task-id}/
)
```

**Google Docs/Drive**: Use rclone, Playwright, or direct download as appropriate.

**Other links**: Agent chooses appropriate method.

#### 6d. Convert to Markdown

After download, convert documents for repo storage:

- `.docx` → `pandoc` to markdown
- `.pdf` → keep as-is (or extract text if needed)
- Already markdown → no conversion

```bash
pandoc "document.docx" -o "document.md" --wrap=none
```

#### 6e. Organize Storage

Route documents based on task classification:

| Classification | Storage Location | Example |
|----------------|------------------|---------|
| Review | `$ACA_DATA/reviews/{sender}/` | `reviews/yara/Dissertation draft.md` |
| Supervision | `$ACA_DATA/reviews/{student}/` | `reviews/kashyap/Chapter1.md` |
| Other | `$ACA_DATA/task-documents/{task-id}/` | `task-documents/20251231-contract-review/contract.md` |

Create directories as needed. Use sender name (lowercase, sanitized) for reviews.

#### 6f. Create Task with Structured Body

**Task body template**:

```markdown
# Task Title

## Context

Brief context: who sent this, what it's about, when received.

**Google Doc:** [link if applicable]
**Email:** sender@email.com

## Summary: What You Need to Respond To

### Primary Question
[Main thing they're asking - extracted from email]

### Secondary Items to Address
1. [Other things mentioned]
2. [Additional questions]

## Response Needed
- [ ] First action item
- [ ] Second action item
- [ ] Optional: third item

## Associated Documents
- `reviews/yara/Dissertation draft - Yara.md` - Chapter 1 draft for review

## Original Email

**From:** Sender Name <email@example.com>
**Subject:** Original subject line
**Date:** Thursday, 18 December 2025 at 12:28:23

---

[Full email text preserved here]
```

#### 6g. Backend and Script Usage

**Backend selection logic**:

```
1. Check if Tasks MCP is available:
   - Try: Call view_tasks() tool
   - If successful: Use Tasks MCP backend
   - If fails: Fall back to scripts backend

2. Scripts backend (Phase 1-2, always available):
   - Use: task_add.py script via Bash tool
   - Pass structured body via --body-from-file or --body
```

**Task creation parameters** (scripts backend):

```
Required:
- --title: Action description (concise, actionable)
- --source-email-id: Outlook entry_id (REQUIRED for emails - enables dedup)

Optional:
- --priority: P0, P1, P2, or P3 (inferred from signals)
- --project: Project slug (from memory match)
- --classification: "Action", "Review", "Admin", etc.
- --due: Deadline in ISO8601 format
- --tags: Comma-separated tags
- --body or --body-from-file: Full structured task body
```

**Duplicate prevention**: If `--source-email-id` matches any existing task (inbox OR archived), creation is blocked.

#### Failure Handling

**Graceful degradation** - if any step fails:
- Note the failure in task body: "Could not download: [resource] - [reason]"
- Continue with available content
- Never abort the whole task creation

If document download fails, still create the task with links to the original resources.

### Step 7: Duplicate Prevention (Automatic)

**Handled by `task_add.py`**: When `--source-email-id` is provided, the script automatically checks inbox AND archived tasks. If the email ID exists, creation is blocked with an error message.

**No manual grep needed** - the script does this for you.

**If duplicate detected**:
- Script exits with error: "Duplicate: Email already processed as task"
- Shows which existing task matched
- Add to "Skipped (duplicate)" section in summary

### Step 8: Present Information and Summary

**MANDATORY**: Before archiving anything, present all important information to user. User must SEE the actual content, not just subject lines.

#### 8a: Present Important FYI Content

For each Important FYI email identified in Step 2, output the extracted information:

```markdown
## Important Information from Email

### Grant Outcome (from ARC, Dec 20)
ARC DP2025 awarded $450K for Platform Governance project.
Funding period: 2026-2028. Start date: January 2026.
Contact: grants@arc.gov.au

### Conference Acceptance (from AOIR Committee, Dec 19)
Paper "Platform Accountability Frameworks" accepted for AOIR 2025.
Presentation scheduled: October 15, 2025, Session 3B.
Registration deadline: September 1, 2025.

### OSB Decision Published (from OSB Operations, Dec 18)
Case 2024-089 decision now public.
Summary: Appeal upheld, content restored.
Full decision: https://oversightboard.com/decisions/2024-089
```

**No confirmation needed** - just output the information so user sees it.

#### 8b: Present Already Responded Items

Show emails where user's response was detected:

```markdown
## Already Responded (No Task Created)

- **OSB Cycle 38 Vote** - you replied Dec 20
- **PhD meeting confirmation** - you replied Dec 19
```

#### 8c: Present Tasks Created

```markdown
## Tasks Created

| Priority | Task | Due | Source |
|----------|------|-----|--------|
| P0 | SNSF Review (10.007.645) | Jan 15 | SNSF |
| P1 | Write Lucinda reference | - | Amanda Kennedy |
| P1 | ARC FT26 assessments | Jan 21 | ARC |
```

#### 8d: Archive Candidates (User Choice)

**After presenting all important info**, offer archive for safe-to-ignore emails:

```markdown
## Archive Candidates

Use AskUserQuestion with multiSelect to let user mark any to KEEP:
- QUT Newsletter Dec 23
- Travel Alert: NYC weather
- Quarantine Digest (7 messages)
- Edward Elgar book alert

(Default: archive all unmarked)
```

#### Full Example Output

```
## Important Information from Email

### FT210100263 Extension Approved (from ORS, Dec 23)
Your ARC Future Fellowship project end date has been extended to 30 September 2026.
Project: "Regulating and countering structural inequality on digital platforms"
No action required - this is confirmation only.

### Milestone Completed (from Pure/Elsevier, Dec 22)
Research output milestone recorded in Pure system.
Details: [logged for institutional reporting]

---

## Already Responded (No Task Created)

- **OSB Cycle 38 Vote** - you replied Dec 20

---

## Tasks Created

| Priority | Task | Due | Source |
|----------|------|-----|--------|
| P0 | Acquit corporate card | urgent | Card Program |
| P1 | ARC COI declaration | - | RMIT |
| P1 | Lucinda Nelson reference | - | Amanda Kennedy |

---

## Archive Candidates

[AskUserQuestion: Mark any to KEEP - default archives all]
```

## Error Handling

### Fail-Fast Scenarios

**Halt immediately and report**:

1. **Outlook MCP unavailable**
   - Error: `mcp__outlook__messages_list_recent` returns error
   - Action: Halt workflow, report to user
   - Message: "Cannot check email - Outlook MCP error: [exact error message]"
   - **DO NOT**: Investigate configs, check ListMcpResourcesTool, or try workarounds

2. **Both task backends unavailable**
   - Error: Cannot create tasks
   - Action: Halt workflow after email analysis
   - Message: "Found X action items but cannot create tasks (both backends unavailable)"

3. **Task creation fails in current backend**
   - Error: Validation error or file system error
   - Action: Try fallback backend, if both fail, halt
   - Message: "Task creation failed: [error details]"

### Graceful Degradation

**Continue with reduced functionality**:

1. **Memory server unavailable**
   - Impact: No context for categorization
   - Fallback: Create all tasks with #needs-categorization
   - Continue: Yes, task capture still valuable

2. **Tasks MCP unavailable (Phase 3+)**
   - Impact: Cannot use MCP backend
   - Fallback: Use task_add.py scripts
   - Continue: Yes, transparently

3. **Low confidence categorization**
   - Impact: Manual review needed
   - Fallback: Flag with #needs-categorization
   - Continue: Yes, task captured

4. **Ambiguous priority**
   - Impact: May not be in correct urgency order
   - Fallback: Default to P2 (normal) with note in body
   - Continue: Yes, user can adjust

### Partial Success

**Some tasks created, others failed**:

```
Report clearly:
✅ Created 3 tasks successfully
❌ Failed to create 2 tasks:
   - "Review contract" - validation error (missing required field)
   - "Schedule meeting" - duplicate detected

Action: User can manually create failed tasks
Log: Record failures to data/logs/task-capture-errors.jsonl
```

## Logging

**Log all operations** to `data/logs/task-capture.jsonl`:

```json
{
  "timestamp": "2025-11-10T10:30:00Z",
  "workflow": "email-task-capture",
  "emails_processed": 12,
  "actions_found": 5,
  "tasks_created": 5,
  "tasks_failed": 0,
  "backend_used": "scripts",
  "confidence_distribution": {
    "high": 3,
    "medium": 1,
    "low": 1
  },
  "categorization_summary": {
    "oversight-board": 1,
    "phd-supervision": 1,
    "personal": 1,
    "travel": 1,
    "needs-categorization": 1
  },
  "errors": []
}
```

**Error log format** (`data/logs/task-capture-errors.jsonl`):

```json
{
  "timestamp": "2025-11-10T10:31:15Z",
  "error_type": "task_creation_failed",
  "backend": "scripts",
  "email_subject": "Review contract for XYZ project",
  "error_detail": "task_add.py returned exit code 1: validation error",
  "action_taken": "skipped, user notified"
}
```

## Decision Trees

### When to Invoke This Workflow

**User phrases that trigger workflow**:

- "Check my email for tasks"
- "Process emails"
- "Any new tasks from email?"
- "What's in my inbox that needs action?"
- "Email triage"
- "Review emails for action items"

**Context requirements**:

- User has access to Outlook MCP (email configured)
- Task backend available (scripts or MCP)
- User not in middle of other focused work

**When NOT to invoke**:

- User asks to read specific email (use Outlook MCP directly)
- User asks about calendar/meetings (different workflow)
- User explicitly says "just summarize, don't create tasks"

### Confidence-Based Categorization

```
For each action item:

1. Query memory with subject + sender + keywords
2. Calculate match score:
   - Strong project keyword match: +40 points
   - Sender-project association in memory: +30 points
   - Clear deadline signals priority: +20 points
   - Explicit action verbs: +10 points

3. Apply thresholds:
   Score >= 80: High confidence → Auto-categorize
   Score 50-79: Medium confidence → Suggest, flag for review
   Score < 50: Low confidence → Create with #needs-categorization

4. Document confidence in task body:
   "Categorization confidence: HIGH (95/100) - Auto-applied"
   "Categorization confidence: MEDIUM (65/100) - Please review"
   "Categorization confidence: LOW (30/100) - Needs manual categorization"
```

## Examples

### Example 1: High-Confidence OSB Vote

**Input email**:

```
From: OSB Secretariat <secretariat@oversightboard.com>
Subject: [ACTION REQUIRED] OSB Cycle 38 Vote - Case #2024-123
Received: 2025-11-10T09:23:00Z

Dear Board Member,

Please cast your vote on Case #2024-123 (hate speech appeal).
Case materials: https://osb.link/cases/2024-123
Deadline: Friday, November 15, 2025, 5:00 PM GMT

Thank you,
OSB Secretariat
```

**Memory query result**:

```
Project: oversight-board
Tags: [osb, vote, content-moderation]
Relationship: Known sender (OSB operations)
Pattern: Similar votes typically P0 priority
Confidence: 95/100 (HIGH)
```

**Task created**:

```yaml
---
title: "OSB Vote: Case #2024-123 - Hate speech appeal"
priority: 0
project: oversight-board
classification: Action
due: 2025-11-15T17:00:00Z
tags: [osb, vote, urgent, content-moderation]
source_email: outlook://entry/AAMkADQ3ZmY...
source_subject: "[ACTION REQUIRED] OSB Cycle 38 Vote - Case #2024-123"
source_from: "OSB Secretariat <secretariat@oversightboard.com>"
source_date: 2025-11-10T09:23:00Z
---

# OSB Vote: Case #2024-123 - Hate speech appeal

## Context

OSB Secretariat requesting vote on hate speech content removal appeal.
Deadline: Friday, November 15, 2025, 5:00 PM GMT

## Summary: What You Need to Respond To

### Primary Question
Cast vote on Case #2024-123 (hate speech appeal) - approve or reject content removal.

### Secondary Items
- Review case materials before voting

## Response Needed
- [ ] Review case materials at https://osb.link/cases/2024-123
- [ ] Cast vote before deadline

## Associated Documents
- Case materials: https://osb.link/cases/2024-123

## Original Email

**From:** OSB Secretariat <secretariat@oversightboard.com>
**Subject:** [ACTION REQUIRED] OSB Cycle 38 Vote - Case #2024-123
**Date:** November 10, 2025 at 9:23 AM

---

Dear Board Member,

Please cast your vote on Case #2024-123 (hate speech appeal).
Case materials: https://osb.link/cases/2024-123
Deadline: Friday, November 15, 2025, 5:00 PM GMT

Thank you,
OSB Secretariat
```

### Example 2: Medium-Confidence Review Request

**Input email**:

```
From: Jane Smith <j.smith@university.edu>
Subject: Feedback on draft paper - AI governance
Received: 2025-11-10T14:15:00Z

Hi Nic,

I'm working on a paper about AI governance frameworks and would appreciate
your feedback on the attached draft, particularly the section on platform
accountability. No rush - happy to receive comments by end of month.

Best,
Jane
```

**Memory query result**:

```
Project: Uncertain - could be "ai-governance" or "research-collaboration"
Tags: [review, feedback, ai, governance]
Relationship: Unknown sender, academic context suggests collaboration
Pattern: Review requests typically P2 unless deadline urgent
Confidence: 65/100 (MEDIUM)
```

**Documents downloaded**:
- Email attachment → `$ACA_DATA/reviews/jane-smith/draft-paper.pdf`
- Converted → `$ACA_DATA/reviews/jane-smith/draft-paper.md`

**Task created**:

```yaml
---
title: "Review draft paper - AI governance (Jane Smith)"
priority: 2
project: needs-categorization
classification: Review
due: 2025-11-30T23:59:59Z
tags: [review, feedback, ai, governance, suggested-categorization]
source_email: outlook://entry/AAMkAGF4ZjY...
source_subject: "Feedback on draft paper - AI governance"
source_from: "Jane Smith <j.smith@university.edu>"
source_date: 2025-11-10T14:15:00Z
---

# Review draft paper - AI governance (Jane Smith)

## Context

Review request from Jane Smith (university.edu) for draft paper on AI governance frameworks.
Requested deadline: End of November (flexible)

**Email:** j.smith@university.edu

## Summary: What You Need to Respond To

### Primary Question
Provide feedback on draft paper, particularly the section on platform accountability.

### Secondary Items
- General comments on the paper welcome
- No strict deadline ("no rush")

## Response Needed
- [ ] Read platform accountability section
- [ ] Provide substantive feedback
- [ ] Send comments by end of month

## Associated Documents
- `reviews/jane-smith/draft-paper.md` - Draft paper (converted from PDF)
- `reviews/jane-smith/draft-paper.pdf` - Original attachment

## Original Email

**From:** Jane Smith <j.smith@university.edu>
**Subject:** Feedback on draft paper - AI governance
**Date:** November 10, 2025 at 2:15 PM

---

Hi Nic,

I'm working on a paper about AI governance frameworks and would appreciate
your feedback on the attached draft, particularly the section on platform
accountability. No rush - happy to receive comments by end of month.

Best,
Jane
```

### Example 3: Low-Confidence / Ambiguous

**Input email**:

```
From: Newsletter <noreply@techpolicy.org>
Subject: Tech Policy Weekly - Issue 42
Received: 2025-11-10T08:00:00Z

This week's highlights:
- New AI regulation in EU
- Platform content moderation updates
- Research grant opportunities closing soon

[... newsletter content ...]
```

**Memory query result**:

```
Project: None matched
Tags: Unclear - informational content
Relationship: Automated newsletter
Pattern: Typically not actionable
Confidence: 15/100 (LOW)
```

**Decision**: Do NOT create task (false positive prevention)

```
Skipped: Newsletter content, no clear action items detected
Rationale: Informational content from automated sender
```

## Troubleshooting

### Common Issues

**Issue**: "Task backend not available"

- **Cause**: Neither Tasks MCP nor task scripts working
- **Fix**: Verify task_add.py script exists and is executable
- **Check**: `ls -la bots/skills/tasks/scripts/task_add.py`

**Issue**: "All tasks created with #needs-categorization"

- **Cause**: Memory server not responding or context insufficient
- **Fix**: Verify memory server connection, enrich memory with more project data
- **Check**: Query memory manually to verify it returns project matches

**Issue**: "Duplicate tasks created"

- **Cause**: Duplicate detection not working or same email processed twice
- **Fix**: Check that source_email field is being set correctly
- **Check**: `grep "source_email:" data/tasks/inbox/*.md`

**Issue**: "Wrong project assignments"

- **Cause**: Memory context doesn't match email patterns well
- **Fix**: Review categorization patterns, update memory with better project descriptions
- **Check**: Review data/logs/task-capture.jsonl for categorization accuracy

**Issue**: "Tasks created but workflow slow (>30 seconds)"

- **Cause**: Too many memory queries or email processing
- **Fix**: Batch memory queries, limit email count per check
- **Check**: Monitor timing in logs, optimize sequential vs parallel calls

## Configuration

### Account-Specific Archive Folders

Different email accounts require different tools for archiving:

| Account | Tool | Parameter | Notes |
|---------|------|-----------|-------|
| Gmail (nic@suzor.net) | `messages_archive` | `folder_id="211"` | Gmail requires folder ID (account param doesn't work) |
| QUT (n.suzor@qut.edu.au) | `messages_move` | `folder_path="Archive"` | Standard Exchange folder path |

**Gmail archive** (uses `messages_archive` with folder ID):
```
mcp__outlook__messages_archive(entry_id="...", folder_id="211")
```

**Exchange/Outlook archive** (uses `messages_move` with folder path):
```
mcp__outlook__messages_move(entry_id="...", folder_path="Archive", account="n.suzor@qut.edu.au")
```

**Why different tools?** Gmail accounts on macOS Outlook don't appear in AppleScript account enumeration, so `messages_move` with `account` parameter fails. Use `messages_list_folders` to discover folder IDs.

### Environment variables (optional)

```bash
# Backend preference (if both available)
TASK_BACKEND_PREFERENCE="mcp"  # or "scripts"

# Confidence thresholds (0-100)
TASK_CAPTURE_HIGH_CONFIDENCE=80
TASK_CAPTURE_MEDIUM_CONFIDENCE=50

# Email processing limits
TASK_CAPTURE_EMAIL_LIMIT=20
TASK_CAPTURE_DAYS_BACK=3

# Auto-create without confirmation (Phase 3+)
TASK_CAPTURE_AUTO_CREATE=false
```

## Validation Criteria

**Workflow is working correctly when**:

1. ✅ Agent invokes workflow when user says "check email for tasks"
2. ✅ Tasks created for legitimate action items (not newsletters/FYI emails)
3. ✅ High-confidence tasks have correct project/priority/tags
4. ✅ Medium-confidence tasks flagged for review
5. ✅ Low-confidence tasks not auto-categorized
6. ✅ No duplicate tasks for same email
7. ✅ Email metadata properly linked (source_email, source_subject, etc.)
8. ✅ Backend selection transparent (MCP or scripts, user doesn't need to know)
9. ✅ Graceful fallback if primary backend unavailable
10. ✅ Clear summary presented to user after processing

**Quality metrics** (track in logs):

- False positive rate: <5% (tasks created for non-actionable emails)
- False negative rate: <10% (action emails missed)
- High-confidence categorization rate: >60%
- Manual recategorization rate: <20%

## Future Enhancements

**Phase 3+ improvements**:

- Email archiving after task creation
- Calendar integration for deadline extraction
- Multi-language support
- Attachment content analysis
- Task dependencies from email threads
- Smart sender importance learning
- Batch processing optimization
- Real-time email monitoring (webhook-based)

---

**Version History**:

- 2.0.0 (2025-12-31): "Ready for Action" tasks - summarize email, download attachments, fetch linked docs, convert to markdown, structured task body
- 1.1.2 (2025-12-23): Fixed Gmail archive to use `messages_archive` tool (not `messages_move`)
- 1.1.1 (2025-12-23): Added account-specific archive folder configuration (Gmail uses folder ID `211`)
- 1.1.0 (2025-12-23): Added sent folder check, FYI classification, present-before-archive requirement
- 1.0.0 (2025-11-10): Initial implementation with scripts backend, pluggable design
