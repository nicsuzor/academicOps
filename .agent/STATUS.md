# academicOps Framework Status

**Last updated**: 2026-03-02

## Vision

academicOps (aops) is an LLM-driven framework for managing academic workflows -- research, teaching, writing -- through structured enforcement, task management, and governance. The framework reduces cognitive load on the academic user by providing intelligent automation that remembers decisions, enforces consistency, and handles routine coordination.

## Architecture Overview

```
academicOps/
├── .agent/           # Agent instructions, commands, skills, rules
│   ├── rules/        # AXIOMS.md (inviolable principles), protected_paths
│   ├── commands/     # Slash commands (learn, email, aops, q, bump, pull)
│   ├── skills/       # Domain skills (analyst, framework, python-dev, custodiet, etc.)
│   └── workflows/    # Workflow definitions (manual-qa, etc.)
├── .github/
│   ├── agents/       # Agent personality prompts (gatekeeper, custodiet, qa, merge-prep, hydrator-reviewer)
│   └── workflows/    # 18 GitHub Actions workflows
├── aops-core/        # Framework core
│   ├── hooks/        # Session hooks (router, policy_enforcer, task_binding, etc.)
│   ├── lib/          # Shared libraries (gates, hydration, sessions, tasks, knowledge_graph, etc.)
│   ├── mcp_servers/  # MCP servers (tasks_server, memory_proxy)
│   └── scripts/      # Utility scripts (transcript, custodiet_block, etc.)
├── specs/            # Design specifications (37 specs)
├── tests/            # Test suite (~90+ test files across unit/integration/e2e/demo)
└── config/           # Configuration files
```

**Data layer** ($ACA_DATA): `/opt/nic/brain` -- sessions, projects, logs, context, goals. Separate from framework code.

## Key Components & Current State

### PR Review Pipeline -- WORKING (with known issues being addressed)

The fully automated PR review pipeline is the most mature component. Post-mortem on PRs 582 and 585 (2026-02-23) revealed three failure modes, all now addressed with fixes:

**Pipeline flow**: `code-quality.yml` (lint + gatekeeper + type-check) -> `pr-review-pipeline.yml` (cascade-check -> custodiet -> QA -> merge-prep -> notify-ready) -> human approval -> `pr-lgtm-merge.yml` (check-status -> lint re-trigger -> approve -> auto-merge)

**Safety mechanisms** (added/improved 2026-02-23):

- **Cascade limit**: Pipeline run-count tracked per PR; halts after 3 runs to prevent infinite bot loops (`pr-review-pipeline.yml`)
- **LGTM check-status gate**: Merge workflow now checks required status checks before enabling auto-merge; re-triggers lint if failing (`pr-lgtm-merge.yml`)
- **Strategic gatekeeper**: Gatekeeper now reads `.agent/STATUS.md` in addition to VISION.md and AXIOMS.md, enabling it to reject PRs that delete working components or conflict with key decisions (`gatekeeper.md`)
- **Loop detector**: Merge-prep uses `Merge-Prep-By:` commit trailer (not author name) -- unchanged from prior fix

**All 18 workflows have `workflow_dispatch` triggers** for manual re-runs.

**Agents**: gatekeeper, custodiet, QA, merge-prep, hydrator-reviewer (5 agents with distinct personalities and authorities)

**Merge methods**: merge commit, squash, and rebase all enabled on both nicsuzor/academicOps and qut-dmrc/buttermilk.

### Hook System -- WORKING

Session lifecycle hooks managed via `aops-core/hooks/router.py`:

- `user_prompt_submit.py` -- prompt routing and gate evaluation
- `policy_enforcer.py` -- axiom enforcement
- `task_binding.py` -- task context injection
- `session_env_setup.py` -- environment setup (CUSTODIET_GATE_MODE, etc.)
- `session_end_commit_check.py` -- commit verification
- `generate_transcript.py` -- transcript generation
- `ntfy_notifier.py` -- push notifications

### Gate System -- WORKING (significant testing added 2026-03-01)

Predicate-based gate engine at `aops-core/lib/gates/`:

- `engine.py` -- gate evaluation
- `definitions.py` -- gate definitions
- `registry.py` -- gate registration
- `custom_conditions.py` / `custom_actions.py` -- extensibility

