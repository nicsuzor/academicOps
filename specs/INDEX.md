---
id: specs-9ec81937
title: aops Specs Index
type: index
status: ready
tags: [moc, index, framework, specs]
---

# aops Specs — Map of Content

Single entry point to the unified spec tree for the [[AcademicOps]] framework, the [[mem]] PKB tool, and the [[overwhelm dashboard]]. Reorganised by concern, not by source repo — the three components are one system, and the specs cluster naturally by what they describe (agents, sessions, enforcement, the PKB itself, the dashboard, etc.) regardless of which repo they originated in.

> Path hierarchy is a navigation aid for humans, not a semantic claim. The PKB graph is denser and more complex than this filesystem tree. Wikilinks and frontmatter carry the real edges.

## Provenance

Consolidated from:

- `academicOps/specs/*` — framework architecture, agents, enforcement, sessions, hydration
- `academicOps/specs/future/*` — backlog specs not yet built
- `academicOps/docs/VISION.md` → [[vision]]
- `mem/docs/specs/*` — PKB graph operations and dashboard view specs
- `mem/overwhelm-dashboard/{spec,DESIGN,docs/data-pipeline,qa}` — dashboard design and QA reports

## Subdirectories

### [[agents]] — Identity, authority, roles

Who the framework's agents are, what they're allowed to do, how they delegate. Pauli, Ruth, James, Marsha, Jr — plus the planner, supervisor, polecats, and the orchestrator boundary.

- [[agent-authority]] — Permissions and skill delegation envelope
- [[agent-permissions]] — Tool allowlists per agent
- [[agent-definition-content]] — Content boundary for agent identity files (skill matter & docs out)
- [[agent-compliance-matrix]] — Audit state against authority spec
- [[supervisor]] — Unified supervision architecture (swarm, burst, hypervisor)
- [[effectual-planning-agent]] — Planner agent design
- [[orchestrator-boundary]] — CLI orchestrator authority boundary
- [[polecat-system]] — Distributed worker dispatch

### [[workflows]] — Multi-step processes

The big-W "what to do and in what order" specs. Workflow engine, decomposition, review, PR pipeline, audits, daily briefing, feedback loops.

- [[workflow-system-spec]] — The workflow engine
- [[workflow-constraints]] — What workflows can and can't do
- [[framework-workflow-expectations]] — How framework workflows differ from project workflows
- [[non-interactive-c1dda99b]] — Headless / CI workflows
- [[research-decomposition]] — Decomposing research outputs
- [[mcp-decomposition-tools]] — Decomposition primitives in PKB MCP
- [[strategic-triage]] — Where strategic work routing happens
- [[conceptual-review-workflow]] — Reviewing concept documents
- [[pr-pipeline]] — Pull request lifecycle (v1, superseded; describes operative merge-prep until v2 Phase 5)
- [[pr-pipeline-v2]] — PR pipeline v2 (operative, phased — two-stage, Environment-gated, convergent; Phase 1 shipped)
- [[audit-protocol]] — Framework audit standard
- [[daily-briefing-bundle]] — `/daily` skill bundle
- [[60-importance-escalation|workflows/daily/60-importance-escalation]] — Importance-to-visibility escalation model
- [[session-digest]] — Scheduled cheap-model intra-day narrative digest (draft — feeds dashboard US-D3, /daily, /learn)
- [[feedback-loops]] — Where the framework learns from itself
- [[reconcile]] — GH ↔ PKB close-the-loop reconciliation (agent-invoked)

### [[sessions]] — Session lifecycle

How an agent session starts, hands over, sleeps, and gets its prompt. Plus the YAML format for session handover and the metrics schema.

- [[session-handover-contract]] — End-of-session contract
- [[session-handover-yaml]] — Concrete YAML format (from mem)
- [[session-naming-convention]] — Naming schema
- [[session-start-injection]] — What gets injected at session start
- [[session-insights-metrics-schema]] — Metrics extracted per session
- [[session-insights-prompt]] — Prompt that drives that extraction
- [[sleep-cycle]] — The periodic consolidation skill
- [[prompt-hydration]] — Just-in-time context loading
- [[hydrator-quality-escalation]] — Escalation when hydration fails

