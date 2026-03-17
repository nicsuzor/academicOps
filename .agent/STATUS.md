# academicOps Framework Status

**Last updated**: 2026-03-09

> **Authoritative scope**: This document describes the state of the aops framework codebase and its immediately-connected infrastructure. It is kept current by the butler on each invocation. Automated reviewers (axiom-review, review-and-fix, etc.) read this document -- accuracy matters. If something is described as "working" here, it is integrated and tested. If it is described as "planned", it does not yet exist in production.
>
> **Canonical direction**: This document reflects actual state. When the codebase or infrastructure changes, update this document to match reality -- do not change behavior to match this document. If there is a discrepancy between this document and the actual codebase, the codebase is correct and this document needs updating.

## Vision

academicOps (aops) is an LLM-driven framework for managing academic workflows -- research, teaching, writing -- through structured enforcement, task management, and governance. The framework reduces cognitive load on the academic user by providing intelligent automation that remembers decisions, enforces consistency, and handles routine coordination.

## Architecture Overview

```
academicOps/
+-- .agent/           # Agent instructions, commands, skills, rules
|   +-- rules/        # AXIOMS.md, HEURISTICS.md, protected_paths
|   +-- commands/     # Slash commands (learn, email, aops, q, bump, pull, dump, path)
|   +-- skills/       # 17 agent-facing skills (see Skills System below)
|   +-- workflows/    # Workflow definitions
+-- .github/
|   +-- agents/       # 5 agent prompts (axiom-review, review-and-fix, merge-prep, worker, summary-brief)
|   +-- workflows/    # 12 GitHub Actions workflows
+-- aops-core/        # Framework core (installed as plugin)
|   +-- hooks/        # Session hooks (router, policy_enforcer, gate_config, etc.)
|   +-- lib/          # Shared libraries (gates, hydration, sessions, tasks, etc.)
|   +-- skills/       # 28 skill definitions with SKILL.md frontmatter (canonical source)
|   +-- mcp_servers/  # MCP server stubs (legacy; task/PKB ops now handled by Rust PKB server)
|   +-- scripts/      # Utility scripts
|   +-- SKILLS.md     # Canonical skills index (36 entries: 8 commands + 28 skills)
|   +-- GLOSSARY.md   # Framework terminology for hydrator context
|   +-- WORKFLOWS.md  # Workflow decision tree and routing
+-- scripts/          # Build, sync, visualization, and maintenance scripts
+-- specs/            # Design specifications (42 files, 40 tracked in INDEX.md)
+-- tests/            # Test suite (~100 test files across unit/integration/e2e/demo/polecat)
+-- config/           # Configuration files
+-- overwhelm-dashboard/  # Streamlit dashboard for cognitive load management
```

**Data layer** ($ACA_DATA): `/opt/nic/brain` -- sessions, projects, logs, context, goals. Separate from framework code.

**External infrastructure**:

- **PKB server** (Rust, github.com/nicsuzor/mem): `aops` CLI + `pkb-search` MCP server binary. Deployed and running. Provides 18+ MCP tools for task management, document CRUD, semantic search, and knowledge graph operations. See "PKB Server" section below.
- **Memory MCP server**: Semantic memory with HTTP transport (`mcp__memory__*`)
- **Outlook MCP server**: Email/calendar integration (`mcp__outlook__*`)
- **Zotero MCP server**: Academic reference management (`mcp__zot__*`)

## Key Components & Current State

### PKB Server -- DEPLOYED AND RUNNING

The Personal Knowledge Base server is the backbone data layer for the framework. It is a Rust binary (`pkb`) installed via `cargo binstall` from the `mem` repository, providing both a CLI (`aops`) and an MCP server (`pkb-search`) over stdio transport.

**Spec**: `specs/pkb-server-spec.md`

**18 MCP tools across 6 groups**:

| Group      | Tools                                                     |
| ---------- | --------------------------------------------------------- |
| Search     | `search`, `task_search`, `get_document`, `list_documents` |
| Task read  | `list_tasks`, `get_task`, `get_network_metrics`           |
| Task write | `create_task`, `update_task`, `complete_task`             |
| Document   | `create`, `create_memory`, `append`, `delete`             |
| Graph      | `pkb_context`, `pkb_trace`, `pkb_orphans`                 |
| Admin      | `reindex`                                                 |

**Framework integration**: Deeply integrated into the hook system. The gate_config.py registers 30+ PKB tool name variants (handling `mcp__pkb__*`, `mcp__plugin_aops-core_pkb__*`, `mcp__pbk__*`, bare names, and versioned prefixes) as `infrastructure` -- gates never block PKB access. The session_env_setup hook checks for the `pkb` binary on PATH at session start.

**Design principles**: "Dumb Server, Smart Agent" (P#78) -- deterministic computation in server, judgment in LLM. Files are markdown with YAML frontmatter (human-readable without tools). The vector store and knowledge graph are derived caches rebuilt from files.

### PR Review Pipeline -- WORKING

Automated PR review pipeline with safety mechanisms.

**Pipeline flow**: `code-quality.yml` (lint + type-check) -> `agent-axiom-review.yml` (Auditor: axiom compliance) + `agent-review-and-fix.yml` (Critic: strategic review & fixes) -> `agent-merge-prep.yml` (merge preparation) -> human approval

**Safety mechanisms**:

- **Cascade limit**: Pipeline run-count tracked per PR; halts after 3 runs to prevent infinite bot loops
- **LGTM check-status gate**: Merge workflow checks required status checks before enabling auto-merge
- **Axiom compliance**: Axiom review agent checks diffs against AXIOMS.md, HEURISTICS.md, and project rules (mechanical, silent on success)
- **Strategic review**: Review-and-fix agent reads `.agent/STATUS.md`, VISION.md, and codebase context to catch strategic misalignment and fix mechanical issues
- **Loop detector**: Merge-prep uses `Merge-Prep-By:` commit trailer for detection

**GitHub Actions workflows** (12):

- `code-quality.yml` -- lint, formatting, type checks
- `agent-axiom-review.yml` -- axiom/heuristic compliance checking
- `agent-review-and-fix.yml` -- strategic review with fix capability
- `agent-merge-prep.yml` -- merge preparation
- `claude.yml` -- Claude agent invocation
- `pytest.yml` -- test suite
- `framework-health.yml` -- framework integrity checks
- `validate-ruleset.yml` -- axiom/rule validation
- `build-extension.yml` -- extension builds
- `copilot-setup-steps.yml` -- Copilot configuration
- `ios-note-capture.yml` -- iOS note capture workflow
- `merge-prep-cron.yml` -- scheduled merge preparation

**Agents** (5 prompt files in `.github/agents/`): auditor (was axiom-review), critic/assessor (was review-and-fix; file still named `assessor.agent.md` pending workflow rename), merge-prep, worker, summary-brief

**Merge methods**: merge commit, squash, and rebase all enabled.

### Hook System -- WORKING

Session lifecycle hooks managed via `aops-core/hooks/router.py`:

- `user_prompt_submit.py` -- prompt routing and gate evaluation
- `policy_enforcer.py` -- axiom enforcement
- `session_env_setup.py` -- environment setup, PKB binary check
- `session_end_commit_check.py` -- commit verification
- `generate_transcript.py` -- transcript generation
- `ntfy_notifier.py` -- push notifications
- `gate_config.py` -- tool categorization, PKB prefix normalization, gate mode configuration
- `autocommit_state.py` -- autocommit state tracking
- `unified_logger.py` -- centralized hook logging
- `internal_models.py` / `schemas.py` -- data models for hook payloads

### Gate System -- WORKING

Predicate-based gate engine at `aops-core/lib/gates/`:

- `engine.py` -- gate evaluation
- `definitions.py` -- gate definitions
- `registry.py` -- gate registration
- `custom_conditions.py` / `custom_actions.py` -- extensibility

**Gate testing suite**:

- `tests/hooks/test_gate_verdicts.py` -- 150+ scenario-driven regression tests from `fixtures/gate_scenarios.json` (edge cases) + `fixtures/gate_scenarios_live.json` (provenance-tracked live data)
- `tests/hooks/test_gate_replay.py` -- 31 tests replaying real hook events from `fixtures/real_hook_events.json`
- `tests/hooks/test_hydration_never_deny.py` -- ensures hydration gate never blocks infrastructure tools, hydrator itself, or user question tools

**Tool categories** (gate_config.py `TOOL_CATEGORIES`):

- `infrastructure` -- PKB tools, AskUserQuestion, TodoWrite, EnterPlanMode, ExitPlanMode. Bypass ALL gates.
- `spawn` -- Agent, Task, Skill, delegate_to_agent, activate_skill. Subject to hydration gate; always allowed when dispatching a compliance agent (hydrator, custodiet, etc.).
- `read_only` -- Read, Glob, Grep, WebFetch, and read-equivalent tools. Subject to hydration gate; exempt from custodiet.
- `write` -- Bash, Edit, Write, run_shell_command, etc. Subject to all gates.

**Hydration gate policy**: Only `infrastructure` tools bypass the hydration gate. `spawn` tools (including Agent/Skill) are blocked until hydration completes. Read-only tools are also subject to hydration (forced hydration before exploration). Gate opens JIT when the hydrator is dispatched (PreToolUse trigger). Custodiet excludes both `infrastructure` and `read_only`.

### Hydration System -- WORKING

Context injection at `aops-core/lib/hydration/`:

- `builder.py` -- hydration pipeline construction
- `context_loaders.py` -- context loading strategies (SKILLS.md, WORKFLOWS.md, AXIOMS.md, HEURISTICS.md, GLOSSARY.md, SCRIPTS.md, project rules, project workflows, project context index, global workflow content)
- `skip_check.py` -- hydration bypass conditions

**Context loaders**: The hydration system loads framework indices (`SKILLS.md`, `WORKFLOWS.md`, `AXIOMS.md`, `HEURISTICS.md`, `GLOSSARY.md`, `SCRIPTS.md`) from the plugin root plus project-specific rules and workflows from the current working directory's `.agent/` folder. Missing framework files now raise `FileNotFoundError` (fail-fast, PR #813) rather than returning empty strings.

### Task Management -- WORKING (via PKB server)

Task management has migrated from the Python task model (`aops-core/lib/task_model.py`, `task_storage.py`, `task_sync.py`, `task_index.py`) to the Rust PKB server. The Python modules remain for backward compatibility but the PKB server is the authoritative task system.

**Known debt**: Task lifecycle hooks do not automatically close tasks when PRs merge (tasks get stuck in merge_ready/review status).

### Skills System -- WORKING

Skills exist in two locations with different roles:

1. **`.agent/skills/`** (17 skills): Agent-facing skill definitions loaded by Claude Code's native skill system. These are the skills that appear when Claude Code lists available skills.
2. **`aops-core/skills/`** (28 skill definitions): Canonical skill definitions with `SKILL.md` frontmatter (triggers, domain, mode, allowed-tools). These are loaded by the hydration system via `SKILLS.md` for routing.

The canonical index is `aops-core/SKILLS.md` with 36 entries (8 commands + 28 skills). Several skills in `aops-core/skills/` do not have corresponding entries in `.agent/skills/` (`assess-hydrator`, `briefing-bundle`, `convert-to-md`, `decision-apply`, `decision-extract`, `densify`, `email-triage`, `excalidraw`, `extract`, `flowchart`, `hdr`, `pdf`, `planning`, `process-bundle`, `strategy`, `swarm-supervisor`).

**Skills by domain**:

| Domain            | Skills                                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------------ |
| framework         | `audit`, `custodiet`, `framework`, `prompt-hydrator`                                             |
| operations        | `daily`, `densify`, `garden`, `hypervisor`, `remember`, `session-insights`, `task-viz`, `worker` |
| academic          | `analyst`, `hdr`, `pdf`                                                                          |
| email             | `email-triage`                                                                                   |
| collaboration     | `annotations`, `critic`                                                                          |
| planning          | `effectual-planner`, `planning`, `strategy`                                                      |
| quality           | `qa`                                                                                             |
| quality-assurance | `assess-hydrator`                                                                                |
| development       | `python-dev`                                                                                     |
| design            | `excalidraw`, `flowchart`                                                                        |
| data processing   | `briefing-bundle`, `process-bundle`, `decision-extract`, `decision-apply`, `extract`             |
| document          | `convert-to-md`                                                                                  |
| multi-agent       | `swarm-supervisor`                                                                               |

### Specs System -- WORKING

42 spec files organized into 6 tiers plus archived. Full audit completed 2026-03-07 (see `specs/AUDIT-specs-2026-03-07.md`). Index at `specs/INDEX.md` now tracks 40 specs with status indicators and dependency chains.

**Key finding from audit**: 78% of specs were untracked before the audit. Several specs describe aspirational architecture not yet implemented (predicate-registry, verification-system advocate agent, worker-hypervisor). Spec dependency chains run 4-5 deep in places.

### The Curia (Agent Team) -- WORKING

The Curia is the named agent team that operates across local sessions and GitHub PRs. Each agent has a consistent identity but manifests differently on each surface.

**Roster** (see `.agent/curia/CURIA.md` for full details):

| Agent        | Charter            | Local Skill       | GitHub Agent                                                         | Mechanical (Hook/Gate)                  |
| ------------ | ------------------ | ----------------- | -------------------------------------------------------------------- | --------------------------------------- |
| **Hydrator** | Context enrichment | `prompt-hydrator` | --                                                                   | hydration gate, `user_prompt_submit.py` |
| **Auditor**  | Rule enforcement   | `custodiet`       | `auditor.agent.md`                                                   | `policy_enforcer.py`                    |
| **Critic**   | Strategic review   | `critic`          | `assessor.agent.md` (→ `critic.agent.md`†), `summary-brief.agent.md` | --                                      |
| **QA**       | Acceptance testing | `qa`              | `qa.agent.md`                                                        | QA gate                                 |
| **Advocate** | Voice matching     | -- (future)       | -- (future)                                                          | --                                      |

**Portability**: The QA agent is designed to work on any repo -- `qa.agent.md` includes an inline fallback methodology for repos without the aops framework installed.

**Cross-references**: Every skill, GitHub agent, and hook file includes a Curia cross-reference line identifying its role and related implementations.

### Polecat System -- WORKING

Agent worker system with sandbox isolation, GitHub integration, and observability. Test suite in `tests/polecat/` covering sandbox, validation, GitHub interaction, prompt templating, worktree management, and observability.

### Session Insights -- WORKING

Scripts for extracting insights from session transcripts in `aops-core/skills/session-insights/scripts/`.

### Overwhelm Dashboard -- WORKING

Streamlit dashboard for cognitive load management at `overwhelm-dashboard/`. Includes task graph redesign epic with three purpose-built views (treemap/circle-pack overview, arc diagram for dependencies, force graph priority spread). QA workflow documented at `.agent/workflows/evaluate-dashboard.md`.

### Acceptance Tests -- IN PROGRESS

Acceptance tests at `tests/acceptance/`:

- `v1.1-release.md` -- 2 tests (email triage routing, framework skill routing). Both FAILING due to test harness gap.
- `v0.3-release.md` -- 12 tests covering hydrator routing accuracy. All PENDING -- blocked on same test harness gap.

**Known blocker**: The hydrator subagent test harness does not inject session context. The hydration `builder.py` constructs the input file during normal session hooks, but the test harness bypasses this path.

### Gemini Extension -- PARTIAL

Gemini CLI extension installed at `~/.gemini/extensions/aops-core/`. Missing 7 of 18 framework `.md` files (GLOSSARY, SCRIPTS, CONSTRAINTS, LIFECYCLE-HOOKS, TASK_FORMAT_GUIDE, TAXONOMY, WORKERS) -- tracked as task `aops-9d899fb4`. Context loaders now fail fast on missing files (PR #813).

## Key Decisions

| Decision                                                 | Rationale                                                                                                                                                                                                                 | Date       |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Delete qa.agent.md and strategic-review.agent.md         | Neither was invoked by any workflow; dead weight. Conceptual-review and custodiet-reviewer cover these concerns. (New portable qa.agent.md created 2026-03-09 with different purpose: PR verification, not issue review.) | 2026-03-03 |
| custodiet-reviewer reads AXIOMS.md dynamically           | Hardcoded axiom list missed new axioms (e.g. P#45 Feedback Loops). Dynamic reading ensures full coverage.                                                                                                                 | 2026-03-03 |
| conceptual-review uses assumption audit lens             | Effectual reasoning: treat all unvalidated parameters as assumptions requiring feedback loops, not settled decisions.                                                                                                     | 2026-03-03 |
| PKB server is Rust-native (replaces Python task scripts) | Performance, reliability, single binary deployment. CLI + MCP from same codebase.                                                                                                                                         | 2026-02-22 |
| All PKB tools are `infrastructure` in gate system        | PKB is framework infrastructure. Gates must never block PKB access. (Was `always_available` pre-PR #730.)                                                                                                                 | 2026-03-04 |
| Hydration gate: only `infrastructure` exempt             | Read-only and `spawn` tools (Agent, Skill, etc.) are blocked until hydration. Gate opens JIT on hydrator PreToolUse.                                                                                                      | 2026-03-04 |
| Agent tool in `spawn` category (not `infrastructure`)    | Prevents bypassing hydration via Agent spawns; compliance agents get a pre-dispatch trigger bypass instead.                                                                                                               | 2026-03-04 |
| Import convention: qualified paths from aops-core/       | Bare imports caused dual sys.modules entries breaking importlib.reload() in tests.                                                                                                                                        | 2026-03-01 |
| Gate verdict + replay regression tests                   | 150 scenario tests + 31 real-event replay tests to prevent gate regressions permanently.                                                                                                                                  | 2026-03-01 |
| "Agent" and "Task" are both `spawn` tools                | Claude Code's subagent tool is "Agent" not "Task". Gate config must list both. (Moved from `always_available` in PR #730.)                                                                                                | 2026-02-28 |
| Iterative stale task sweep                               | 236+ open tasks with significant junk; batch-review with human decisions, not bulk auto-cancel                                                                                                                            | 2026-02-23 |
| Conceptual review agent reads STATUS.md                  | Without strategic context, the review agent cannot catch PRs that delete working components (PR 582 post-mortem)                                                                                                          | 2026-02-23 |
| Pipeline cascade limit (max 3 runs)                      | PR 582 showed bots triggering bots in unbounded loops; comment-based counting bounds total cycles                                                                                                                         | 2026-02-23 |
| LGTM triggers lint re-run if failing                     | PR 585 showed LGTM silently failing when lint was stale; merge workflow now checks and re-triggers                                                                                                                        | 2026-02-23 |
| Transcript path: $AOPS_SESSIONS/polecats/                | Worker transcripts go to sessions repo, not old ~/.aops/transcripts path                                                                                                                                                  | 2026-02-23 |
| Commit trailer for loop detection                        | Author name unreliable (multiple bots use github-actions[bot])                                                                                                                                                            | 2026-02-22 |
| All workflows get workflow_dispatch                      | Manual re-run capability for debugging and recovery                                                                                                                                                                       | 2026-02-22 |
| Review dismissal by agents                               | Agents should dismiss reviews they've addressed; humans override remaining                                                                                                                                                | 2026-02-22 |
| All merge methods enabled                                | Flexibility for different PR types                                                                                                                                                                                        | 2026-02-22 |
| Tests at repo root, not in aops-core                     | Single test suite covering all components                                                                                                                                                                                 | prior      |
| Skills are read-only (P#23)                              | Mutable state in $ACA_DATA only                                                                                                                                                                                           | prior      |
| Categorical imperative (P#2)                             | Every change must be a universal rule                                                                                                                                                                                     | prior      |

## Open Questions

1. **Task lifecycle gap**: Tasks stuck in merge_ready/review where code was already committed to main. Task lifecycle hooks do not automatically close tasks when PRs merge. This is a systemic issue.
2. **Issue review over-triggering**: The issue review agents fire on read-only and tracking operations. Needs filtering improvement.
3. **Hydrator guardrails**: Hydrator agent drifts into implementation advice instead of staying advisory. Needs stronger prompt constraints.
4. **Autonomous automation readiness**: Most workflows are at "supervised" maturity. No workflows have been validated for fully autonomous operation yet.
5. **STATUS.md as bot input**: Bots (axiom-review, review-and-fix) read this document as authoritative context. Stale information here causes false positives in reviews. This document MUST be kept accurate.
6. **Hydrator acceptance test harness gap**: The hydrator subagent cannot be tested in isolation because the test harness does not construct the input file that `builder.py` normally provides during session hooks. Both v1.1 and v0.3 acceptance tests are blocked on this.
7. **Skills duplication across locations**: 17 skills in `.agent/skills/` and 28 in `aops-core/skills/` with incomplete overlap. The relationship between these two locations needs clarification -- which is authoritative, and should the `.agent/skills/` set be generated from `aops-core/skills/`?
8. **Knowledge diffusion**: Butler specialist knowledge (in MEMORY.md, butler system prompt) is not systematically transferred to framework-accessible locations (GLOSSARY.md, context_loaders, specs). See strategic analysis in this session's conversation.

## Roadmap

### Recently Completed

- **Curia agent team legibility** -- Named agent team ("The Curia") with roster at `.agent/curia/CURIA.md`. Renamed GitHub agents (axiom-review -> auditor, review-and-fix -> critic). Cross-references added to all skills, agents, and hooks. Portable QA agent (`qa.agent.md`) works on any repo. Curia alias "auditor" added to gate config (assessor/advocate removed — not compliance bypass agents).
- **Review agent consolidation** (PR #705) -- deleted qa.agent.md and strategic-review.agent.md (both unused); custodiet-reviewer now reads AXIOMS.md dynamically; conceptual-review refocused on assumption audit + effectual reasoning.
- **Conceptual review agent** -- Replaced gatekeeper/custodiet/hydrator-reviewer issue-review pattern with strategic-review and conceptual-review agents.
- Gate hardening sprint: 150 verdict tests, 31 replay tests, Agent tool fix, import convention fix, gate status strip -- 2026-02-28 / 2026-03-01
- PR pipeline post-mortem and fixes (cascade limit, LGTM check-status, strategic gatekeeper) -- 2026-02-23
- Stale task sweep iterations 1-4 -- 2026-02-23
- **Specs audit and INDEX.md rewrite** (2026-03-07) -- Full inventory of 42 specs; INDEX.md rebuilt with 6 tiers, status tracking, dependency chains, and maintenance guide. Audit documented in `specs/AUDIT-specs-2026-03-07.md`.
- **Fail-fast on missing framework files** (PR #813) -- Context loaders raise FileNotFoundError instead of returning sentinel or empty string. Ensures deployment issues are surfaced immediately.
- **Stitch design assets cleanup** -- Removed 8.9MB unused stitch design assets and dead aliases.
- **Review agent consolidation** (PR #705) -- deleted qa.agent.md and strategic-review.agent.md (both unused); custodiet-reviewer now reads AXIOMS.md dynamically.
- **PKB server deployed** -- Rust-native CLI + MCP server replacing Python task scripts. 18 MCP tools, deep gate integration.
- Gate hardening sprint: 150 verdict tests, 31 replay tests, Agent tool fix, import convention fix -- 2026-02-28 / 2026-03-01

### Near-term

- **Fix hydrator acceptance test harness** -- unblock v0.3 and v1.1 acceptance tests
- **Knowledge diffusion** -- transfer butler specialist knowledge into framework-accessible locations (see Open Question #8)
- Address task lifecycle gap (auto-close tasks when PRs merge)
- Strengthen hydrator guardrails
- Complete Gemini extension file gap (task `aops-9d899fb4`)
- Wire custodiet-reviewer into a GitHub Actions workflow

### Medium-term

- Graduate PR pipeline from "supervised" to "autonomous" after multiple clean runs
- PKB server spec v2 refinements (episodic memories, tool consolidation)
- Clarify skills system architecture (`.agent/skills/` vs `aops-core/skills/`)
- Dogfooding workflow improvements

### Long-term

- Full autonomous agent workflows with butler oversight
- Cross-project task management
- Session insights automation

---

_Update log_ (keep last 3 entries; older history is in git):

- **2026-03-09**: Curia agent team legibility. Created `.agent/curia/CURIA.md` roster mapping 5 named agents to implementations across surfaces. Renamed GitHub agents: axiom-review -> auditor, review-and-fix -> critic (file: assessor.agent.md, pending workflow rename). Updated workflow YAMLs. Added cross-references to all skills, GitHub agents, and hooks. Created portable `qa.agent.md` (works on any repo via fallback methodology). Added Curia alias "auditor" to gate_config.py (assessor/advocate removed — not compliance bypass roles).
- **2026-03-05**: Added v0.3 acceptance tests (`tests/acceptance/v0.3-release.md`) -- 12 tests covering hydrator routing accuracy across workflow discrimination, academic workflows, project-scoped workflow loading, skill bypass, multi-intent splitting, and batch routing. Added "Acceptance Tests" section to Components. Documented hydrator test harness gap as Open Question #6 and near-term roadmap item. Both v1.1 and v0.3 tests blocked on harness fix.
- **2026-03-04**: Gate hardening (PR #730). Tool categories refactored: `always_available` split into `infrastructure` (PKB, meta tools) and `spawn` (Agent, Task, Skill, delegate_to_agent). Spawn tools now blocked by hydration gate. Custodiet deadlock fixed: PreToolUse trigger resets counter before policy evaluates. Test fixtures rebuilt from live production logs (861 provenance-tracked scenarios). Gate test count: 150+ verdict tests + 31 replay tests.
- **2026-03-09**: Butler invocation and full STATUS.md refresh. Corrected skills count: 36 entries in canonical SKILLS.md (8 commands + 28 skills), 28 skill definitions in `aops-core/skills/`, 17 in `.agent/skills/`. Added skills duplication as Open Question #7. Added knowledge diffusion as Open Question #8. Added Gemini Extension, Overwhelm Dashboard, and Specs System sections. Updated architecture tree to show `aops-core/skills/` and key index files. Added recent completions (specs audit, fail-fast, stitch cleanup). Trimmed older key decisions table for readability. Corrected update log entry that incorrectly said agent count went from "5 -> 3" (there are still 5 agents in `.github/agents/`).
- **2026-03-05**: Added v0.3 acceptance tests (`tests/acceptance/v0.3-release.md`) -- 12 tests covering hydrator routing accuracy. Added "Acceptance Tests" section. Documented hydrator test harness gap as Open Question #6.
- **2026-03-04**: Gate hardening (PR #730). Tool categories refactored: `always_available` split into `infrastructure` and `spawn`. Test fixtures rebuilt from live production logs (861 provenance-tracked scenarios).
