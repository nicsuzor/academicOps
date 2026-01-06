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

| Axiom | Rule | Enforcement | Point | Level |
|-------|------|-------------|-------|-------|
| A#0 | No Other Truths | AXIOMS.md injection | SessionStart | Prompt |
| A#1 | Categorical Imperative | prompt-hydrator suggests skills | UserPromptSubmit | Soft Gate |
| A#2 | Don't Make Shit Up | AXIOMS.md | SessionStart | Prompt |
| A#3 | Always Cite Sources | AXIOMS.md | SessionStart | Prompt |
| A#4 | Do One Thing | TodoWrite visibility, custodiet drift detection | During execution | Observable, Soft Gate |
| A#5 | Data Boundaries | settings.json deny rules | PreToolUse | Hard Gate |
| A#6 | Project Independence | AXIOMS.md | SessionStart | Prompt |
| A#7 | Fail-Fast (Code) | policy_enforcer.py blocks destructive git | PreToolUse | Hard Gate |
| A#8 | Fail-Fast (Agents) | fail_fast_watchdog.py injects reminder | PostToolUse | Soft Gate |
| A#9 | Self-Documenting | policy_enforcer.py blocks *-GUIDE.md | PreToolUse | Hard Gate |
| A#10 | Single-Purpose Files | policy_enforcer.py 200-line limit | PreToolUse | Hard Gate |
| A#11 | DRY, Modular, Explicit | AXIOMS.md | SessionStart | Prompt |
| A#12 | Use Standard Tools | pyproject.toml, pre-commit | Config | Convention |
| A#13 | Always Dogfooding | AXIOMS.md | SessionStart | Prompt |
| A#14 | Skills are Read-Only | settings.json denies skill writes | PreToolUse | Hard Gate |
| A#15 | Trust Version Control | policy_enforcer.py blocks backup patterns | PreToolUse | Hard Gate |
| A#16 | No Workarounds | fail_fast_watchdog.py | PostToolUse | Soft Gate |
| A#17 | Verify First | TodoWrite checkpoint | During execution | Observable |
| A#18 | No Excuses | AXIOMS.md | SessionStart | Prompt |
| A#19 | Write for Long Term | AXIOMS.md | SessionStart | Prompt |
| A#20 | Relational Integrity | wikilink conventions | Pre-commit (planned) | Convention |
| A#21 | Nothing Is Someone Else's | AXIOMS.md | SessionStart | Prompt |
| A#22 | Acceptance Criteria Own Success | /qa skill enforcement | Stop | Soft Gate |
| A#23 | Plan-First Development | EnterPlanMode tool | Before coding | Hard Gate |
| A#24 | Research Data Immutable | settings.json denies records/** | PreToolUse | Hard Gate |
| A#25 | Just-In-Time Context | sessionstart_load_axioms.py | SessionStart | Automatic |
| A#26 | Minimal Instructions | policy_enforcer.py 200-line limit | PreToolUse | Hard Gate |
| A#27 | Feedback Loops | AXIOMS.md | SessionStart | Prompt |
| A#28 | Current State Machine | autocommit_state.py (auto-commit+push) | PostToolUse | Soft Gate |
| A#29 | One Spec Per Feature | AXIOMS.md | SessionStart | Prompt |

## Heuristic → Enforcement Mapping

