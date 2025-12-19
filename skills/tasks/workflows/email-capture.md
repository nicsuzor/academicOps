---
name: email-task-capture
description: Extract action items from emails and create tasks automatically with context-aware categorization
permalink: skills/tasks/workflows/email-capture
tags: [workflow, email, task-capture, automation, bmem]
version: 1.0.0
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

**Use bmem semantic search** (preferred over grep):
```
mcp__bmem__search_notes(query="email subject keywords", types=["task"])
```

**Fallback to file search if bmem unavailable**:
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

Use **Outlook MCP** to retrieve recent emails.

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

### Step 2: Analyze Each Email for Actions

For each email, extract potential action items by identifying:

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

**Extract for each action**:

```
{
  "title": "Concise action description (50 chars max)",
  "body": "Full context from email body (relevant paragraphs)",
  "deadline": "Extracted deadline (ISO format) or null",
  "raw_text": "Original email excerpt containing this action"
}
```

### Step 3: Gather Context from bmem

For each extracted action, query **bmem MCP** for relevant context.

**Tool**: `mcp__bmem__search_notes`

**Parameters**:

```json
{
  "query": "search terms from email" // Required: search query string only
}
```

**Example invocation**:

```json
{
  "tool": "mcp__bmem__search_notes",
  "parameters": {
    "query": "OSB vote content removal oversight board"
  }
}
```

**Query construction**:

- Email subject line
- Sender name/email
- Key terms from action description

**Extract from bmem**:

- **Projects**: Active projects matching email content
- **Goals**: Related strategic goals
- **Relationships**: Sender importance/collaboration history
- **Patterns**: Similar past tasks, typical categorizations

**Example**:

```
Email subject: "OSB Cycle 38 Vote - Content removal case #2024-123"
bmem query: "OSB vote content removal oversight board"
Returns: project: oversight-board, tags: [osb, vote, content-moderation]
```

### Step 4: Categorize with Confidence Scoring

Match actions to projects/tags with confidence scores:

**High confidence (>80%)**: Auto-apply categorization

- Strong project keyword match in bmem
- Known sender-project association
- Clear deadline signals priority

**Medium confidence (50-80%)**: Suggest but flag for review

- Partial keyword match
- Unknown sender but clear topic
- Add tag: `#suggested-categorization`

**Low confidence (<50%)**: Create in inbox, needs manual categorization

- Ambiguous content
- No bmem matches
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

### Step 6: Create Tasks via Backend

**Backend selection logic**:

```
1. Check if Tasks MCP is available:
   - Try: Call view_tasks() tool
   - If successful: Use Tasks MCP backend
   - If fails: Fall back to scripts backend

2. Scripts backend (Phase 1-2, always available):
   - Use: task_add.py script via Bash tool
   - Format: Same bmem-compliant markdown as MCP

3. Format is backend-agnostic - both create identical task files
```

**Task creation parameters**:

Scripts backend (`task_add.py`):

```
Required:
- --title: Action description (concise, actionable)

Optional:
- --priority: P0, P1, P2, or P3 (inferred from signals)
- --project: Project slug (from bmem match)
- --classification: "Action", "Review", "Admin", etc.
- --due: Deadline in ISO8601 format (e.g., 2025-11-15T17:00:00Z)
- --tags: Comma-separated tags (no spaces)
- --body: Full task description including email metadata

Email metadata (embed in --body text):
- Entry ID from Outlook MCP
- Email subject
- Sender name/email
- Received timestamp
```

**Scripts backend example**:

```bash
# Run from repo root with uv run
uv run python bots/skills/tasks/scripts/task_add.py \
  --title "OSB Vote: Content removal case #2024-123" \
  --priority P0 \
  --project "oversight-board" \
  --classification "Action" \
  --due "2025-11-15T17:00:00Z" \
  --tags "osb,vote,urgent" \
  --body "Email from: OSB Secretariat <secretariat@oversightboard.com>
Received: 2025-11-10T09:23:00Z
Entry ID: AAMkADQ3...
Subject: [ACTION REQUIRED] OSB Cycle 38 Vote

Vote required on content removal case #2024-123 (hate speech appeal).
Review case materials: https://osb.link/cases/2024-123
Deadline: Friday Nov 15, 5pm GMT"
```

**Important syntax notes**:

- Priority: Use `P0`, `P1`, `P2`, `P3` format (not `0`, `1`, `2`, `3`)
- Body: Single string argument (no heredoc needed for simple content)
- Tags: Comma-separated without spaces
- Email metadata: Include in body text (entry_id, subject, from, received)

**Tasks MCP backend example**:

```
Tool: create_task
Parameters:
{
  "title": "OSB Vote: Content removal case #2024-123",
  "priority": 0,
  "project": "oversight-board",
  "classification": "Action",
  "due": "2025-11-15T17:00:00Z",
  "tags": ["osb", "vote", "urgent"],
  "body": "Email from: OSB Secretariat...\n[same body as above]"
}
```

### Step 7: Final Duplicate Check (Per-Task)

**This is a secondary check** - Step 0 should have caught most duplicates. This step catches edge cases during task creation.

**For each task about to be created**:

1. Search by email subject: `grep -li "SUBJECT_KEYWORDS" $ACA_DATA/tasks/inbox/*.md $ACA_DATA/tasks/archived/*.md`
2. Search by entry_id if available: `grep -l "source_email.*ENTRY_ID" $ACA_DATA/tasks/inbox/*.md`

**If match found**:
- Skip creation
- Add to "Skipped (duplicate)" section in summary
- Log: which existing task matched, why

**Common duplicate scenarios**:
- Same email processed multiple times (entry_id match)
- Similar email from same sender about same topic (subject/sender match)
- Task was created manually before workflow ran (title match)

### Step 8: Present Summary

After processing all emails, show user:

```
📧 Email Task Capture Summary

Processed 12 emails, found 5 action items:

✅ Created 5 tasks:

1. [P0] OSB Vote: Content removal case #2024-123
   Project: oversight-board | Due: Nov 15
   Source: OSB Secretariat | High confidence

2. [P1] Review PhD thesis - Sasha Ness final submission
   Project: phd-supervision | Due: Nov 20
   Source: Sasha Ness | High confidence

3. [P2] Provide feedback on DIGI misinformation event draft
   Project: needs-categorization | No deadline
   Source: Unknown sender | Low confidence ⚠️

4. [P1] Confirm attendance: ARC panel meeting Dec 5
   Project: personal | Due: Nov 30
   Source: ARC Office | Medium confidence

5. [P3] Book accommodation for Sydney trip
   Project: travel | Due: Dec 1
   Source: Booking confirmation | High confidence

⚠️ 1 task needs manual categorization (low confidence)
📝 Backend used: task_add.py script
✨ All tasks available in inbox

What would you like to do?
- Archive processed emails (not implemented yet)
- Review low-confidence tasks
- Continue working
```

## Error Handling

### Fail-Fast Scenarios

**Halt immediately and report**:

1. **Outlook MCP unavailable**
   - Error: Cannot access email
   - Action: Halt workflow, report to user
   - Message: "Cannot check email - Outlook MCP not responding"

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

1. **bmem MCP unavailable**
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

1. Query bmem with subject + sender + keywords
2. Calculate match score:
   - Strong project keyword match: +40 points
   - Sender-project association in bmem: +30 points
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

**bmem query result**:

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

Email from OSB Secretariat requesting vote on hate speech content removal appeal.

Case materials available: https://osb.link/cases/2024-123
Deadline: Friday, November 15, 2025, 5:00 PM GMT

Categorization confidence: HIGH (95/100) - Auto-applied based on:
- Project keyword match (oversight-board)
- Known sender relationship (OSB operations)
- Explicit deadline and urgency markers

## Source Email

From: OSB Secretariat <secretariat@oversightboard.com>
Received: November 10, 2025 at 9:23 AM
Entry ID: outlook://entry/AAMkADQ3ZmY...

[Full email body preserved for reference]
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

**bmem query result**:

```
Project: Uncertain - could be "ai-governance" or "research-collaboration"
Tags: [review, feedback, ai, governance]
Relationship: Unknown sender, academic context suggests collaboration
Pattern: Review requests typically P2 unless deadline urgent
Confidence: 65/100 (MEDIUM)
```

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

Review request for draft paper on AI governance frameworks, focusing on
platform accountability section.

Requested deadline: End of November (flexible)

⚠️ Categorization confidence: MEDIUM (65/100) - Please review and adjust:
- Uncertain project match (could be ai-governance or research-collaboration)
- Unknown sender but academic context
- Suggested deadline inferred from "end of month"

**Action needed**: Verify project categorization and priority

## Source Email

From: Jane Smith <j.smith@university.edu>
Received: November 10, 2025 at 2:15 PM
Entry ID: outlook://entry/AAMkAGF4ZjY...
Attachment: draft-paper.pdf

[Full email body preserved for reference]
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

**bmem query result**:

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

- **Cause**: bmem MCP not responding or context insufficient
- **Fix**: Verify bmem MCP connection, enrich bmem context with more project data
- **Check**: Query bmem manually to verify it returns project matches

**Issue**: "Duplicate tasks created"

- **Cause**: Duplicate detection not working or same email processed twice
- **Fix**: Check that source_email field is being set correctly
- **Check**: `grep "source_email:" data/tasks/inbox/*.md`

**Issue**: "Wrong project assignments"

- **Cause**: bmem context doesn't match email patterns well
- **Fix**: Review categorization patterns, update bmem project descriptions
- **Check**: Review data/logs/task-capture.jsonl for categorization accuracy

**Issue**: "Tasks created but workflow slow (>30 seconds)"

- **Cause**: Too many bmem queries or email processing
- **Fix**: Batch bmem queries, limit email count per check
- **Check**: Monitor timing in logs, optimize sequential vs parallel calls

## Configuration

**Environment variables** (optional):

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

## Related Documentation

- **Task Backend**: [[../README.md]]
- **Task Scripts**: [[../scripts/]]
- **Tasks MCP**: `.mcp.json` configuration
- **bmem Integration**: [[bmem search|#step-3-gather-context-from-bmem]]
- **Outlook MCP**: User email access configuration
- **Framework**: `Skill(skill="framework")` for experiment tracking

---

**Version History**:

- 1.0.0 (2025-11-10): Initial implementation with scripts backend, pluggable design
