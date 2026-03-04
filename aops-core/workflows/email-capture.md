---
id: email-capture
name: email-task-capture
category: instruction
bases: [base-task-tracking, base-handover]
description: Extract action items from emails and create "ready for action" tasks with summaries, downloaded documents, and clear response requirements
permalink: skills/tasks/workflows/email-capture
tags: [workflow, email, task-capture, automation, memory, documents]
version: 2.1.0
phase: 2
backend: scripts
---

# Email → Task Capture Workflow

**Purpose**: Automatically extract action items from emails and create properly categorized tasks with full context linking.

**When to invoke**: User says "check my email for tasks", "process emails", "any new tasks from email?", or similar phrases indicating email-to-task workflow.

## Summary Checklist

1. **Step 0: Check Existing Tasks** - Prevent duplicates for emails already processed.
2. **Step 1: Fetch and Check Responses** - Get recent emails and check if already responded to.
3. **Step 2: Analyze and Classify** - Categorize into Actionable, Important FYI, or Safe to ignore.
4. **Step 3 & 4: Context and Categorization** - Query PKB for project matching and confidence scoring.
5. **Step 5: Infer Priority** - Assign P0-P3 based on deadlines and signals.
6. **Step 6: Create "Ready for Action" Tasks** - Generate summaries, download resources, and create tasks.
7. **Step 7: Duplicate Prevention** - Handled automatically by `task_add.py`.
8. **Step 8: Present Information and Summary** - Show Important FYI content and created tasks.

## Critical Guardrails

- **Mandatory First Step**: Always check for existing tasks before creation.
- **Mandatory Parent Linkage**: Every created task MUST have a `parent` (epic or project task).
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
2. **Duplication**: Ensure no duplicate tasks are created for the same email.
3. **Categorization**: Verify high-confidence tasks have correct projects and priority.
4. **Resources**: Check that attachments and linked docs are downloaded and converted correctly.