| Heuristic | Rule | Enforcement | Point | Level |
|-----------|------|-------------|-------|-------|
| H#1 | Skill Invocation Framing | prompt-hydrator guidance | UserPromptSubmit | Soft Gate |
| H#2 | Skill-First Action | prompt-hydrator suggests skills | UserPromptSubmit | Soft Gate |
| H#3 | Verification Before Assertion | session_reflect.py detection, custodiet periodic check | Stop, PostToolUse | Detection, Soft Gate |
| H#4 | Explicit Instructions Override | HEURISTICS.md, custodiet periodic check | SessionStart, PostToolUse | Prompt, Soft Gate |
| H#5 | Error Messages Primary Evidence | HEURISTICS.md | SessionStart | Prompt |
| H#6 | Context Uncertainty Favors Skills | prompt-hydrator guidance | UserPromptSubmit | Soft Gate |
| H#7 | Link, Don't Repeat | HEURISTICS.md | SessionStart | Prompt |
| H#8 | Avoid Namespace Collisions | HEURISTICS.md | SessionStart | Prompt |
| H#9 | Skills No Dynamic Content | settings.json denies skill writes | PreToolUse | Hard Gate |
| H#10 | Light Instructions via Reference | HEURISTICS.md | SessionStart | Prompt |
| H#11 | No Promises Without Instructions | HEURISTICS.md | SessionStart | Prompt |
| H#12 | Semantic Search Over Keyword | HEURISTICS.md | SessionStart | Prompt |
| H#13 | Edit Source, Run Setup | HEURISTICS.md | SessionStart | Prompt |
| H#14 | Mandatory Second Opinion | planner agent invokes critic | Planning | Soft Gate |
| H#15 | Streamlit Hot Reloads | HEURISTICS.md | SessionStart | Prompt |
| H#16 | Use AskUserQuestion | HEURISTICS.md | SessionStart | Prompt |
| H#17 | Check Skill Conventions | HEURISTICS.md | SessionStart | Prompt |
| H#18 | Distinguish Script vs LLM | HEURISTICS.md | SessionStart | Prompt |
| H#19 | Questions Need Answers First | HEURISTICS.md, custodiet periodic check | SessionStart, PostToolUse | Prompt, Soft Gate |
| H#20 | Critical Thinking Over Compliance | HEURISTICS.md | SessionStart | Prompt |
| H#21 | Core-First Expansion | HEURISTICS.md | SessionStart | Prompt |
| H#22 | Indices Before Exploration | HEURISTICS.md | SessionStart | Prompt |
| H#23 | Synthesize After Resolution | HEURISTICS.md | SessionStart | Prompt |
| H#24 | Ship Scripts, Don't Inline | HEURISTICS.md | SessionStart | Prompt |
| H#25 | User-Centric Acceptance | HEURISTICS.md | SessionStart | Prompt |
| H#26 | Semantic vs Episodic Storage | HEURISTICS.md | SessionStart | Prompt |
| H#27 | Debug, Don't Redesign | HEURISTICS.md | SessionStart | Prompt |
| H#28 | Mandatory Acceptance Testing | /qa skill | Stop | Soft Gate |
| H#29 | TodoWrite vs Persistent Tasks | HEURISTICS.md | SessionStart | Prompt |
| H#30 | Design-First | HEURISTICS.md | SessionStart | Prompt |
| H#31 | No LLM Calls in Hooks | HEURISTICS.md | SessionStart | Prompt |
| H#32 | Delete, Don't Deprecate | HEURISTICS.md | SessionStart | Prompt |
| H#33 | Real Data Fixtures | HEURISTICS.md | SessionStart | Prompt |
| H#34 | Semantic Link Density | check_orphan_files.py | Pre-commit | Detection |
| H#35 | Spec-First File Modification | HEURISTICS.md | SessionStart | Prompt |
| H#36 | File Category Classification | check_file_taxonomy.py | Pre-commit | Detection |
| H#37 | LLM Semantic Evaluation | PR template checklist, critic agent | PR Review | Review |
| H#37a | Full Evidence for Validation | @pytest.mark.demo requirement | Test design | Convention |
| H#37b | Real Fixtures Over Contrived | docs/testing-patterns.md | Test design | Convention |
| H#37c | Execution Over Inspection | framework skill compliance protocol | Skill invocation | Prompt |

## Enforcement Level Summary

