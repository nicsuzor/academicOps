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

Who the framework's agents are, what they're allowed to do, how they delegate. Pauli, RBG, James, Marsha, Ida — plus the planner.

- [[agents]] — Agent ecosystem overview
- [[ida]] — Ida agent specification
- [[pauli]] — Pauli agent specification
- [[rbg]] — RBG agent specification
- [[marsha]] — Marsha agent specification
- [[james]] — James agent specification
- [[agent-authority]] — Permissions and skill delegation envelope (frontmatter schema, four-axis permissions model, tool allowlists)

(The content boundary for agent identity files — skill matter & docs out — is enforced by the `/craft` skill; the standalone `agent-definition-content` spec, along with `orchestrator-boundary` and `interactive-coworking`, was retired in the 2026-07 simplification pass.)

### Polecat & supervision — worker dispatch and delegate-and-verify

The execution and supervision architecture: how work is isolated, dispatched, and driven to a proven terminal state. These are subsystem-architecture specs, not agent-identity specs.

- [[polecat-system]] — Ephemeral per-task workspaces, atomic claiming, PR-based merge
- [[supervisor]] — Delegate-and-verify supervision (stateless tick; epic / portfolio / conversational scale)
- [[spec-partial-work-tight-loop-delivery|Partial-work tight-loop delivery]] — Honest partial stops and tight delivery loops

### [[workflows]] — Multi-step processes

The big-W "what to do and in what order" specs. Workflow engine, decomposition, review, PR pipeline, audits, daily briefing, feedback loops.

- [[framework-workflow-expectations]] — How framework workflows differ from project workflows
- [[non-interactive-c1dda99b]] — Headless / CI workflows
- [[research-decomposition]] — Decomposing research outputs
- [[conceptual-review-workflow]] — Reviewing concept documents
- [[pr-pipeline]] — PR pipeline (operative SSoT — two-stage, review-approval-gated, convergent; conflict resolution via the mechanic on admission, §3.11)
- [[feedback-loops]] — Where the framework learns from itself
- [[reconcile]] — GH ↔ PKB close-the-loop reconciliation (agent-invoked)

(`workflow-system-spec`, `workflow-constraints`, `mcp-decomposition-tools`, `strategic-triage`, `audit-protocol`, `daily-briefing-bundle`, `session-digest`, and the `workflows/daily/*` draft bundle were removed in the 2026-07 documentation simplification pass — each described a `bd`-CLI-era mechanism, a sibling PKB/dashboard repo's infrastructure, or an unlanded draft with no live implementation in this repo. See git history if the design intent is needed.)

### [[sessions]] — Session lifecycle

How an agent session starts, hands over, sleeps, and gets its prompt. Plus the YAML format for session handover and the metrics schema.

- [[session-handover-contract]] — End-of-session contract
- [[session-handover-yaml]] — Concrete YAML format (from mem)
- [[session-naming-convention]] — Naming schema
- [[session-start-injection]] — What gets injected at session start
- [[summaries-schema|specs/summaries-schema.md]] — Metrics extracted per session
- [[session-insights-prompt]] — Prompt that drives that extraction

- [[prompt-hydration]] — Just-in-time context loading
- [[hydrator-quality-escalation]] — Escalation when hydration fails

### [[enforcement]] — Rules upheld

The five-layer enforcement model and its implementations.

- [[enforcement]] — Top-level five-layer model
- [[ENFORCEMENT-MAP]] — Axiom × mechanism map, gate lifecycle, pyramid positions (L0–L7)
- [[premise-gate-spec|specs/enforcement/premise-gate.md]] — The premise gate design statement (first executive surface for `judgment-non-delegable`; pairs with the operative instruction file in the remember skill and the review-time twin)

(`enforcement-mechanisms`, `hook-router`, `ultra-vires-enforcer`, and `enforcement-aops-recommender` were retired during the 2026-07 simplification pass — each was a near-duplicate of `ENFORCEMENT-MAP.md`/`GATES.md`/`specs/agents/rbg.md`, which now hold the operative content.)

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

### Plugin system + skill delegation

Plugin agent schema and Skill/Agent invocation semantics are covered inline by [[agent-authority]]; the standalone `plugin-architecture` and `skill-delegation` drafts were retired during the 2026-07 simplification pass as unlanded specs with no live implementation.

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
