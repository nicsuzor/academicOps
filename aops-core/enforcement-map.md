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

## Axiom Registry: Tiered Architecture

Axioms are organized into tiers, each enforced by a distinct agent personality. This section is the **manifest** — agents read it to discover which rule files to load for their context.

### Tier 1: Universal Axioms (always active)

**File**: `$AOPS/agents/enforcer.md` (canonical source; `$AOPS/AXIOMS.md` until retirement — epic task-2d73b052, subtask .8)
**Agent**: Enforcer (`aops-core/agents/enforcer.md`)
**Scope**: All work, all contexts, all platforms

Contains: P#3 (Don't Make Shit Up), P#5 (Do One Thing), P#6 (Data Boundaries), P#9 (Fail-Fast Agents), P#26 (Verify First), P#27 (No Excuses), P#30 (Nothing Is Someone Else's Responsibility), P#31 (Acceptance Criteria Own Success), P#50 (Explicit Approval), P#99 (Delegated Authority Only).

### Tier 2: Contextual Rules (activated by project context)

| Context     | File                              | Agent                          | Activates when                       |
| ----------- | --------------------------------- | ------------------------------ | ------------------------------------ |
| Academic    | `$AOPS/skills/research/axioms.md` | Academic standards enforcer    | Research, teaching, publication work |
| Development | `$AOPS/agents/dev-standards.md`   | Engineering standards enforcer | Code, infrastructure, CI/CD work     |
| Framework   | `$AOPS/agents/framework-ops.md`   | Framework operations enforcer  | Working on/within academicOps        |

### Tier 3: Heuristics (advisory)

**File**: `$AOPS/HEURISTICS.md`
**Scope**: Inform but don't block. Checked periodically by custodiet/enforcer.

### How agents consume the registry

Domain rules are embedded in the agents and skills that own them (the bazaar model). Instead of loading different rule files into a general-purpose agent based on detected context, you invoke the right specialist agent for the job:

1. **Universal axioms** (Tier 1): Always active — loaded at SessionStart for all agents via `AXIOMS.md`. The enforcer agent (`aops-core/agents/enforcer.md`) carries these axioms as core knowledge for PR review and session audits
2. **Academic rules**: Owned by the research skill (`skills/research/axioms.md`) — active when the research skill is invoked
3. **Dev rules**: Owned by the dev-standards agent (`agents/dev-standards.md`) — invoke for code planning, review, or execution
4. **Framework rules**: Owned by the framework-ops agent (`agents/framework-ops.md`) — invoke for framework development or operations

