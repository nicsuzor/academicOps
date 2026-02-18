"""
Polecat prompt templates.

Builds self-contained prompts for polecat workers so they don't depend
on /pull or any other skill invocation. The task is already claimed and
the worktree is ready — the agent just needs to execute.
"""

POLECAT_WORK_TEMPLATE = """\
.
You are a polecat worker. Your task has already been claimed and your \
worktree is ready. The task context below is self-contained — do not \
run `/pull` or the hydrator. Just execute.

## Your Task

- **ID**: {task_id}
- **Title**: {task_title}
- **Type**: {task_type}
- **Project**: {task_project}
{extras}
## Task Body

{task_body}
{soft_dep_context}
## Instructions

### Step 1: Assess — EXECUTE or TRIAGE

Determine whether to execute or triage.

**EXECUTE** (all must be true):

- Task describes specific deliverable(s)
- Target files/systems are known or locatable
- Context is sufficient for implementation decisions
- No external dependencies blocking you

**TRIAGE** (any is true):

- Task requires human judgment/approval
- Task is too vague to determine deliverables
- Task depends on external input not yet available
- Task exceeds session scope

### Step 2A: Execute

If executing:

1. Read task body for context and acceptance criteria
2. Implement the changes
3. Verify against acceptance criteria
4. Run tests if applicable
5. Commit all changes with a descriptive message

For `type: learn` tasks specifically:
1. Investigate per task instructions
2. Write findings to task body via `update_task(id, body=...)`
3. Decompose actionable items into subtasks
4. Decomposition IS completion for learn tasks

### Step 2B: Triage

If triaging, pick one:

- **Assign**: `update_task(id="{task_id}", assignee="nic")` if it needs human judgment
- **Decompose**: Break into 3-7 subtasks if scope is clear but too large
- **Block**: `update_task(id="{task_id}", status="blocked", body="Blocked: [reason]")` if unclear

After triaging, HALT. Do not continue to execution.

### Step 3: Finish

{finish_instructions}
"""

FINISH_LOCAL_TASK = """\
After successful execution, mark the task complete:

```
complete_task(id="{task_id}")
```

Do NOT call complete_task unless all changes are committed and acceptance \
criteria are met."""

FINISH_GITHUB_ISSUE = """\
After successful execution, ensure all changes are committed with a \
descriptive message. The polecat system will handle pushing and PR creation. \
Do NOT call complete_task — there is no local task to complete."""


def build_task_extras(task: dict) -> str:
    """Build optional metadata lines for the prompt."""
    lines = []
    if task.get("parent"):
        lines.append(f"- **Parent**: {task['parent']}")
    if task.get("priority") is not None:
        lines.append(f"- **Priority**: P{task['priority']}")
    if task.get("tags"):
        lines.append(f"- **Tags**: {', '.join(task['tags'])}")
    if lines:
        return "\n".join(lines) + "\n"
    return ""


def build_soft_dep_context(soft_deps: list[dict] | None) -> str:
    """Format soft dependency context block.

    Args:
        soft_deps: List of resolved soft dependency dicts, each with
                   at minimum {id, title, status} and optionally {body}.
    """
    if not soft_deps:
        return ""

    done = [d for d in soft_deps if d.get("status") == "done"]
    if not done:
        return ""

    lines = ["\n## Soft Dependency Context (Advisory)\n"]
    for dep in done:
        lines.append(f"### [{dep['id']}] {dep.get('title', '(untitled)')}\n")
        body = dep.get("body", "").strip()
        if body:
            if len(body) > 2000:
                body = body[:2000] + "\n\n[truncated]"
            lines.append(body)
        lines.append("\n---\n")

    return "\n".join(lines)


def build_polecat_prompt(
    task_id: str,
    task_title: str,
    task_type: str = "task",
    task_project: str = "",
    task_body: str = "",
    task_meta: dict | None = None,
    soft_deps: list[dict] | None = None,
    is_issue: bool = False,
) -> str:
    """Build a self-contained polecat work prompt.

    Args:
        task_id: Task identifier (local task ID or synthesized issue ID).
        task_title: Human-readable task title.
        task_type: Task type (task, action, learn, bug, feature, etc.).
        task_project: Project slug.
        task_body: Full task body/description.
        task_meta: Optional dict with parent, priority, tags, etc.
        soft_deps: Optional resolved soft dependency list.
        is_issue: If True, use GitHub issue finish instructions.

    Returns:
        Complete prompt string ready to pass to claude/gemini.
    """
    extras = build_task_extras(task_meta or {})
    soft_dep_context = build_soft_dep_context(soft_deps)

    if is_issue:
        finish_instructions = FINISH_GITHUB_ISSUE
    else:
        finish_instructions = FINISH_LOCAL_TASK.format(task_id=task_id)

    return POLECAT_WORK_TEMPLATE.format(
        task_id=task_id,
        task_title=task_title,
        task_type=task_type or "task",
        task_project=task_project or "(none)",
        task_body=task_body or "(no body)",
        extras=extras,
        soft_dep_context=soft_dep_context,
        finish_instructions=finish_instructions,
    )
