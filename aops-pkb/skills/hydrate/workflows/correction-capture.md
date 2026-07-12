---
id: correction-capture
category: meta
bases: [base-memory-capture]
description: Capture in-session human corrections as hydrator quality improvement tasks
triggers:
  - human corrects agent assumption
  - user says "that's not how it works"
  - agent receives architectural correction
permalink: workflows/correction-capture
tags: [workflow, quality, hydrator, feedback-loop]
---

# Correction Capture Workflow

**Purpose**: When a human corrects an agent's understanding during a session, capture that correction as a durable improvement to the hydration system -- not just a one-time fix for the current session.

**When to invoke**: Any time the user corrects a factual assumption, points out existing work the agent missed, or explains how something actually works differently from what the agent assumed.

## Process

### 1. Acknowledge and Record

Immediately acknowledge the correction. Do not defend the wrong assumption.

Record the correction as a PKB memory:

```
mcp__pkb__create_memory(
  title="Correction: [what was wrong] -> [what is correct]",
  body="[Full correction details with source]",
  tags=["hydrator-quality", "in-session-correction", "[domain-tag]"]
)
```

### 2. Classify the Gap

Determine which gap type this correction represents:

| Gap Type                   | Signal                                                        |
| -------------------------- | ------------------------------------------------------------- |
| **Missing fact**           | Agent did not know a specific fact about the system           |
| **Missing file reference** | Agent did not know a relevant file exists                     |
| **Wrong assumption**       | Agent assumed something contradicting reality                 |
| **Stale context**          | Agent had outdated information                                |
| **Missing workflow step**  | A workflow omitted a step that would have prevented the error |

### 3. Create Improvement Task

Create a task under the hydration gate reliability epic:

```
mcp__pkb__create_task(
  title="Hydrator gap: [concise description of what was missing]",
  parent="aops-fa32b8ad",
  type="bug",
  priority=1,
  tags=["hydrator-quality", "[gap-type]"],
  body="## Correction\n\n[What the user said]\n\n## What Was Wrong\n\n[What the agent assumed]\n\n## What Is Correct\n\n[The actual fact/behavior]\n\n## Gap Type\n\n[gap-type from classification]\n\n## Proposed Fix\n\n[Which file/doc/config needs updating to prevent recurrence]"
)
```

### 4. Fix Inline If Obvious

If the fix is localized and obvious (e.g., adding a line to a reference doc, adding a detection pattern to SKILL.md, adding a file to context-map.json):

- Make the fix in the current session
- Note in the task body: "Fixed inline in session [date]"
- Close the task with verification evidence

If the fix requires investigation or structural changes, leave the task open for a future session.

### 5. Continue Working

Resume the original task with the corrected understanding. The correction capture should take less than 2 minutes.

## Key Rules

1. **The corrected agent does the filing, not the human.** The human's correction is the signal; task creation is the agent's responsibility.
2. **Speed matters.** This is a 2-minute interrupt, not a research project. Record, classify, file, continue.
3. **Always create the task.** Even if you fix the issue inline, the task provides an audit trail of what gaps existed.
4. **Tag consistently.** Always use `hydrator-quality` tag. Always parent to `aops-fa32b8ad`.
5. **Link to the spec.** Reference `specs/hydrator-quality-escalation.md` in the task body for process context.
