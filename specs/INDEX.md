---
name: specs-index
title: Specifications Index
type: index
category: framework
description: Index of all framework specifications grouped by tier and status.
modified: 2026-03-07
---

# Specifications Index

All specs in this folder, grouped by tier and annotated with implementation status.

**Status key**: ✅ Implemented/Active · 🔶 Partial · 📋 Draft/Design · 🗄️ Archived

**Convention**: Each spec includes a "Giving Effect" section linking to implementation files. Specs should declare `status`, `tier`, and `depends_on` in frontmatter.

## Tier 1: Core Architecture

How the system works today. Required reading for understanding the framework.

| Spec                            | Status | Purpose                                                                                                                                         |
| ------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| [[enforcement.md]]              | ✅     | 5-layer enforcement architecture                                                                                                                |
| [[supervisor.md]]               | ✅     | Polecat orchestration: supervisor workflow, swarms, worker management                                                                           |
| [[prompt-hydration.md]]         | ✅     | Transform raw prompt into execution plan. Includes optimisation proposals (merged from former selective-injection and hydration-overhead specs) |
| [[session-start-injection.md]]  | ✅     | Three-tier context loading (baseline + JIT)                                                                                                     |
| [[hook-router.md]]              | ✅     | Single dispatch entry point for all hooks                                                                                                       |
| [[ultra-vires-enforcer.md]]     | 🔶     | Drift detection (agent defined, automated gate archived)                                                                                        |
| [[agent-authority.md]]          | 📋     | Agent permissions + skill delegation — frontmatter schema, deny-by-default, authority non-transit                                               |
| [[skill-delegation.md]]         | 📋     | Skill/Agent/direct-prompt invocation mechanics, context-passing contract, orchestrator spawn matrices                                           |
| [[workflow-system-spec.md]]     | 📋     | Composable markdown-based workflow engine                                                                                                       |
| [[plugin-architecture.md]]      | ✅     | Component boundaries (aops-core vs aops-tools)                                                                                                  |
| [[verification-system.md]]      | 📋     | Verify-first enforcement (design decision, not yet implemented)                                                                                 |
| [[effectual-planning-agent.md]] | ✅     | Strategic planning under uncertainty, network-based prioritisation                                                                              |
| [[workflow-constraints.md]]     | 🔶     | Constraint-based workflows. Partially implemented (100-line limit, substance in Skills)                                                         |
| [[command-intercept.md]]        | 📋     | PreToolUse tool parameter transformation                                                                                                        |

## Tier 1.5: Engineering Methodology

Cross-cutting practices for how agents approach technical work.

| Spec                             | Status | Purpose                                                                                             |
| -------------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| [[evidence-driven-debugging.md]] | ✅     | Instrument → evidence → fix → formalise. Investigation artifacts are infrastructure, not throwaway. |

## Tier 2: Operational Workflows

Procedures for specific work types that humans and agents follow.

| Spec                              | Status | Purpose                                                                        |
| --------------------------------- | ------ | ------------------------------------------------------------------------------ |
| [[session-handover-contract.md]]  | 📋     | **Retires Framework Reflection**. Structured YAML-based handover contract.     |
| [[pr-pipeline.md]]                | ✅     | PR lifecycle: bots prepare, human decides. Supersedes `archived/pr-process.md` |
| [[collaborate-workflow.md]]       | ✅     | Interactive collaboration sessions with transcript processing                  |
| [[decision-queue-spec.md]]        | ✅     | Batch decision processing (extract → annotate → apply)                         |
| [[daily-briefing-bundle.md]]      | 📋     | Morning briefing document (Chief of Staff metaphor)                            |
| [[audit-protocol.md]]             | ✅     | Framework audit dimensions and procedures                                      |
| [[conceptual-review-workflow.md]] | ✅     | Multi-agent iterative review pattern                                           |
| [[research-decomposition.md]]     | 🔶     | Research-specific task decomposition (in progress)                             |
| [[strategic-triage.md]]           | 📋     | Scheduled effectual planning: graph → 3-5 strategic recommendations            |

## Tier 3: Polecat System (Parallel Execution)

Coherent subsystem for parallel agent work via git worktrees.

| Spec                                       | Status | Purpose                                                                             |
| ------------------------------------------ | ------ | ----------------------------------------------------------------------------------- |
| [[polecat-system.md]]                      | ✅     | Foundation: ephemeral workspaces via git worktrees                                  |
| [[polecat-swarms.md]]                      | ✅     | Parallel workers + refinery + engineer review gate                                  |
| [[polecat-supervision.md]]                 | ✅     | Supervisor workflow: commissioning, merging, refinery                               |
| [[worker-hypervisor.md]]                   | ✅     | Hypervisor for concurrent worker pool management. May be superseded by bazaar model |
| [[non-interactive-agent-workflow-spec.md]] | ✅     | Full autonomous agent lifecycle (task → PR → merge → knowledge capture)             |

## Tier 4: Data Layer & Tools