| Level | Count | Description |
|-------|-------|-------------|
| Hard Gate | 10 | Blocks action (PreToolUse hooks, deny rules) |
| Soft Gate | 8 | Injects guidance, agent can proceed |
| Prompt | 43 | Instructional (AXIOMS.md or HEURISTICS.md at SessionStart) |
| Observable | 2 | Creates visible artifact (TodoWrite) |
| Detection | 3 | Logs for post-hoc analysis |
| Review | 1 | Human/LLM review at PR time |
| Convention | 3 | Documented pattern, no mechanical check |
| Config | 1 | External tool config (pyproject.toml, pre-commit) |

**Note**: "Prompt" level rules are injected at session start via `sessionstart_load_axioms.py`. Agents receive them automatically but compliance is not mechanically enforced.

---

## Soft Gate Guardrails (Prompt Hydration)

These guardrails are applied by [[specs/prompt-hydration]] based on task classification. Each maps to a heuristic and defines when/how to apply it.

### Guardrail Registry

| Guardrail | Heuristic | Failure Prevented | Instruction |
|-----------|-----------|-------------------|-------------|
| `verify_before_complete` | H3 | Claiming success without checking | "VERIFY actual state before claiming complete" |
| `answer_only` | H19 | Jumping to implementation when asked a question | "Answer, then STOP" |
| `require_skill` | H2 | Skipping skill for domain work | "Invoke Skill first" |
| `plan_mode` | A#23 | Framework changes without approval | "Enter Plan Mode first" |
| `require_acceptance_test` | H28 | Claiming complete without e2e test | "TodoWrite MUST include verification" |
| `quote_errors_exactly` | H5 | Paraphrasing errors | "Quote error messages EXACTLY" |
| `fix_within_design` | H27 | Redesigning during debugging | "Fix within current architecture" |
| `follow_literally` | H4 | Interpreting user instructions | "Follow instructions LITERALLY" |
| `critic_review` | H14 | Presenting plans without review | "Invoke critic before presenting" |
| `use_todowrite` | H29 | Losing track of steps | "Create TodoWrite to track progress" |
| `criteria_gate` | A#23, H25, H28 | Implementing without acceptance criteria | "Define criteria first (hard gate)" |

### Task Type → Guardrail Mapping

| Task Type | Guardrails Applied |
|-----------|-------------------|
| `framework` | verify_before_complete, require_skill:framework, plan_mode, critic_review, criteria_gate, use_todowrite |
| `cc_hook` | verify_before_complete, require_skill:plugin-dev:hook-development, plan_mode, criteria_gate, use_todowrite |
| `cc_mcp` | verify_before_complete, require_skill:plugin-dev:mcp-integration, plan_mode, criteria_gate, use_todowrite |
| `debug` | verify_before_complete, quote_errors_exactly, fix_within_design, criteria_gate, use_todowrite |
| `feature` | verify_before_complete, require_acceptance_test, criteria_gate, use_todowrite |
| `python` | verify_before_complete, require_skill:python-dev, require_acceptance_test, criteria_gate, use_todowrite |
| `question` | answer_only |
| `persist` | require_skill:remember |
| `analysis` | require_skill:analyst, criteria_gate, use_todowrite |
| `review` | verify_before_complete, use_todowrite |
| `simple` | verify_before_complete, criteria_gate |

---

## Periodic Compliance (Custodiet)

The custodiet hook (`hooks/custodiet.py`) provides periodic semantic compliance checking via [[specs/ultra-vires-custodiet]].

### Mechanism

| Parameter | Value | Description |
|-----------|-------|-------------|
| `TOOL_CALL_THRESHOLD` | 7 (2 for debug) | Full compliance check every N tool calls |
| `REMINDER_PROBABILITY` | 0.3 | 30% chance of reminder between checks |
| Skip tools | Read, Glob, Grep, memory retrieval | Don't count passive reads |

### Compliance Check (Threshold)

