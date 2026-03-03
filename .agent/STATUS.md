# academicOps Framework Status

**Last updated**: 2026-03-03

> **Authoritative scope**: This document describes the state of the aops framework codebase and its immediately-connected infrastructure. It is kept current by the butler on each invocation. Automated reviewers (gatekeeper, conceptual-review, etc.) read this document -- accuracy matters. If something is described as "working" here, it is integrated and tested. If it is described as "planned", it does not yet exist in production.
>
> **Canonical direction**: This document reflects actual state. When the codebase or infrastructure changes, update this document to match reality -- do not change behavior to match this document. If there is a discrepancy between this document and the actual codebase, the codebase is correct and this document needs updating.

## Vision

academicOps (aops) is an LLM-driven framework for managing academic workflows -- research, teaching, writing -- through structured enforcement, task management, and governance. The framework reduces cognitive load on the academic user by providing intelligent automation that remembers decisions, enforces consistency, and handles routine coordination.

## Architecture Overview

```
academicOps/
+-- .agent/           # Agent instructions, commands, skills, rules
|   +-- rules/        # AXIOMS.md (inviolable principles), protected_paths
|   +-- commands/     # Slash commands (learn, email, aops, q, bump, pull, dump)
|   +-- skills/       # 17 domain skills (see Skills System below)
|   +-- workflows/    # Workflow definitions (manual-qa, etc.)
+-- .github/
|   +-- agents/       # 3 agent prompts (worker, merge-prep, conceptual-review)
|   +-- workflows/    # 11 GitHub Actions workflows
+-- aops-core/        # Framework core
|   +-- hooks/        # Session hooks (router, policy_enforcer, gate_config, etc.)
|   +-- lib/          # Shared libraries (gates, hydration, sessions, tasks, etc.)
|   +-- mcp_servers/  # MCP server stubs (legacy; task/PKB ops now handled by Rust PKB server)
|   +-- scripts/      # Utility scripts
+-- scripts/          # Build, sync, visualization, and maintenance scripts
+-- specs/            # Design specifications (37 specs)
+-- tests/            # Test suite (~100 test files across unit/integration/e2e/demo/polecat)
+-- config/           # Configuration files
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

**Framework integration**: Deeply integrated into the hook system. The gate_config.py registers 30+ PKB tool name variants (handling `mcp__pkb__*`, `mcp__plugin_aops-core_pkb__*`, `mcp__pbk__*`, bare names, and versioned prefixes) as `always_available` -- gates never block PKB access. The session_env_setup hook checks for the `pkb` binary on PATH at session start. The router hooks reference PKB tools for task binding. The Python task CLI scripts have been removed; PKB is now Rust-native.

**Design principles**: "Dumb Server, Smart Agent" (P#78) -- deterministic computation in server, judgment in LLM. Files are markdown with YAML frontmatter (human-readable without tools). The vector store and knowledge graph are derived caches rebuilt from files.

### PR Review Pipeline -- WORKING

Automated PR review pipeline with safety mechanisms.

**Pipeline flow**: `code-quality.yml` (lint + type-check) -> `agent-conceptual-review.yml` (strategic/architectural review) -> `agent-merge-prep.yml` (merge preparation) -> human approval

**Safety mechanisms**:

- **Cascade limit**: Pipeline run-count tracked per PR; halts after 3 runs to prevent infinite bot loops
- **LGTM check-status gate**: Merge workflow checks required status checks before enabling auto-merge
- **Strategic review**: Conceptual review agent reads `.agent/STATUS.md`, AXIOMS.md, and codebase context to catch PRs that conflict with key decisions
- **Loop detector**: Merge-prep uses `Merge-Prep-By:` commit trailer for detection

**GitHub Actions workflows** (11):

- `code-quality.yml` -- lint, formatting, type checks
- `agent-conceptual-review.yml` -- strategic/architectural PR review
- `agent-merge-prep.yml` -- merge preparation
- `claude.yml` -- Claude agent invocation
- `pytest.yml` -- test suite
- `framework-health.yml` -- framework integrity checks
- `validate-ruleset.yml` -- axiom/rule validation
- `build-extension.yml` -- extension builds
- `copilot-setup-steps.yml` -- Copilot configuration
- `ios-note-capture.yml` -- iOS note capture workflow
- `merge-prep-cron.yml` -- scheduled merge preparation

**Agents** (3 prompt files in `.github/agents/`): worker, merge-prep, conceptual-review

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

- `tests/hooks/test_gate_verdicts.py` -- 150 scenario-driven regression tests from `fixtures/gate_scenarios.json`
- `tests/hooks/test_gate_replay.py` -- 31 tests replaying real hook events from `fixtures/real_hook_events.json`
- `tests/hooks/test_hydration_never_deny.py` -- ensures hydration gate never blocks always_available tools, hydrator itself, or user question tools

**Hydration gate policy**: Only `always_available` tools (Agent, Task, Skill, AskUserQuestion, activate_skill, all PKB tools) bypass the hydration gate. Read-only tools get WARN, not exempt. Custodiet excludes both `always_available` and `read_only`.

### Hydration System -- WORKING

Context injection at `aops-core/lib/hydration/`:

- `builder.py` -- hydration pipeline construction
- `context_loaders.py` -- context loading strategies
- `skip_check.py` -- hydration bypass conditions

### Task Management -- WORKING (via PKB server)

Task management has migrated from the Python task model (`aops-core/lib/task_model.py`, `task_storage.py`, `task_sync.py`, `task_index.py`) to the Rust PKB server. The Python modules remain for backward compatibility but the PKB server is the authoritative task system.

**Known debt**: Task lifecycle hooks do not automatically close tasks when PRs merge (tasks get stuck in merge_ready/review status).

### Skills System -- WORKING

17 skills in `.agent/skills/`:

| Skill             | Purpose                                             |
| ----------------- | --------------------------------------------------- |
| analyst           | Research data analysis, statistics, visualization   |
| annotations       | Document annotation workflows                       |
| audit             | Framework health auditing, orphan detection         |
| critic            | Critical review and feedback                        |
| custodiet         | Compliance enforcement ("who watches the watchers") |
| daily             | Daily note capture and management                   |
| effectual-planner | Effectual planning methodology                      |
| framework         | Framework development, component design             |
| garden            | Knowledge garden maintenance, frontmatter linting   |
| hypervisor        | Multi-agent orchestration, batch workers            |
| prompt-hydrator   | Context injection for user prompts                  |
| python-dev        | Python development patterns, testing, tooling       |
| qa                | Quality assurance testing                           |
| remember          | Knowledge capture and memory management             |
| session-insights  | Session transcript analysis and insight extraction  |
| task-viz          | Task graph visualization (DOT, attention maps)      |
| worker            | Autonomous task execution                           |

### Polecat System -- WORKING

Agent worker system with sandbox isolation, GitHub integration, and observability. Test suite in `tests/polecat/` covering sandbox, validation, GitHub interaction, prompt templating, worktree management, and observability.

### Session Insights -- WORKING

Scripts for extracting insights from session transcripts in `.agent/skills/session-insights/scripts/`.

## Key Decisions

| Decision                                                 | Rationale                                                                                                             | Date       |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------- |
| Delete qa.agent.md and strategic-review.agent.md         | Neither was invoked by any workflow; dead weight. Conceptual-review and custodiet-reviewer cover these concerns.      | 2026-03-03 |
| custodiet-reviewer reads AXIOMS.md dynamically           | Hardcoded axiom list missed new axioms (e.g. P#45 Feedback Loops). Dynamic reading ensures full coverage.             | 2026-03-03 |
| conceptual-review uses assumption audit lens             | Effectual reasoning: treat all unvalidated parameters as assumptions requiring feedback loops, not settled decisions. | 2026-03-03 |
| PKB server is Rust-native (replaces Python task scripts) | Performance, reliability, single binary deployment. CLI + MCP from same codebase.                                     | 2026-02-22 |
| All PKB tools are always_available in gate system        | PKB is framework infrastructure. Gates must never block PKB access.                                                   | 2026-03-01 |
| Hydration gate: only always_available exempt             | Read-only tools get WARN (not exempt). Prevents gate from blocking its own hydrator (Agent tool).                     | 2026-03-01 |
| Import convention: qualified paths from aops-core/       | Bare imports caused dual sys.modules entries breaking importlib.reload() in tests.                                    | 2026-03-01 |
| Gate verdict + replay regression tests                   | 150 scenario tests + 31 real-event replay tests to prevent gate regressions permanently.                              | 2026-03-01 |
| "Agent" added to always_available tools                  | Claude Code's subagent tool is "Agent" not "Task". Gate config must list both.                                        | 2026-02-28 |
| Iterative stale task sweep                               | 236+ open tasks with significant junk; batch-review with human decisions, not bulk auto-cancel                        | 2026-02-23 |
| Conceptual review agent reads STATUS.md                  | Without strategic context, the review agent cannot catch PRs that delete working components (PR 582 post-mortem)      | 2026-02-23 |
| Pipeline cascade limit (max 3 runs)                      | PR 582 showed bots triggering bots in unbounded loops; comment-based counting bounds total cycles                     | 2026-02-23 |
| LGTM triggers lint re-run if failing                     | PR 585 showed LGTM silently failing when lint was stale; merge workflow now checks and re-triggers                    | 2026-02-23 |
| Transcript path: $AOPS_SESSIONS/polecats/                | Worker transcripts go to sessions repo, not old ~/.aops/transcripts path                                              | 2026-02-23 |
| Commit trailer for loop detection                        | Author name unreliable (multiple bots use github-actions[bot])                                                        | 2026-02-22 |
| All workflows get workflow_dispatch                      | Manual re-run capability for debugging and recovery                                                                   | 2026-02-22 |
| Review dismissal by agents                               | Agents should dismiss reviews they've addressed; humans override remaining                                            | 2026-02-22 |
| All merge methods enabled                                | Flexibility for different PR types                                                                                    | 2026-02-22 |
| Tests at repo root, not in aops-core                     | Single test suite covering all components                                                                             | prior      |
| Skills are read-only (P#23)                              | Mutable state in $ACA_DATA only                                                                                       | prior      |
| Categorical imperative (P#2)                             | Every change must be a universal rule                                                                                 | prior      |

## Open Questions

1. **Task lifecycle gap**: Tasks stuck in merge_ready/review where code was already committed to main. Task lifecycle hooks do not automatically close tasks when PRs merge. This is a systemic issue.
2. **Issue review over-triggering**: The issue review agents fire on read-only and tracking operations. Needs filtering improvement.
3. **Hydrator guardrails**: Hydrator agent drifts into implementation advice instead of staying advisory. Needs stronger prompt constraints.
4. **Autonomous automation readiness**: Most workflows are at "supervised" maturity. No workflows have been validated for fully autonomous operation yet.
5. **STATUS.md as bot input**: Bots (gatekeeper, conceptual-review) read this document as authoritative context. Stale information here causes false positives in reviews (see issue #701 where conceptual-review flagged the PKB server as non-existent because STATUS.md listed it as a roadmap item). This document MUST be kept accurate.

## Roadmap

### Recently Completed

- **Review agent consolidation** (PR #705) -- deleted qa.agent.md and strategic-review.agent.md (both unused); custodiet-reviewer now reads AXIOMS.md dynamically; conceptual-review refocused on assumption audit + effectual reasoning.
- **PKB server deployed** -- Rust-native CLI + MCP server replacing Python task scripts. 18 MCP tools, deep gate integration, binary availability check at session start.
- **Conceptual review agent** -- Replaced gatekeeper/custodiet/hydrator-reviewer issue-review pattern with strategic-review and conceptual-review agents.
- Gate hardening sprint: 150 verdict tests, 31 replay tests, Agent tool fix, import convention fix, gate status strip -- 2026-02-28 / 2026-03-01
- PR pipeline post-mortem and fixes (cascade limit, LGTM check-status, strategic gatekeeper) -- 2026-02-23
- Stale task sweep iterations 1-4 -- 2026-02-23

### Near-term

- Address task lifecycle gap (auto-close tasks when PRs merge)
- Strengthen hydrator guardrails
- Address issue review over-triggering
- Wire custodiet-reviewer into a GitHub Actions workflow (deferred from PR #705)
- Axiom clustering refactor (reorganize AXIOMS.md into logical groups)

### Medium-term

- Graduate PR pipeline from "supervised" to "autonomous" after multiple clean runs
- PKB server spec v2 refinements (episodic memories, tool consolidation per spec D2)
- Dogfooding workflow improvements

### Long-term

- Full autonomous agent workflows with butler oversight
- Cross-project task management
- Session insights automation

---

_Update log_ (keep last 3 entries; older history is in git):

- **2026-03-03**: Agent consolidation (PR #705). Deleted qa.agent.md and strategic-review.agent.md (dead agents, no workflow invocations). Agent count updated: 5 -> 3 (worker, merge-prep, conceptual-review). custodiet-reviewer now reads AXIOMS.md dynamically. conceptual-review refocused on assumption audit + effectual reasoning.
- **2026-03-03**: Major accuracy update (PR #702). Corrected PKB server status from "medium-term roadmap" to "deployed and running" (was causing false review findings, issue #701). Updated workflow count (18->11), agent list (now 5: qa, worker, strategic-review, merge-prep, conceptual-review), skills count (13->17), test count (~90->~100), architecture tree (removed nonexistent aops-tools/). Added PKB Server section as top component. Added authoritative-scope notice. Removed references to merged PRs from "In Progress". Added update log.
- **2026-03-02**: Previous update (gate system, hydration policy).
