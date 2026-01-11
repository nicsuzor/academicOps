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

| Axiom                                               | Rule                                      | Enforcement                     | Point                                           | Level                |
| --------------------------------------------------- | ----------------------------------------- | ------------------------------- | ----------------------------------------------- | -------------------- |
| [[axioms/no-other-truths.md                         | no-other-truths]]                         | No Other Truths                 | AXIOMS.md injection                             | SessionStart         |
| [[axioms/categorical-imperative.md                  | categorical-imperative]]                  | Categorical Imperative          | prompt-hydrator suggests skills                 | UserPromptSubmit     |
| [[axioms/dont-make-shit-up.md                       | dont-make-shit-up]]                       | Don't Make Shit Up              | AXIOMS.md                                       | SessionStart         |
| [[axioms/always-cite-sources.md                     | always-cite-sources]]                     | Always Cite Sources             | AXIOMS.md                                       | SessionStart         |
| [[axioms/do-one-thing.md                            | do-one-thing]]                            | Do One Thing                    | TodoWrite visibility, custodiet drift detection | During execution     |
| [[axioms/data-boundaries.md                         | data-boundaries]]                         | Data Boundaries                 | settings.json deny rules                        | PreToolUse           |
| [[axioms/project-independence.md                    | project-independence]]                    | Project Independence            | AXIOMS.md                                       | SessionStart         |
| [[axioms/fail-fast-code.md                          | fail-fast-code]]                          | Fail-Fast (Code)                | policy_enforcer.py blocks destructive git       | PreToolUse           |
| [[axioms/fail-fast-agents.md                        | fail-fast-agents]]                        | Fail-Fast (Agents)              | fail_fast_watchdog.py injects reminder          | PostToolUse          |
| [[axioms/self-documenting.md                        | self-documenting]]                        | Self-Documenting                | policy_enforcer.py blocks *-GUIDE.md            | PreToolUse           |
| [[axioms/single-purpose-files.md                    | single-purpose-files]]                    | Single-Purpose Files            | policy_enforcer.py 200-line limit               | PreToolUse           |
| [[axioms/dry-modular-explicit.md                    | dry-modular-explicit]]                    | DRY, Modular, Explicit          | AXIOMS.md                                       | SessionStart         |
| [[axioms/use-standard-tools.md                      | use-standard-tools]]                      | Use Standard Tools              | pyproject.toml, pre-commit                      | Config               |
| [[axioms/always-dogfooding.md                       | always-dogfooding]]                       | Always Dogfooding               | AXIOMS.md                                       | SessionStart         |
| [[axioms/skills-are-read-only.md                    | skills-are-read-only]]                    | Skills are Read-Only            | settings.json denies skill writes               | PreToolUse           |
| [[axioms/trust-version-control.md                   | trust-version-control]]                   | Trust Version Control           | policy_enforcer.py blocks backup patterns       | PreToolUse           |
| [[axioms/no-workarounds.md                          | no-workarounds]]                          | No Workarounds                  | fail_fast_watchdog.py                           | PostToolUse          |
| [[axioms/verify-first.md                            | verify-first]]                            | Verify First                    | TodoWrite checkpoint                            | During execution     |
| [[axioms/no-excuses.md                              | no-excuses]]                              | No Excuses                      | AXIOMS.md                                       | SessionStart         |
| [[axioms/write-for-long-term.md                     | write-for-long-term]]                     | Write for Long Term             | AXIOMS.md                                       | SessionStart         |
| [[axioms/maintain-relational-integrity.md           | maintain-relational-integrity]]           | Relational Integrity            | wikilink conventions                            | Pre-commit (planned) |
| [[axioms/nothing-is-someone-elses-responsibility.md | nothing-is-someone-elses-responsibility]] | Nothing Is Someone Else's       | AXIOMS.md                                       | SessionStart         |
| [[axioms/acceptance-criteria-own-success.md         | acceptance-criteria-own-success]]         | Acceptance Criteria Own Success | /qa skill enforcement                           | Stop                 |
| [[axioms/plan-first-development.md                  | plan-first-development]]                  | Plan-First Development          | EnterPlanMode tool                              | Before coding        |
| [[axioms/research-data-immutable.md                 | research-data-immutable]]                 | Research Data Immutable         | settings.json denies records/**                 | PreToolUse           |
| [[axioms/just-in-time-context.md                    | just-in-time-context]]                    | Just-In-Time Context            | sessionstart_load_axioms.py                     | SessionStart         |
| [[axioms/minimal-instructions.md                    | minimal-instructions]]                    | Minimal Instructions            | policy_enforcer.py 200-line limit               | PreToolUse           |
| [[axioms/feedback-loops-for-uncertainty.md          | feedback-loops-for-uncertainty]]          | Feedback Loops                  | AXIOMS.md                                       | SessionStart         |
| [[axioms/current-state-machine.md                   | current-state-machine]]                   | Current State Machine           | autocommit_state.py (auto-commit+push)          | PostToolUse          |
| [[axioms/one-spec-per-feature.md                    | one-spec-per-feature]]                    | One Spec Per Feature            | AXIOMS.md                                       | SessionStart         |

## Heuristic → Enforcement Mapping

| Heuristic                                           | Rule                                  | Enforcement                         | Point                                                  | Level                     |
| --------------------------------------------------- | ------------------------------------- | ----------------------------------- | ------------------------------------------------------ | ------------------------- |
| [[heuristics/skill-invocation-framing.md            | skill-invocation-framing]]            | Skill Invocation Framing            | prompt-hydrator guidance                               | UserPromptSubmit          |
| [[heuristics/skill-first-action.md                  | skill-first-action]]                  | Skill-First Action                  | prompt-hydrator suggests skills                        | UserPromptSubmit          |
| [[heuristics/verification-before-assertion.md       | verification-before-assertion]]       | Verification Before Assertion       | session_reflect.py detection, custodiet periodic check | Stop, PostToolUse         |
| [[heuristics/explicit-instructions-override.md      | explicit-instructions-override]]      | Explicit Instructions Override      | HEURISTICS.md, custodiet periodic check                | SessionStart, PostToolUse |
| [[heuristics/error-messages-primary-evidence.md     | error-messages-primary-evidence]]     | Error Messages Primary Evidence     | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/context-uncertainty-favors-skills.md   | context-uncertainty-favors-skills]]   | Context Uncertainty Favors Skills   | prompt-hydrator guidance                               | UserPromptSubmit          |
| [[heuristics/link-dont-repeat.md                    | link-dont-repeat]]                    | Link, Don't Repeat                  | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/avoid-namespace-collisions.md          | avoid-namespace-collisions]]          | Avoid Namespace Collisions          | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/skills-no-dynamic-content.md           | skills-no-dynamic-content]]           | Skills No Dynamic Content           | settings.json denies skill writes                      | PreToolUse                |
| [[heuristics/light-instructions-via-reference.md    | light-instructions-via-reference]]    | Light Instructions via Reference    | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/no-promises-without-instructions.md    | no-promises-without-instructions]]    | No Promises Without Instructions    | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/semantic-search-over-keyword.md        | semantic-search-over-keyword]]        | Semantic Search Over Keyword        | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/edit-source-run-setup.md               | edit-source-run-setup]]               | Edit Source, Run Setup              | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/mandatory-second-opinion.md            | mandatory-second-opinion]]            | Mandatory Second Opinion            | planner agent invokes critic                           | Planning                  |
| [[heuristics/streamlit-hot-reloads.md               | streamlit-hot-reloads]]               | Streamlit Hot Reloads               | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/use-askuserquestion.md                 | use-askuserquestion]]                 | Use AskUserQuestion                 | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/check-skill-conventions.md             | check-skill-conventions]]             | Check Skill Conventions             | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/distinguish-script-vs-llm.md           | distinguish-script-vs-llm]]           | Distinguish Script vs LLM           | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/questions-require-answers.md           | questions-require-answers]]           | Questions Need Answers First        | HEURISTICS.md, custodiet periodic check                | SessionStart, PostToolUse |
| [[heuristics/critical-thinking-over-compliance.md   | critical-thinking-over-compliance]]   | Critical Thinking Over Compliance   | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/core-first-expansion.md                | core-first-expansion]]                | Core-First Expansion                | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/indices-before-exploration.md          | indices-before-exploration]]          | Indices Before Exploration          | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/synthesize-after-resolution.md         | synthesize-after-resolution]]         | Synthesize After Resolution         | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/ship-scripts-dont-inline.md            | ship-scripts-dont-inline]]            | Ship Scripts, Don't Inline          | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/user-centric-acceptance.md             | user-centric-acceptance]]             | User-Centric Acceptance             | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/semantic-vs-episodic-storage.md        | semantic-vs-episodic-storage]]        | Semantic vs Episodic Storage        | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/debug-dont-redesign.md                 | debug-dont-redesign]]                 | Debug, Don't Redesign               | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/mandatory-acceptance-testing.md        | mandatory-acceptance-testing]]        | Mandatory Acceptance Testing        | /qa skill                                              | Stop                      |
| [[heuristics/todowrite-vs-persistent-tasks.md       | todowrite-vs-persistent-tasks]]       | TodoWrite vs Persistent Tasks       | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/design-first-not-constraint-first.md   | design-first-not-constraint-first]]   | Design-First                        | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/no-llm-calls-in-hooks.md               | no-llm-calls-in-hooks]]               | No LLM Calls in Hooks               | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/delete-dont-deprecate.md               | delete-dont-deprecate]]               | Delete, Don't Deprecate             | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/real-data-fixtures.md                  | real-data-fixtures]]                  | Real Data Fixtures                  | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/semantic-link-density.md               | semantic-link-density]]               | Semantic Link Density               | check_orphan_files.py                                  | Pre-commit                |
| [[heuristics/spec-first-file-modification.md        | spec-first-file-modification]]        | Spec-First File Modification        | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/file-category-classification.md        | file-category-classification]]        | File Category Classification        | check_file_taxonomy.py                                 | Pre-commit                |
| [[heuristics/llm-semantic-evaluation.md             | llm-semantic-evaluation]]             | LLM Semantic Evaluation             | PR template checklist, critic agent                    | PR Review                 |
| [[heuristics/full-evidence-for-validation.md        | full-evidence-for-validation]]        | Full Evidence for Validation        | @pytest.mark.demo requirement                          | Test design               |
| [[heuristics/real-fixtures-over-contrived.md        | real-fixtures-over-contrived]]        | Real Fixtures Over Contrived        | docs/testing-patterns.md                               | Test design               |
| [[heuristics/execution-over-inspection.md           | execution-over-inspection]]           | Execution Over Inspection           | framework skill compliance protocol                    | Skill invocation          |
| [[heuristics/test-failure-requires-user-decision.md | test-failure-requires-user-decision]] | Test Failure Requires User Decision | HEURISTICS.md                                          | SessionStart              |
| [[heuristics/no-horizontal-dividers.md              | no-horizontal-dividers]]              | No Horizontal Dividers              | markdownlint-cli2                                      | Pre-commit                |

## Enforcement Level Summary

| Level      | Count | Description                                                |
| ---------- | ----- | ---------------------------------------------------------- |
| Hard Gate  | 11    | Blocks action (PreToolUse hooks, deny rules, pre-commit)   |
| Soft Gate  | 8     | Injects guidance, agent can proceed                        |
| Prompt     | 43    | Instructional (AXIOMS.md or HEURISTICS.md at SessionStart) |
| Observable | 2     | Creates visible artifact (TodoWrite)                       |
| Detection  | 3     | Logs for post-hoc analysis                                 |
| Review     | 1     | Human/LLM review at PR time                                |
| Convention | 3     | Documented pattern, no mechanical check                    |
| Config     | 1     | External tool config (pyproject.toml, pre-commit)          |

**Note**: "Prompt" level rules are injected at session start via `sessionstart_load_axioms.py`. Agents receive them automatically but compliance is not mechanically enforced.

## Soft Gate Guardrails (Prompt Hydration)

These guardrails are applied by [[specs/prompt-hydration]] based on task classification. Each maps to a heuristic and defines when/how to apply it.

### Guardrail Registry

| Guardrail                 | Heuristic                                       | Failure Prevented                                                                   | Instruction                                                               |
| ------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `verify_before_complete`  | [[heuristics/verification-before-assertion.md   | verification-before-assertion]]                                                     | Claiming success without checking                                         |
| `answer_only`             | [[heuristics/questions-require-answers.md       | questions-require-answers]]                                                         | Jumping to implementation when asked a question                           |
| `require_skill`           | [[heuristics/skill-first-action.md              | skill-first-action]]                                                                | Skipping skill for domain work                                            |
| `plan_mode`               | [[axioms/plan-first-development.md              | plan-first-development]]                                                            | Framework changes without approval                                        |
| `require_acceptance_test` | [[heuristics/mandatory-acceptance-testing.md    | mandatory-acceptance-testing]]                                                      | Claiming complete without e2e test                                        |
| `quote_errors_exactly`    | [[heuristics/error-messages-primary-evidence.md | error-messages-primary-evidence]]                                                   | Paraphrasing errors                                                       |
| `fix_within_design`       | [[heuristics/debug-dont-redesign.md             | debug-dont-redesign]]                                                               | Redesigning during debugging                                              |
| `follow_literally`        | [[heuristics/explicit-instructions-override.md  | explicit-instructions-override]]                                                    | Interpreting user instructions                                            |
| `critic_review`           | [[heuristics/mandatory-second-opinion.md        | mandatory-second-opinion]]                                                          | Presenting plans without review                                           |
| `use_todowrite`           | [[heuristics/todowrite-vs-persistent-tasks.md   | todowrite-vs-persistent-tasks]]                                                     | Losing track of steps                                                     |
| `criteria_gate`           | [[axioms/acceptance-criteria-own-success.md     | acceptance-criteria-own-success]], [[heuristics/no-promises-without-instructions.md | no-promises-without-instructions]], [[heuristics/edit-source-run-setup.md |

### Task Type → Guardrail Mapping

| Task Type   | Guardrails Applied                                                                                         |
| ----------- | ---------------------------------------------------------------------------------------------------------- |
| `framework` | verify_before_complete, require_skill:framework, plan_mode, critic_review, criteria_gate, use_todowrite    |
| `cc_hook`   | verify_before_complete, require_skill:plugin-dev:hook-development, plan_mode, criteria_gate, use_todowrite |
| `cc_mcp`    | verify_before_complete, require_skill:plugin-dev:mcp-integration, plan_mode, criteria_gate, use_todowrite  |
| `debug`     | verify_before_complete, quote_errors_exactly, fix_within_design, criteria_gate, use_todowrite              |
| `feature`   | verify_before_complete, require_acceptance_test, criteria_gate, use_todowrite                              |
| `python`    | verify_before_complete, require_skill:python-dev, require_acceptance_test, criteria_gate, use_todowrite    |
| `question`  | answer_only                                                                                                |
| `persist`   | require_skill:remember                                                                                     |
| `analysis`  | require_skill:analyst, criteria_gate, use_todowrite                                                        |
| `review`    | verify_before_complete, use_todowrite                                                                      |
| `simple`    | verify_before_complete, criteria_gate                                                                      |

## Periodic Compliance (Custodiet)

The custodiet hook (`hooks/custodiet_gate.py`) provides periodic semantic compliance checking via [[specs/ultra-vires-custodiet]].

### Mechanism

| Parameter              | Value                              | Description                              |
| ---------------------- | ---------------------------------- | ---------------------------------------- |
| `TOOL_CALL_THRESHOLD`  | 7 (2 for debug)                    | Full compliance check every N tool calls |
| `REMINDER_PROBABILITY` | 0.3                                | 30% chance of reminder between checks    |
| Skip tools             | Read, Glob, Grep, memory retrieval | Don't count passive reads                |

### Compliance Check (Threshold)

At threshold, spawns haiku subagent to review session transcript for:

- Axiom violations ([[axioms/fail-fast-code.md|fail-fast-code]], [[axioms/verify-first.md|verify-first]], [[axioms/acceptance-criteria-own-success.md|acceptance-criteria-own-success]])
- Heuristic violations ([[heuristics/verification-before-assertion.md|verification-before-assertion]], [[heuristics/explicit-instructions-override.md|explicit-instructions-override]], [[heuristics/questions-require-answers.md|questions-require-answers]])
- Drift patterns (scope creep, plan deviation)

Uses `decision: "block"` output format to force agent attention.

### Random Reminders (Between Checks)

Between threshold checks, randomly injects soft reminders from `hooks/data/reminders.txt`.

**Soft-tissue file**: Edit `reminders.txt` to add/modify reminders. One per line, `#` for comments.

Uses passive `additionalContext` format - agent may proceed without addressing.

## Path Protection (Deny Rules)

| Category         | Pattern                                       | Blocked Tools           | Purpose                  | Axiom                               |
| ---------------- | --------------------------------------------- | ----------------------- | ------------------------ | ----------------------------------- |
| Task files       | `**/data/tasks/**`                            | Write, Edit, Bash       | Force `/tasks` skill     | [[axioms/categorical-imperative.md  |
| Claude config    | `~/.claude/*.json`                            | Read, Write, Edit, Bash | Protect secrets          | [[axioms/data-boundaries.md         |
| Claude runtime   | `~/.claude/{hooks,skills,commands,agents}/**` | Write, Edit, Bash       | Force edits via `$AOPS/` | [[axioms/skills-are-read-only.md    |
| Research records | `**/tja/records/**`, `**/tox/records/**`      | Write, Edit, Bash       | Research data immutable  | [[axioms/research-data-immutable.md |

**Note**: Reading `~/.claude/hooks/**` etc IS allowed (skill invocation needs it).

## Pattern Blocking (PreToolUse Hook)

| Category          | Pattern             | Blocked Tools | Purpose                    | Axiom                            |
| ----------------- | ------------------- | ------------- | -------------------------- | -------------------------------- |
| Doc bloat         | `*-GUIDE.md`        | Write         | Force README consolidation | [[axioms/single-purpose-files.md |
| Doc bloat         | `.md` > 200 lines   | Write         | Force chunking             | [[axioms/self-documenting.md     |
| Git: hard reset   | `git reset --hard`  | Bash          | Preserve uncommitted work  | [[axioms/fail-fast-code.md       |
| Git: clean        | `git clean -[fd]`   | Bash          | Preserve untracked files   | [[axioms/fail-fast-code.md       |
| Git: force push   | `git push --force`  | Bash          | Protect shared history     | [[axioms/fail-fast-code.md       |
| Git: checkout all | `git checkout -- .` | Bash          | Preserve local changes     | [[axioms/fail-fast-code.md       |
| Git: stash drop   | `git stash drop`    | Bash          | Preserve stashed work      | [[axioms/fail-fast-code.md       |

## Commit-Time Validation (Pre-commit)

| Category         | Hook                                      | Purpose                | Axiom                                  |
| ---------------- | ----------------------------------------- | ---------------------- | -------------------------------------- |
| File hygiene     | trailing-whitespace, check-yaml/json/toml | Clean commits          | [[axioms/use-standard-tools.md         |
| Code quality     | shellcheck, eslint, ruff                  | Catch errors           | [[axioms/use-standard-tools.md         |
| Formatting       | dprint                                    | Consistent formatting  | [[axioms/use-standard-tools.md         |
| Data integrity   | bmem-validate                             | Valid frontmatter      | [[axioms/current-state-machine.md      |
| Data purity      | data-markdown-only                        | Only `.md` in data/    | [[axioms/current-state-machine.md      |
| Framework health | check-skill-line-count                    | SKILL.md < 500 lines   | [[axioms/self-documenting.md           |
| Framework health | check-orphan-files                        | Detect orphan files    | [[heuristics/semantic-link-density.md  |
| Markdown style   | markdownlint                              | No horizontal dividers | [[heuristics/no-horizontal-dividers.md |

## CI/CD Validation (GitHub Actions)

| Workflow             | Purpose                                  | Axiom                                     |
| -------------------- | ---------------------------------------- | ----------------------------------------- |
| test-setup.yml       | Validate symlinks exist and are relative | [[axioms/fail-fast-code.md                |
| framework-health.yml | Framework health metrics and enforcement | [[axioms/maintain-relational-integrity.md |
| claude.yml           | Claude Code bot integration              | -                                         |

## Agent Tool Permissions

Main agent has all tools except deny rules. Subagents are restricted:

| Agent             | Tools Granted                                  | Model  | Purpose                 |
| ----------------- | ---------------------------------------------- | ------ | ----------------------- |
| Main agent        | All (minus deny rules)                         | varies | Primary task execution  |
| prompt-hydrator   | Read, Grep, mcp__memory__retrieve_memory, Task | haiku  | Context enrichment      |
| custodiet         | Read                                           | haiku  | Compliance checking     |
| critic            | Read                                           | opus   | Plan/conclusion review  |
| planner           | All (inherits from main)                       | sonnet | Implementation planning |
| effectual-planner | All (inherits from main)                       | opus   | Strategic planning      |

**Note**: `tools:` in agent frontmatter RESTRICTS available tools - it cannot GRANT access beyond what settings.json allows. Deny rules apply globally.

## Source Files

| Mechanism        | Authoritative Source                                                            |
| ---------------- | ------------------------------------------------------------------------------- |
| Deny rules       | `$AOPS/config/claude/settings.json` → `permissions.deny`                        |
| Agent tools      | `$AOPS/agents/*.md` → `tools:` frontmatter                                      |
| PreToolUse       | `$AOPS/hooks/policy_enforcer.py`                                                |
| PostToolUse      | `$AOPS/hooks/fail_fast_watchdog.py`, `autocommit_state.py`, `custodiet_gate.py` |
| UserPromptSubmit | `$AOPS/hooks/user_prompt_submit.py`                                             |
| SessionStart     | `$AOPS/hooks/sessionstart_load_axioms.py`                                       |
| Stop             | `$AOPS/hooks/session_reflect.py`                                                |
| Pre-commit       | `~/writing/.pre-commit-config.yaml`                                             |
| CI/CD            | `$AOPS/.github/workflows/`                                                      |