No programmatic context detection required — the right agent for the job already has its rules (P#49).

## Axiom → Enforcement Mapping

| Axiom                                       | Rule                                | Enforcement                                                                                       | Point                     | Level  |
| ------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------- | ------ |
| [[dont-make-shit-up]]                       | Don't Make Shit Up                  | AXIOMS.md                                                                                         | SessionStart              |        |
| [[always-cite-sources]]                     | Always Cite Sources                 | skills/research/axioms.md                                                                         | SessionStart              |        |
| [[do-one-thing]]                            | Do One Thing                        | TodoWrite visibility, custodiet drift detection, verbatim prompt comparison                       | During execution          |        |
| [[data-boundaries]]                         | Data Boundaries                     | settings.json deny rules                                                                          | PreToolUse                |        |
| [[project-independence]]                    | Project Independence                | HEURISTICS.md                                                                                     | SessionStart              |        |
| [[fail-fast-code]]                          | Fail-Fast (Code)                    | policy_enforcer.py blocks destructive git                                                         | PreToolUse                |        |
| [[fail-fast-code]]                          | Fail-Fast (Code) - No Fallbacks     | check_no_fallbacks.py AST visitor detects `.get(..., "")`, `.get(..., [])`, `or ""` patterns      | Pre-commit (active)       |        |
| [[fail-fast-code]]                          | Fail-Fast (Code) Analysis           | axiom_enforcer (DISABLED)                                                                         | PreToolUse                |        |
| [[fail-fast-agents]]                        | Fail-Fast (Agents)                  | fail_fast_watchdog.py injects reminder                                                            | PostToolUse               |        |
| [[self-documenting]]                        | Self-Documenting                    | policy_enforcer.py blocks *-GUIDE.md                                                              | PreToolUse                |        |
| [[single-purpose-files]]                    | Single-Purpose Files                | policy_enforcer.py 200-line limit                                                                 | PreToolUse                |        |
| [[dry-modular-explicit]]                    | DRY, Modular, Explicit              | agents/dev-standards.md                                                                           | SessionStart              |        |
| [[use-standard-tools]]                      | Use Standard Tools                  | pyproject.toml, pre-commit                                                                        | Config                    |        |
| [[always-dogfooding]]                       | Always Dogfooding                   | agents/framework-ops.md                                                                           | SessionStart              |        |
| [[skills-are-read-only]]                    | Skills are Read-Only                | settings.json denies skill writes                                                                 | PreToolUse                |        |
| [[trust-version-control]]                   | Trust Version Control               | policy_enforcer.py blocks backup patterns                                                         | PreToolUse                |        |
| [[no-workarounds]]                          | No Workarounds                      | fail_fast_watchdog.py                                                                             | PostToolUse               |        |
| [[verify-first]]                            | Verify First                        | TodoWrite checkpoint                                                                              | During execution          |        |
| [[verify-first]]                            | Verify Push Target                  | AXIOMS.md corollary: explicit refspec for git push                                                | Before git push           | 1c     |
| [[trust-version-control]]                   | Always File PR                      | agents/dev-standards.md P#24 corollary: commit → push → PR. Never leave work uncommitted.         | Stop                      | 1c     |
| [[verify-first]]                            | Write-Without-Read Check            | axiom_enforcer (DISABLED)                                                                         | PreToolUse                |        |
| [[verify-first]], [[dont-make-shit-up]]     | Check Existing Automation First     | Instruction injection (check .github/workflows/ before manual execution)                          | UserPromptSubmit          | 1c     |
| [[verify-first]]                            | Primary Evidence Before Conclusions | AXIOMS.md P#26 corollary (read all comments/reviews/logs before concluding)                       | SessionStart              | 1a     |
| [[no-excuses]]                              | No Excuses                          | AXIOMS.md                                                                                         | SessionStart              |        |
| [[write-for-long-term]]                     | Write for Long Term                 | HEURISTICS.md                                                                                     | SessionStart              |        |
| [[maintain-relational-integrity]]           | Relational Integrity                | check_framework_integrity.py (index wikilinks, skill entries, workflow length)                    | Pre-commit (active)       |        |
| [[nothing-is-someone-elses-responsibility]] | Nothing Is Someone Else's           | AXIOMS.md                                                                                         | SessionStart              |        |
| [[acceptance-criteria-own-success]]         | Acceptance Criteria Own Success     | /qa skill (on-demand)                                                                             | Stop                      |        |
| [[plan-first-development]]                  | Plan-First Development              | EnterPlanMode tool                                                                                | Before coding             |        |
| [[research-data-immutable]]                 | Research Data Immutable             | settings.json denies records/**                                                                   | PreToolUse                |        |
| [[just-in-time-context]]                    | Just-In-Time Context                | sessionstart_load_axioms.py                                                                       | SessionStart              |        |
| [[minimal-instructions]]                    | Minimal Instructions                | HEURISTICS.md, policy_enforcer.py 200-line limit                                                  | PreToolUse                |        |
| [[feedback-loops-for-uncertainty]]          | Feedback Loops                      | HEURISTICS.md                                                                                     | SessionStart              |        |
| [[current-state-machine]]                   | Current State Machine               | autocommit_state.py (auto-commit+push)                                                            | PostToolUse               |        |
| [[one-spec-per-feature]]                    | One Spec Per Feature                | agents/framework-ops.md                                                                           | SessionStart              |        |
| [[mandatory-handover]]                      | Mandatory Handover Workflow         | UserPromptSubmit (hint), dump.md Step 2                                                           | UserPromptSubmit, Stop    |        |
| [[capture-outstanding-work]]                | Capture Outstanding Work            | dump.md Step 2 (create follow-up tasks for incomplete/deferred work)                              | Stop                      |        |
| [[explicit-approval-costly-ops]]            | Costly Operations Approval          | external-batch-submission.md workflow + AskUserQuestion before batch submit                       | During execution          |        |
| [[academic-output-quality]]                 | Academic Output Quality (P#53)      | skills/research/axioms.md quality gate: user sign-off required for public deliverables            | Stop                      |        |
| [[no-shitty-nlp]]                           | No Shitty NLP (P#49)                | agents/framework-ops.md, HEURISTICS.md, custodiet periodic check, REMINDERS.md                    | SessionStart, PostToolUse | 1a, 3b |
| [[no-shitty-nlp]]                           | Agentic-First Design (P#49)         | agents/framework-ops.md corollary: no programmatic LLM API wrappers; custodiet detects "API call" | SessionStart, PostToolUse | 1a, 3b |
| [[data-boundaries]]                         | Credential Isolation                | `SSH_AUTH_SOCK=""` in settings.local.json; `GH_TOKEN` from limited `AOPS_BOT_GH_TOKEN` PAT        | SessionStart              | 6      |
| [[non-interactive-execution]]               | Non-interactive Execution (P#55)    | agents/framework-ops.md, C3 constraint; agent behavior and system prompts                         | During execution          |        |

## Heuristic → Enforcement Mapping

| Heuristic                    | Rule                     | Enforcement               | Point            | Level |
| ---------------------------- | ------------------------ | ------------------------- | ---------------- | ----- |
| [[skill-invocation-framing]] | Skill Invocation Framing | Lightweight hydrator hint | UserPromptSubmit |       |
| [[skill-first-action]]       | Skill-First Action       | Lightweight hydrator hint | UserPromptSubmit |       |

| [[verification-before-assertion]] | Verification Before Assertion | session_reflect.py detection, custodiet periodic check | Stop, PostToolUse | |
| [[explicit-instructions-override]] | Explicit Instructions Override | HEURISTICS.md, custodiet periodic check | SessionStart, PostToolUse | |
| [[error-messages-primary-evidence]] | Error Messages Primary Evidence | HEURISTICS.md | SessionStart | |
| [[context-uncertainty-favors-skills]] | Context Uncertainty Favors Skills | Lightweight hydrator hint | UserPromptSubmit | |

| [[link-dont-repeat]] | Link, Don't Repeat | HEURISTICS.md | SessionStart | |
| [[avoid-namespace-collisions]] | Avoid Namespace Collisions | HEURISTICS.md | SessionStart | |
| [[skills-no-dynamic-content]] | Skills No Dynamic Content | settings.json denies skill writes | PreToolUse | |
| [[light-instructions-via-reference]] | Light Instructions via Reference | HEURISTICS.md | SessionStart | |
| [[no-promises-without-instructions]] | No Promises Without Instructions | HEURISTICS.md | SessionStart | |
| [[semantic-search-over-keyword]] | Semantic Search Over Keyword | HEURISTICS.md | SessionStart | |
| [[edit-source-run-setup]] | Edit Source, Run Setup | HEURISTICS.md | SessionStart | |
| [[streamlit-hot-reloads]] | Streamlit Hot Reloads | HEURISTICS.md | SessionStart | |
| [[use-askuserquestion]] | Use AskUserQuestion | HEURISTICS.md | SessionStart | |
| [[check-skill-conventions]] | Check Skill Conventions | HEURISTICS.md | SessionStart | |
| [[right-tool-for-the-work]] | Right Tool for the Work (P#78) | HEURISTICS.md, custodiet periodic check | SessionStart, PostToolUse | |
| [[questions-require-answers]] | Questions Need Answers First | HEURISTICS.md, custodiet periodic check | SessionStart, PostToolUse | |
| [[critical-thinking-over-compliance]] | Critical Thinking Over Compliance | HEURISTICS.md | SessionStart | |
| [[core-first-expansion]] | Core-First Expansion | HEURISTICS.md | SessionStart | |
| [[indices-before-exploration]] | Indices Before Exploration | HEURISTICS.md | SessionStart | |
| [[synthesize-after-resolution]] | Synthesize After Resolution | HEURISTICS.md | SessionStart | |
| [[ship-scripts-dont-inline]] | Ship Scripts, Don't Inline | HEURISTICS.md | SessionStart | |
| [[user-centric-acceptance]] | User-Centric Acceptance | HEURISTICS.md | SessionStart | |
| [[semantic-vs-episodic-storage]] | Semantic vs Episodic Storage | HEURISTICS.md, lightweight hydrator hint, custodiet check | SessionStart, PostToolUse | |
| [[debug-dont-redesign]] | Debug, Don't Redesign | HEURISTICS.md | SessionStart | |
| [[mandatory-acceptance-testing]] | Mandatory Acceptance Testing | /qa skill (on-demand) | Stop | |
| [[todowrite-vs-persistent-tasks]] | TodoWrite vs Persistent Tasks | HEURISTICS.md | SessionStart | |
| [[design-first-not-constraint-first]] | Design-First | HEURISTICS.md | SessionStart | |
| [[no-llm-calls-in-hooks]] | No LLM Calls in Hooks | HEURISTICS.md | SessionStart | |
| [[delete-dont-deprecate]] | Delete, Don't Deprecate | HEURISTICS.md | SessionStart | |
| [[real-data-fixtures]] | Real Data Fixtures | HEURISTICS.md | SessionStart | |
| [[semantic-link-density]] | Semantic Link Density | check_orphan_files.py | Pre-commit | |
| [[spec-first-file-modification]] | Spec-First File Modification | HEURISTICS.md | SessionStart | |
| [[file-category-classification]] | File Category Classification | check_file_taxonomy.py | Pre-commit | |
| [[full-evidence-for-validation]] | Full Evidence for Validation | @pytest.mark.demo requirement | Test design | |
| [[real-fixtures-over-contrived]] | Real Fixtures Over Contrived | docs/testing-patterns.md | Test design | |
| [[execution-over-inspection]] | Execution Over Inspection | framework skill compliance protocol | Skill invocation | |
| [[test-failure-requires-user-decision]] | Test Failure Requires User Decision | HEURISTICS.md | SessionStart | |
| [[no-horizontal-dividers]] | No Horizontal Dividers | markdownlint-cli2 | Pre-commit | |
| [[enforcement-changes-require-rules-md-update]] | Enforcement Changes Require enforcement-map.md Update | HEURISTICS.md | SessionStart | |
| [[just-in-time-information]] | Just-In-Time Information | HEURISTICS.md | SessionStart | |
| [[summarize-tool-responses]] | Summarize Tool Responses | HEURISTICS.md | SessionStart | 1a |
| [[structured-justification-format]] | Structured Justification Format | PreToolUse hook (planned) | Before framework edit | 1d |
| [[extract-implies-persist]] | Extract Implies Persist in PKM Context | Lightweight hydrator hint | UserPromptSubmit | |

| [[background-agent-visibility]] | Background Agent Visibility | HEURISTICS.md | SessionStart | |
| [[imminent-deadline-surfacing]] | Imminent Deadline Surfacing | daily skill DEADLINE TODAY category | /daily invocation | 1a |
| [[decomposed-tasks-complete]] | Decomposed Tasks Are Complete | HEURISTICS.md | SessionStart | |
| [[task-sequencing-on-insert]] | Task Sequencing on Insert | HEURISTICS.md | SessionStart | |
| [[methodology-belongs-to-researcher]] | Methodology Belongs to Researcher | HEURISTICS.md, lightweight hydrator hint | SessionStart, UserPromptSubmit | |
| [[preserve-pre-existing-content]] | Preserve Pre-Existing Content | HEURISTICS.md | SessionStart | |
| [[user-intent-discovery]] | User Intent Discovery Before Implementation | HEURISTICS.md, lightweight hydrator hint | SessionStart, UserPromptSubmit | |
| [[user-intent-discovery]] | Slash Command Args Intent Parsing | skip_check.py: multi-word args trigger lightweight hint | UserPromptSubmit | 3b |
| [[verify-non-duplication-batch-create]] | Verify Non-Duplication Before Create | HEURISTICS.md, triage-email workflow | SessionStart, task creation | 1a |
| [[run-python-via-uv]] | Run Python via uv | HEURISTICS.md | SessionStart | 1a |
| [[protect-dist-directory]] | Protect dist/ Directory | .agents/rules/HEURISTICS.md, policy_enforcer.py | SessionStart, PreToolUse | 1a |
| [[subagent-verdicts-binding]] | Subagent Verdicts Are Binding | HEURISTICS.md | SessionStart, SubagentStop | 1a |
| [[qa-tests-black-box]] | QA Tests Are Black-Box | HEURISTICS.md | SessionStart, QA execution | 1b |
| [[cli-testing-extended-timeouts]] | CLI Testing Requires Extended Timeouts | HEURISTICS.md | SessionStart | 1a |
| [[explain-dont-ask]] | Explain, Don't Ask (P#104) | HEURISTICS.md | SessionStart | |
| [[qa-independent-evidence]] | QA Must Produce Independent Evidence | HEURISTICS.md, /pull Step 3A.V | Before completion | 1c |
| [[qualitative-evaluation-over-quantitative]] | Qualitative Evaluation Over Quantitative (P#115) | HEURISTICS.md, /qa skill Qualitative Assessment mode | SessionStart, /qa invocation | |
| [[delegate-agency-to-capable-agents]] | Delegate Agency to Capable Agents (P#116) | HEURISTICS.md | SessionStart | |
| [[bound-subagent-scope-before-dispatch]] | Bound Subagent Scope Before Dispatch (P#119) | HEURISTICS.md, custodiet periodic check | SessionStart, PostToolUse | |
| [[standard-tooling-over-framework-gates]] | Standard Tooling Over Framework Gates (P#105) | HEURISTICS.md | SessionStart | 1a |
| [[user-sign-off-required]] | User Sign-Off Required (P#111) | HEURISTICS.md | Stop | |
| [[receipts-on-qa]] | Receipts on QA (P#112) | HEURISTICS.md | QA execution | |
| [[over-verify-externally-visible]] | Over-Verify Externally Visible Work (P#113) | HEURISTICS.md | During execution | |
| [[no-silent-release]] | No Silent Release (P#114) | HEURISTICS.md | Before release | |
| [[butler-gap-principle]] | Butler Gap Principle (frame design questions as framework gaps) | framework SKILL.md | Skill invocation | |
| [[butler-preflight-investigation]] | Butler Pre-Flight Investigation (verify mechanism capabilities before answering) | framework SKILL.md | Skill invocation | |

## Enforcement Level Summary

| Level      | Count | Description                                                                     |
| ---------- | ----- | ------------------------------------------------------------------------------- |
| Hard Gate  | 12    | Blocks action (PreToolUse hooks, deny rules, pre-commit)                        |
| Soft Gate  | 8     | Injects guidance, agent can proceed                                             |
| Prompt     | 43    | Instructional (AXIOMS.md, HEURISTICS.md, CORE.md, REMINDERS.md at SessionStart) |
| Observable | 2     | Creates visible artifact (TodoWrite)                                            |
| Detection  | 3     | Logs for post-hoc analysis                                                      |
| Review     | 1     | Human/LLM review at PR time                                                     |
| Convention | 3     | Documented pattern, no mechanical check                                         |
| Config     | 1     | External tool config (pyproject.toml, pre-commit)                               |

**Note**: "Prompt" level rules are instructional. Compliance is not mechanically enforced but is checked periodically by custodiet.

### What Constitutes Prompt-Level Enforcement

Context loading follows a **three-tier architecture** (see [[session-start-injection]]):

| Tier | File                   | Purpose                          | When Loaded               |
| ---- | ---------------------- | -------------------------------- | ------------------------- |
| 1    | `$AOPS/CORE.md`        | Framework tools (essential only) | SessionStart (ALL agents) |
| 2    | `$cwd/.agents/CORE.md` | Project-specific context         | SessionStart (if exists)  |
| 3    | `AXIOMS.md` etc.       | Detailed guidance                | JIT via hints             |

**Design principle**: Minimal baseline, maximal JIT. Agents start with only what they need to understand the framework and project. Everything else loads on-demand.

### File Loading Summary

| File                        | Purpose                         | Loaded Via                       |
| --------------------------- | ------------------------------- | -------------------------------- |
| `$AOPS/CORE.md`             | Framework tool inventory (~2KB) | SessionStart hook                |
| `$cwd/.agents/CORE.md`      | Project conventions             | SessionStart hook (if exists)    |
| `AXIOMS.md`                 | Tier 1: Universal axioms        | SessionStart (always)            |
| `agents/dev-standards.md`   | Tier 2: Development rules       | When dev-standards agent invoked |
| `agents/framework-ops.md`   | Tier 2: Framework rules         | When framework-ops agent invoked |
| `skills/research/axioms.md` | Tier 2: Academic rules          | When research skill invoked      |
| `HEURISTICS.md`             | Tier 3: Advisory heuristics     | JIT via hints                    |

## MCP Tool Injection Requirements

| Tool               | Exempt | Rationale                                                                             |
| ------------------ | ------ | ------------------------------------------------------------------------------------- |
| `store_memory`     | **No** | Must route through `/remember` skill to create both markdown + memory (aops-887fba77) |
| `retrieve_memory`  | Yes    | Read-only, no state change                                                            |
| `recall_memory`    | Yes    | Read-only, no state change                                                            |
| Task manager tools | Yes    | Establish task binding (infrastructure)                                               |

## Periodic Compliance (Custodiet)

The custodiet hook (`hooks/router.py`) provides periodic semantic compliance checking via [[ultra-vires-custodiet]].

### Mechanism

| Parameter             | Value               | Description                                          |
| --------------------- | ------------------- | ---------------------------------------------------- |
| `TOOL_CALL_THRESHOLD` | 50                  | Full compliance check every N tool calls             |
| Counted tools         | ALL tool calls      | Counter increments for every tool (Read, Edit, etc.) |
| Blocked tools         | MUTATING_TOOLS only | Only Edit/Write/Bash blocked at threshold            |

### Compliance Check (Threshold)

At threshold, spawns haiku subagent to review session transcript for:

- Axiom violations ([[fail-fast-code]], [[verify-first]], [[acceptance-criteria-own-success]])
- Heuristic violations ([[verification-before-assertion]], [[explicit-instructions-override]], [[questions-require-answers]])
- Drift patterns (scope creep, plan deviation)
- Insight capture (advisory) - flags when discoveries aren't persisted to remember skill

Uses `decision: "block"` output format to force agent attention. Insight capture is advisory only (no block).

**Enforcement mode**: `block` (default). Custodiet violations halt the session. Override via `CUSTODIET_GATE_MODE=warn` env var.

## Path Protection (Deny Rules)

| Category          | Pattern                                       | Blocked Tools           | Purpose                                                  | Axiom                        |
| ----------------- | --------------------------------------------- | ----------------------- | -------------------------------------------------------- | ---------------------------- |
| Claude config     | `~/.claude/*.json`                            | Read, Write, Edit, Bash | Protect secrets                                          | [[data-boundaries]]          |
| Claude runtime    | `~/.claude/{hooks,skills,commands,agents}/**` | Write, Edit, Bash       | Force edits via `$AOPS/`                                 | [[skills-are-read-only]]     |
| Claude plugins    | `~/.claude/plugins/**`                        | Write, Edit             | Protect installed plugins                                | [[skills-are-read-only]]     |
| Gemini extensions | `~/.gemini/extensions/**`                     | Write, Edit             | Protect installed extensions                             | [[skills-are-read-only]]     |
| Research records  | `**/tja/records/**`, `**/tox/records/**`      | Write, Edit, Bash       | Research data immutable                                  | [[research-data-immutable]]  |
| Session state     | `/tmp/claude-session/**`                      | Write, Edit, Bash       | Protect session data                                     | Mechanical trigger integrity |
| Task indices      | `**/data/tasks/*.json`                        | Read, Bash              | Enforce MCP server usage                                 | [[just-in-time-context]]     |
| Polecat worktree  | `**` (deny) / `<worktree>/**` (allow)         | Write, Edit             | Sandbox polecat agent writes to designated worktree only | [[data-boundaries]]          |

**Note**: Reading `~/.claude/hooks/**` etc IS allowed (skill invocation needs it).

**Note**: Task JSON files (index.json, id_mapping.json) must be queried via tasks MCP server (list_tasks, search_tasks, get_task_tree, etc.) to prevent token bloat from reading large files directly.

**Note**: Claude plugins and Gemini extensions protection enforced via:

- Claude: `~/.claude/settings.json` → `permissions.deny`
- Gemini: `~/.gemini/policies/deny-extension-writes.toml` (policy engine)

## Credential Isolation (#581)

Agent must not have access to user's SSH key (which has admin/bypass rights on repos). Instead, agent uses a limited-scope fine-grained PAT.

| Mechanism                   | How                                                         | Enforcement Level |
| --------------------------- | ----------------------------------------------------------- | ----------------- |
| SSH agent blocked           | `SSH_AUTH_SOCK=""` in `~/.claude/settings.local.json`       | 6 (env override)  |
| Limited PAT for GitHub      | `AOPS_BOT_GH_TOKEN` → `GH_TOKEN` via `session_env_setup.py` | 6 (env override)  |
| No interactive auth prompts | `GIT_TERMINAL_PROMPT=0` in `~/.claude/settings.local.json`  | 6 (env override)  |

**Source files**:

- `~/.claude/settings.local.json` — env var overrides
- `aops-core/hooks/session_env_setup.py` — maps `AOPS_BOT_GH_TOKEN` → `GH_TOKEN` at session start

**PAT scope**: User-managed fine-grained PAT with limited permissions (push to non-protected branches, create PRs/issues). No admin, no bypass branch protection.

## API Validation (Tasks MCP Server)

| Rule                         | API           | Validation                                                  | Override     | Reference         |
| ---------------------------- | ------------- | ----------------------------------------------------------- | ------------ | ----------------- |
| Parent task completion guard | complete_task | Reject if task has incomplete children (not done/cancelled) | `force=True` | [[aops-45392b53]] |

**Note**: Technical enforcement prevents accidental premature completion. Agents must either complete children first or explicitly override with force flag.

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

## Session-End Validation (Stop Hooks)

Session end is blocked until requirements are met. Three-phase validation ensures proper handover.

### Framework Reflection Validation

**Enforcement**: `gate_registry.py` (AfterAgent → `check_agent_response_listener`) + `check_stop_gate`.

The stop gate requires reflection for session completion:

| Condition                | Gate                     | Set By                                       | Check                       |
| ------------------------ | ------------------------ | -------------------------------------------- | --------------------------- |
| (1) Reflection validated | `handover_skill_invoked` | `check_agent_response_listener` (AfterAgent) | All required fields present |

**Note**: Reflection is required for any work that modifies files.

**Gate (2) Field Validation**: When `## Framework Reflection` is detected in agent response, all 8 required fields must be present:

| Required Field | Purpose                           |
| -------------- | --------------------------------- |
| **Prompts**:   | Original request                  |
| **Outcome**:   | One of: success, partial, failure |

| `**Accomplishments**:` | What was completed |
| `**Friction points**:` | Issues encountered (write none if none) |
| `**Proposed changes**:` | Framework improvements (write none if none) |
| `**Next step**:` | Task IDs for follow-up work (write none if none) |

**Malformed Reflection Handling**: If `## Framework Reflection` is present but missing required fields:

- Gate remains closed (`handover_skill_invoked` NOT set)
- Warning message lists missing fields
- Context injection shows correct format
- Agent can retry with complete reflection

**Stop Gate Enforcement**: `check_stop_gate` blocks session end if any required flag is not set.

**Workflow**:

1. Agent completes work
2. Agent invokes QA skill to verify results against original request and acceptance criteria
3. PostToolUse hook sets `qa_invoked` flag
4. Agent outputs Framework Reflection with ALL required fields
5. AfterAgent hook validates format and sets `handover_skill_invoked` flag
6. Agent invokes `/dump` command
7. Agent attempts to end session (triggers Stop event)
8. Stop gate checks flags (handover, QA)
9. If flags set: session ends
10. If any flag missing: blocks with instructions for the missing step

### Uncommitted Work Check

**Enforcement**: `session_end_commit_check.py` Stop hook.

Blocks session end if:

- Framework Reflection or test success detected in transcript
- AND uncommitted changes exist in git

Auto-commits staged changes. Blocks if unstaged changes require manual commit.

## Commit-Time Validation (Pre-commit)

| Category         | Hook                                      | Purpose                                         | Axiom                             |
| ---------------- | ----------------------------------------- | ----------------------------------------------- | --------------------------------- |
| File hygiene     | trailing-whitespace, check-yaml/json/toml | Clean commits                                   | [[use-standard-tools]]            |
| Code quality     | shellcheck, eslint, ruff                  | Catch errors                                    | [[use-standard-tools]]            |
| Formatting       | dprint                                    | Consistent formatting                           | [[use-standard-tools]]            |
| Data integrity   | bmem-validate                             | Valid frontmatter                               | [[current-state-machine]]         |
| Data purity      | data-markdown-only                        | Only `.md` in data/                             | [[current-state-machine]]         |
| Framework health | check-framework-integrity                 | Index wikilinks, skill entries, workflow length | [[maintain-relational-integrity]] |
| Framework health | check-skill-line-count                    | SKILL.md < 500 lines                            | [[self-documenting]]              |
| Framework health | check-orphan-files                        | Detect orphan files                             | [[semantic-link-density]]         |
| Markdown style   | markdownlint                              | No horizontal dividers                          | [[no-horizontal-dividers]]        |

## CI/CD Validation (GitHub Actions)

| Workflow             | Purpose                                  | Axiom                             |
| -------------------- | ---------------------------------------- | --------------------------------- |
| test-setup.yml       | Validate symlinks exist and are relative | [[fail-fast-code]]                |
| framework-health.yml | Framework health metrics and enforcement | [[maintain-relational-integrity]] |
| claude.yml           | Claude Code bot integration              | -                                 |
| agent-enforcer.yml   | Axiom compliance review for PRs          | Universal axioms (Tier 1)         |

## Agent Tool Permissions

Main agent has all tools except deny rules. Subagents are restricted:

| Agent          | Tools Granted                                | Model  | Purpose                                                                                                        |
| -------------- | -------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Main agent     | All (minus deny rules)                       | varies | Primary task execution                                                                                         |
| custodiet      | Read                                         | haiku  | Periodic session compliance checking                                                                           |
| enforcer       | Read (local), Bash+Read (GHA)                | varies | Axiom compliance checking (PR review, session audits)                                                          |
| qa             | Read, Grep, Glob                             | opus   | Independent verification (anti-sycophancy: must verify against original request verbatim, not agent reframing) |
| planner        | All (inherits from main)                     | sonnet | Implementation planning                                                                                        |
| planning skill | See `skills/planning/SKILL.md` allowed-tools | opus   | Strategic planning (invoked via `Skill(skill="planning")`)                                                     |

**Note**: `tools:` in agent frontmatter RESTRICTS available tools - it cannot GRANT access beyond what settings.json allows. Deny rules apply globally.

## Knowledge Persistence

Enforcement of [[semantic-vs-episodic-storage]] and [[current-state-machine]].

| Component              | Purpose                               | Sync to PKB          |
| ---------------------- | ------------------------------------- | -------------------- |
| Remember skill         | Dual-write markdown + PKB             | Yes (on invocation)  |
| Remember sync workflow | Reconcile markdown → PKB              | Yes (repair/rebuild) |
| Session-insights       | Extract and persist session learnings | Yes (Step 6.5)       |

**Markdown is SSoT** - PKB is derivative index for semantic search.

**Insight capture flow**:

- Operational findings → bd issues
- Knowledge discoveries → `Skill(skill="remember")` → markdown + memory
- Session learnings → `/session-insights` → JSON + memory

## Task Assignment Convention

Context injected via CORE.md at SessionStart.

| Assignment      | Tag                 | Purpose                             |
| --------------- | ------------------- | ----------------------------------- |
| Bot/agent work  | `tags: ["polecat"]` | Automated tasks for agent execution |
| Human/user work | `tags: ["human"]`   | Manual tasks requiring user action  |

**Rule**: Use tags for task assignment, not the `context` field.

**Enforcement**: Prompt-level (CORE.md). No mechanical gate.

## File Location Conventions

Context injected via CORE.md at SessionStart. Guides where agents place files.

| Content Type           | Location             | Example                                  |
| ---------------------- | -------------------- | ---------------------------------------- |
| aops feature specs     | `$AOPS/specs/`       | `$AOPS/specs/task-graph-network-v1.0.md` |
| User knowledge/designs | `$ACA_DATA/designs/` | `$ACA_DATA/designs/my-project-design.md` |
| Generated outputs      | `$ACA_DATA/outputs/` | `$ACA_DATA/outputs/`                     |

**Enforcement**: Prompt-level (CORE.md). No mechanical gate.

## Source Files

| Mechanism        | Authoritative Source                                                                 |
| ---------------- | ------------------------------------------------------------------------------------ |
| Deny rules       | `$AOPS/config/claude/settings.json` → `permissions.deny`                             |
| Agent tools      | `$AOPS/aops-core/agents/*.md` → `tools:` frontmatter                                 |
| PreToolUse       | `aops-core/hooks/router.py` (custodiet, subagent_restrictions), `policy_enforcer.py` |
| PostToolUse      | `aops-core/hooks/router.py`                                                          |
| UserPromptSubmit | `aops-core/hooks/router.py`                                                          |
| SessionStart     | `aops-core/hooks/session_env_setup.py`                                               |
| Stop             | `aops-core/hooks/session_end_commit_check.py`                                        |
| Pre-commit       | `$AOPS/.pre-commit-config.yaml`                                                      |
| CI/CD            | `$AOPS/.github/workflows/`                                                           |
| Remember skill   | `$AOPS/aops-core/skills/remember/SKILL.md`                                           |
| Memory sync      | `$AOPS/aops-core/skills/remember/procedures/sync.md`                                 |
| Session insights | `$AOPS/aops-core/skills/session-insights/SKILL.md`                                   |
| Session state    | `$AOPS/aops-core/lib/session_state.py`                                               |
