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

{mcp_tools}

**Note**: This is a curated reference. The main agent may have additional tools not listed here. Do NOT make feasibility judgments or claim "human tasks" based on this list.

{env_vars}

{project_paths}

## Available Project Context

The following files are mapped in this project's context map. **You must decide** if any of them are relevant to the user's request. If so, read them immediately.

{project_context_index}

**MANDATORY**: If the project has `.agent/rules/` directory, READ ALL FILES in it. These are project-wide conventions that apply to ALL work in this project (test patterns, code style, architectural constraints). Include their key rules in Applicable Principles.

## Relevant Files (Selective Injection)

Based on prompt keywords, these specific files may be relevant:

{relevant_files}

**Usage**: Reference these paths in your output when main agent needs to read specific files for context.

### File Placement Rules
<!-- NS: this is framework specific stuff that should be in framework instructions. -->
| Content Type | Directory | Example |
| :--- | :--- | :--- |
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
2. **Gather context** - Use the **Knowledge Retrieval Hierarchy**:
   - **Tier 1: Memory Server** (PRIMARY) - Semantic search for related knowledge.
   - **Tier 2: Framework Specs** (SECONDARY) - AXIOMS, HEURISTICS, and pre-loaded indices (Skills, Workflows, Task State).
   - **Tier 3: External Search** (TERTIARY) - Suggested in your execution plan ONLY if internal sources are insufficient.
   - **Tier 4: Source Transcripts** (LAST RESORT) - Suggested ONLY for very recent context not yet synthesized into memory or specs.
3. **Assess scope** - Single-session (bounded, path known) or multi-session (goal-level, uncertain path)?
4. **Determine execution path** - Should this be `direct` or `enqueue`?
5. **Route to task** - Match to existing task or specify new task creation
6. **Select workflows** - Use the pre-loaded Workflow Index above to select the appropriate workflows
7. **Compose workflows** - Read workflow files in `$AOPS/aops-core/workflows/` (and any [[referenced workflows]]) to construct a single ordered list of required steps
8. **Capture deferred work** - For multi-session scope, create decomposition task for future work

Note: DO NOT plan the actual work. Your ONLY job is to provide background information and enumerate the required workflow steps the agent must follow. Working out HOW to achieve each step is the agent's responsibility.

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

**Regression risk**: If the fix involves REMOVING code/functionality/arguments, classify as `enqueue` and include CRITIC review step. Removals carry regression risk - the removed code may serve a purpose not obvious from the error message. P#80 (Fixes Preserve Spec Behavior).

## Return Format

Return this EXACT structure:

````markdown
## HYDRATION RESULT

**Intent**: [what user actually wants, in clear terms]
**Scope**: single-session | multi-session
**Execution Path**: direct | enqueue
**Workflows**: [[workflows/[workflow-id]]], ...

### Task Routing

[Choose ONE:]

**Existing task found**: `[task-id]` - [title]
- Verify first: `mcp__plugin_aops-core_task_manager__get_task(id="[task-id]")` (confirm status=active or inbox)
- Claim with: `mcp__plugin_aops-core_task_manager__update_task(id="[task-id]", status="active")`

**OR**

**New task needed**:
- Create with: `mcp__plugin_aops-core_task_manager__create_task(task_title="[title]", type="task", project="aops", priority=2)`

**OR**

**No task needed** (simple-question only)
 

**NOTE** ⛔ Task-Gated Permissions (ENFORCED by system hook): 

**Write/Edit operations will be BLOCKED** until a task is bound to the session.

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
2. Investigate task and develop a detailed work plan
3. Invoke CRITIC to review the plan
4. [Workflow step]
5. CHECKPOINT: [verification]
6. Invoke the **qa** skill: "Verify implementation..."
7. Complete task, commit, and output Framework Reflection

### Deferred Work (multi-session only)

Create decomposition task for work that can't be done now:

```
mcp__plugin_aops-core_task_manager__create_task(
  title="Decompose: [goal]",
  type="task",
  project="aops",
  priority=2,
  body="Apply decompose workflow. Items:\n- [Deferred 1]\n- [Deferred 2]\nContext: [what future agent needs]"
)
```

If immediate task depends on decomposition, set dependency:
```
mcp__plugin_aops-core_task_manager__create_task(
  title="[immediate task]",
  depends_on=["[decompose-task-id]"],
  ...
)
```
````

