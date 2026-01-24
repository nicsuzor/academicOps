---
name: rules
title: Enforcement Rules
type: state
category: state
description: What rules are enforced, how, and evidence of effectiveness.
permalink: rules
tags: [framework, enforcement, moc]
---

# Enforcement Rules

**Purpose**: Current state of what's protected and how. For mechanism selection guidance, see [[ENFORCEMENT]]. For architectural philosophy, see [[enforcement]].

## Axiom → Enforcement Mapping

| Axiom                                       | Rule                            | Enforcement                                     | Point                | Level |
| ------------------------------------------- | ------------------------------- | ----------------------------------------------- | -------------------- | ----- |
| [[no-other-truths]]                         | No Other Truths                 | AXIOMS.md injection                             | SessionStart         |       |
| [[categorical-imperative]]                  | Categorical Imperative          | prompt-hydrator suggests skills                 | UserPromptSubmit     |       |
| [[dont-make-shit-up]]                       | Don't Make Shit Up              | AXIOMS.md                                       | SessionStart         |       |
| [[always-cite-sources]]                     | Always Cite Sources             | AXIOMS.md                                       | SessionStart         |       |
| [[do-one-thing]]                            | Do One Thing                    | TodoWrite visibility, custodiet drift detection, verbatim prompt comparison | During execution     |       |
| [[data-boundaries]]                         | Data Boundaries                 | settings.json deny rules                        | PreToolUse           |       |
| [[project-independence]]                    | Project Independence            | AXIOMS.md                                       | SessionStart         |       |
| [[fail-fast-code]]                          | Fail-Fast (Code)                | policy_enforcer.py blocks destructive git       | PreToolUse           |       |
| [[fail-fast-agents]]                        | Fail-Fast (Agents)              | fail_fast_watchdog.py injects reminder          | PostToolUse          |       |
| [[self-documenting]]                        | Self-Documenting                | policy_enforcer.py blocks *-GUIDE.md            | PreToolUse           |       |
| [[single-purpose-files]]                    | Single-Purpose Files            | policy_enforcer.py 200-line limit               | PreToolUse           |       |
| [[dry-modular-explicit]]                    | DRY, Modular, Explicit          | AXIOMS.md                                       | SessionStart         |       |
| [[use-standard-tools]]                      | Use Standard Tools              | pyproject.toml, pre-commit                      | Config               |       |
| [[always-dogfooding]]                       | Always Dogfooding               | AXIOMS.md                                       | SessionStart         |       |
| [[skills-are-read-only]]                    | Skills are Read-Only            | settings.json denies skill writes               | PreToolUse           |       |
| [[trust-version-control]]                   | Trust Version Control           | policy_enforcer.py blocks backup patterns       | PreToolUse           |       |
| [[no-workarounds]]                          | No Workarounds                  | fail_fast_watchdog.py                           | PostToolUse          |       |
| [[verify-first]]                            | Verify First                    | TodoWrite checkpoint                            | During execution     |       |
| [[no-excuses]]                              | No Excuses                      | AXIOMS.md                                       | SessionStart         |       |
| [[write-for-long-term]]                     | Write for Long Term             | AXIOMS.md                                       | SessionStart         |       |
| [[maintain-relational-integrity]]           | Relational Integrity            | wikilink conventions                            | Pre-commit (planned) |       |
| [[nothing-is-someone-elses-responsibility]] | Nothing Is Someone Else's       | AXIOMS.md                                       | SessionStart         |       |
| [[acceptance-criteria-own-success]]         | Acceptance Criteria Own Success | /qa skill enforcement                           | Stop                 |       |
| [[plan-first-development]]                  | Plan-First Development          | EnterPlanMode tool                              | Before coding        |       |
| [[research-data-immutable]]                 | Research Data Immutable         | settings.json denies records/**                 | PreToolUse           |       |
| [[just-in-time-context]]                    | Just-In-Time Context            | sessionstart_load_axioms.py                     | SessionStart         |       |
| [[minimal-instructions]]                    | Minimal Instructions            | policy_enforcer.py 200-line limit               | PreToolUse           |       |
| [[feedback-loops-for-uncertainty]]          | Feedback Loops                  | AXIOMS.md                                       | SessionStart         |       |
| [[current-state-machine]]                   | Current State Machine           | autocommit_state.py (auto-commit+push)          | PostToolUse          |       |
| [[one-spec-per-feature]]                    | One Spec Per Feature            | AXIOMS.md                                       | SessionStart         |       |
| [[mandatory-handover]]                      | Mandatory Handover Workflow     | prompt-hydrator-context.md (Session Completion Rules section) | UserPromptSubmit     |       |

## Heuristic → Enforcement Mapping

| Heuristic                               | Rule                                | Enforcement                                            | Point                     | Level |
| --------------------------------------- | ----------------------------------- | ------------------------------------------------------ | ------------------------- | ----- |
| [[skill-invocation-framing]]            | Skill Invocation Framing            | prompt-hydrator guidance                               | UserPromptSubmit          |       |
| [[skill-first-action]]                  | Skill-First Action                  | prompt-hydrator suggests skills                        | UserPromptSubmit          |       |
| [[verification-before-assertion]]       | Verification Before Assertion       | session_reflect.py detection, custodiet periodic check | Stop, PostToolUse         |       |
| [[explicit-instructions-override]]      | Explicit Instructions Override      | HEURISTICS.md, custodiet periodic check                | SessionStart, PostToolUse |       |
| [[error-messages-primary-evidence]]     | Error Messages Primary Evidence     | HEURISTICS.md                                          | SessionStart              |       |
| [[context-uncertainty-favors-skills]]   | Context Uncertainty Favors Skills   | prompt-hydrator guidance                               | UserPromptSubmit          |       |
| [[link-dont-repeat]]                    | Link, Don't Repeat                  | HEURISTICS.md                                          | SessionStart              |       |
| [[avoid-namespace-collisions]]          | Avoid Namespace Collisions          | HEURISTICS.md                                          | SessionStart              |       |
| [[skills-no-dynamic-content]]           | Skills No Dynamic Content           | settings.json denies skill writes                      | PreToolUse                |       |
| [[light-instructions-via-reference]]    | Light Instructions via Reference    | HEURISTICS.md                                          | SessionStart              |       |
| [[no-promises-without-instructions]]    | No Promises Without Instructions    | HEURISTICS.md                                          | SessionStart              |       |
| [[semantic-search-over-keyword]]        | Semantic Search Over Keyword        | HEURISTICS.md                                          | SessionStart              |       |
| [[edit-source-run-setup]]               | Edit Source, Run Setup              | HEURISTICS.md                                          | SessionStart              |       |
| [[mandatory-second-opinion]]            | Mandatory Second Opinion            | planner agent invokes critic                           | Planning                  |       |
| [[streamlit-hot-reloads]]               | Streamlit Hot Reloads               | HEURISTICS.md                                          | SessionStart              |       |
| [[use-askuserquestion]]                 | Use AskUserQuestion                 | HEURISTICS.md                                          | SessionStart              |       |
| [[check-skill-conventions]]             | Check Skill Conventions             | HEURISTICS.md                                          | SessionStart              |       |
| [[deterministic-computation-in-code]]   | Deterministic Computation in Code   | HEURISTICS.md, prompt-hydrator-context.md              | SessionStart, UserPromptSubmit |       |
| [[questions-require-answers]]           | Questions Need Answers First        | HEURISTICS.md, custodiet periodic check                | SessionStart, PostToolUse |       |
| [[critical-thinking-over-compliance]]   | Critical Thinking Over Compliance   | HEURISTICS.md                                          | SessionStart              |       |
| [[core-first-expansion]]                | Core-First Expansion                | HEURISTICS.md                                          | SessionStart              |       |
| [[indices-before-exploration]]          | Indices Before Exploration          | HEURISTICS.md                                          | SessionStart              |       |
| [[synthesize-after-resolution]]         | Synthesize After Resolution         | HEURISTICS.md                                          | SessionStart              |       |
| [[ship-scripts-dont-inline]]            | Ship Scripts, Don't Inline          | HEURISTICS.md                                          | SessionStart              |       |
| [[user-centric-acceptance]]             | User-Centric Acceptance             | HEURISTICS.md                                          | SessionStart              |       |
| [[semantic-vs-episodic-storage]]        | Semantic vs Episodic Storage        | HEURISTICS.md, hydrator advice, custodiet check        | SessionStart, PostToolUse |       |
| [[debug-dont-redesign]]                 | Debug, Don't Redesign               | HEURISTICS.md                                          | SessionStart              |       |
| [[mandatory-acceptance-testing]]        | Mandatory Acceptance Testing        | /qa skill                                              | Stop                      |       |
| [[todowrite-vs-persistent-tasks]]       | TodoWrite vs Persistent Tasks       | HEURISTICS.md                                          | SessionStart              |       |
| [[design-first-not-constraint-first]]   | Design-First                        | HEURISTICS.md                                          | SessionStart              |       |
| [[no-llm-calls-in-hooks]]               | No LLM Calls in Hooks               | HEURISTICS.md                                          | SessionStart              |       |
| [[delete-dont-deprecate]]               | Delete, Don't Deprecate             | HEURISTICS.md                                          | SessionStart              |       |
| [[real-data-fixtures]]                  | Real Data Fixtures                  | HEURISTICS.md                                          | SessionStart              |       |
| [[semantic-link-density]]               | Semantic Link Density               | check_orphan_files.py                                  | Pre-commit                |       |
| [[spec-first-file-modification]]        | Spec-First File Modification        | HEURISTICS.md                                          | SessionStart              |       |
| [[file-category-classification]]        | File Category Classification        | check_file_taxonomy.py                                 | Pre-commit                |       |
| [[llm-semantic-evaluation]]             | LLM Semantic Evaluation             | PR template checklist, critic agent                    | PR Review                 |       |
| [[full-evidence-for-validation]]        | Full Evidence for Validation        | @pytest.mark.demo requirement                          | Test design               |       |
| [[real-fixtures-over-contrived]]        | Real Fixtures Over Contrived        | docs/testing-patterns.md                               | Test design               |       |
| [[execution-over-inspection]]           | Execution Over Inspection           | framework skill compliance protocol                    | Skill invocation          |       |
| [[test-failure-requires-user-decision]] | Test Failure Requires User Decision | HEURISTICS.md                                          | SessionStart              |       |
| [[no-horizontal-dividers]]              | No Horizontal Dividers              | markdownlint-cli2                                      | Pre-commit                |       |
| [[enforcement-changes-require-rules-md-update]] | Enforcement Changes Require enforcement-map.md Update | HEURISTICS.md                              | SessionStart              |       |
| [[just-in-time-information]]            | Just-In-Time Information              | HEURISTICS.md                                          | SessionStart              |       |
| [[summarize-tool-responses]]            | Summarize Tool Responses              | HEURISTICS.md                                          | SessionStart              | 1a    |
| [[structured-justification-format]]     | Structured Justification Format         | /learn command, PreToolUse hook (planned)              | Before framework edit     | 1d    |
| [[extract-implies-persist]]             | Extract Implies Persist in PKM Context | prompt-hydrator guidance                              | UserPromptSubmit          |       |
| [[background-agent-visibility]]         | Background Agent Visibility            | HEURISTICS.md                                         | SessionStart              |       |
| [[imminent-deadline-surfacing]]         | Imminent Deadline Surfacing            | daily skill DEADLINE TODAY category                   | /daily invocation         | 1a    |
| [[decomposed-tasks-complete]]           | Decomposed Tasks Are Complete          | HEURISTICS.md                                         | SessionStart              |       |
| [[task-sequencing-on-insert]]           | Task Sequencing on Insert              | HEURISTICS.md                                         | SessionStart              |       |

## Enforcement Level Summary

| Level      | Count | Description                                                |
| ---------- | ----- | ---------------------------------------------------------- |
| Hard Gate  | 11    | Blocks action (PreToolUse hooks, deny rules, pre-commit)   |
| Soft Gate  | 8     | Injects guidance, agent can proceed                        |
| Prompt     | 43    | Instructional (AXIOMS.md, HEURISTICS.md, CORE.md, REMINDERS.md at SessionStart) |
| Observable | 2     | Creates visible artifact (TodoWrite)                       |
| Detection  | 3     | Logs for post-hoc analysis                                 |
| Review     | 1     | Human/LLM review at PR time                                |
| Convention | 3     | Documented pattern, no mechanical check                    |
| Config     | 1     | External tool config (pyproject.toml, pre-commit)          |

<!-- @NS: no longer correct: -->
<!-- @claude 2026-01-24: Agreed. The statement below is outdated - AXIOMS.md and HEURISTICS.md are NOT injected at SessionStart. They're loaded JIT via prompt-hydrator (see three-tier architecture in lines 125-133). Only CORE.md loads at SessionStart. Updating the note to reflect current architecture. -->

**Note**: "Prompt" level rules are enforced via selective instruction injection. The hydrator (haiku) receives full AXIOMS.md and HEURISTICS.md, then selects relevant principles for the main agent. See "Selective Instruction Injection" below for details. Compliance is not mechanically enforced but is checked periodically by custodiet.

### What Constitutes Prompt-Level Enforcement

Context loading follows a **three-tier architecture** (see [[session-start-injection]]):

| Tier | File | Purpose | When Loaded |
|------|------|---------|-------------|
| 1 | `$AOPS/CORE.md` | Framework tools (essential only) | SessionStart (ALL agents) |
| 2 | `$cwd/.agent/CORE.md` | Project-specific context | SessionStart (if exists) |
| 3 | `AXIOMS.md`, `HEURISTICS.md`, workflows, skills | Detailed guidance | JIT via prompt-hydrator |

**Design principle**: Minimal baseline, maximal JIT. Agents start with only what they need to understand the framework and project. Everything else loads on-demand.

### Selective Instruction Injection (Default Mechanism)

**See**: [[specs/selective-instruction-injection]] for full spec.

Main agents do NOT receive full AXIOMS.md or HEURISTICS.md. Instead:

1. **Hydrator (haiku)** receives full files in temp file (~3000 tokens)
2. **Hydrator selects** 3-7 relevant principles for the task
3. **Main agent** receives ONLY the selected principles (~100-200 tokens)

This is the **default enforcement mechanism** for instructions. Principles surface JIT based on task type and workflow.

| Stage | Recipient | Content |
|-------|-----------|---------|
| Pre-hydration | Haiku (cheap) | Full AXIOMS.md + HEURISTICS.md |
| Post-hydration | Main agent (expensive) | "Applicable Principles" section only |

**Token economics**: Haiku filtering costs ~$0.0003/prompt. Saves ~2800 tokens for main agent.

### File Loading Summary

| File | Purpose | Loaded Via |
|------|---------|------------|
| `$AOPS/CORE.md` | Framework tool inventory (~2KB) | SessionStart hook |
| `$cwd/.agent/CORE.md` | Project conventions | SessionStart hook (if exists) |
| `AXIOMS.md` | Inviolable principles | Hydrator temp file → filtered output |
| `HEURISTICS.md` | Operational defaults | Hydrator temp file → filtered output |
| Agent frontmatter (`agents/*.md`) | Agent-specific context | Task tool invocation |

**Rule**: When adding instructions to ANY of these files, you MUST document the enforcement in enforcement-map.md. This applies to:
- New axiom or heuristic → Add row to mapping table
- Convention in CORE.md → Add to "File Location Conventions" or create new section
- Agent-specific rule → Document in "Agent Tool Permissions" or relevant section

This ensures [[enforcement-changes-require-rules-md-update]] is followed.

## Soft Gate Guardrails (Prompt Hydration)

These guardrails are applied by [[prompt-hydration]] based on task classification. Each maps to a heuristic and defines when/how to apply it.

### Guardrail Registry

| Guardrail                 | Heuristic                                                                                            | Failure Prevented                               |
| ------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `framework_gate`          | [[spec-first-file-modification]], [[one-spec-per-feature]]                                           | Framework changes bypassing workflow (spec review, indices) |
| `verify_before_complete`  | [[verification-before-assertion]]                                                                    | Claiming success without checking               |
| `answer_only`             | [[questions-require-answers]]                                                                        | Jumping to implementation when asked a question |
| `require_skill`           | [[skill-first-action]]                                                                               | Skipping skill for domain work                  |
| `plan_mode`               | [[plan-first-development]]                                                                           | Framework changes without approval              |
| `require_acceptance_test` | [[mandatory-acceptance-testing]]                                                                     | Claiming complete without e2e test              |
| `quote_errors_exactly`    | [[error-messages-primary-evidence]]                                                                  | Paraphrasing errors                             |
| `fix_within_design`       | [[debug-dont-redesign]]                                                                              | Redesigning during debugging                    |
| `follow_literally`        | [[explicit-instructions-override]]                                                                   | Interpreting user instructions                  |
| `critic_review`           | [[mandatory-second-opinion]]                                                                         | Presenting plans without review                 |
| `use_todowrite`           | [[todowrite-vs-persistent-tasks]]                                                                    | Losing track of steps                           |
| `criteria_gate`           | [[acceptance-criteria-own-success]], [[no-promises-without-instructions]], [[edit-source-run-setup]] | Missing acceptance criteria                     |
| `capture_insights`        | [[semantic-vs-episodic-storage]]                                                                     | Losing discoveries (bd for ops, remember for knowledge) |
| `zero_friction_capture`   | [[action-over-clarification]]                                                                        | Asking questions on exploratory ideas instead of capturing |

### Task Type → Guardrail Mapping

| Task Type   | Guardrails Applied                                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------------------------- |
| `framework` | framework_gate, verify_before_complete, require_skill:framework, plan_mode, critic_review, criteria_gate, use_todowrite, capture_insights |
| `cc_hook`   | verify_before_complete, require_skill:plugin-dev:hook-development, plan_mode, criteria_gate, use_todowrite                |
| `cc_mcp`    | verify_before_complete, require_skill:plugin-dev:mcp-integration, plan_mode, criteria_gate, use_todowrite                 |
| `debug`     | verify_before_complete, quote_errors_exactly, fix_within_design, criteria_gate, use_todowrite, capture_insights           |
| `feature`   | verify_before_complete, require_acceptance_test, criteria_gate, use_todowrite, capture_insights                           |
| `python`    | verify_before_complete, require_skill:python-dev, require_acceptance_test, criteria_gate, use_todowrite                   |
| `question`  | answer_only                                                                                                               |
| `persist`   | require_skill:remember                                                                                                    |
| `analysis`  | require_skill:analyst, criteria_gate, use_todowrite, capture_insights                                                     |
| `review`    | verify_before_complete, use_todowrite, capture_insights                                                                   |
| `simple`    | verify_before_complete, criteria_gate                                                                                     |

## Periodic Compliance (Custodiet)

The custodiet hook (`hooks/custodiet_gate.py`) provides periodic semantic compliance checking via [[ultra-vires-custodiet]].

### Mechanism

| Parameter              | Value                              | Description                              |
| ---------------------- | ---------------------------------- | ---------------------------------------- |
| `TOOL_CALL_THRESHOLD`  | 7 (2 for debug)                    | Full compliance check every N tool calls |
| `REMINDER_PROBABILITY` | 0.3                                | 30% chance of reminder between checks    |
| Skip tools             | Read, Glob, Grep, memory retrieval | Don't count passive reads                |

### Compliance Check (Threshold)

At threshold, spawns haiku subagent to review session transcript for:

- Axiom violations ([[fail-fast-code]], [[verify-first]], [[acceptance-criteria-own-success]])
- Heuristic violations ([[verification-before-assertion]], [[explicit-instructions-override]], [[questions-require-answers]])
- Drift patterns (scope creep, plan deviation)
- Insight capture (advisory) - flags when discoveries aren't persisted to bd or remember skill

Uses `decision: "block"` output format to force agent attention. Insight capture is advisory only (no block).

### Random Reminders (Between Checks)

Between threshold checks, randomly injects soft reminders from `hooks/data/reminders.txt`.

**Soft-tissue file**: Edit `reminders.txt` to add/modify reminders. One per line, `#` for comments.

Uses passive `additionalContext` format - agent may proceed without addressing.

## Path Protection (Deny Rules)

| Category         | Pattern                                       | Blocked Tools           | Purpose                    | Axiom                        |
| ---------------- | --------------------------------------------- | ----------------------- | -------------------------- | ---------------------------- |
| Claude config    | `~/.claude/*.json`                            | Read, Write, Edit, Bash | Protect secrets            | [[data-boundaries]]          |
| Claude runtime   | `~/.claude/{hooks,skills,commands,agents}/**` | Write, Edit, Bash       | Force edits via `$AOPS/`   | [[skills-are-read-only]]     |
| Research records | `**/tja/records/**`, `**/tox/records/**`      | Write, Edit, Bash       | Research data immutable    | [[research-data-immutable]]  |
| Session state    | `/tmp/claude-session/**`                      | Write, Edit, Bash       | Hydration gate enforcement | Mechanical trigger integrity |
| Task indices     | `**/data/tasks/*.json`                        | Read, Bash              | Enforce MCP server usage   | [[just-in-time-context]]     |

**Note**: Reading `~/.claude/hooks/**` etc IS allowed (skill invocation needs it).

**Note**: Task JSON files (index.json, id_mapping.json) must be queried via tasks MCP server (list_tasks, search_tasks, get_task_tree, etc.) to prevent token bloat from reading large files directly.

## API Validation (Tasks MCP Server)

| Rule                         | API          | Validation                                            | Override      | Reference                |
| ---------------------------- | ------------ | ----------------------------------------------------- | ------------- | ------------------------ |
| Parent task completion guard | complete_task | Reject if task has incomplete children (not done/cancelled) | `force=True` | [[aops-45392b53]] |

**Note**: Technical enforcement prevents accidental premature completion. Agents must either complete children first or explicitly override with force flag.

## Task-Gated Permissions (PreToolUse Hook)

Destructive operations require an active task binding. See [[specs/permission-model-v1]].

| Operation Type | Tool | Requires Task | Bypass |
|----------------|------|---------------|--------|
| File creation/modification | Write, Edit, NotebookEdit | Yes | `.` prefix, subagent |
| Destructive Bash | `rm`, `mv`, `git commit`, etc. | Yes | `.` prefix, subagent |
| Read-only | Read, Glob, Grep, `git status` | No | N/A |
| Task operations | create_task, update_task | No (they establish binding) | N/A |

**Enforcement**: `task_required_gate.py` PreToolUse hook (currently in WARN mode, BLOCK mode planned).

**Binding flow**:
1. Hydrator guides: "claim existing or create new task"
2. Agent calls `update_task(status="active")` or `create_task(...)`
3. `task_binding.py` PostToolUse hook sets `current_task` in session state
4. `task_required_gate.py` allows destructive operations

**Bypass conditions**:
- User prefix `.` (sets `gates_bypassed` flag via UserPromptSubmit)
- Subagent sessions (`CLAUDE_AGENT_TYPE` env var set)

## Pattern Blocking (PreToolUse Hook)

| Category          | Pattern             | Blocked Tools | Purpose                    | Axiom                    |
| ----------------- | ------------------- | ------------- | -------------------------- | ------------------------ |
| Doc bloat         | `*-GUIDE.md`        | Write         | Force README consolidation | [[single-purpose-files]] |
| Doc bloat         | `.md` > 200 lines   | Write         | Force chunking             | [[self-documenting]]     |
| Git: hard reset   | `git reset --hard`  | Bash          | Preserve uncommitted work  | [[fail-fast-code]]       |
| Git: clean        | `git clean -[fd]`   | Bash          | Preserve untracked files   | [[fail-fast-code]]       |
| Git: force push   | `git push --force`  | Bash          | Protect shared history     | [[fail-fast-code]]       |
| Git: checkout all | `git checkout -- .` | Bash          | Preserve local changes     | [[fail-fast-code]]       |
| Git: stash drop   | `git stash drop`    | Bash          | Preserve stashed work      | [[fail-fast-code]]       |

## Commit-Time Validation (Pre-commit)

| Category         | Hook                                      | Purpose                | Axiom                      |
| ---------------- | ----------------------------------------- | ---------------------- | -------------------------- |
| File hygiene     | trailing-whitespace, check-yaml/json/toml | Clean commits          | [[use-standard-tools]]     |
| Code quality     | shellcheck, eslint, ruff                  | Catch errors           | [[use-standard-tools]]     |
| Formatting       | dprint                                    | Consistent formatting  | [[use-standard-tools]]     |
| Data integrity   | bmem-validate                             | Valid frontmatter      | [[current-state-machine]]  |
| Data purity      | data-markdown-only                        | Only `.md` in data/    | [[current-state-machine]]  |
| Framework health | check-skill-line-count                    | SKILL.md < 500 lines   | [[self-documenting]]       |
| Framework health | check-orphan-files                        | Detect orphan files    | [[semantic-link-density]]  |
| Markdown style   | markdownlint                              | No horizontal dividers | [[no-horizontal-dividers]] |

## CI/CD Validation (GitHub Actions)

| Workflow             | Purpose                                  | Axiom                             |
| -------------------- | ---------------------------------------- | --------------------------------- |
| test-setup.yml       | Validate symlinks exist and are relative | [[fail-fast-code]]                |
| framework-health.yml | Framework health metrics and enforcement | [[maintain-relational-integrity]] |
| claude.yml           | Claude Code bot integration              | -                                 |

## Agent Tool Permissions

Main agent has all tools except deny rules. Subagents are restricted:

| Agent             | Tools Granted                                  | Model  | Purpose                 |
| ----------------- | ---------------------------------------------- | ------ | ----------------------- |
| Main agent        | All (minus deny rules)                         | varies | Primary task execution  |
| prompt-hydrator   | Read, Grep, mcp__memory__retrieve_memory, Task | haiku  | Context enrichment      |
| custodiet         | Read                                           | haiku  | Compliance checking     |
| critic            | Read                                           | opus   | Plan/conclusion review  |
| qa                | Read, Grep, Glob                               | opus   | Independent verification|
| planner           | All (inherits from main)                       | sonnet | Implementation planning |
| effectual-planner | All (inherits from main)                       | opus   | Strategic planning      |

**Note**: `tools:` in agent frontmatter RESTRICTS available tools - it cannot GRANT access beyond what settings.json allows. Deny rules apply globally.

## Knowledge Persistence

Enforcement of [[semantic-vs-episodic-storage]] and [[current-state-machine]].

| Component | Purpose | Sync to Memory Server |
|-----------|---------|----------------------|
| Remember skill | Dual-write markdown + memory server | Yes (on invocation) |
| Remember sync workflow | Reconcile markdown → memory server | Yes (repair/rebuild) |
| Session-insights | Extract and persist session learnings | Yes (Step 6.5) |

**Markdown is SSoT** - Memory server is derivative index for semantic search.

**Insight capture flow**:
- Operational findings → bd issues
- Knowledge discoveries → `Skill(skill="remember")` → markdown + memory
- Session learnings → `/session-insights` → JSON + memory

## Task Assignment Convention

Context injected via CORE.md at SessionStart.

| Assignment | Tag | Purpose |
|------------|-----|---------|
| Bot/agent work | `tags: ["bot"]` | Automated tasks for agent execution |
| Human/user work | `tags: ["human"]` | Manual tasks requiring user action |

**Rule**: Use tags for task assignment, not the `context` field.

**Enforcement**: Prompt-level (CORE.md). No mechanical gate.

## File Location Conventions

Context injected via CORE.md at SessionStart. Guides where agents place files.

| Content Type | Location | Example |
|-------------|----------|---------|
| aops feature specs | `$AOPS/specs/` | `$AOPS/specs/task-graph-network-v1.0.md` |
| User knowledge/designs | `$ACA_DATA/designs/` | `$ACA_DATA/designs/my-project-design.md` |
| Generated outputs | `$ACA_DATA/outputs/` | `$ACA_DATA/outputs/task-viz.excalidraw` |

**Enforcement**: Prompt-level (CORE.md). No mechanical gate.

## Source Files

| Mechanism        | Authoritative Source                                                            |
| ---------------- | ------------------------------------------------------------------------------- |
| Deny rules       | `$AOPS/config/claude/settings.json` → `permissions.deny`                        |
| Agent tools      | `$AOPS/agents/*.md` → `tools:` frontmatter                                      |
| PreToolUse       | `$AOPS/hooks/hydration_gate.py`, `task_required_gate.py`, `policy_enforcer.py`  |
| PostToolUse      | `$AOPS/hooks/fail_fast_watchdog.py`, `autocommit_state.py`, `custodiet_gate.py` |
| UserPromptSubmit | `$AOPS/hooks/user_prompt_submit.py`                                             |
| SessionStart     | `$AOPS/hooks/sessionstart_load_axioms.py`                                       |
| Stop             | `$AOPS/hooks/session_reflect.py`                                                |
| Pre-commit       | `~/writing/.pre-commit-config.yaml`                                             |
| CI/CD            | `$AOPS/.github/workflows/`                                                      |
| Remember skill   | `$AOPS/aops-core/skills/remember/SKILL.md`                                      |
| Memory sync      | `$AOPS/aops-core/skills/remember/workflows/sync.md`                             |
| Session insights | `$AOPS/aops-core/skills/session-insights/SKILL.md`                              |
