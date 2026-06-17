---
title: aops Framework Connectivity Index
type: index
status: ready
tags: [moc, index, connectivity, framework, specs]
---

# academicOps Framework Connectivity Index

**Scope:** canonical source tree (this repository). Read-only analysis. This is a point-in-time snapshot (generated 2026-06-15). It can drift as components/specs change; regenerate by enumerating agents/skills/commands/specs and re-deriving the edges.
**Excluded:** `dist/**` (built artifacts) and `.claude/worktrees/**` (isolated checkouts) — these are
generated/ephemeral copies of the canonical source enumerated below, not separate components.

**Method note.** Skill→spec edges are mostly _not_ declared in skill frontmatter (almost no skill
carries a spec pointer). They are inferred by topic-match against `specs/**`, corroborated by the
spec body naming the component or its `## Giving Effect` block. Where the link is a judgment call or
the spec's pointer is stale, that is stated explicitly rather than asserted. The framework's own
`specs/INDEX.md` is the map-of-content used to anchor agent/workflow specs.

A key structural fact about this framework: **most user-facing slash commands are NOT command files.**
There are only **7 command files** under `aops-core/commands/`. The rest of the "commands" advertised
to users (`/sleep`, `/remember`, `/dump`, `/end-session`, `/verify`, `/dogfood`, `/strategic-review`,
`/supervise`, `/daily`, `/craft`, `/design-rubric`, `/research`, `/project`, `/peer-review`, `/diagram`,
`/pdf`, `/extract`, `/deep-research`, `/analyst`, `/loop`, `/goal`, `/planning`, `/strategy`, `/garden`,
`/densify`, …) are **skill invocations** — the harness exposes a skill by its `name`/`triggers`, not via
a `commands/*.md` file. So "command" in this codebase means specifically one of the 7 thin shortcut
files, each of which delegates to a skill. This is reflected in the tables.

---

## Table 1 — Components → Spec

`Connected? = yes` only where a real backing spec governs the component. "topic-match (judgment)"
means the edge is inferred, not declared.

### Agents (`aops-core/agents/*.md`)

| Component | Type  | Owner agent          | Backing spec (path)                                                                                                       | Spec status                      | Connected? |
| --------- | ----- | -------------------- | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ---------- |
| junior    | agent | (self / coordinator) | `specs/agents/agent-authority.md` + `agent-permissions.md` + `agent-definition-content.md` (govern all agents)            | inbox / inbox / draft            | yes        |
| james     | agent | (self)               | `specs/review-dispatch-topology.md`, `specs/workflows/pr-pipeline-v2.md` (orchestrator role); agent-authority/permissions | ready / operative-phased         | yes        |
| marsha    | agent | (self)               | `specs/agents/agent-permissions.md`; `specs/workflows/pr-pipeline-v2.md`; QA role in `review-dispatch-topology.md`        | inbox / operative-phased / ready | yes        |
| pauli     | agent | (self)               | `specs/agents/effectual-planning-agent.md` (planner/strategist role); agent-authority/permissions                         | ready                            | yes        |
| rbg       | agent | (self)               | `specs/enforcement/ultra-vires-enforcer.md`, `specs/enforcement/enforcement.md`; agent-permissions                        | ready / ready                    | yes        |

### Agents (`.github/agents/*.md` — PR-pipeline / CI agents)

| Component             | Type           | Owner agent       | Backing spec (path)                                                                         | Spec status                          | Connected?     |
| --------------------- | -------------- | ----------------- | ------------------------------------------------------------------------------------------- | ------------------------------------ | -------------- |
| pr-reviewer           | agent          | (CI)              | `specs/workflows/pr-pipeline-v2.md` + `pr-pipeline.md`; `specs/review-dispatch-topology.md` | operative-phased / operative / ready | yes            |
| qa                    | agent          | (CI)              | `specs/workflows/pr-pipeline-v2.md`; `specs/workflows/framework-workflow-expectations.md`   | operative-phased / ready             | yes            |
| mechanic              | agent          | (CI)              | `specs/workflows/pr-pipeline-v2.md` (Stage-2 dev / admitted fix loop)                       | operative-phased                     | yes            |
| enforcer              | agent          | (CI; RBG framing) | `specs/enforcement/ultra-vires-enforcer.md`, `specs/enforcement/enforcement.md`             | ready / ready                        | yes            |
| shared-error-handling | agent fragment | n/a               | — (shared include, not a standalone agent)                                                  | —                                    | n/a (fragment) |

