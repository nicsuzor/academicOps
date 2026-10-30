---
title: Enforcement Map
status: ready
---

# Enforcement Map

The enforcement map is the canonical state register documenting the empirical distribution of active behavioral controls across the framework, providing architects and auditors with the exact mechanism, force, and pinpoint location enforcing each governed rule so they can calibrate, strengthen, or retire regulatory measures.

## User stories

### US-1 Calibrating Regulatory Interventions

As a framework architect or auditor, I want a single-source register of active enforcement mechanisms mapped to governed rules, so that I can evaluate proportionality, identify regulatory gaps, and decide whether to strengthen, weaken, or retire an enforcement measure without reading extensive narrative text.

- **AC-1.1** Given any governed rule in the register, when an auditor inspects its entry, then the register reports the active mechanism category, severity gradation, and pinpoint source location within a single four-column row.
- **AC-1.2** Given a proposal to add or escalate an enforcement mechanism, when an architect checks the register, then the register reveals all non-instruction carriers already bound to that rule.
- **AC-1.3** Given an enforcement mechanism that is disabled in code or experiencing divergence from documentation, when an auditor checks the register, then the register displays explicit operational status flags (`[DISABLED]` or `[MAP DRIFT]`) in the detail pinpoint.

### US-2 Register Boundary and Concision Maintenance

As a compliance reviewer or worker, I want clear row-by-row inclusion boundaries and strict concision constraints, so that the register remains bounded, scannable, and free of routine prompt instruction bloat.

- **AC-2.1** Given a routine prompt directive, tone guideline, or UI formatting rule with no non-instruction carrier and no universal axiom standing, when evaluated for inclusion, then it is excluded from the register.
- **AC-2.2** Given a universal axiom or rule reinforced by a non-instruction mechanism, when evaluated for inclusion, then it is included in the register.
- **AC-2.3** Given any entry in the register, when inspected for concision, then the Detail column contains strictly file and line pinpoints with optional state flags.

## Design

### 1. Document Role and Authority

The enforcement map is the sole authoritative state document for active behavioral enforcement mechanisms across the framework. It records the current truth of what exists in code, configurations, and review lenses. The map presents an empirical table of active measures.

### 2. Table Schema

The register is formatted as a single consistent table across all sections, using a standard four-column schema:

| Column | Content Specification | Concision Invariant |
| :- | :- | :- |
| **Rule** | Linked reference to the canonical rule source document followed by one concise sentence stating the operative obligation. | Limited to one sentence (≤ 25 words). |
| **Mechanism** | Comma-separated carrier categories from the controlled vocabulary (`doctrine only`, `instructions`, `JIT injection`, `structural`, `process`, `post-hoc`). | Strictly controlled vocabulary terms. |
| **Severity** | Comma-separated intervention force gradations matching each carrier category. | Strictly controlled force gradation terms. |
| **Detail** | Pinpoint source references (`path:line` or `path#symbol`), carrier component or handler names, and operational state flags (`[DISABLED]`, `[MAP DRIFT]`). | Maximum 2 lines. Strictly pinpoints, component names, and state flags. |

### 3. Row-by-Row Inclusion Criteria

A candidate rule or measure earns a row in the enforcement map if and only if it meets at least one of the following two closed criteria:

1. **Universal Axiom Standing:** It is a universal axiom declared in the framework's universal axiom set.
2. **Escalated or Multi-Carrier Enforcement:** Its enforcement includes at least one non-instruction carrier category (`JIT injection`, `structural`, `process`, or `post-hoc`), or it carries an explicit operational state flag (`[DISABLED]`, `[MAP DRIFT]`).

All other instructions, prompt directives, formatting conventions, and persona guidelines reside exclusively in their respective instruction files.

### 4. Detail Concision Invariant

The Detail column provides verification coordinates for auditors:

- Entries provide file paths and line numbers or symbols (`path:line`, `path#symbol`) linking directly to the enforcing code or configuration.
- Entries name the enforcing carrier component, hook handler, or script.
- Entries indicate operational status using the standard state flags (`[DISABLED]`, `[MAP DRIFT]`) where applicable.
- Entries remain strictly within two lines.
