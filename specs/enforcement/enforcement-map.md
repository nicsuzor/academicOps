---
title: Enforcement Map
status: ready
---

# Enforcement Map

The enforcement map is a concise cross-reference table that shows what kind of enforcement is applied to each rule, and is not a summary of specifications or workflows. It documents the empirical distribution of active behavioral controls across the framework, providing auditors and framework architects with the mechanism category, intervention severity, and verification coordinates for each governed rule.

## User stories

### US-1 Cross-Referencing Rule Enforcement

As a framework architect, reviewer, or auditor, I want a concise cross-reference table showing what kind of enforcement is applied to each rule, so that I can inspect active regulatory measures, evaluate proportionality, and identify enforcement gaps without reading narrative specifications or searching workflow implementations.

- **AC-1.1** Given any governed rule, when an auditor inspects the table, then the entry identifies the rule name, its carrier mechanism category, its intervention severity, and its verification coordinates within a four-column row.
- **AC-1.2** Given a rule governed by multi-carrier or non-instruction mechanisms, when an auditor reviews its entry, then all active carrier categories (`structural`, `process`, `JIT injection`, `post-hoc`) and their corresponding severities are listed.
- **AC-1.3** Given an enforcement mechanism that is disabled in code or experiencing divergence from documentation, when an auditor inspects the entry, then the detail column displays explicit operational status flags (`[DISABLED]` or `[MAP DRIFT]`).

### US-2 Boundary and Concision Maintenance

As a repository maintainer or compliance reviewer, I want strict inclusion boundaries and concision limits on the enforcement map, so that the table is restricted to rule cross-references and does not accumulate summaries of workflows, operational subsystem specifications, or narrative incident logs.

- **AC-2.1** Given a candidate entry representing a specification feature, architectural contract, or workflow process rather than a rule governing agent conduct, when evaluated for inclusion, then it is excluded from the map.
- **AC-2.2** Given a candidate entry representing a single-carrier prompt instruction without non-instruction enforcement or operational status flags, when evaluated for inclusion, then it resides in its respective instruction file and is excluded from the map.
- **AC-2.3** Given a governed rule that has universal axiom standing or is reinforced by a non-instruction carrier category, when evaluated for inclusion, then it is included in the map.
- **AC-2.4** Given any entry in the map, when checked for concision, then its Detail column contains strictly verification coordinates (`path:line`), component names, and status flags within a two-line limit, with zero narrative observations or historical logs.

## Design

### 1. Document Role and Boundaries

The enforcement map (`specs/ENFORCEMENT-MAP.md`) is a concise cross-reference table showing what kind of enforcement is applied to each rule. It is not a summary of specifications or workflows. Architectural explanations belong in subsystem specifications; process instructions belong in workflow templates; runtime status belongs in observability tooling. The map records only the rule-to-enforcement mapping.

### 2. Four-Column Schema

The map formats all entries using a standard four-column schema:

| Column | Content | Concision Invariant |
| :- | :- | :- |
| **Rule** | Linked name of the canonical rule followed by one concise sentence stating the operative obligation. | Exactly one rule; ≤ 25 words. |
| **Mechanism** | Comma-separated carrier categories from the controlled vocabulary (`doctrine only`, `instructions`, `JIT injection`, `structural`, `process`, `post-hoc`). | Strictly controlled vocabulary terms. |
| **Severity** | Comma-separated intervention force gradations matching each carrier category (`suggestion`, `advisory`, `imperative`, `absolute`, `scoped`, `permissions`, `warning`, `friction`, `block`, `protection`, `isolation`, `advisory check`, `routing`, `required gate`, `reversability`, `observability`, `proactive detection`). | Strictly controlled force gradation terms. |
| **Detail** | Pinpoint source references (`path:line`), carrier component or handler names, and operational state flags (`[DISABLED]`, `[MAP DRIFT]`). | Maximum 2 lines; strictly coordinates and flags. |

### 3. Inclusion Criteria

A row earns a place in the map if and only if it satisfies both of the following conditions:

1. **Rule Governance:** The entry names a rule governing agent conduct (a universal axiom, project rule, or standing behavioral rule); and
2. **Binary Inclusion Filter:** The entry meets at least one of the following two closed criteria:
   - Universal Axiom Standing: It is an axiom declared in the framework's universal axiom set; OR
   - Escalated or Multi-Carrier Enforcement: Its enforcement includes at least one non-instruction carrier category (`structural`, `process`, `JIT injection`, `post-hoc`), or it carries an explicit operational status flag (`[DISABLED]`, `[MAP DRIFT]`).

The map contains strictly rules governing agent conduct; single-carrier prompt instructions without non-instruction carriers or status flags reside exclusively in their respective instruction files, and subsystem specifications and workflows reside in their respective directories.

### 4. Detail Concision Invariant

The Detail column contains strictly verification coordinates for auditors:

- File paths and line numbers or symbols (`path:line`, `path#symbol`).
- Carrier component, hook handler, or script names.
- Operational status flags (`[DISABLED]`, `[MAP DRIFT]`).