### Skills — `aops-core/skills/`

| Component        | Type  | Owner agent                      | Backing spec (path)                                                                                                                               | Spec status              | Connected?            |
| ---------------- | ----- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | --------------------- |
| aops             | skill | (none declared)                  | — (no governing spec found; it is the core institutional-memory skill)                                                                            | —                        | **no**                |
| cowork-sync      | skill | (none)                           | `specs/plugins/plugin-architecture.md` (cowork build packaging) — weak/partial                                                                    | ready                    | ambiguous             |
| craft            | skill | pauli                            | `specs/workflows/framework-workflow-expectations.md` (instruction quality) — topic-match (judgment)                                               | ready                    | ambiguous             |
| daily            | skill | pauli                            | `specs/workflows/daily-briefing-bundle.md` + `specs/workflows/daily/*` (the daily workflow tree)                                                  | inbox / mixed            | yes                   |
| design-rubric    | skill | pauli                            | `specs/future/kb-385bd253-review-lenses-library-specification.md` (review lenses) — topic-match (judgment)                                        | none(fm)                 | ambiguous             |
| dogfood          | skill | (none)                           | `specs/future/dogfood.md`                                                                                                                         | none(fm)                 | yes                   |
| dump             | skill | pauli (claims)                   | — (no governing spec; emergency-bail counterpart to end_session)                                                                                  | —                        | **no**                |
| end_session      | skill | (none)                           | `specs/workflows/session-digest.md`; `specs/GATES.md` (session-close gate) — topic-match                                                          | draft / none(fm)         | yes                   |
| planner          | skill | pauli                            | `specs/agents/effectual-planning-agent.md` (spec's `Giving Effect` points to a stale `skills/planning/` path; planner is the live implementation) | ready                    | yes (link stale)      |
| project          | skill | (none)                           | `specs/future/spec-967126cf-…-project-scaffold-redesign….md` (redesign target, not current)                                                       | proposed                 | ambiguous             |
| remember         | skill | pauli                            | `specs/workflows/feedback-loops.md` + sessions/`sleep-cycle` specs (consolidation) — topic-match                                                  | ready                    | yes                   |
| research         | skill | (none)                           | — (no dedicated spec; research methodology guardian)                                                                                              | —                        | **no**                |
| sleep            | skill | pauli                            | superseded_by `remember`; backed historically by the sleep-cycle/consolidation specs                                                              | —                        | yes (deprecated stub) |
| strategic-review | skill | (none; deploys rbg/pauli/marsha) | `specs/review-dispatch-topology.md`                                                                                                               | ready                    | yes                   |
| supervisor       | skill | (none)                           | `specs/agents/supervisor.md`                                                                                                                      | ready                    | yes                   |
| survey           | skill | junior                           | `specs/workflows/session-digest.md`, `specs/workflows/feedback-loops.md`, `specs/ENFORCEMENT-MAP.md` (referenced in body)                         | draft / ready / none(fm) | yes                   |
| verify           | skill | marsha                           | `specs/workflows/audit-protocol.md`; `specs/GATES.md`; design-rubric pairing                                                                      | ready / none(fm)         | yes                   |

### Skills — `aops-tools/skills/`

| Component     | Type  | Owner agent | Backing spec (path)                                                                                     | Spec status | Connected? |
| ------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------- | ----------- | ---------- |
| analyst       | skill | (none)      | `specs/workflows/workflow-system-spec.md` (transformation-layer) — topic-match (judgment)               | inbox       | ambiguous  |
| deep-research | skill | (none)      | `specs/workflows/research-decomposition.md` — topic-match (judgment)                                    | in_progress | ambiguous  |
| diagram       | skill | (none)      | — (no governing spec found)                                                                             | —           | **no**     |
| extract       | skill | (none)      | `specs/future/skills/*` (fact-check/ground-truth/training-set-builder are extraction backlog) — partial | none(fm)    | ambiguous  |
| pdf           | skill | (none)      | `specs/workflows/daily/40-pdf-render.md` (render leg) — partial                                         | none(fm)    | ambiguous  |
| peer-review   | skill | (none)      | `specs/workflows/conceptual-review-workflow.md` — topic-match (judgment)                                | ready       | ambiguous  |
| style         | skill | (none)      | — (no governing spec found)                                                                             | —           | **no**     |

### Skills — `aops-extras/skills/` (tech-specific HOW layers under the analyst skill)

| Component  | Type  | Owner agent | Backing spec (path)                            | Spec status | Connected? |
| ---------- | ----- | ----------- | ---------------------------------------------- | ----------- | ---------- |
| dbt        | skill | (none)      | — (HOW layer for `analyst`; no dedicated spec) | —           | **no**     |
| streamlit  | skill | (none)      | — (HOW layer for `analyst`; no dedicated spec) | —           | **no**     |
| python-viz | skill | (none)      | — (HOW layer for `analyst`; no dedicated spec) | —           | **no**     |

### Commands — `aops-core/commands/` (the only 7 command files; each delegates to a skill)

| Component    | Type    | Delegates to skill                                      | Backing spec (via skill)                                                              | Spec status   | Connected?        |
| ------------ | ------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------- | ----------------- |
| /bump        | command | (none — inline one-liner "you seem stuck, continue")    | —                                                                                     | —             | **no**            |
| /dispatch    | command | `task-lifecycle` (dispatch mode) → background worker    | via task-lifecycle: `specs/agents/supervisor.md`; references `[[premise-gate]]`       | ready         | yes               |
| /email       | command | (workflow, not a skill) → `[[workflows/email-capture]]` | `specs/workflows/daily/20-email-capture.md`                                           | none(fm)      | yes (to workflow) |
| /issue-sweep | command | `survey` (sweep mode) → dispatches `jr`                 | via survey: `specs/ENFORCEMENT-MAP.md`, session-digest                                | mixed         | yes               |
| /learn       | command | `survey` (retro mode) → dispatches `pauli`              | via survey                                                                            | mixed         | yes               |
| /maintain    | command | `planner` (maintain mode)                               | via planner: `specs/agents/effectual-planning-agent.md`; `specs/workflows/densify.md` | ready / inbox | yes               |
| /pull        | command | `task-lifecycle` (execute mode) → inline claim+run      | via task-lifecycle: `specs/agents/supervisor.md`; references `[[premise-gate]]`       | ready         | yes               |
| /q           | command | `planner` (capture mode)                                | via planner                                                                           | ready         | yes               |

---

## Table 2 — Specs → Component

`Connected? = no ⇒ ORPHANED` (no live agent/skill/command implements or is governed by it).
Statuses are from frontmatter (`NONE` = no `status:` field).

| Spec (path)                                                                            | Status           | Implementing component(s)                                                              | Connected?          |
| -------------------------------------------------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------- | ------------------- |
| specs/agents/agent-authority.md                                                        | inbox            | all 5 aops-core agents (authority envelope)                                            | yes                 |
| specs/agents/agent-compliance-matrix.md                                                | ready            | audit artifact over the agents                                                         | yes                 |
| specs/agents/agent-definition-content.md                                               | draft            | all agent-def files (content boundary)                                                 | yes                 |
| specs/agents/agent-permissions.md                                                      | inbox            | all agents (tool allowlists)                                                           | yes                 |
| specs/agents/effectual-planning-agent.md                                               | ready            | `planner` skill / `pauli` (spec's own link to `skills/planning/` is **stale**)         | yes (stale link)    |
| specs/agents/orchestrator-boundary.md                                                  | inbox            | junior / CLI orchestrator boundary                                                     | yes                 |
| specs/agents/polecat-system.md                                                         | ready            | polecat dispatch (external `polecat/cli.py`; not a skill/agent in this tree)           | yes (ext component) |
| specs/agents/supervisor.md                                                             | ready            | `supervisor` skill; `task-lifecycle` skill; `/pull` + `/dispatch`                      | yes                 |
| specs/audit/AGENT-COMPLIANCE-MATRIX.md                                                 | NONE             | audit snapshot (governs agents)                                                        | yes                 |
| specs/audit/AGENT-REMEDIATION-BACKLOG.md                                               | NONE             | audit backlog (governs agents)                                                         | yes                 |
| specs/audit/AGENT-TOOLS.md                                                             | NONE             | agent tool inventory                                                                   | yes                 |
| specs/CAPABILITIES.md                                                                  | NONE             | framework-wide reference (no single component)                                         | partial             |
| specs/CONSTRAINTS.md                                                                   | NONE             | enforcement layer / all agents                                                         | yes                 |
| specs/DEPLOYMENTS.md                                                                   | NONE             | build/release (`scripts/build.py`, dist surfaces)                                      | yes                 |
| specs/enforcement/auto-mode-classifier.md                                              | draft            | hook layer (enforcement hooks, external to skills)                                     | yes                 |
| specs/enforcement/enforcement-aops-recommender.md                                      | inbox            | hook layer (aops recommender hook)                                                     | yes                 |
| specs/enforcement/enforcement.md                                                       | ready            | enforcer agent / rbg / hook layer                                                      | yes                 |
| specs/enforcement/enforcement-mechanisms.md                                            | inbox            | hook layer                                                                             | yes                 |
| specs/enforcement/hook-router.md                                                       | ready            | hook router (hooks layer)                                                              | yes                 |
| specs/ENFORCEMENT-MAP.md                                                               | NONE             | enforcement map; referenced by `survey` skill                                          | yes                 |
| specs/enforcement/ultra-vires-enforcer.md                                              | ready            | rbg / enforcer agent                                                                   | yes                 |
| specs/future/cluster-1122-coordinator-relay-remediation.md                             | proposed         | (future backlog)                                                                       | **no — ORPHAN**     |
| specs/future/constraint-checking-tests.md                                              | inbox            | (future backlog)                                                                       | **no — ORPHAN**     |
| specs/future/dogfood.md                                                                | NONE             | `dogfood` skill                                                                        | yes                 |
| specs/future/kb-385bd253-review-lenses-library-specification.md                        | NONE             | (future; loosely → design-rubric, not built)                                           | **no — ORPHAN**     |
| specs/future/plugin-consolidation.md                                                   | inbox            | (future backlog)                                                                       | **no — ORPHAN**     |
| specs/future/polecat-dispatch-from-container-via-ssh.md                                | accepted         | (superseded by local-docker model; not built)                                          | **no — ORPHAN**     |
| specs/future/predicate-registry.md                                                     | inbox            | (future backlog)                                                                       | **no — ORPHAN**     |
| specs/future/skill-delegation.md                                                       | inbox            | (future; describes skill-delegation envelope — not a single component)                 | **no — ORPHAN**     |
| specs/future/skills/fact-check.md                                                      | NONE             | (future skill, not built; nearest: `extract`)                                          | **no — ORPHAN**     |
| specs/future/skills/ground-truth.md                                                    | NONE             | (future skill, not built)                                                              | **no — ORPHAN**     |
| specs/future/skills/osb-drafting.md                                                    | NONE             | (future skill, not built)                                                              | **no — ORPHAN**     |
| specs/future/skills/review.md                                                          | NONE             | (future skill, not built; nearest: strategic-review)                                   | **no — ORPHAN**     |
| specs/future/skills/review-training.md                                                 | NONE             | (future skill, not built)                                                              | **no — ORPHAN**     |
| specs/future/skills/training-set-builder.md                                            | NONE             | (future skill, not built)                                                              | **no — ORPHAN**     |
| specs/future/spec-967126cf-…project-scaffold-redesign….md                              | proposed         | (future redesign of `project` skill — not built)                                       | **no — ORPHAN**     |
| specs/GATES.md                                                                         | NONE             | enforcement gates; end_session/verify                                                  | yes                 |
| specs/INDEX.md                                                                         | ready            | map-of-content (meta; governs no component)                                            | partial (MoC)       |
| specs/meta/AUDIT-specs-2026-03-07.md                                                   | NONE             | audit snapshot (meta)                                                                  | partial (audit)     |
| specs/meta/doc-taxonomy.md                                                             | NONE             | doc taxonomy reference (meta)                                                          | partial (meta)      |
| specs/observability/evidence-driven-debugging.md                                       | ready            | (methodology doc; no single component)                                                 | **no — ORPHAN**     |
| specs/observability/framework-observability.md                                         | ready            | observability tooling (hooks/metrics; no skill)                                        | partial             |
| specs/observability/observability.md                                                   | ready            | observability layer                                                                    | partial             |
| specs/plugins/plugin-architecture.md                                                   | ready            | `scripts/build.py` / plugin packaging                                                  | yes                 |
| specs/polecat/spec-partial-work-tight-loop-delivery.md                                 | draft            | polecat workers (external)                                                             | yes (ext)           |
| specs/releases/release-publish-pipeline.md                                             | operative-target | `scripts/build.py` / release CI                                                        | yes                 |
| specs/releases/v0.4-integrity-and-security.md                                          | draft            | release milestone (multi-component)                                                    | partial             |
| specs/review-dispatch-topology.md                                                      | ready            | `strategic-review` skill; james/rbg/pauli/marsha                                       | yes                 |
| specs/session-insights-metrics-schema.md                                               | ready            | session metrics extraction (hooks/digest)                                              | yes                 |
| specs/SURFACES.md                                                                      | NONE             | surface reference (governs many components)                                            | yes                 |
| specs/workflows/audit-protocol.md                                                      | ready            | `verify` skill                                                                         | yes                 |
| specs/workflows/conceptual-review-workflow.md                                          | ready            | `peer-review` skill (topic-match)                                                      | ambiguous           |
| specs/workflows/daily/00-architecture.md                                               | NONE             | `daily` skill                                                                          | yes                 |
| specs/workflows/daily/10-daily-orchestrator.md                                         | NONE             | `daily` skill                                                                          | yes                 |
| specs/workflows/daily/20-email-capture.md                                              | NONE             | `/email` command                                                                       | yes                 |
| specs/workflows/daily/30-news-briefing.md                                              | NONE             | `daily` skill / news leg                                                               | yes                 |
| specs/workflows/daily/40-pdf-render.md                                                 | NONE             | `pdf` skill / daily render leg                                                         | yes                 |
| specs/workflows/daily/50-aops-core-vs-tools.md                                         | NONE             | packaging boundary (meta)                                                              | partial             |
| specs/workflows/daily/60-importance-escalation.md                                      | NONE             | `daily` skill (escalation model)                                                       | yes                 |
| specs/workflows/daily-briefing-bundle.md                                               | inbox            | `daily` skill                                                                          | yes                 |
| specs/workflows/daily/README.md                                                        | NONE             | daily workflow tree index                                                              | partial             |
| specs/workflows/densify.md                                                             | inbox            | `planner` skill (maintain/densify mode); `/maintain`                                   | yes                 |
| specs/workflows/feedback-loops.md                                                      | ready            | `survey`/`remember` skills; `/learn`                                                   | yes                 |
| specs/workflows/framework-workflow-expectations.md                                     | ready            | qa agent / framework workflows                                                         | yes                 |
| specs/workflows/mcp-decomposition-tools.md                                             | ready            | PKB MCP decomposition tools (external)                                                 | yes (ext)           |
| specs/workflows/non-interactive-agent-workflow-spec.md                                 | ready            | polecat / headless workers                                                             | yes                 |
| specs/workflows/pr-pipeline.md                                                         | operative        | pr-reviewer/qa/mechanic agents (v1, superseded by v2)                                  | yes                 |
| specs/workflows/pr-pipeline-v2.md                                                      | operative-phased | pr-reviewer/qa/mechanic/james                                                          | yes                 |
| specs/workflows/pr-state-index.md                                                      | NONE             | PR state tracking (CI; no skill)                                                       | partial             |
| specs/workflows/reconcile.md                                                           | ready            | reconcile workflow (agent-invoked; no dedicated skill — nearest: remember/end_session) | ambiguous           |
| specs/workflows/research-decomposition.md                                              | in_progress      | `deep-research` skill (topic-match); planner                                           | ambiguous           |
| specs/workflows/session-digest.md                                                      | draft            | session digest job; survey/end_session                                                 | yes                 |
| specs/workflows/spec-64352eac-planner-pre-dispatch-decomposition-gate.md               | ready            | `planner` / `/pull` + `/dispatch` premise gate                                         | yes                 |
| specs/workflows/spec-7715b135-capture-execute-review-pipeline-consolidation-roadmap.md | NONE             | roadmap (consolidation of capture/execute/review; multi-component)                     | partial (roadmap)   |
| specs/workflows/strategic-triage.md                                                    | inbox            | `planner` skill / triage routing                                                       | yes                 |
| specs/workflows/workflow-constraints.md                                                | in_progress      | workflow engine constraints                                                            | partial             |
| specs/workflows/workflow-system-spec.md                                                | inbox            | workflow engine (no single skill; `analyst` topic-match)                               | ambiguous           |

---

## Section 3 — The disconnects (full outer join NULLs)

### 3a. Components with NO backing spec (left-side orphans)

Agents — none. All 5 aops-core agents and all 4 `.github` CI agents are governed by at least one spec
(`agent-authority`/`agent-permissions`/`agent-definition-content`, or the pr-pipeline/enforcement specs).

Skills with NO governing spec at all:

- **aops** (the core institutional-memory/coordination skill — no spec governs it)
- **dump** (emergency-bail; no spec — only its counterpart `end_session` has session-close specs)
- **research** (research-methodology guardian; no dedicated spec)
- **diagram** (`aops-tools`; no spec)
- **style** (`aops-tools`; no spec)
- **dbt**, **streamlit**, **python-viz** (`aops-extras`; tech-specific HOW layers under `analyst`, no dedicated specs)

Commands with NO backing spec (independent of skill mapping):

- **/bump** (inline one-liner; delegates to nothing, governed by nothing)

Ambiguous (a topic-matching spec exists but the edge is inferred, not declared — flagged, not asserted):
`cowork-sync`, `craft`, `design-rubric`, `project`, `analyst`, `deep-research`, `extract`, `pdf`, `peer-review`.

### 3b. Specs with NO implementing component (right-side orphans — ORPHANED)

Confirmed orphans (no live agent/skill/command gives them effect):

- `specs/future/cluster-1122-coordinator-relay-remediation.md` (proposed)
- `specs/future/constraint-checking-tests.md` (inbox)
- `specs/future/kb-385bd253-review-lenses-library-specification.md` (review-lenses library — not built)
- `specs/future/plugin-consolidation.md` (inbox)
- `specs/future/polecat-dispatch-from-container-via-ssh.md` (accepted, but superseded by the local-docker model — dead)
- `specs/future/predicate-registry.md` (inbox)
- `specs/future/skill-delegation.md` (inbox)
- `specs/future/skills/fact-check.md`, `ground-truth.md`, `osb-drafting.md`, `review.md`, `review-training.md`, `training-set-builder.md` (six unbuilt future skills)
- `specs/future/spec-967126cf-…project-scaffold-redesign….md` (proposed redesign of `project`, not built)
- `specs/observability/evidence-driven-debugging.md` (methodology doc; no implementing component)

**On the named candidate `effectual-planning-agent.md`:** NOT a clean orphan. Its `## Giving Effect`
block links `[[skills/planning/SKILL.md]]`, which is a **stale path** (the live skill is
`aops-core/skills/planner/`), but the `planner` skill (owned by `pauli`) is unambiguously its
implementation — the planner SKILL.md even carries "effectual planning" as a trigger. So the spec is
connected; the _wikilink inside it is broken_. Worth flagging as a hygiene fix, not an orphan.

Reference/meta specs that govern no single component (not "orphans" in the same sense, but they have
no implementing component): `specs/CAPABILITIES.md`, `specs/INDEX.md` (MoC), `specs/meta/*`,
`specs/workflows/daily/50-aops-core-vs-tools.md`, `specs/workflows/daily/README.md`,
`specs/workflows/spec-7715b135-…roadmap.md`, `specs/releases/v0.4-integrity-and-security.md`.

### 3c. Skills with NO owner agent (frontmatter `owner:` absent)

Owned skills: `craft`, `daily`, `design-rubric`, `planner`, `remember`, `sleep` → **pauli**; `survey` →
**junior**. (`dump` is _claimed_ by pauli in the pauli agent body — "You own ... `/dump`" — but the
dump SKILL.md frontmatter carries **no `owner:` field**, so the ownership is asserted on the agent
side only, not declared on the skill.)

Skills with no `owner:` at all:

- aops-core: **aops, cowork-sync, dogfood, dump, end_session, project, research, strategic-review, supervisor, verify**
  (`verify` is described as "Owned by marsha" in its description prose but has **no `owner:`
  frontmatter field** — same asymmetry as dump.)
- aops-tools: **analyst, deep-research, diagram, extract, pdf, peer-review, style** (all unowned)
- aops-extras: **dbt, streamlit, python-viz** (all unowned)

### 3d. Agents owning NO skill (no skill's `owner:` frontmatter names them)

- **junior** — owns `survey` only (and it is the default coordinator; owns the chat surface, not skills per se).
- **james** — owns no skill (orchestrator; _invoked by_ `strategic-review` but not its declared owner).
- **marsha** — owns no skill by frontmatter (`verify` names her only in prose, not in `owner:`).
- **rbg** — owns no skill (judge/enforcer; backed by enforcement specs, not a skill).
- `.github` CI agents (**pr-reviewer, qa, mechanic, enforcer**) — own no skills (CI roles).

Only **pauli** (6 skills) and **junior** (1 skill) actually own skills via frontmatter.

### 3e. Commands not mapped to any skill

Of the 8 command files:

- **/bump** — maps to no skill (inline one-liner).
- **/email** — delegates to a **workflow** (`[[workflows/email-capture]]`), not a skill.
- /pull → `task-lifecycle` (execute mode); /dispatch → `task-lifecycle` (dispatch mode); /issue-sweep → `survey`; /learn → `survey`; /maintain → `planner`; /q → `planner` (these 6 do delegate to a skill).

---

## Count summary

- **Agents:** 9 total — 5 canonical (`aops-core/agents/`: junior, james, marsha, pauli, rbg) + 4 CI (`.github/agents/`: pr-reviewer, qa, mechanic, enforcer). (`shared-error-handling.md` is a shared include, not an agent.)
- **Skills:** 27 total — 17 `aops-core` + 7 `aops-tools` + 3 `aops-extras`.
- **Commands:** 8 total (`aops-core/commands/`: bump, dispatch, email, issue-sweep, learn, maintain, pull, q).
- **Specs:** 75 total under `specs/**`.

**Orphan counts:**

- Components with NO backing spec: **8 skills** (aops, dump, research, diagram, style, dbt, streamlit, python-viz) + **1 command** (/bump). Plus 9 skills in the "ambiguous, inferred-only" bucket.
- Specs with NO implementing component (ORPHANED): **17** confirmed (15 `future/*` + `observability/evidence-driven-debugging.md`; the stale-link caveat on effectual-planning is NOT counted as orphan). Plus ~7 reference/meta specs that govern no single component.
- Skills with NO owner agent: **20 of 27**.
- Agents owning NO skill: **7 of 9** (all except pauli and junior).
- Commands not mapped to any skill: **2 of 8** (/bump, /email).
