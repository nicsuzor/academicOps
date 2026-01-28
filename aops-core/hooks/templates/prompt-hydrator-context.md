---
name: prompt-hydrator-context
title: Prompt Hydrator Context Template
category: template
description: |
  Template written to temp file by UserPromptSubmit hook for prompt-hydrator subagent.
  Variables: {prompt} (user prompt), {session_context} (recent prompts, tools, tasks),
             {axioms} (full AXIOMS.md), {heuristics} (full HEURISTICS.md),
             {task_state} (current work state from tasks MCP)
  NOTE: Hydrator selects relevant principles from axioms/heuristics for main agent.
  Main agent receives ONLY selected principles, not full files.
---

# Prompt Hydration Request

Transform this user prompt into an execution plan with scope detection and task routing.

## User Prompt

{prompt}
{session_context}

## Framework Paths

{framework_paths}

**Use these prefixes in execution plans** - never use relative paths like `specs/file.md`.

## Relevant Files (Selective Injection)

Based on prompt keywords, these specific files may be relevant:

{relevant_files}

**Usage**: Reference these paths in your output when main agent needs to read specific files for context.

### File Placement Rules

| Content Type | Directory | Example |
|--------------|-----------|---------|
| **Specs** (design docs, architecture) | `$AOPS/specs/` | `specs/workflow-system-spec.md` |
| **Workflows** (step-by-step procedures) | `$AOPS/aops-core/workflows/` | `aops-core/workflows/feature-dev.md` |
| **Agents** (subagent definitions) | `$AOPS/aops-core/agents/` | `aops-core/agents/prompt-hydrator.md` |
| **Core Skills** (framework infrastructure) | `$AOPS/aops-core/skills/` | `aops-core/skills/framework/SKILL.md` |
| **Tool Skills** (domain utilities) | `$AOPS/aops-tools/skills/` | `aops-tools/skills/pdf/SKILL.md` |

**CRITICAL**: Specs go in top-level `specs/`, not inside plugins. Workflows go inside `aops-core/workflows/`. Never create `specs/SPEC.md` inside a plugin - use top-level `specs/`.

## Workflow Index (Pre-loaded)

{workflows_index}

## Skills Index (Pre-loaded)

{skills_index}

## Axioms (Pre-loaded)

{axioms}

## Heuristics (Pre-loaded)

{heuristics}

## Current Work State

{task_state}

## Your Task

1. **Understand intent** - What does the user actually want?
2. **Assess scope** - Single-session (bounded, path known) or multi-session (goal-level, uncertain path)?
3. **Determine execution path** - Should this be `direct` or `enqueue`?
4. **Route to task** - Match to existing task or specify new task creation
5. **Select workflow** - Use the pre-loaded Workflow Index above to select the appropriate workflow
6. **Compose workflows** - Read workflow files in `$AOPS/aops-core/workflows/` (and any [[referenced workflows]])
7. **Capture deferred work** - For multi-session scope, create decomposition task for future work

### Execution Path Decision

**Direct** (bypass queue) when ANY is true:
- User invoked a `/command` or `/skill` (e.g., `/commit`, `/pdf`)
- Pure information request (e.g., "what is X?", "how does Y work?")
- Conversational (e.g., "thanks", "can you explain...")
- No file modifications needed
- Workflow is `simple-question` or `direct-skill`

**Enqueue** (default for work) when:
- Work will modify files
- Work requires planning or multi-step execution
- Work has dependencies or verification requirements

**Detection heuristic**: Starts with `/` → direct. No file changes → direct. Everything else → enqueue.

## Return Format

Return this EXACT structure:

````markdown
## HYDRATION RESULT

**Intent**: [what user actually wants, in clear terms]
**Scope**: single-session | multi-session
**Execution Path**: direct | enqueue
**Workflow**: [[workflows/[workflow-id]]]

### Task Routing

[Choose ONE:]

**Existing task found**: `[task-id]` - [title]
- Verify first: `mcp__plugin_aops-core_tasks__get_task(id="[task-id]")` (confirm status=active or inbox)
- Claim with: `mcp__plugin_aops-core_tasks__update_task(id="[task-id]", status="active")`

**OR**

**New task needed**:
- Create with: `mcp__plugin_aops-core_tasks__create_task(task_title="[title]", type="task", project="aops", priority=2)`

**OR**

**No task needed** (simple-question only)

### Acceptance Criteria

1. [Specific, verifiable condition]
2. [Another condition]

### Relevant Context

- [Context from memory search]
- [Related tasks]

### Applicable Principles

- **P#[n] [Name]**: [Why this applies]

### Execution Plan

## Execution Steps
1. [Task claim/create from above]
2. [Workflow step]
3. CHECKPOINT: [verification]
4. Invoke the **qa** skill: "Verify implementation..."
5. Complete task, commit, and output Framework Reflection

### Deferred Work (multi-session only)

Create decomposition task for work that can't be done now:

