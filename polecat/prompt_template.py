"""
Polecat prompt templates.

Builds prompts for polecat workers. The task is already claimed and
the worktree is ready. Hydration runs normally to provide relevant
skill context (e.g., testing philosophy for test-writing tasks).
"""

POLECAT_WORK_TEMPLATE = """\
You are a polecat worker. Your task has already been claimed and your \
worktree is ready. Do not run `/pull` — the task context is below. \
The hydrator will provide relevant skills and workflows automatically.

**Task Body Convention (Intent + AC, not prescription)**: Task bodies state intent and \
observable Acceptance Criteria. Treat any proposed file paths, function names, or \
implementation steps as suggestions to verify, not ground truth. Verify paths and design \
before acting. When decomposing tasks yourself, adhere to this same rule: state intent+AC \
and never write unverified prescriptive paths.

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

### Step 0: Pre-flight — Check for Prior Work

Before doing anything, check whether this task has already been worked on:

1. If **Existing PR** appears in the metadata above, HALT immediately. Do not execute.
   Run `gh pr view` on the PR URL shown in **Existing PR** above to confirm state, then triage:
   - If PR is open and looks correct: `update_task(id="{task_id}", assignee="nic", body="[prior work] PR already filed (see Existing PR in task metadata)")`
   - If PR is merged: task may have been completed — check and update status accordingly.
2. If task body mentions a filed PR or prior completion, HALT and triage the same way.
3. If task status is anything other than `in_progress`, `ready`, or `queued`, HALT and triage.

Only proceed to Step 1 if you confirm no prior work exists.

**Path verification**: Before quoting from a file the task body names, verify the file exists at the named path. If it doesn't, HALT and report — do not substitute a similar-looking file.

**Data verification (research tasks)**: If your task body asks you to quote, count, classify, or analyse primary data (model traces, transcripts, raw records, dbt mart rows, BigQuery results), verify you can read the data *before* quoting from it. Run one probe (e.g. `bq query LIMIT 1`, `duckdb -c "SELECT COUNT(*) FROM ..."`, `head` of a raw record) and quote its actual output in your progress log. If the probe fails — credentials missing, cache absent, source unreachable — HALT and report the gap. Do NOT substitute summary documents, prior reports, or template excerpts for the primary source. If a derived cache is stale per the project's CLAUDE.md threshold, HALT and report — do not silently run `scripts/refresh.sh` unless the task body explicitly authorises it. This is a direct application of CORE.md's Halt Rule and P#42 to the data-evidence chain.

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
2. Write findings to task body via `update_task(id, body="...")`
3. Decompose actionable items into subtasks
4. Decomposition IS completion for learn tasks

### Step 2B: Triage

If triaging, pick one:

- **Assign**: `update_task(id="{task_id}", assignee="nic")` if it needs human judgment
- **Decompose**: Break into 3-7 subtasks if scope is clear but too large
- **Block**: `release_task(id="{task_id}", status="blocked", summary="What was attempted", blocker="[reason]")` if unclear

After triaging, HALT. Do not continue to execution.

### Step 3: Finish

{finish_instructions}
"""

FINISH_LOCAL_TASK = """\
After successful execution:

0. **Pre-push gate check — re-read the task body NOW.** Before any \
`git push` or `gh pr create`, scan the task body for task-specific \
mandatory gates. Look for: "MUST", "mandatory", "required", \
"before PR", "before push", "re-review", "verdict", any explicit \
review/QA/handover instruction, or numbered "process gates" / \
"checkpoints". For each such gate, satisfy it (typically by \
dispatching the named review agent on the implementation) and \
record the verdict in this session BEFORE proceeding to step 2. \
Completion momentum will tempt you to skip this — do not. Generic \
"Finish" steps NEVER override task-body mandatory gates. \
(Background: GitHub issue #583 — a worker shipped a PR after \
satisfying gates 1+2 but skipping gate 3 at the moment of highest \
finishing momentum.)

1. **Commit** all changes with a descriptive message.

2. **If code or files were changed**, push your branch and file a PR \
(`GH_PROMPT_DISABLED=1` is already set in your environment):

   ```bash
   git push -u origin HEAD
   gh pr create \\
     --title "<task title>" \\
     --body "<what changed and why>\\n\\nCloses {task_id}" \\
     --head <branch-name> \\
     --base main
   ```

   All four flags (`--title`, `--body`, `--head`, `--base`) are required.
   Omitting `--head` or `--base` will cause `gh` to hang.

3. **Release the task** in PKB to record what was done:

   - If a PR was filed:
     ```
     mcp__pkb__release_task(id="{task_id}", status="merge_ready",
       summary="<what changed and why>", pr_url="<PR URL>", branch="<branch>")
     ```
     This sets the task to `merge_ready` with a summary of the work. The governing
     system will close the task after the PR is merged.

     **Do NOT wait for CI after filing a PR** — exit promptly after push + PR + reflection.

   - If no code changes (learn tasks, investigations, etc.):
     ```
     mcp__pkb__release_task(id="{task_id}", status="done",
       summary="<what was investigated and findings>")
     ```

Do NOT release until all changes are committed and acceptance criteria \
are met."""

FINISH_GITHUB_ISSUE = """\
After successful execution, ensure all changes are committed with a \
descriptive message. The polecat system will handle pushing and PR creation. \
Do NOT call mcp__pkb__complete_task — there is no local task to complete."""


def build_task_extras(task: dict) -> str:
    """Build optional metadata lines for the prompt."""
    lines = []
    if task.get("parent"):
        lines.append(f"- **Parent**: {task['parent']}")
    if task.get("priority") is not None:
        lines.append(f"- **Priority**: P{task['priority']}")
    if task.get("tags"):
        lines.append(f"- **Tags**: {', '.join(str(t) for t in task['tags'])}")
    if task.get("status"):
        lines.append(f"- **Status**: {task['status']}")
    pr_url = task.get("pr_url")
    pr = task.get("pr")
    if pr_url:
        lines.append(f"- **Existing PR**: {pr_url}")
    elif pr:
        lines.append(f"- **Existing PR**: #{pr}")
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