**Gate testing suite** (added 2026-02-28 / 2026-03-01):

- `tests/hooks/test_gate_verdicts.py` -- 150 scenario-driven regression tests from `fixtures/gate_scenarios.json`
- `tests/hooks/test_gate_replay.py` -- 31 tests replaying real hook events from `fixtures/real_hook_events.json`
- `tests/hooks/test_hydration_never_deny.py` -- ensures hydration gate never blocks always_available tools, hydrator itself, or user question tools

**Recent gate fixes (2026-02-28 / 2026-03-01)**:

- **Agent tool recognition** (PR #662): Claude Code's subagent tool is "Agent", not "Task". Added "Agent" to always_available, SPAWN_TOOLS, and all hardcoded tool name checks.
- **Import convention** (PR #664): All imports use qualified paths from `aops-core/` root (e.g., `from hooks.gate_config import ...`). Bare imports caused dual `sys.modules` entries that broke `importlib.reload()` in tests.
- **Gate status strip** (PR #666): Lifecycle-aware display with text-weight unicode icons, replacing bracket-format strip.
- **Test environment isolation**: Gate env vars leak from live sessions into tests. Must pin ALL gate-relevant vars in autouse fixtures and use `importlib.reload()`.

**Hydration gate policy**: Only `always_available` tools (Agent, Task, Skill, AskUserQuestion, activate_skill) bypass the hydration gate. Read-only tools get WARN, not exempt. Custodiet excludes both `always_available` and `read_only`.

### Hydration System -- WORKING

Context injection at `aops-core/lib/hydration/`:

- `builder.py` -- hydration pipeline construction
- `context_loaders.py` -- context loading strategies
- `skip_check.py` -- hydration bypass conditions

### Task Management -- WORKING (significant debt, sweep in progress)

`aops-core/lib/task_model.py`, `task_storage.py`, `task_sync.py`, `task_index.py`
MCP server: `aops-core/mcp_servers/tasks_server.py`

**Task debt (surveyed 2026-02-23)**: ~236 open tasks across all projects (166 aops, 55 academic, 15+ other). Iterative sweep in progress (task `aops-sweep-20260223`).

**Sweep progress**: Iterations 1-4 complete. 13 cancelled, 3 marked done, 9 kept, 2 fixed. ~223 open tasks remaining. Key patterns found: (1) orphaned children of done/cancelled parents, (2) tasks stuck in merge_ready/review where work was already committed to main -- this is a systemic issue where task lifecycle hooks do not automatically close tasks when PRs merge.

### Issue Review Agents -- EARLY

- `issue-review-custodiet.yml` -- proposal quality review on issue open
- `issue-review-hydrator.yml` -- infrastructure context on issue open
- Known issue: hook over-triggering on read-only operations
- Hydrator tends to drift into implementation advice (needs stronger guardrails)

### Skills System -- WORKING

13+ skills in `.agent/skills/`: analyst, annotations, audit, convert-to-md, critic, custodiet, effectual-planner, framework, garden, pdf, python-dev, qa, remember, session-insights, task-viz, hypervisor

### Session Insights -- WORKING

Scripts for extracting insights from session transcripts in `.agent/skills/session-insights/scripts/`.

## Key Decisions

| Decision                                           | Rationale                                                                                                  | Date       |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------- |
| Hydration gate: only always_available exempt       | Read-only tools get WARN (not exempt). Prevents gate from blocking its own hydrator (Agent tool).          | 2026-03-01 |
| Import convention: qualified paths from aops-core/ | Bare imports caused dual sys.modules entries breaking importlib.reload() in tests.                         | 2026-03-01 |
| Gate verdict + replay regression tests             | 150 scenario tests + 31 real-event replay tests to prevent gate regressions permanently.                   | 2026-03-01 |
| "Agent" added to always_available tools            | Claude Code's subagent tool is "Agent" not "Task". Gate config must list both.                             | 2026-02-28 |
| Iterative stale task sweep                         | 236+ open tasks with significant junk; batch-review with human decisions, not bulk auto-cancel             | 2026-02-23 |
| Gatekeeper reads STATUS.md                         | Without strategic context, gatekeeper cannot catch PRs that delete working components (PR 582 post-mortem) | 2026-02-23 |
| Pipeline cascade limit (max 3 runs)                | PR 582 showed bots triggering bots in unbounded loops; comment-based counting bounds total cycles          | 2026-02-23 |
| LGTM triggers lint re-run if failing               | PR 585 showed LGTM silently failing when lint was stale; merge workflow now checks and re-triggers         | 2026-02-23 |
| Transcript path: $AOPS_SESSIONS/polecats/          | Worker transcripts go to sessions repo, not old ~/.aops/transcripts path (updated 2026-02-23 during sweep) | 2026-02-23 |
| Commit trailer for loop detection                  | Author name unreliable (multiple bots use github-actions[bot])                                             | 2026-02-22 |
| All workflows get workflow_dispatch                | Manual re-run capability for debugging and recovery                                                        | 2026-02-22 |
| Review dismissal by agents                         | Agents should dismiss reviews they've addressed; humans override remaining                                 | 2026-02-22 |
| All merge methods enabled                          | Flexibility for different PR types                                                                         | 2026-02-22 |
| Tests at repo root, not in aops-core               | Single test suite covering all components                                                                  | prior      |
| Skills are read-only (P#23)                        | Mutable state in $ACA_DATA only                                                                            | prior      |
| Categorical imperative (P#2)                       | Every change must be a universal rule                                                                      | prior      |

## Open Questions

1. **Issue review over-triggering**: The issue review agents fire on read-only and tracking operations. Needs filtering improvement.
2. **Hydrator guardrails**: Hydrator agent drifts into implementation advice instead of staying advisory. Needs stronger prompt constraints.
3. **Autonomous automation readiness**: Most workflows are at "supervised" maturity. No workflows have been validated for fully autonomous operation yet. PR 582/585 post-mortem confirms the pipeline is not yet ready for autonomous -- the new safety mechanisms need supervised validation.
4. **PATHS.md staleness**: Generated paths reference `/home/nic/src/academicOps` but the repo is at `/opt/nic/academicOps` on this machine. Environment-specific -- may need regeneration.
5. **Run-count accuracy**: The cascade limit uses comment pattern matching, not a proper counter. Could be inaccurate if comments are deleted or have unusual formatting. Monitor in practice.
6. **Task debt**: ~223 open tasks remaining after iteration 4. Systemic pattern confirmed: tasks stuck in merge_ready/review where code was already committed to main but task status never updated. The task lifecycle hooks do not automatically close tasks when PRs merge.
7. **Weekend PRs pending merge**: PRs #662, #664, #666 from the gate hardening sprint need to land. Some have pytest failures or conflicts that need resolution.

## Roadmap

### Recently Completed

- Gate hardening sprint: 150 verdict tests, 31 replay tests, Agent tool fix, import convention fix, gate status strip -- 2026-02-28 / 2026-03-01
- Stale task sweep iteration 4: 3 done, 2 cancelled -- 2026-02-23
- Stale task sweep iterations 1-3: 8 cancelled, 9 kept, 2 fixed -- 2026-02-23
- PR pipeline post-mortem and fixes (cascade limit, LGTM check-status, strategic gatekeeper) -- 2026-02-23
- PR review pipeline end-to-end (loop detection, skip notices, review dismissal) -- 2026-02-22
- workflow_dispatch on all workflows
- Test fix on main (CUSTODIET_GATE_MODE)

### In Progress

- **Merge weekend PRs** (#662, #664, #666, #667) -- gate fixes and credential isolation need to land on main
- **Iterative stale task sweep** (aops-sweep-20260223) -- iteration 4 complete; iteration 5 candidates prepared

### Near-term

- **Validate PR pipeline fixes on next real PR** (supervised run) -- the three new safety mechanisms need real-world validation
- Address issue review over-triggering
- Strengthen hydrator guardrails

### Medium-term

- Graduate PR pipeline from "supervised" to "autonomous" after multiple clean runs
- PKB server implementation (spec exists at `specs/pkb-server-spec.md`)
- Dogfooding workflow (recently added, commit f62c0442)

### Long-term

- Full autonomous agent workflows with butler oversight
- Cross-project task management
- Session insights automation