```
mcp__plugin_aops-core_tasks__create_task(
  title="Decompose: [goal]",
  type="task",
  project="aops",
  priority=2,
  body="Apply decompose workflow. Items:\n- [Deferred 1]\n- [Deferred 2]\nContext: [what future agent needs]"
)
```

If immediate task depends on decomposition, set dependency:
```
mcp__plugin_aops-core_tasks__create_task(
  title="[immediate task]",
  depends_on=["[decompose-task-id]"],
  ...
)
```
````

## Utility Scripts (Not Skills)

These scripts exist but aren't user-invocable skills. Provide exact invocation when relevant:

| Request | Script | Invocation |
|---------|--------|------------|
| "save transcript", "export session" | `session_transcript.py` | `uv run python $AOPS/scripts/session_transcript.py <session.jsonl> -o output.md` |

## Key Rules

- **Framework Gate (CHECK FIRST)**: If prompt involves modifying `$AOPS/` (framework files), route to `[[framework-change]]` (governance) or `[[feature-dev]]` (code). NEVER route framework work to `[[simple-question]]`. Include Framework Change Context in output.
- **Code Changes → Search Existing Patterns First**: Before recommending new code (functions, classes, utilities), search `$AOPS/aops-core/hooks/` and `$AOPS/aops-core/lib/` for existing patterns. Common patterns: loading markdown files (see `user_prompt_submit.py`), parsing content (see `transcript_parser.py`), session state (see `lib/session_state.py`). Per P#12 (DRY), reuse existing code rather than duplicating.
- **Hook Changes → Read Docs First**: When modifying files in `**/hooks/*.py` OR adding/changing hook output fields (`decision`, `reason`, `stopReason`, `systemMessage`, `hookSpecificOutput`, `additionalContext`), classify as `cc_hook` task type and require reading `$AOPS/aops-core/skills/framework/references/hooks.md` for field semantics. Route to `[[feature-dev]]` workflow. P#26 (Verify First).
- **Python Code Changes → TDD**: When debugging or fixing Python code (`.py` files), include `Skill(skill="python-dev")` in the execution plan. The python-dev skill enforces TDD: write failing test FIRST, then implement fix. No trial-and-error edits.
- **Token/Session Analysis → Use Tooling**: When prompt involves "token", "efficiency", "usage", or "session analysis", surface `/session-insights` skill and `transcript_parser.py`. Per P#78, deterministic computation (token counting, aggregation) stays in Python, not LLM exploration.
- **Short confirmations**: If prompt is very short (≤10 chars: "yes", "ok", "do it", "sure"), check the MOST RECENT agent response and tools. The user is likely confirming/proceeding with what was just proposed, NOT requesting new work from task queue.
- **Scope detection**: Multi-session = goal-level, uncertain path, spans days+. Single-session = bounded, known steps.
- **Prefer existing tasks**: Search task state before creating new tasks.
- **QA MANDATORY**: Every plan (except simple-question) needs QA verification step.
- **Deferred work**: Only for multi-session. Captures what can't be done now without losing it.
- **Set dependency when sequential**: If immediate work is meaningless without the rest, set depends_on.

## ⚠️ Session Completion Rules (MANDATORY)

**Every file-modifying execution plan MUST include these final steps:**

1. **Complete task**: `mcp__plugin_aops-core_tasks__complete_task(id="<task-id>")`
2. **Commit and push**: `git add -A && git commit -m "..." && git push` (use Skill(skill="commit") if available)
3. **Output Framework Reflection** in this exact format:

```markdown
## Framework Reflection

**Prompts**: [Original request in brief]
**Guidance received**: [Hydrator advice, or "N/A"]
**Followed**: [Yes/No/Partial - explain]
**Outcome**: success | partial | failure
**Accomplishments**: [What was completed]
**Friction points**: [Issues encountered, or "none"]
**Root cause** (if not success): [Why work was incomplete]
**Proposed changes**: [Framework improvements, or "none"]
**Next step**: [Follow-up needed, or "none"]
```

**Why**: Session insights parsing depends on this format. Work without reflection is invisible to aggregation.

**Include in execution plan**:
```javascript
{{content: "Complete task, commit, and output Framework Reflection", status: "pending", activeForm: "Completing session"}}
```

## ⛔ Task-Gated Permissions (ENFORCED)

**Write/Edit operations will be BLOCKED** until a task is bound to the session.

The `task_required_gate` PreToolUse hook enforces this:
- **Claim existing**: `mcp__plugin_aops-core_tasks__update_task(id="...", status="active")`
- **Create new**: `mcp__plugin_aops-core_tasks__create_task(...)`

Until one of these runs, the agent CANNOT modify files. This is architectural enforcement, not a suggestion.

**Bypass**: User prefix `.` bypasses this gate for emergency/trivial fixes.

**Flow**: Your plan → main agent → (optional critic review) → main agent executes.

**NOTE**: You do NOT invoke critic. Main agent decides based on plan complexity:
- **Skip critic**: simple-question workflow, direct skill routes, trivial single-step tasks
- **Invoke critic**: multi-step execution plans, file modifications, architectural decisions
