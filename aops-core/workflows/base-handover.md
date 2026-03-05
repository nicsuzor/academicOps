---
id: base-handover
title: "Base: Handover"
category: base
bases: [base-commit]
---

# Landing the Plane (Session Completion)

Work is NOT complete until `git push` succeeds, a PR is filed, and reflection is provided.

## MANDATORY WORKFLOW

1. **Complete all file changes**
2. **Run quality gates** (tests, verify)
3. **Update task status** (mark done/progress)
4. **Invoke `/dump`** (`aops-core:dump`)
5. **Commit and PUSH**
6. **File a PR**
7. **Output Framework Reflection**
8. **Summary to user** (Step 6 below — LAST output)

## CRITICAL RULES

- Work is **NOT complete** until `git push` succeeds AND a PR is filed
- **NEVER stop** before pushing to remote and filing a PR
- Using mutating tools after handover will reset the gate

---

## Step 1: Update Task

Update your claimed task with progress and release it. If no task was claimed, create a historical one.

```python
mcp__pkb__update_task(id="<id>", status="done", body="## Session Progress\n- [Accomplished]")
```

## Step 2: Commit & File PR

**Per P#24**: Commit AND push after completing work. File a PR (MANDATORY). For **polecat worktrees**, set status to `merge_ready`.

```bash
git add <files> && git commit -m "<type>: <desc>

Task: <task-id>
Epic: <epic-id>" && git push
```

---

## Detailed Procedures

For procedures on following steps, see **[[references/handover-details]]**:

- **Quick Exit** - Protocol for sessions with no work done
- **Step 3: Follow-up Tasks** - Procedure for task decomposition (MANDATORY: set `parent` for all new tasks)
- **Step 4: Memory Persistence** - Capture learnings in PKB
- **Edge Cases** - Historical tasks and infrastructure blocks

---

## Step 5: Output Framework Reflection

Output the reflection using `## Framework Reflection` as an **H2 heading** (not bold text). Use `**Field**: value` for each field. Minimum 3 fields: Outcome, Accomplishments, Next step.

### DO (correct — parseable by session-insights)

```markdown
## Framework Reflection

**Outcome**: success
**Accomplishments**: Fixed the repo-sync cron script
**Next step**: None — PR merged, task complete
```

### DON'T (broken — parser cannot extract fields)

```markdown
**Framework Reflection:**

- Fixed the repo-sync cron script
- Everything looks good now
```

## Step 6: Summary to User — LAST OUTPUT

After the Framework Reflection, output this. **Nothing follows.** It must stay visible in the terminal.

```
---
## Session Complete

**What was done**: [1–3 sentences]
**Task(s) worked**: [task-id-1], [task-id-2]
**Follow-up items**: [description → task-id] or "None"

Next: `/pull <task-id>` to resume, or `/pull` to pick from queue.
---
```
