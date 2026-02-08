

## Framework Paths

{framework_paths}

{env_vars}


### File Placement Rules
<!-- NS: this is framework specific stuff that should be in framework instructions. -->
<!-- @claude 2026-02-07: Agreed. These rules only apply when working ON aops-core, not when using the framework for other projects. Task created: aops-3e771f3b. -->
<!-- NS: move these to ./.agent/templates/prompt-hydrator-context.md -->
| Content Type | Directory | Example |
| :--- | :--- | :--- |
| **Specs** (design docs, architecture) | `$AOPS/specs/` | `specs/workflow-system-spec.md` |
| **Workflows** (step-by-step procedures) | `$AOPS/aops-core/workflows/` | `aops-core/workflows/feature-dev.md` |
| **Agents** (subagent definitions) | `$AOPS/aops-core/agents/` | `aops-core/agents/prompt-hydrator.md` |
| **Core Skills** (framework infrastructure) | `$AOPS/aops-core/skills/` | `aops-core/skills/framework/SKILL.md` |
| **Tool Skills** (domain utilities) | `$AOPS/aops-tools/skills/` | `aops-tools/skills/pdf/SKILL.md` |

**CRITICAL**: Specs go in top-level `specs/`, not inside plugins. Workflows go inside `aops-core/workflows/`. Never create `specs/SPEC.md` inside a plugin - use top-level `specs/`.


## Utility Scripts (Not Skills)

{scripts_index}

## The AcademicOps Framework (AOPS)
<!-- Nic: we should clarify here the distinction between working on the AOPS framework and USING the AOPS framework when working on another project. -->
<!-- @claude 2026-02-07: Key distinction: (1) Working ON aops = modifying $AOPS/ files, requires framework skill and governance; (2) Working WITH aops = using framework in another project, framework rules don't apply. The Framework Gate below handles this but could be clearer. Task created: aops-3e771f3b (consolidated with framework-specific rules task). -->
- **Framework Gate (CHECK FIRST)**: If prompt involves modifying `$AOPS/` (framework files), route to `[[framework-change]]` (governance) or `[[feature-dev]]` (code). NEVER route framework work to `[[simple-question]]`. Include Framework Change Context in output.
- **Internal Framework Development**: When work is ON the framework (not just using it) - modifying hooks, skills, workflows, agents, session logs, or debugging/fixing any of those - include `Skill(skill="framework")` in the execution plan. The framework skill has specialized workflows (e.g., `02-debug-framework-issue`) for this work. Distinguish: "using the framework to solve a user problem" vs "developing/debugging the framework itself".

## Key Rules
<!-- Nic: Rules are duplicated -- we should just have them in one place. We should also separate out the rules for working on AOPS from the universal rules. -->
<!-- @claude 2026-02-07: Agreed on both counts. Current duplication: (1) Key Rules here, (2) AXIOMS.md, (3) HEURISTICS.md, (4) per-skill instructions. Task created: aops-3e771f3b (consolidated with framework-specific rules task). Proposal: Universal rules → AXIOMS only; AOPS-specific rules → framework skill; remove duplicates from hydrator template. -->
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