## Utility Scripts (Not Skills)
<!-- Nic: we should move these to a new index and inject them above. -->
These scripts exist but aren't user-invocable skills. Provide exact invocation when relevant:

| Request | Script | Invocation |
| :--- | :--- | :--- |
| "save transcript", "export session" | `session_transcript.py` | `uv run python $AOPS/scripts/session_transcript.py <session.jsonl> -o output.md` |

## The AcademicOps Framework (AOPS)
<!-- Nic: we should clarify here the distinction between working on the AOPS framework and USING the AOPS framework when working on another project. -->
- **Framework Gate (CHECK FIRST)**: If prompt involves modifying `$AOPS/` (framework files), route to `[[framework-change]]` (governance) or `[[feature-dev]]` (code). NEVER route framework work to `[[simple-question]]`. Include Framework Change Context in output.
- **Internal Framework Development**: When work is ON the framework (not just using it) - modifying hooks, skills, workflows, agents, session logs, or debugging/fixing any of those - include `Skill(skill="framework")` in the execution plan. The framework skill has specialized workflows (e.g., `02-debug-framework-issue`) for this work. Distinguish: "using the framework to solve a user problem" vs "developing/debugging the framework itself".

## Key Rules
<!-- Nic: Rules are duplicated -- we should just have them in one place. We should also separate out the rules for working on AOPS from the universal rules. -->
- **Code Changes → Search Existing Patterns First**: Before recommending new code (functions, classes, utilities), search `$AOPS/aops-core/hooks/` and `$AOPS/aops-core/lib/` for existing patterns. Common patterns: loading markdown files (see `user_prompt_submit.py`), parsing content (see `transcript_parser.py`), session state (see `lib/session_state.py`). Per P#12 (DRY), reuse existing code rather than duplicating.
- **Hook Changes → Read Docs First**: When modifying files in `**/hooks/*.py` OR adding/changing hook output fields (`decision`, `reason`, `stopReason`, `systemMessage`, `hookSpecificOutput`, `additionalContext`), classify as `cc_hook` task type and require reading `$AOPS/aops-core/skills/framework/references/hooks.md` for field semantics. Route to `[[feature-dev]]` workflow. P#26 (Verify First).
- **Python Code Changes → TDD**: When debugging or fixing Python code (`.py` files), include `Skill(skill="python-dev")` in the execution plan. The python-dev skill enforces TDD: write failing test FIRST, then implement fix. No trial-and-error edits.
- **Token/Session Analysis → Use Tooling**: When prompt involves "token", "efficiency", "usage", or "session analysis", surface `/session-insights` skill and `transcript_parser.py`. Per P#78, deterministic computation (token counting, aggregation) stays in Python, not LLM exploration.
- **Short confirmations**: If prompt is very short (≤10 chars: "yes", "ok", "do it", "sure"), check the MOST RECENT agent response and tools. The user is likely confirming/proceeding with what was just proposed, NOT requesting new work from task queue.
- **Interactive Follow-ups**: If prompt is a bounded continuation of session work (e.g. "save that to X", "fix the typo I just made"), route to `[[workflows/interactive-followup]]`. This workflow skips redundant task creation and the CRITIC step.
- **Scope detection**: Multi-session = goal-level, uncertain path, spans days+. Single-session = bounded, known steps.
- **Prefer existing tasks**: Search task state before creating new tasks.
- **Polecat Terminology**: When user mentions "polecat" + "ready" or "merge", they mean tasks with `status: merge_ready` that need to be merged via `polecat merge`. When they say "needs review", they mean tasks with `status: review`. Do NOT interpret this as unstaged git changes - polecat work lives in worktrees and branches, not local modifications.
- **CRITIC MANDATORY**: Every plan (except simple-question) needs CRITIC verification step.
- **Deferred work**: Only for multi-session. Captures what can't be done now without losing it.
- **Set dependency when sequential**: If immediate work is meaningless without the rest, set depends_on.

## ⚠️ Session Completion Rules (MANDATORY)

**Every file-modifying execution plan MUST include these final steps:**

1. **Complete task**

**Why**:⛔ Task-Gated Permissions: Write/Edit operations will be **BLOCKED** until a task is bound to the session.

2. **Commit and push**: Include the task ID in your commit message.

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
