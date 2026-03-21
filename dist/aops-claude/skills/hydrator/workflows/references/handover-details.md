# Handover Details and Edge Cases

Detailed procedures for specific handover activities and handling unusual situations.

## Quick Exit: No Work Done

If the session only involved answering user questions with no code changes, task work, or meaningful framework work:

```markdown
## Framework Reflection

User asked: "<brief summary of question/topic>"
Answer: "<summary of answer>"
Next steps: "<what the user or agent should do next, including task ID if applicable>"
```

Then **stop** - skip all other steps.

## Step 3: File Follow-up Tasks

If outstanding work remains, file follow-up tasks using [[decompose]] principles:

- **Group related items** into a single task with bullet points; don't create one task per TODO.
- **Granularity**: each task should be a coherent work unit (≤4h, single "why").
- **No reflexive tasks**: only create tasks where the action path is clear.
- **Include context**: body should contain enough for the next agent to resume.
- **Completion loop (P#109)**: If creating multiple follow-up subtasks, also create a verify-parent task.

```python
mcp__pkb__create_task(
  title="<coherent work unit>",
  type="task",
  project="<project>",
  priority=2,
  body="Follow-up from <session>. Context: <what needs doing and why>",
  parent="<parent-task-id>"
)
```

## Step 4: Persist to Memory

For each task complete and learning to persist:

```python
mcp__pkb__create_memory(
  title="Session handover: <brief summary>",
  body="<work done and key learnings>",
  tags=["dump", "handover"]
)
```

## Step 4.5: Codify Learnings

Before committing, ask: **"What did this session reveal that should improve future sessions?"**

| Scope                                      | Action                                             |
| ------------------------------------------ | -------------------------------------------------- |
| Framework improvement (affects all agents) | File a GitHub issue in the aops repo               |
| Project-specific pattern                   | Edit or create `./.agent/workflows/<name>.md`      |
| One-off / not actionable                   | Note in `**Proposed changes**` field of Reflection |

**For framework issues** (use `gh` CLI):

```bash
gh issue create --repo nicsuzor/academicOps \
  --title "[Improvement] <what and why>" \
  --label "framework" \
  --body "<what you observed, what should change, expected impact>"
```

**For project workflow updates**: edit `./.agent/workflows/<relevant>.md` directly — this will be included in your commit.

> **Connection to Reflection**: The `**Proposed changes**` field in the Framework Reflection should describe what was filed or updated here, or "None". Do this step _before_ writing the reflection so you can reference the issue number.

---

## Step 5: Reflection Template (AGENTS.md Format)

Output the reflection using `## Framework Reflection` as an **H2 heading** — this is critical for the session-insights parser to extract fields. Use `**Field**: value` on each line.

**Minimum** (3 fields — for simple sessions):

```markdown
## Framework Reflection

**Outcome**: success
**Accomplishments**: Fixed the repo-sync cron script
**Next step**: None — PR merged, task complete
```

**Full** (9 fields — for complex or partial sessions):

```markdown
## Framework Reflection

**Prompts**: [Original request in brief]
**Guidance received**: [Hydrator/custodiet advice, or "N/A"]
**Followed**: [Yes/No/Partial - explain]
**Outcome**: [success/partial]
**Accomplishments**: [What was accomplished]
**Friction points**: [What caused hurdles or dump]
**Root cause**: [Why work couldn't complete]
**Proposed changes**: [Framework improvements identified]
**Next step**: [Exact context for next session to resume, including Task ID]
```

> **WARNING**: Do NOT use `**Framework Reflection:**` (bold text) — use `## Framework Reflection` (heading). The bold-text variant is not reliably parsed and results in empty session summaries on the dashboard.

## Edge Cases

### No task currently claimed BUT work was completed

CREATE a historical task to capture the session's work (MANDATORY: set `parent` to project task):

```python
mcp__pkb__create_task(
  title="[Session] <brief description of work done>",
  type="task",
  project="<relevant project or 'aops'>",
  parent="<project-id>", # MANDATORY: Link to hierarchy
  status="done",
  priority=3,
  body="Historical task created at /dump.\n\n## Work Completed\n<what was accomplished>\n\n## Outcome\n<success/partial/failed>\n\n## Context\n<any follow-up notes>"
)
```

### Blocked by infrastructure bug (P#9/P#25)

When session ends because tooling failed and a bug was filed:

1. **Mark original task as blocked** via `mcp__pkb__update_task` with `status="blocked"` and `depends_on=["<bug-task-id>"]`.
2. **Reflection outcome**: `partial` with friction point explaining the failure.
3. **Do NOT leave task as "active"** - blocked tasks should be visible as blocked.
