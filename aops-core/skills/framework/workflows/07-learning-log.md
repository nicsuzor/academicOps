---
title: Learning Log Workflow
type: instruction
category: instruction
permalink: workflow-learning-log
description: Document agent behavior patterns as learn-type tasks for later synthesis
---

# Workflow 7: Learning Log

**When**: After observing agent behavior patterns, errors, or framework gaps that should be tracked.

**Key principle**: Per AXIOMS #28 (Current State Machine) - episodic observations go to tasks, not direct file edits. Analysis happens later via workflow 05 (QA Verification).

**IMPORTANT**: This workflow creates `type="learn"` tasks for **observational tracking only**. To make actual framework changes, use `/learn` instead - it combines logging with graduated fixes.

**CRITICAL**: If you need to read session JSONL files, invoke `Skill(skill='transcript')` FIRST to convert to markdown. Raw JSONL wastes 10-70K tokens; transcripts are 90% smaller.

## Workflow

### Phase 1: Search for Existing Task

**First**: Search for existing task that matches this observation:

```python
mcp__pkb__list_tasks(status="active")
mcp__pkb__task_search(query="[keywords]")
```

Categories/labels:

- `bug` - Component-level bugs (script errors, hook crashes)
- `learning` - Pattern-level observations (agent behavior patterns)
- `experiment` - Systemic investigations (infrastructure issues)
- `devlog` - Development observations

### Phase 2: Create or Update Task

**If matching task exists**: Update with new observation (append to body)

```python
task = mcp__pkb__get_task(id="[TASK_ID]")
# Append new observation to existing body
mcp__pkb__update_task(
    id="[TASK_ID]",
    body=task["body"] + """

## Observation [DATE]

**What**: [description]
**Context**: [when/where]
**Evidence**: [specifics]
"""
)
```

**If no matching task**: Create new learn task

```python
mcp__pkb__create_task(
    title="[category]: [descriptive-title]",
    type="learn",  # Learn tasks are for observation/tracking, NOT execution
    tags=["[category]"],
    body="""## Initial Observation

**Date**: YYYY-MM-DD
**Session ID**: [session-id if available]
**Category**: bug | learning | experiment
**Proximate Cause**: [what agent did wrong]
**Root Cause**: [deferred - will be analyzed via qa workflow]
**Root Cause Category**: Clarity | Context | Blocking | Detection | Gap

## Evidence

[details]

## Queued Analysis

- [ ] Generate transcript (session_id above)
- [ ] Root cause analysis
- [ ] Reflection on framework component failure
- [ ] Create proposal tasks for changes
"""
)
```

### Phase 3: Link to Related Tasks (if applicable)

If observation relates to an existing task, use `depends_on` to link it.

### Phase 4: Report and Exit

Report to user:

1. Task ID created/updated
2. Category assigned
3. Next step: "Run `/qa [task-id]` to perform full analysis"

**DO NOT perform root cause analysis immediately.** The `/qa` command (workflow 05) handles transcript generation, analysis, and proposal creation.

## Task Tags (Categories)

| Tag          | Use For                  | Example Title                                 |
| ------------ | ------------------------ | --------------------------------------------- |
| `bug`        | Component-level bugs     | `bug: task_view.py KeyError on missing field` |
| `learning`   | Agent behavior patterns  | `learning: agents ignoring explicit scope`    |
| `experiment` | Systemic investigations  | `experiment: hook context injection timing`   |
| `devlog`     | Development observations | `devlog: session-insights workflow`           |
| `decision`   | Architectural choices    | `decision: tasks for episodic storage`        |

**Default**: `learning` if unclear.

## Root Cause Categories (for reference)

We don't control agents - they're probabilistic. Root causes must be framework component failures:

| Category          | Definition                                         | Fix Location                              |
| ----------------- | -------------------------------------------------- | ----------------------------------------- |
| Clarity Failure   | Instruction ambiguous or insufficiently emphasized | AXIOMS, skill text, guardrail instruction |
| Context Failure   | Component didn't provide relevant information      | Intent router, hydration                  |
| Blocking Failure  | Should have blocked but didn't                     | PreToolUse hook, deny rule                |
| Detection Failure | Should have caught but didn't                      | PostToolUse hook                          |
| Gap               | No component exists for this case                  | Create new enforcement                    |

## Constraints

**DO ONE THING**: Document observations only. Do NOT:

- Fix reported issues
- Perform root cause analysis (deferred to /qa)
- Implement solutions
- Debug problems

**VERIFY-FIRST**: Review observation carefully before categorizing.

## Example

```
User: /log agent ignored my explicit request to run ALL tests, only ran 3

Phase 1 - Search:
mcp__pkb__task_search(query="instruction scope learning")
→ Found: aops-42 "learning: agents ignoring explicit scope instructions"

Phase 2 - Update existing task:
task = mcp__pkb__get_task(id="aops-42")
mcp__pkb__update_task(id="aops-42", body="[existing + new observation]")

Report: "Added observation to aops-42 - recurring pattern. Run `/qa aops-42` to perform full analysis."
```

### Example: New Task

```
User: /log hook crashed with TypeError in prompt_router.py

Phase 1 - Search:
mcp__pkb__task_search(query="prompt_router TypeError bug")
→ No matching tasks

Phase 2 - Create new learn task:
mcp__pkb__create_task(
    title="bug: prompt_router.py TypeError on None response",
    type="learn",  # Observational - NOT for direct execution
    tags=["bug"],
    body="""## Initial Observation

**Date**: 2025-12-26
**Session ID**: abc123
**Category**: bug
**Proximate Cause**: Hook returned None, code expected dict
**Root Cause**: [deferred to qa workflow]

## Evidence

Stack trace:
[error details]

## Queued Analysis

- [ ] Generate transcript
- [ ] Root cause analysis
- [ ] Create fix proposal"""
)

Report: "Created aops-47 for prompt_router bug. Run `/qa aops-47` to analyze."
```
