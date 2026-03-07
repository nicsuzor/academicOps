---
title: Specs Folder Audit
type: note
tags:
  - audit
  - framework
  - specs
generated_by: qa
modified: 2026-03-07
---

# Specs Folder Audit — 2026-03-07

## Summary

42 spec files. INDEX.md lists 9. That's a 78% drift rate — most specs aren't tracked, and the INDEX gives no picture of the actual landscape.

Beyond the index rot, the deeper problem is **scope blowout**: the specs describe an extremely ambitious architecture (prompt hydration, multi-agent review, constraint-based workflows, parallel worker swarms, observability pipelines, task scoring algorithms) that has grown organically without pruning. Many specs reference each other in chains 4-5 deep, creating a specification dependency graph that's hard to hold in mind — and harder for agents to navigate.

## The core issues

### 1. INDEX.md is stale and structurally inadequate

Lists 9 of 42 files. Categories ("Core Framework", "Workflow", "Integration") don't reflect the actual landscape. No status tracking. No indication of what's implemented, what's draft, what's superseded.

### 2. Superseded specs still live alongside active ones

`pr-process.md` is superseded by `pr-pipeline-v2.md` but both sit in the same folder with no indication of which is canonical. Same risk exists for any spec that's been revised — readers (including agents) can't tell which version to follow.

### 3. Spec chains create invisible coupling

Several specs form deep dependency chains:

- **Planning chain**: effectual-planning-agent → conceptual-review-workflow → research-decomposition
- **Workflow chain**: workflow-system-spec → workflow-constraints → predicate-registry → constraint-checking-tests
- **Execution chain**: non-interactive-agent-workflow-spec → polecat-swarms → polecat-supervision → worker-hypervisor
- **Context chain**: session-start-injection → project-context-schema-v1 → selective-instruction-injection
- **Observability chain**: framework-observability → session-insights-prompt → session-insights-metrics-schema → feedback-loops

These chains mean changing one spec can invalidate downstream specs without warning. No spec declares its upstream dependencies in frontmatter.

### 4. Overlapping scope without clear boundaries

- `task-map.md` is explicitly "one section of" `overwhelm-dashboard.md` — why is it a separate spec?
- `session-insights-prompt.md` is a prompt template, not really a spec
- `constraint-checking-tests.md` is test cases, not a spec
- `design-reduce-hydration-overhead.md` is a design doc / optimisation proposal, not a spec

These are different document types mixed together without distinction.

### 5. Many specs describe aspirational architecture

Several specs describe systems that don't appear to be implemented (or are partially implemented):

- Constraint-based workflows (workflow-constraints, predicate-registry)
- Verification system advocate agent (phase 1 "not implemented")
- Selective instruction injection (draft optimisation)
- Worker hypervisor (draft)
- Research decomposition (draft)

There's nothing wrong with aspirational specs, but they need to be clearly distinguished from specs that describe _how the system currently works_, otherwise agents will try to follow procedures that don't exist.

## Proposed grouping

### Tier 1: Core Architecture (how the system works today)

These are the specs agents and humans need to understand the current system:

| Spec                       | Status                  | Purpose                              |
| -------------------------- | ----------------------- | ------------------------------------ |
| enforcement.md             | Implemented             | 5-layer enforcement architecture     |
| flow.md                    | Active (v1 implemented) | Core execution loop                  |
| prompt-hydration.md        | Implemented             | Prompt → execution plan pipeline     |
| session-start-injection.md | Active                  | Context loading tiers                |
| hook-router.md             | Active                  | Single dispatch for all hooks        |
| ultra-vires-custodiet.md   | Partial                 | Drift detection agent                |
| workflow-system-spec.md    | Active                  | Markdown-based workflow engine       |
| plugin-architecture.md     | Active                  | Component boundaries (core vs tools) |

### Tier 2: Operational Workflows (procedures for specific work types)

| Spec                     | Status | Purpose                              |
| ------------------------ | ------ | ------------------------------------ |
| pr-pipeline-v2.md        | Active | PR lifecycle (supersedes pr-process) |
| collaborate-workflow.md  | Active | Interactive collaboration sessions   |
| decision-queue-spec.md   | Active | Batch decision processing            |
| daily-briefing-bundle.md | Draft  | Morning briefing document            |
| audit-protocol.md        | Active | Framework audit procedures           |

### Tier 3: Polecat System (parallel execution)

These form a coherent subsystem and could live in their own subfolder:

