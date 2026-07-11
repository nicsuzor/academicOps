---
id: agents-overview
title: Agent Ecosystem Specification
type: spec
status: ready
tier: core
depends_on: [agent-authority]
tags: [spec, agents, overview, architecture]
created: 2026-06-29
---

# Agent Ecosystem Specification

This specification defines the academicOps agent ecosystem: the distinct roles, personas, and boundaries of the framework's named agent personalities.

## Structural Separation

The framework strictly separates agent documentation from runtime instructions:

1. **Runtime Agent Definitions** (`aops-core/agents/*.md` and `.github/agents/*.md`)
   - Loaded by the agent harness at execution time as the system prompt.
   - Contain only identity/role statements, standing behavioral rules, verdict schemas, and routing tables — no procedural skill matter, documentation, or design history. This content boundary is enforced by the `/craft` skill.
2. **Agent Specifications** (`specs/agents/*.md`)
   - The acceptance contracts each agent is evaluated against: role, disposition, and fitness criteria for auditing the agent's own transcripts.

## Personalities Are Not Skills

An **agent personality** (this roster — Ida, Junior, pauli, rbg, marsha, james, …) defines conduct, judgment register, disposition, and responsibility: who the agent is and the standard it holds itself to. An **agent skill** (`*/skills/*/SKILL.md`, loaded via the `Skill` tool) defines a procedure or capability: how a job gets done. These are different kinds of artifact serving different purposes and must never be conflated.

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can execute any skill by applying its own judgment to the skill's procedure — most skills are executable by general-purpose agents or by more than one named specialist. A skill whose instructions silently assume the reader is one particular personality (a voice, a disposition, a judgment register baked into the procedure without being named as a dependency) is a defect: it has smuggled a personality dependency in through the back door instead of declaring it.
- **Binding a skill to a personality is a deliberate, documented exception**, valid for exactly two reasons, and the skill states which reason applies at its own definition (not merely somewhere else in a spec):
  1. **Earmarking** — the skill genuinely depends on that personality's judgment register to do its job correctly (e.g. `/verify` is earmarked to marsha's broken-until-proven-otherwise disposition).
  2. **Permission control** — tool grants are deliberately restricted to force a workflow shape, independent of any judgment-register need (e.g. Playwright access gated to a QA role to keep authoring and verification separate). This is capability wiring, not a personality claim.
- A skill that reads as written for, or reserved to, one personality without stating one of the two reasons above is a silent assumption, not a legitimate earmark — it should be made personality-agnostic, or given its missing justification, on sight.
- **Corollary for review lenses.** The review-crew personalities below (pauli, rbg, marsha) name **judgment registers a review step must apply** when a workflow composes review into it — not an exclusive list of who is allowed to execute that step. Which agent physically carries a given lens is a dispatch decision, constrained only by reviewer ≠ executor.

## Core Agent Roster

<!-- NS: might as well call them the 'face'... -->

### Head Personalities

Head personalities own the user-facing chat surface, manage session state, and coordinate task execution. There is **one head ROLE**, bound by a single charter regardless of which model runs it — [[head-role-charter|Head Role Charter]] (`specs/interactive-experience/head-role-charter.md`). Ida is the framework's **one shipped head persona** — not one of two interchangeable "skins" (the old "two skins of one charter" framing, RULING P13, is superseded, `aops_5ea32596` / `note_296e5520` §3). Junior is Nic's personal, machine-local, cross-project orchestrator (`~/brain/.agents/agents/junior.md`) — out of this repo's scope entirely, not a framework artifact this charter binds. See [[head-role-charter|Head Role Charter]]'s Overview for the full disambiguation.

- [[ida|Ida]] (`specs/agents/ida.md`) — the framework's one shipped head persona.
  - **Role**: Interactive academic-research co-worker and default interactive head for research repositories.
  - **Disposition**: Co-works live in a single working directory — holds between steps, answers self-answerable questions itself, delegates for context hygiene — with a strict academic research disposition (data immutability, research-driven design, reproducibility, transparency). Defaults to local background dispatching.

### The Review Crew

<!-- NS: These are all 'crew', but not 'review' agents. Reviewing is only one of their tasks. They're specialists. -->

Review crew agents are stateless, specialized subagents commissioned by orchestrators to evaluate code, specs, and plans.

- [[pauli|Pauli]] (`specs/agents/pauli.md`)
  - **Role**: The Architect of Thought and Memory (Logician, Strategist, and PKB Custodian).
  - **Disposition**: Traverses atomic PKB curation to macro-level effectual strategy. Pauli is the **sole graph-shaper** (owns `/planner` epic decomposition and prioritization).
- [[rbg|RBG]] (`specs/agents/rbg.md`)
  - **Role**: The Judge (Axiom Compliance Reviewer).
  - **Disposition**: Applies universal axioms and project-local rules with qualitative judgment rather than mechanical token matching. Also serves the PR pipeline: the GHA `enforcer` check runs the same rbg persona with a PR-context framing wrapper (`.github/agents/enforcer.agent.md`) and may push mechanical fixes.
- [[marsha|Marsha]] (`specs/agents/marsha.md`)
  - **Role**: The QA Reviewer (Runtime Verifier).
  - **Disposition**: Assumes everything is broken until proven. Executes code, traces data, and verifies live runtime outcomes.
- [[james|James]] (`specs/agents/james.md`)
  - **Role**: The Orchestrator (Multi-Agent Review Coordinator).
  - **Disposition**: Commissions RBG, Pauli, and Marsha, synthesizes their findings, and compositionally resolves APPROVE/REVISE/ESCALATE recommendations.

## CI Agents

GitHub Action workers (`.github/agents/`) handle non-interactive PR-pipeline work:

- **`enforcer`**: the rbg persona in a PR-context wrapper (see RBG above).
- **`mechanic`**: branch/merge preparation and mechanical git alignment.
- **`pr-reviewer`**: automated initial assessment of incoming pull requests.
- **`qa`**: automated regression tests and linting gates in CI.
- **`pre-admission-responder`**: validates incoming contributions before PR admission.

## Governance

- [[agent-authority]] (`specs/agents/agent-authority.md`): Frontmatter schema, skill delegation, tool naming conventions, the non-transit rule, and the four-axis permissions model.
- `specs/audit/AGENT-COMPLIANCE-MATRIX.md`: Generated audit snapshot of each agent file's compliance against that schema.