Task system, knowledge base, and MCP tool interfaces.

| Spec                           | Status | Purpose                                                                         |
| ------------------------------ | ------ | ------------------------------------------------------------------------------- |
| [[work-management.md]]         | ✅     | Task CRUD, dependencies, strategic tracking via MCP                             |
| [[context-map-schema.md]]      | ✅     | **SSoT**: context-map.json schema for repo self-description and discovery       |
| [[mcp-decomposition-tools.md]] | ✅     | Data access layer for task decomposition (dumb server, smart agent)             |
| [[pkb-server-spec.md]]         | 📋     | Combined CLI + MCP server for knowledge base (mem/Rust)                         |
| [[bd-markdown-integration.md]] | 📋     | Connect tasks to project markdown with auto-decomposition                       |
| [[multi-parent-edges.md]]      | 📋     | Target-node severity ladder + `contributes_to` edge urgency propagation via BFS |

## Tier 5: Observability & Learning

How the framework watches itself and improves.

| Spec                             | Status | Purpose                                                                              |
| -------------------------------- | ------ | ------------------------------------------------------------------------------------ |
| [[framework-observability.md]]   | ✅     | Self-reflexive observation pipeline (observe → analyze → improve)                    |
| [[observability.md]]             | ✅     | **SSoT**: files × environments × processes table; $AOPS_SESSIONS retirement analysis |
| [[session-naming-convention.md]] | ✅     | Canonical naming convention for all session artifacts (v4 unified format)            |
| [[feedback-loops.md]]            | ✅     | Structured feedback: observations → heuristic updates                                |
| [[sleep-cycle.md]]               | 📋     | Scheduled consolidation: write-optimised artifacts → read-optimised knowledge        |

**Supporting documents** (schemas and templates, not standalone specs):

| File                                   | Type            | Supports                |
| -------------------------------------- | --------------- | ----------------------- |
| [[session-insights-prompt.md]]         | Prompt template | framework-observability |
| [[session-insights-metrics-schema.md]] | Schema          | framework-observability |

## Tier 6: Task Visibility & UX

How tasks are surfaced, scored, and visualised for the human.

| Spec                       | Status | Purpose                                                         |
| -------------------------- | ------ | --------------------------------------------------------------- |
| [[overwhelm-dashboard.md]] | ✅     | Streamlit dashboard for cognitive load management               |
| [[task-focus-scoring.md]]  | ✅     | Hot/cold classification and ready-queue ranking                 |
| [[task-map.md]]            | ✅     | Network graph visualisation (subsection of overwhelm-dashboard) |

> **Note**: "Intent" is expressed through PKB priority — a small number of P1
> tasks signal current focus. There is no separate intentions spec, config file,
> or tag. The earlier `intentions.yaml` / `intention` tag system was removed
> 2026-03-27; see `docs/VISION.md` for the rationale.

## Archived

Superseded or unowned specs moved to `specs/archived/`:

| Spec                                      | Reason                           | Notes                                     |
| ----------------------------------------- | -------------------------------- | ----------------------------------------- |
| [[archived/pr-process.md]]                | Superseded by [[pr-pipeline.md]] | v1 PR lifecycle                           |
| [[archived/project-context-schema-v1.md]] | Unowned                          | Worker context schema — revisit if needed |

**Merged into other specs** (files deleted):

| Former spec                         | Merged into                                      | Notes                            |
| ----------------------------------- | ------------------------------------------------ | -------------------------------- |
| selective-instruction-injection.md  | [[prompt-hydration.md]] § Optimisation Proposals | Haiku principle filtering        |
| design-reduce-hydration-overhead.md | [[prompt-hydration.md]] § Optimisation Proposals | Investigation overhead reduction |

## Dependency Chains

Major spec dependency chains (changing upstream specs may invalidate downstream):

```
Planning:     effectual-planning-agent → conceptual-review → research-decomposition
Scheduling:   effectual-planning-agent → strategic-triage → daily (recommendations)
              sleep-cycle ↔ strategic-triage (sibling scheduled agents)
Constraints:  workflow-system-spec → workflow-constraints → predicate-registry → constraint-checking-tests
Execution:    non-interactive-agent-workflow → polecat-swarms → polecat-supervision → worker-hypervisor
Observability: observability.md (SSoT: files×envs×processes) → framework-observability → session-insights-prompt → session-insights-metrics-schema → feedback-loops
              session-naming-convention → observability.md
```

## Maintenance

When adding a new spec:

1. Add frontmatter: `status`, `tier`, `depends_on` (list of upstream spec filenames)
2. Add a "Giving Effect" section linking to implementation files
3. Add the spec to the appropriate tier table in this INDEX
4. If the spec supersedes another, add `supersedes:` to frontmatter and move the old spec to `archived/`

## Audit History

- **2026-03-07**: Full audit and rewrite. Inventory grew from 9 indexed to 40 tracked. See [[AUDIT-specs-2026-03-07.md]].
