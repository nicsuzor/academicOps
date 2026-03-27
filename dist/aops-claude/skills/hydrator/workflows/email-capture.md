---
id: email-capture
name: email-task-capture
category: instruction
bases: [base-task-tracking, base-handover]
description: Extract action items from emails and create "ready for action" tasks with summaries, linked resources, and clear response requirements
permalink: workflows/email-capture
tags: [workflow, email, task-capture, automation, memory, documents]
version: 2.1.0
phase: 2
backend: scripts
---

# Email → Task Capture Workflow

**Purpose**: Automatically extract action items from emails and create properly categorized tasks with full context linking.

**When to invoke**: User says "check my email for tasks", "process emails", "any new tasks from email?", or similar phrases indicating email-to-task workflow.

## Summary Checklist

1. **Step 0: Check Existing Tasks** - Search PKB before creating to prevent duplicates (see procedure below).
2. **Step 1: Fetch and Check Responses** - Get recent emails and check if already responded to.
3. **Step 2: Analyze and Classify** - Categorize into Actionable, Important FYI, or Safe to ignore.
4. **Step 3 & 4: Context and Categorization** - Query PKB for project matching and confidence scoring.
5. **Step 5: Infer Priority** - Assign P0-P3 based on deadlines and signals.
6. **Step 6: Create "Ready for Action" Tasks** - Generate summaries, note attachment filenames, preserve links, and create tasks.
7. **Step 7: Duplicate Prevention** - Handled by Step 0 above. There is no server-side dedup on creation.
8. **Step 8: Present Information and Summary** - Show Important FYI content and created tasks.

### Step 0 Procedure (MANDATORY before any task creation)

For EACH email that would generate a task:

1. `task_search(query="<email subject or key action phrase>")` — check for existing task
2. If match found: compare titles and content. If clearly the same action → **SKIP creation**, note "already tracked as `<matched_id>`"
3. If ambiguous match (similar but not identical): present both to user before creating
4. If no match: proceed with creation

## Critical Guardrails

- **Mandatory First Step**: Always check for existing tasks before creation.
- **Mandatory Parent Linkage**: Every created task MUST have a `parent` (epic or project task).
- **Mandatory Task Body Quality**: Every task MUST contain quoted email text, all links, and entry_id. See [[email-capture-details]] § "Task Body Quality Requirements". A task without the actual email content is non-compliant.
- **Mandatory Link Preservation**: All URLs from the email body MUST appear in the task. Attachment filenames noted but NOT downloaded during triage — retrieval happens when the task is actioned.
- **Verification of Tool**: To check if `~~email` is available, CALL THE TOOL. Don't check configs.
- **Confidence Scoring**: High confidence auto-categorizes; low confidence flags for review.
- **Fail-Fast**: Halt immediately if the email connector is unavailable.

## Detailed Procedures

For step-by-step instructions and technical configurations, see **[[email-capture-details]]**:

- Detailed duplication check and response detection logic
- Classification matrix and signal indicators
- PKB context mapping and confidence scoring thresholds
- Priority inference rules (P0-P3)
- Task body templates and resource download/conversion procedures
- Presentation formatting and archive candidate selection
- Error handling and logging requirements
- Account-specific archive configurations (Gmail vs Exchange)

## How to Verify

1. **Task Creation**: Check that tasks for legitimate action items are created.
2. **Task Body Quality**: Every task body contains quoted email text, all links, entry_id, and sender/date metadata. A task that paraphrases without quoting is non-compliant.
3. **Link Preservation**: All URLs from the email appear in the task. Attachment filenames noted. No silently dropped links.
4. **Duplication**: Ensure no duplicate tasks are created for the same email.
5. **Categorization**: Verify high-confidence tasks have correct projects and priority.
6. **Daily Note Integration**: When invoked with `--daily`, FYI items contain actual email content (not just subject lines) for inclusion in the daily note.