### [[enforcement]] — Rules upheld

The five-layer enforcement model and its implementations.

- [[enforcement]] — Top-level five-layer model
- [[enforcement-mechanisms]] — Concrete mechanisms per layer
- [[ENFORCEMENT-MAP]] — Axiom × mechanism map, gate lifecycle, pyramid positions (L0–L7)
- [[enforcement-aops-recommender]] — The aops-recommender pattern
- [[hook-router]] — Hook dispatching
- [[ultra-vires-enforcer]] — Authority envelope checker

### [[pkb]] — Knowledge base core

The PKB itself: server, taxonomy, graph operations, ranking, planning. From both academicOps (server-spec, taxonomy, areas-not-projects) and mem (batch-graph-operations, task-focus-scoring, planning-web).

- [[pkb-server-spec]] — `pkb` binary (CLI + MCP server)
- [[pkb-type-taxonomy]] — Node type categories (actionable / reference / structural)
- [[work-management]] — Task lifecycle and graph insertion
- [[multi-parent-edges]] — Tasks with multiple parents
- [[areas-not-projects]] — Why some things are areas, not projects
- [[batch-graph-operations]] — Batch CRUD over the graph (mem)
- [[task-focus-scoring]] — Focus score algorithm (mem)
- [[planning-web]] — Web of plans / dashboard data model (mem)

> See also [[TAXONOMY|aops-core/skills/remember/references/TAXONOMY.md]] — the canonical taxonomy of types, statuses, and edges (in academicOps repo, not brain).

### [[dashboard]] — Overwhelm dashboard + mem views

The Svelte overwhelm dashboard and the mem PKB view specs that feed it. Same surface, different layers.

- [[spec|dashboard/spec]] — Top-level dashboard spec (overwhelm)
- [[design|dashboard/design]] — Visual design system (overwhelm DESIGN.md)
- [[data-pipeline|dashboard/data-pipeline]] — Pipeline from session dumps to dashboard widgets
- [[theme-guide]] — Visual theme rules
- [[view-dashboard]] — "Health of my work" view
- [[view-focus]] — "What should I do right now?" view
- [[view-graph]] — "How does my work connect?" view
- [[view-epic-tree]] — Epic decomposition view
- [[view-metro]] — Metro / timeline view
- [[view-node-detail]] — "What is this thing?" view
- [[view-assumptions]] — Assumption tracker
- [[view-duplicates]] — Duplicate finder
- [[qa|dashboard/qa]] — QA reports against the dashboard

### [[observability]] — Logs, metrics, debugging

How the framework reports on itself and how agents debug it.

- [[framework-observability]] — Top-level observability design
- [[observability]] — Lower-level component observability
- [[evidence-driven-debugging]] — Debugging discipline

### [[plugins]] — Plugin system + skill delegation

How third-party capability is plugged in, and how skills delegate to other skills.

- [[plugin-architecture]] — Plugin model
- [[skill-delegation]] — Skill-invokes-skill semantics

### [[meta]] — Audits over the spec set itself

- [[AUDIT-specs-2026-03-07]] — Spec audit snapshot

### [[future]] — Backlog specs (not yet built)

Future state design — separated to keep the active spec tree from being polluted with not-yet-real things.

- [[predicate-registry]]
- [[plugin-consolidation]]
- [[constraint-checking-tests]]
- [[dogfood]]
- And [[future/skills|future/skills]] — six speculative skill specs (review, review-training, ground-truth, fact-check, training-set-builder, osb-drafting)

## See also

- [[aops|projects/aops/aops]] — Project hub
- [[vision]] — Why the framework exists
- [[TAXONOMY]] — Canonical taxonomy (lives in academicOps, not brain)
- [[KNOWLEDGE.md]] — PKB system principles
- [[densify]] — Workflow that progressively wikilinks the PKB (spec under [[workflows]])
