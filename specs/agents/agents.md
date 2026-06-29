---
id: agents-overview
title: Agent Ecosystem Specification
type: spec
status: ready
tier: core
depends_on: [agent-authority, agent-permissions, agent-definition-content]
tags: [spec, agents, overview, architecture]
created: 2026-06-29
---

# Agent Ecosystem Specification

This specification defines the academicOps agent ecosystem, detailing the distinct roles, personas, capabilities, and boundaries of the framework's named agent personalities.

## Structural Separation

To prevent prompt bloat and keep runtime execution cost-effective, the framework strictly separates agent documentation from runtime instructions:

1. **Runtime Agent Definitions** (`aops-core/agents/*.md` and `.github/agents/*.md`)
   - Written in YAML frontmatter and markdown.
   - Loaded by the agent harness at execution time as the system prompt.
   - Bounded strictly by [[agent-definition-content]]: they contain only identity/role statements, standing behavioral rules, verdict schemas, and routing tables. No procedural skill matter, no documentation, no design history.
2. **Agent Specifications / Acceptance Contracts** (`specs/agents/*.md`)
   - The authoritative specifications and design documentation for each agent personality.
   - Serve as the **fitness rubrics** and **acceptance contracts** that the runtime definitions are evaluated against.
   - Enforce qualitative acceptance criteria (ACs), tone guidelines, and failure modes. Read by QA reviewers (like Marsha) to evaluate session transcripts and audit agent behavior.

## Core Agent Roster

The academicOps framework defines six canonical agent personalities, split into two main classes:

### Head Personalities

Head personalities own the user-facing chat surface, manage session state, and coordinate task execution.

- [[junior|Junior]] (`specs/agents/junior.md`)
  - **Role**: General-purpose framework coordinator and default interactive head.
  - **Disposition**: Co-works live, manages tasks, preserves memory in the PKB, and protects the user from detail-grind.
- [[ida|Ida]] (`specs/agents/ida.md`)
  - **Role**: Interactive academic-research co-worker.
  - **Disposition**: Built on the same interactive co-working floor as Junior, but adds a strict academic research disposition (data immutability, research-driven design, reproducibility, transparency). Defaults to local background dispatching.

### The Review Crew

Review crew agents are stateless, specialized subagents commissioned by orchestrators to evaluate code, specs, and plans.

- [[pauli|Pauli]] (`specs/agents/pauli.md`)
  - **Role**: The Architect of Thought and Memory (Logician, Strategist, and PKB Custodian).
  - **Disposition**: Traverses atomic PKB curation to macro-level effectual strategy. Pauli is the **sole graph-shaper** (owns `/planner` epic decomposition and prioritization).
- [[rbg|RBG]] (`specs/agents/rbg.md`)
  - **Role**: The Judge (Axiom Compliance Reviewer).
  - **Disposition**: Applies universal axioms and project-local rules with qualitative judgment rather than mechanical token matching.
- [[marsha|Marsha]] (`specs/agents/marsha.md`)
  - **Role**: The QA Reviewer (Runtime Verifier).
  - **Disposition**: Assumes everything is broken until proven. Executes code, traces data, and verifies live runtime outcomes.
- [[james|James]] (`specs/agents/james.md`)
  - **Role**: The Orchestrator (Multi-Agent Review Coordinator).
  - **Disposition**: Commissions RBG, Pauli, and Marsha, synthesizes their findings, and compositionally resolves APPROVE/REVISE/ESCALATE recommendations.

---

## Sibling & CI Agents

Specialized agent variants exist for automation and non-interactive workflows:

- `enforcer`
  - A compact, Haiku-class variant of RBG.
  - Used in periodic GitHub Actions gates to check axiom compliance on PRs.
  - Derived automatically as a build artifact from the canonical `rbg` specification.
- GitHub Action Workers (`.github/agents/`)
  - **`mechanic`**: Handles branch/merge preparation and mechanical git alignment.
  - **`pr-reviewer`**: Automated initial assessment of incoming pull requests.
  - **`qa`**: Runs automated regression tests and linting gates in CI.
  - **`pre-admission-responder`**: Validates incoming contributions against basic requirements before PR admission.

---

## Governance Specs

- [[agent-authority]] (`specs/agents/agent-authority.md`): Defines the frontmatter schema, skill delegation, tool naming conventions, and the non-transit rule.
- [[agent-permissions]] (`specs/agents/agent-permissions.md`): Defines the four-axis permissions model (tools, mcpServers, bashScopes, fileAccess).
- [[agent-definition-content]] (`specs/agents/agent-definition-content.md`): Governs what is permitted in runtime agent definition files.
- [[agent-compliance-matrix]] (`specs/agents/agent-compliance-matrix.md`): Audits the compliance status of each agent file against specifications.