At threshold, spawns haiku subagent to review session transcript for:
- Axiom violations (A#7 Fail-Fast, A#17 Verify First, A#22 Acceptance Criteria)
- Heuristic violations (H3 Verification, H4 Explicit Instructions, H19 Questions)
- Drift patterns (scope creep, plan deviation)

Uses `decision: "block"` output format to force agent attention.

### Random Reminders (Between Checks)

Between threshold checks, randomly injects soft reminders from `hooks/data/reminders.txt`.

**Soft-tissue file**: Edit `reminders.txt` to add/modify reminders. One per line, `#` for comments.

Uses passive `additionalContext` format - agent may proceed without addressing.

---

## Path Protection (Deny Rules)

| Category | Pattern | Blocked Tools | Purpose | Axiom |
|----------|---------|---------------|---------|-------|
| Task files | `**/data/tasks/**` | Write, Edit, Bash | Force `/tasks` skill | A#1 |
| Claude config | `~/.claude/*.json` | Read, Write, Edit, Bash | Protect secrets | A#5 |
| Claude runtime | `~/.claude/{hooks,skills,commands,agents}/**` | Write, Edit, Bash | Force edits via `$AOPS/` | A#14 |
| Research records | `**/tja/records/**`, `**/tox/records/**` | Write, Edit, Bash | Research data immutable | A#24 |

**Note**: Reading `~/.claude/hooks/**` etc IS allowed (skill invocation needs it).

## Pattern Blocking (PreToolUse Hook)

| Category | Pattern | Blocked Tools | Purpose | Axiom |
|----------|---------|---------------|---------|-------|
| Doc bloat | `*-GUIDE.md` | Write | Force README consolidation | A#9, A#26 |
| Doc bloat | `.md` > 200 lines | Write | Force chunking | A#10, A#26 |
| Git: hard reset | `git reset --hard` | Bash | Preserve uncommitted work | A#7, A#15 |
| Git: clean | `git clean -[fd]` | Bash | Preserve untracked files | A#7, A#15 |
| Git: force push | `git push --force` | Bash | Protect shared history | A#7, A#15 |
| Git: checkout all | `git checkout -- .` | Bash | Preserve local changes | A#7, A#15 |
| Git: stash drop | `git stash drop` | Bash | Preserve stashed work | A#7, A#15 |

## Commit-Time Validation (Pre-commit)

| Category | Hook | Purpose | Axiom |
|----------|------|---------|-------|
| File hygiene | trailing-whitespace, check-yaml/json/toml | Clean commits | A#12 |
| Code quality | shellcheck, eslint, ruff | Catch errors | A#12 |
| Formatting | dprint | Consistent formatting | A#12 |
| Data integrity | bmem-validate | Valid frontmatter | A#28 |
| Data purity | data-markdown-only | Only `.md` in data/ | A#28 |
| Framework health | check-skill-line-count | SKILL.md < 500 lines | A#10, A#26 |
| Framework health | check-orphan-files | Detect orphan files | H#34 |

## CI/CD Validation (GitHub Actions)

| Workflow | Purpose | Axiom |
|----------|---------|-------|
| test-setup.yml | Validate symlinks exist and are relative | A#7 |
| framework-health.yml | Framework health metrics and enforcement | A#20 |
| claude.yml | Claude Code bot integration | - |

---

## Source Files

| Mechanism | Authoritative Source |
|-----------|---------------------|
| Deny rules | `$AOPS/config/claude/settings.json` → `permissions.deny` |
| PreToolUse | `$AOPS/hooks/policy_enforcer.py` |
| PostToolUse | `$AOPS/hooks/fail_fast_watchdog.py`, `autocommit_state.py`, `custodiet.py` |
| UserPromptSubmit | `$AOPS/hooks/user_prompt_submit.py` |
| SessionStart | `$AOPS/hooks/sessionstart_load_axioms.py` |
| Stop | `$AOPS/hooks/session_reflect.py` |
| Pre-commit | `~/writing/.pre-commit-config.yaml` |
| CI/CD | `$AOPS/.github/workflows/` |
