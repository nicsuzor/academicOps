---
name: pull
category: instruction
description: Pull a task from the queue, execute it with hydrator guidance, and complete with session reflection
allowed-tools: Task, Bash, Read, Grep, Skill, AskUserQuestion
permalink: commands/pull
---

# /pull - Pull and Execute a Task

**Purpose**: Pull a ready task from the bd queue, claim it, execute it with hydrator guidance, and complete with proper session reflection. The counterpart to `/q` (queue).

## Workflow

### Step 1: Find Ready Work

Run `bd ready --assignee=bot` to see bot-assigned tasks available for work:

```bash
bd ready --assignee=bot
```

This shows issues that are:
- Assigned to `bot` (agent-executable tasks)
- Status: open (not in_progress, blocked, or closed)
- No unresolved blockers
- Sorted by priority (P0 first)

**Note**: Tasks assigned to `nic` require human action and are not pulled by agents.

### Step 2: Claim the Top Issue (or Halt if None)

**If no ready issues**: Report "No ready issues for bot" and HALT. Do not proceed.

**If issues exist**: Auto-claim the first (highest priority) issue from `bd ready` output:

```bash
bd update <first-issue-id> --status=in_progress
```

If user provides an issue ID directly via `/pull <issue-id>`, claim that specific issue instead.

### Step 3: Show Claimed Issue

Display the issue details with `bd show <issue-id>` to understand the full context before proceeding.

### Step 4: Assess Task Path

After reviewing the issue, determine which execution path applies:

#### Path 1: EXECUTE
**All criteria must be true:**
- **What**: Task describes specific deliverable(s)
- **Where**: Target files/systems are known or locatable within 5 minutes of search
- **Why**: Context is sufficient to make implementation decisions
- **How**: Steps are known or determinable from codebase/docs
- **Scope**: Estimated completion within current session
- **Blockers**: No external dependencies (human approval, external input, waiting)

**Action**: Proceed to Step 5 (Hydrator) → Execute → Close.

#### Path 2: TRIAGE
**Any criterion is true:**
- Task requires human judgment/approval
- Task has unknowns requiring exploration beyond this session
- Task is too vague to determine deliverables
- Task depends on external input not yet available
- Task exceeds session scope

**Actions (in order):**
1. **Assign to role**: `bd update <id> --assignee=nic` for human work
2. **Subtask explosion** (if appropriate): Break into child issues when:
   - You can identify discrete, actionable steps
   - Each subtask passes EXECUTE criteria independently
   - Each subtask is 15-60 minutes of work
   - The breakdown covers the parent task's scope
   ```bash
   bd create "<subtask>" --type=task --parent=<parent-id> --priority=<n>
   ```
3. **If cannot explode**: Add comment explaining what's blocking, assign to `nic`
   ```bash
   bd comment <id> "Blocked: <reason>. Needs strategy review."
   bd update <id> --assignee=nic
   ```

**After TRIAGE**: Mark original task appropriately (in_progress if subtasks created, or reassigned) and HALT. Do not proceed to execution.

#### Mid-Execution Reclassification

If during EXECUTE you hit an unexpected blocker:
1. Stop work
2. Update task with findings: `bd comment <id> "Attempted: X. Blocked by: Y"`
3. Reclassify to TRIAGE path

### Step 5: Invoke Hydrator for Execution Plan

**(EXECUTE path only)**

Call the hydrator with the issue context to generate an execution plan:

```
Task(
  subagent_type="aops-core:prompt-hydrator",
  model="haiku",
  description="Hydrate claimed issue",
  prompt="Generate execution plan for claimed issue. Issue context:\n\n<issue details from bd show>\n\nProvide TodoWrite plan with acceptance criteria, relevant context, and verification steps."
)
```

### Step 6: Execute the Plan

1. **Create TodoWrite** with the hydrator's plan
2. **Work through each item** systematically
3. **Run QA verification** before completion (if code changed)

### Step 7: Handle Follow-up Work

If the task generates follow-up work:

```bash
# Create follow-up issues
bd create "<follow-up title>" --type=task --priority=<n> --description="Follow-up from <original-issue-id>: <context>"

# Link as dependency if appropriate
bd dep add <new-issue-id> depends-on <completed-issue-id>
```

### Step 8: Close the Issue

```bash
bd update <issue-id> --status=closed
bd sync
```

### Step 9: Record Learnings

If the work produced insights worth preserving:

```
Skill(skill="remember")
```

Use this for:
- Patterns discovered during implementation
- Decisions and their rationale
- Knowledge that will help future work

### Step 10: Commit and Push

```bash
git add -A
git commit -m "<meaningful commit message>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git pull --rebase
bd sync
git push
```

### Step 11: Session Reflection

End with Framework Reflection (see AGENTS.md "Framework Reflection (Session End)" for template).

## Arguments

- `/pull` - Auto-claim mode: claims highest priority ready issue (or halts if none)
- `/pull <issue-id>` - Direct mode: claims and executes specific issue

## Key Rules

1. **Always claim before working** - Never start work without `bd update --status=in_progress`
2. **Always hydrate** - Let the hydrator analyze the issue and generate the plan
3. **Always verify** - QA step before closing for code changes
4. **Always record** - Use remember skill for insights worth preserving
5. **Always push** - Work is not complete until `git push` succeeds
6. **Always reflect** - End with Framework Reflection for continuous improvement

## Examples

### Example 1: EXECUTE Path (fully specified task)
```
/pull
```
1. Runs `bd ready --assignee=bot` → finds `aops-xyz` (P1: Fix authentication bug)
2. Auto-claims: `bd update aops-xyz --status=in_progress`
3. Shows issue details via `bd show aops-xyz`
4. **Assesses path**: What ✓, Where ✓, Why ✓, How ✓, Scope ✓, No blockers ✓ → **EXECUTE**
5. Hydrator analyzes issue, generates TodoWrite plan
6. Agent executes plan, fixes bug
7. Creates follow-up: `aops-abc` for adding tests
8. Closes: `bd update aops-xyz --status=closed`
9. Records learnings via remember skill
10. Commits and pushes
11. Outputs Framework Reflection

### Example 2: TRIAGE Path (needs human input)
```
/pull
```
1. Runs `bd ready --assignee=bot` → finds `aops-abc` (P1: Book progress checkpoint)
2. Auto-claims: `bd update aops-abc --status=in_progress`
3. Shows issue details → requires human assessment of creative work
4. **Assesses path**: Requires human judgment → **TRIAGE**
5. Assigns to human: `bd update aops-abc --assignee=nic`
6. Adds comment: `bd comment aops-abc "Requires human assessment of completion percentage"`
7. **HALT** - does not proceed to execution

### Example 3: TRIAGE with Subtask Explosion
```
/pull
```
1. Runs `bd ready --assignee=bot` → finds `aops-def` (P1: Refactor auth system)
2. Auto-claims: `bd update aops-def --status=in_progress`
3. Shows issue details → large scope but decomposable
4. **Assesses path**: Exceeds session scope → **TRIAGE**
5. Creates subtasks:
   - `bd create "Extract auth middleware" --parent=aops-def --priority=1`
   - `bd create "Add JWT validation" --parent=aops-def --priority=1`
   - `bd create "Update auth tests" --parent=aops-def --priority=2`
6. Parent stays in_progress, subtasks are ready for future `/pull`

**If no ready issues:**
```
/pull
```
→ "No ready issues for bot. HALT."
