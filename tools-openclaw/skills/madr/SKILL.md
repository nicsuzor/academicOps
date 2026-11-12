---
name: madr
description: Draft Markdown Architectural Decision Records (MADR) capturing context, considered options, decision outcomes, and consequences. Use when recording an architectural decision, documenting a technical choice, or evaluating design alternatives. Exclude for declarative target-state specifications (use specs) or task planning (use reify).
allowed-tools: Read, Write, Edit
---

# MADR Architectural Decision Records

Author structured Markdown Architectural Decision Records (MADR) to document technical choices, evaluated options, and downstream consequences.

## Structural Anatomy

Every MADR document follows a five-part structure:

1. **Title**: Short title representative of the solved problem and chosen solution (e.g. `# Use SQLite for Session State`).
2. **Context and Problem Statement**: Two to three sentences framing the architectural dilemma, constraints, and forces. Articulate the problem as an objective question where possible.
3. **Considered Options**: Enumerated list of mutually distinct alternatives evaluated to address the problem, including the status quo or simplest baseline.
4. **Decision Outcome**: The chosen option paired with explicit justification explaining why it satisfies decision drivers, resolves specific forces, or outperforms alternatives.
5. **Consequences**: Downstream impacts separated into positive improvements (`* Good, because...`) and accepted trade-offs or operational costs (`* Bad, because...`).

## Drafting Procedure

1. **Load Template**: Read [`template.md`](template.md) for the minimal starting scaffold.
2. **Frame Problem First**: Describe the operational context and forces before detailing solutions. Avoid solution-biased problem statements.
3. **Enumerate Alternatives**: State at least two viable options under `## Considered Options`. Give each option a short descriptive title.
4. **Justify the Choice**: State the chosen option under `## Decision Outcome` with functional reasoning directly addressing the problem statement drivers.
5. **Detail Consequences**: Record positive benefits and negative compromises under `### Consequences`. Acknowledge trade-offs and operational liabilities.

## Invariants and Scope Boundaries

- **Pure Format Guidance**: This skill governs _how_ to draft a MADR. It does not mandate file paths, directory structures, sequential numbering schemes, or review workflows; those belong to repository-specific rules.
- **Brevity**: Maintain high instruction density and concise records (typically 30-60 lines).
- **Immutability**: Decision records document point-in-time rationale. When architecture evolves, record a new decision rather than mutating historical evaluations in place.
