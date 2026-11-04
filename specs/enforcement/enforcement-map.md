---
title: Enforcement Map
status: ready
---

# Enforcement Map

The enforcement map is a concise cross-reference table that shows what kind of enforcement is applied to each rule, and is not a summary of specifications or workflows. When editing the enforcement map, every row must only reference a specific rule derived from our axioms and applicable to agents working in any third-party project. Workflows are not rules and do not enforce rules; creating or modifying workflows must not produce token enforcement map rows, as the only applicable rule is "agents must follow workflows given to them" and nothing more than that. It documents the empirical distribution of active behavioral controls across the framework, providing auditors and framework architects with the mechanism category, intervention severity, and verification coordinates for each governed axiom-derived rule.

## User stories

### US-1 Cross-Referencing Rule Enforcement

As a framework architect, reviewer, or auditor, I want a concise cross-reference table showing what kind of enforcement is applied to each axiom-derived rule applicable across any third-party project, so that I can inspect active regulatory measures, evaluate proportionality, and identify enforcement gaps without reading narrative specifications or searching workflow implementations.

- **AC-1.1** Given any governed rule derived from our axioms and applicable to agents working in any third-party project, when an auditor inspects the table, then the entry identifies the rule name, its carrier mechanism category, its intervention severity, and its verification coordinates within a four-column row.
- **AC-1.2** Given an axiom-derived rule governed by multi-carrier or non-instruction mechanisms, when an auditor reviews its entry, then all active carrier categories (`structural`, `process`, `JIT injection`, `post-hoc`) and their corresponding severities are listed.
- **AC-1.3** Given an enforcement mechanism that is disabled in code or experiencing divergence from documentation, when an auditor inspects the entry, then the detail column displays explicit operational status flags (`[DISABLED]` or `[MAP DRIFT]`).

### US-2 Boundary and Concision Maintenance

As a repository maintainer or compliance reviewer, I want strict inclusion boundaries and concision limits on the enforcement map, so that every row only references a specific rule derived from our axioms and applicable to agents working in any third-party project, and the table never accumulates token rows for workflows, repository-local project rules, operational subsystem specifications, or narrative incident logs.

- **AC-2.1** Given a candidate entry representing a workflow, repository-local project rule, specification feature, or architectural contract rather than a specific rule derived from our axioms and applicable to agents working in any third-party project, when evaluated for inclusion, then it is excluded from the map (for workflows, the only applicable rule is "agents must follow workflows given to them" and nothing more than that).
- **AC-2.2** Given a candidate entry representing a single-carrier prompt instruction without universal axiom standing, non-instruction enforcement, or operational status flags, when evaluated for inclusion, then it resides in its respective instruction file and is excluded from the map.
- **AC-2.3** Given a specific rule derived from our axioms and applicable to agents working in any third-party project that has universal axiom standing or is reinforced by a non-instruction carrier category, when evaluated for inclusion, then it is included in the map.
- **AC-2.4** Given any entry in the map, when checked for concision, then its Detail column contains strictly verification coordinates (`path:line`), component names, and status flags within a two-line limit, with zero narrative observations or historical logs.

## Design

### 1. Document Role and Boundaries

The enforcement map (`specs/ENFORCEMENT-MAP.md`) is a concise cross-reference table showing what kind of enforcement is applied to each rule. When editing the enforcement map, every row must only reference a specific rule derived from our axioms (`plugins/rbg/skills/axioms/`) and applicable to agents working in any third-party project. Workflows are not rules and do not enforce rules; creating or modifying workflows must not produce token enforcement map rows, as the only applicable rule is "agents must follow workflows given to them" and nothing more than that. Architectural explanations belong in subsystem specifications; process instructions belong in workflow templates; repository-local rules belong in `.agents/rules/`; runtime status belongs in observability tooling. The map records only the mapping from universal axiom-derived rules to their enforcement mechanisms.

### 2. Four-Column Schema

The map formats all entries using a standard four-column schema:

| Column | Content | Concision Invariant |
| :- | :- | :- |
| **Rule** | Linked name of the canonical axiom-derived rule applicable to agents working in any third-party project, followed by one concise sentence stating the operative obligation. | Exactly one axiom-derived rule; <= 25 words. |
| **Mechanism** | Comma-separated carrier categories from the controlled vocabulary (`doctrine only`, `instructions`, `JIT injection`, `structural`, `process`, `post-hoc`). | Strictly controlled vocabulary terms. |
| **Severity** | Comma-separated intervention force gradations matching each carrier category (`suggestion`, `advisory`, `imperative`, `absolute`, `scoped`, `permissions`, `warning`, `friction`, `block`, `protection`, `isolation`, `advisory check`, `routing`, `required gate`, `reversability`, `observability`, `proactive detection`). | Strictly controlled force gradation terms. |
| **Detail** | Pinpoint source references (`path:line`), carrier component or handler names, and operational state flags (`[DISABLED]`, `[MAP DRIFT]`). | Maximum 2 lines; strictly coordinates and flags. |

### 3. Inclusion Criteria

A row earns a place in the map if and only if it satisfies all of the following conditions:

1. **Axiom-Derived Universal Rule Governance:** The entry references a specific rule derived from our axioms (`plugins/rbg/skills/axioms/`) and applicable to agents working in any third-party project (never a repository-local project rule, subsystem feature specification, or workflow);
2. **Workflow Exclusion:** Workflows are not rules and do not enforce rules. Creating or modifying a workflow (`wf-*.md`, `SKILL.md`, or process template) never qualifies for a row in the map, because the only applicable rule is "agents must follow workflows given to them" and nothing more than that; and
3. **Binary Inclusion Filter:** The axiom-derived rule meets at least one of the following two closed criteria:
   - Universal Axiom Standing: It is a canonical axiom declared in the framework's universal axiom set; OR
   - Escalated or Multi-Carrier Enforcement: It is a specific rule derived from our axioms and applicable to agents in any third-party project whose enforcement includes at least one non-instruction carrier category (`structural`, `process`, `JIT injection`, `post-hoc`), or an explicit operational status flag (`[DISABLED]`, `[MAP DRIFT]`).

The map contains strictly specific rules derived from our axioms and applicable to agents working in any third-party project; single-carrier prompt instructions without non-instruction carriers or status flags reside exclusively in their respective instruction files, repository-local project rules reside in `.agents/rules/`, and subsystem specifications and workflows reside in their respective directories.

### 4. Detail Concision Invariant

The Detail column contains strictly verification coordinates for auditors:

- File paths and line numbers or symbols (`path:line`, `path#symbol`).
- Carrier component, hook handler, or script names.
- Operational status flags (`[DISABLED]`, `[MAP DRIFT]`).
