---
name: rules
title: Enforcement Rules
type: reference
description: What rules are enforced, how, and evidence of effectiveness.
permalink: rules
tags: [framework, enforcement, moc]
---

# Enforcement Rules

**Purpose**: Current state of what's protected and how. For mechanism selection guidance, see [[ENFORCEMENT|docs/ENFORCEMENT.md]]. For architectural philosophy, see [[enforcement|specs/enforcement.md]].

## Axiom → Enforcement Mapping

| Axiom | Rule | Enforcement | Point | Level |
|-------|------|-------------|-------|-------|
| A#0 | No Other Truths | AXIOMS.md injection | SessionStart | Prompt |
| A#1 | Categorical Imperative | prompt-hydrator suggests skills | UserPromptSubmit | Soft Gate |
| A#2 | Don't Make Shit Up | Convention only | - | Convention |
| A#3 | Always Cite Sources | Convention only | - | Convention |
| A#4 | Do One Thing | TodoWrite visibility | During execution | Observable |
| A#5 | Data Boundaries | settings.json deny rules | PreToolUse | Hard Gate |
| A#6 | Project Independence | Convention only | - | Convention |
| A#7 | Fail-Fast (Code) | policy_enforcer.py blocks destructive git | PreToolUse | Hard Gate |
| A#8 | Fail-Fast (Agents) | fail_fast_watchdog.py injects reminder | PostToolUse | Soft Gate |
| A#9 | Self-Documenting | policy_enforcer.py blocks *-GUIDE.md | PreToolUse | Hard Gate |
| A#10 | Single-Purpose Files | policy_enforcer.py 200-line limit | PreToolUse | Hard Gate |
| A#11 | DRY, Modular, Explicit | Convention only | - | Convention |
| A#12 | Use Standard Tools | pyproject.toml, pre-commit | Config | Convention |
| A#13 | Always Dogfooding | Convention only | - | Convention |
| A#14 | Skills are Read-Only | settings.json denies skill writes | PreToolUse | Hard Gate |
| A#15 | Trust Version Control | policy_enforcer.py blocks backup patterns | PreToolUse | Hard Gate |
| A#16 | No Workarounds | fail_fast_watchdog.py | PostToolUse | Soft Gate |
| A#17 | Verify First | TodoWrite checkpoint | During execution | Observable |
| A#18 | No Excuses | Convention only | - | Convention |
| A#19 | Write for Long Term | Convention only | - | Convention |
| A#20 | Relational Integrity | wikilink conventions | Pre-commit (planned) | Convention |
| A#21 | Nothing Is Someone Else's | Convention only | - | Convention |
| A#22 | Acceptance Criteria Own Success | /qa skill enforcement | Stop | Soft Gate |
| A#23 | Plan-First Development | EnterPlanMode tool | Before coding | Hard Gate |
| A#24 | Research Data Immutable | settings.json denies records/** | PreToolUse | Hard Gate |
| A#25 | Just-In-Time Context | sessionstart_load_axioms.py | SessionStart | Automatic |
| A#26 | Minimal Instructions | policy_enforcer.py 200-line limit | PreToolUse | Hard Gate |
| A#27 | Feedback Loops | Convention only | - | Convention |
| A#28 | Current State Machine | Convention only | - | Convention |
| A#29 | One Spec Per Feature | Convention only | - | Convention |

## Heuristic → Enforcement Mapping

| Heuristic | Rule | Enforcement | Point | Level |
|-----------|------|-------------|-------|-------|
| H#1 | Skill Invocation Framing | prompt-hydrator guidance | UserPromptSubmit | Soft Gate |
| H#2 | Skill-First Action | prompt-hydrator suggests skills | UserPromptSubmit | Soft Gate |
| H#3 | Verification Before Assertion | session_reflect.py detection | Stop | Detection |
| H#4 | Explicit Instructions Override | Convention only | - | Convention |
| H#5 | Error Messages Primary Evidence | Convention only | - | Convention |
| H#6 | Context Uncertainty Favors Skills | prompt-hydrator guidance | UserPromptSubmit | Soft Gate |
| H#7 | Link, Don't Repeat | Convention only | - | Convention |
| H#8 | Avoid Namespace Collisions | Convention only | - | Convention |
| H#9 | Skills No Dynamic Content | settings.json denies skill writes | PreToolUse | Hard Gate |
| H#10 | Light Instructions via Reference | Convention only | - | Convention |
| H#11 | No Promises Without Instructions | Convention only | - | Convention |
| H#12 | Semantic Search Over Keyword | Convention only | - | Convention |
| H#13 | Edit Source, Run Setup | Convention only | - | Convention |
| H#14 | Mandatory Second Opinion | planner agent invokes critic | Planning | Soft Gate |
| H#15 | Streamlit Hot Reloads | Convention only | - | Convention |
| H#16 | Use AskUserQuestion | Convention only | - | Convention |
| H#17 | Check Skill Conventions | Convention only | - | Convention |
| H#18 | Distinguish Script vs LLM | Convention only | - | Convention |
| H#19 | Questions Need Answers First | Convention only | - | Convention |
| H#20 | Critical Thinking Over Compliance | Convention only | - | Convention |
| H#21 | Core-First Expansion | Convention only | - | Convention |
| H#22 | Indices Before Exploration | Convention only | - | Convention |
| H#23 | Synthesize After Resolution | Convention only | - | Convention |
| H#24 | Ship Scripts, Don't Inline | Convention only | - | Convention |
| H#25 | User-Centric Acceptance | Convention only | - | Convention |
| H#26 | Semantic vs Episodic Storage | Convention only | - | Convention |
| H#27 | Debug, Don't Redesign | Convention only | - | Convention |
| H#28 | Mandatory Acceptance Testing | /qa skill | Stop | Soft Gate |
| H#29 | TodoWrite vs Persistent Tasks | Convention only | - | Convention |
| H#30 | Design-First | Convention only | - | Convention |
| H#31 | No LLM Calls in Hooks | Convention only | - | Convention |
| H#32 | Delete, Don't Deprecate | Convention only | - | Convention |
| H#33 | Real Data Fixtures | Convention only | - | Convention |
| H#34 | Semantic Link Density | check_orphan_files.py | Pre-commit | Detection |

## Enforcement Level Summary

| Level | Count | Description |
|-------|-------|-------------|
| Hard Gate | 10 | Blocks action (PreToolUse hooks, deny rules) |
| Soft Gate | 8 | Injects guidance, agent can proceed |
| Observable | 2 | Creates visible artifact (TodoWrite) |
| Detection | 2 | Logs for post-hoc analysis |
| Convention | 41 | Documented, no automated checking |

**Enforcement gaps**: 41 rules rely on convention only. See GitHub Issues for enforcement design backlog.

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
| PostToolUse | `$AOPS/hooks/fail_fast_watchdog.py`, `autocommit_state.py` |
| UserPromptSubmit | `$AOPS/hooks/user_prompt_submit.py` |
| SessionStart | `$AOPS/hooks/sessionstart_load_axioms.py` |
| Stop | `$AOPS/hooks/session_reflect.py` |
| Pre-commit | `~/writing/.pre-commit-config.yaml` |
| CI/CD | `$AOPS/.github/workflows/` |