| Spec                   | Status | Purpose                        |
| ---------------------- | ------ | ------------------------------ |
| polecat-system.md      | Active | Worktree-based agent isolation |
| polecat-swarms.md      | Active | Parallel workers + refinery    |
| polecat-supervision.md | Active | Supervisor workflow            |

### Tier 4: Data Layer & Tools

| Spec                       | Status | Purpose                       |
| -------------------------- | ------ | ----------------------------- |
| work-management.md         | Active | Task CRUD and dependencies    |
| mcp-decomposition-tools.md | Active | Data access for decomposition |
| pkb-server-spec.md         | Active | Knowledge base CLI + MCP      |
| bd-markdown-integration.md | Draft  | Tasks ↔ markdown linking      |

### Tier 5: Observability & Learning

| Spec                       | Status          | Purpose                         |
| -------------------------- | --------------- | ------------------------------- |
| framework-observability.md | Active          | Observation pipeline            |
| feedback-loops.md          | Active          | Observation → framework changes |
| verification-system.md     | Design decision | Verify-first enforcement        |

### Tier 6: Task Visibility & UX

| Spec                   | Status | Purpose                                         |
| ---------------------- | ------ | ----------------------------------------------- |
| overwhelm-dashboard.md | Active | Streamlit dashboard                             |
| task-focus-scoring.md  | Active | Hot/cold task classification                    |
| task-map.md            | Active | Network visualisation (subsection of dashboard) |

### Tier 7: Aspirational / Design Docs (not yet implemented)

| Spec                                   | Status | Purpose                              |
| -------------------------------------- | ------ | ------------------------------------ |
| effectual-planning-agent.md            | Draft  | Strategic planning under uncertainty |
| conceptual-review-workflow.md          | Draft  | Multi-agent iterative review         |
| research-decomposition.md              | Draft  | Research-specific task decomposition |
| non-interactive-agent-workflow-spec.md | Draft  | Full autonomous agent lifecycle      |
| worker-hypervisor.md                   | Draft  | Parallel execution management        |
| workflow-constraints.md                | Draft  | Constraint-based workflow format     |
| predicate-registry.md                  | Draft  | Standard predicate definitions       |
| selective-instruction-injection.md     | Draft  | Optimise context loading             |
| design-reduce-hydration-overhead.md    | Draft  | Reduce hydration latency             |
| project-context-schema-v1.md           | Draft  | Worker context schema                |
| command-intercept.md                   | Draft  | Tool parameter transformation        |

### Should be reclassified (not specs)

| File                               | What it actually is          | Suggested action              |
| ---------------------------------- | ---------------------------- | ----------------------------- |
| session-insights-prompt.md         | Prompt template              | Move to agents/ or skills/    |
| session-insights-metrics-schema.md | Schema definition            | Move alongside implementation |
| constraint-checking-tests.md       | Test cases                   | Move to tests/                |
| pr-process.md                      | Superseded by pr-pipeline-v2 | Archive                       |

## Proposed refactoring actions

### Quick wins (file moves, no content changes)

1. **Archive** `pr-process.md` → `specs/archived/pr-process.md` with a note that pr-pipeline-v2 supersedes it
2. **Reclassify** `session-insights-prompt.md`, `session-insights-metrics-schema.md`, `constraint-checking-tests.md` — move to appropriate locations
3. **Create** `specs/archived/` directory for superseded specs

### INDEX.md rewrite

Rewrite INDEX.md to list all 42 specs (minus reclassified ones) grouped by the tiers above, with status indicators:

- ✅ Implemented / Active
- 🔶 Partial / In Progress
- 📋 Draft / Design
- 🗄️ Archived / Superseded

### Frontmatter standardisation

Add to every spec:

```yaml
status: implemented | active | partial | draft | archived
depends_on: [list of upstream spec filenames]
supersedes: filename (if applicable)
superseded_by: filename (if applicable)
tier: core | workflow | polecat | data | observability | ux | aspirational
```

### Consolidation candidates (content changes, needs human review)

- **task-map.md** into **overwhelm-dashboard.md** — task-map is already declared as a subsection
- **session-insights-prompt + session-insights-metrics-schema** — these support framework-observability and could be appendices rather than standalone specs
- **workflow-constraints + predicate-registry** — tightly coupled, could be one spec with two sections

### Longer-term: scope review

The aspirational tier (11 specs) describes a system significantly more complex than what's running. Worth a deliberate decision: which of these are on the roadmap vs which were exploratory thinking that should be archived? Each aspirational spec that stays creates maintenance burden (other specs reference it, agents may try to follow it, and it needs updating when the architecture evolves).
