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
7. **Verify** all committed, pushed, PR filed
8. **Output Framework Reflection**

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
- **Step 3: Follow-up Tasks** - Procedure for task decomposition
- **Step 4: Memory Persistence** - Capture learnings in PKB
- **Edge Cases** - Historical tasks and infrastructure blocks

---

## Step 5: Output Framework Reflection

Output the reflection in exact AGENTS.md format (see **[[references/handover-details]]** for template):

```markdown
## Framework Reflection

**Prompts**: [Brief] | **Outcome**: [success/partial]
**Accomplishments**: [Summary]
**Next step**: [Context for next session, including Task ID]
```

## Step 6: Halt

After reflection, **stop working**. Output:

```
---
Work COMPLETE: [Summary]. Next: `/pull <task-id>` to resume.
---
```
