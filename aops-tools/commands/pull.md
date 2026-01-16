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

### Step 2: Present Options to User

Use AskUserQuestion to let the user choose which issue to claim:

```
AskUserQuestion(
  questions=[{
    question: "Which issue would you like to work on?",
    header: "Select task",
    options: [
      {label: "[issue-id] - [title]", description: "[priority] - [brief context]"},
      // ... up to 4 options from bd ready output
    ],
    multiSelect: false
  }]
)
```

If user provides an issue ID directly via `/pull <issue-id>`, skip to Step 3.

### Step 3: Claim the Issue

Mark the selected issue as in-progress:

```bash
bd update <issue-id> --status=in_progress
```

### Step 4: Invoke Hydrator for Execution Plan

Call the hydrator with the issue context to generate an execution plan:

```
Task(
  subagent_type="aops-core:prompt-hydrator",
  model="haiku",
  description="Hydrate claimed issue",
  prompt="Generate execution plan for claimed issue. Issue context:\n\n<issue details from bd show>\n\nProvide TodoWrite plan with acceptance criteria, relevant context, and verification steps."
)
```

### Step 5: Execute the Plan

1. **Create TodoWrite** with the hydrator's plan
2. **Work through each item** systematically
3. **Run QA verification** before completion (if code changed)

### Step 6: Handle Follow-up Work

If the task generates follow-up work:

```bash
# Create follow-up issues
bd create "<follow-up title>" --type=task --priority=<n> --description="Follow-up from <original-issue-id>: <context>"

# Link as dependency if appropriate
bd dep add <new-issue-id> depends-on <completed-issue-id>
```

### Step 7: Close the Issue

```bash
bd update <issue-id> --status=closed
bd sync
```

### Step 8: Record Learnings

If the work produced insights worth preserving:

```
Skill(skill="remember")
```

Use this for:
- Patterns discovered during implementation
- Decisions and their rationale
- Knowledge that will help future work

### Step 9: Commit and Push

```bash
git add -A
git commit -m "<meaningful commit message>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git pull --rebase
bd sync
git push
```

### Step 10: Session Reflection

End with Framework Reflection (see AGENTS.md "Framework Reflection (Session End)" for template).

## Arguments

- `/pull` - Interactive mode: presents ready issues for selection
- `/pull <issue-id>` - Direct mode: claims and executes specific issue

## Key Rules

1. **Always claim before working** - Never start work without `bd update --status=in_progress`
2. **Always hydrate** - Let the hydrator analyze the issue and generate the plan
3. **Always verify** - QA step before closing for code changes
4. **Always record** - Use remember skill for insights worth preserving
5. **Always push** - Work is not complete until `git push` succeeds
6. **Always reflect** - End with Framework Reflection for continuous improvement

## Example

```
/pull
```
1. Shows ready bot-assigned issues via `bd ready --assignee=bot`
2. User selects `aops-xyz` (P1: Fix authentication bug)
3. Claims issue: `bd update aops-xyz --status=in_progress`
4. Hydrator analyzes issue, generates TodoWrite plan
5. Agent executes plan, fixes bug
6. Creates follow-up: `aops-abc` for adding tests
7. Closes: `bd update aops-xyz --status=closed`
8. Records: `Skill(skill="remember")` for the pattern discovered
9. Commits and pushes
10. Outputs Framework Reflection
