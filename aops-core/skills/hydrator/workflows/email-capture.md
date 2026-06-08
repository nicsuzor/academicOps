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

Automatically extract action items from emails and create properly categorized tasks with full context linking.

## Operational Directives

- **Conciseness**: Keep all outputs, task descriptions, and summaries extremely concise.
- **No Micromanagement**: Let the agent query tools and search files naturally to resolve details.
- **Duplicate Prevention**: Always run `task_search(query="...")` for the email subject/key action phrase before creating a task. If a match exists, skip creation and link to it. If ambiguous, consult the user.

## Checklist & Procedure

1. **Fetch & Check**: Retrieve recent emails. Check if already responded to.
2. **Classify**: Categorize emails into _Actionable_, _Important FYI_, or _Safe to Ignore_.
3. **Context & Categorize**: Query the PKB to match tasks to active projects/epics.
4. **Metadata (not priority/severity)**: Leave `priority` at the uncurated default band — never infer a band from the email's urgency or deadline. Setting `priority=0` (P0) requires deliberate calibration and justification (see [[../../remember/references/TAXONOMY.md#p0-calibration-bar]]). Omit `severity` (or set `severity=0`) as severity belongs only on target milestones (see [[../../remember/references/TAXONOMY.md#severity-target-boundary]]). Route the deadline to `due` (deadline-aware ranking happens via `focus_score`, not the band) and extract `effort`, `consequence`. Intent/priority authority: [[framework-conventions-summary#intent-authority]].
5. **Create Tasks**: Create a task with a clear title, body (including quoted email text, entry_id, and metadata), and parent linkage.
6. **Present Summary**: Present created tasks and Important FYI items.

## Critical Guardrails

- **Mandatory Parent Linkage**: Every created task must link to a `parent` epic or project task.
- **Link Preservation**: Include all URLs and attachment filenames from the email in the task body (do not download attachments).
- **Email MCP Verification**: Call Outlook/email MCP tools to verify availability. Retry fully-qualified names if first call fails. Halt only if a real call fails with a named error.
- **Verification of Task Quality**: Task bodies must contain the original email quotes, entry_id, and sender/date.

For step-by-step configurations and heuristics, refer to **[[email-capture-details]]**.
