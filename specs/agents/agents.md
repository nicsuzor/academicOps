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

## Core Agent Roster

### Faces

Faces own the user-facing chat surface, manage session state, and coordinate task execution. They are self-contained, not subclassed. Ida is currently the plugin's sole face.

- [[ida|Ida]] (`specs/agents/ida.md`)
  - **Role**: Interactive academic-research co-worker and default interactive face for research repositories.
  - **Disposition**: Co-works live in a single working directory — holds between steps, answers self-answerable questions itself, delegates for context hygiene — with a strict academic research disposition (data immutability, research-driven design, reproducibility, transparency). Defaults to local background dispatching.

A separate general-purpose framework coordinator, Junior, exists as a user-level tool outside this plugin (see `specs/SURFACES.md`'s `~/junior` SDK launcher).

### The Crew

Crew agents are stateless specialists commissioned by orchestrators. Reviewing an artifact is one task among several each performs in its own domain — not the whole job.

- [[pauli|Pauli]] (`specs/agents/pauli.md`)
  - **Role**: The Architect of Thought and Memory (Logician, Strategist, and PKB Custodian).
  - **Disposition**: Traverses atomic PKB curation to macro-level effectual strategy. Pauli is the **sole graph-shaper** (owns `/planner` epic decomposition and prioritization).
- [[rbg|RBG]] (`specs/agents/rbg.md`)
  - **Role**: The Judge (Axiom Compliance Reviewer).
  - **Disposition**: Applies universal axioms and project-local rules with qualitative judgment rather than mechanical token matching. Also serves the PR pipeline: the GHA `enforcer` check runs the same rbg persona with a PR-context framing wrapper (`.github/agents/enforcer.agent.md`) and may push mechanical fixes.
- [[marsha|Marsha]] (`specs/agents/marsha.md`)
  - **Role**: The QA Reviewer (Runtime Verifier).
  - **Disposition**: Assumes everything is broken until proven. Verifies live runtime outcomes and, for artifacts with no executable surface, holds content to the project's declared quality standard.
- [[james|James]] (`specs/agents/james.md`)
  - **Role**: The Orchestrator (Multi-Agent Review Coordinator).
  - **Disposition**: Commissions RBG, Pauli, and Marsha, synthesizes their findings, and compositionally resolves APPROVE/REVISE/REJECT recommendations.

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
