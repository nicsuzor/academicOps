---
title: Enforcement Map Generation
type: template
category: process
description: Create or audit a flat, actionable 4-column enforcement map mapping specific axiom-derived rules applicable across any third-party project to concrete enforcement mechanisms and severity levels.
tags: [enforcement, governance, architecture, audit, template]
---

# Process: Enforcement Map Generation

A process for creating and maintaining a flat, diagnostically useful enforcement map (`specs/ENFORCEMENT-MAP.md`) that maps specific rules derived from our universal axioms and applicable to agents working in any third-party project to their concrete enforcement mechanisms and severity levels.

## When to use

- Mapping or auditing how the framework enforces specific rules derived from our universal axioms (`plugins/rbg/skills/axioms/`) that apply to agents working in any third-party project.
- Evaluating whether axiom-derived rules are appropriately bound across mechanism categories (`instructions`, `JIT injection`, `structural`, `process`, `post-hoc`).
- Identifying unenforced axiom-derived rules, disabled mechanisms, and spec drift.

## When NOT to use

- Creating or modifying workflows (`wf-*.md`, `SKILL.md`, or process templates): **workflows are not rules and do not enforce rules**. Creating or modifying workflows must not produce token enforcement map rows, as the only applicable rule is "agents must follow workflows given to them" and nothing more than that.
- Documenting repository-local project rules (specific only to `academicOps`), standard software features, or functional specifications.
- General architectural overviews that do not require concrete `path:line` verification.

## The Fitness Test

> **When editing the enforcement map, every row must ONLY reference a specific rule derived from our axioms and applicable to agents working in any third-party project. A row earns its place only if it supports, on its own, a decision to strengthen an instruction, weaken it, remove a hook, or alter a gate.**

## 1. Rule Formulation & Logical Binding Principles

1. **Axiom-Derived Universal Scope Only:**
   - Every row must reference a specific rule derived from our axioms (`plugins/rbg/skills/axioms/`) and applicable to agents working in any third-party project.
   - Never add rows for repository-local project rules, persona-specific conversational habits, subsystem feature specs, or workflows.
   - Workflows are not rules and do not enforce rules; creating or modifying workflows must not produce token enforcement map rows, as the only applicable rule is "agents must follow workflows given to them" and nothing more than that.
2. **Explain Operative Intent (What the Rule is Trying to Accomplish):**
   - State the linked canonical axiom-derived rule followed by one concise sentence (≤ 25 words) stating the operative obligation governing agent conduct across any third-party project.
3. **Logical Accuracy & Binding Scope:**
   - **Instructions only bind the agents that load them.** Ensure the mechanism column and pinpoint references reflect what actually carries or enforces the rule across client sessions (or mark disabled mechanisms with `[DISABLED]`).

## 2. Table Schema & Vocabulary

The deliverable is a **single flat markdown table** with exactly 4 columns:

| Column | Definition | Rules & Constraints |
| :- | :- | :- |
| **Rule** | Linked name of the specific axiom-derived rule applicable to agents in any third-party project, followed by one concise sentence stating the operative obligation. | Exactly one axiom-derived rule; ≤ 25 words. Never a workflow, subsystem spec, or repo-local rule. |
| **Mechanism** | Comma-separated carrier categories from the controlled vocabulary. | Drawn strictly from the controlled vocabulary below. |
| **Severity** | Comma-separated escalation force gradations matching each carrier category. | Drawn strictly from the severity index below. |
| **Detail** | Pinpoint reference (`path:line`), carrier component or handler names, and operational state flags (`[DISABLED]`, `[MAP DRIFT]`). | Maximum 2 lines; strictly verification coordinates and status flags, with zero narrative observations. |

### Mechanism Controlled Vocabulary

1. `doctrine only` — Declared principle or policy with no explicit path to agents.
2. `instructions` — Guiding text provided to an agent (`suggestion`, `advisory`, `imperative`, `absolute`).
3. `JIT injection` — Advisory information provided at a targeted point of a workflow.
4. `structural` — Scope and force guarantees (`scoped`, `permissions`, `warning`, `friction`, `block`, `protection`, `isolation`).
5. `process` — Review or gate requirements (`advisory check`, `routing`, `required gate`).
6. `post-hoc` — Auditability and detection (`reversability`, `observability`, `proactive detection`).

### Severity Index (Escalation within Mechanisms)

- _Instructions:_ `suggestion` · `advisory` · `imperative` · `absolute`
- _Structural:_ `scoped` · `permissions` · `warning` · `friction` · `block` · `protection` · `isolation`
- _Process:_ `advisory check` · `routing` · `required gate`
- _Post-hoc:_ `reversability` · `observability` · `proactive detection`

## 3. Curation, Slimming & State Rules

1. **Strict Axiom-Derived Third-Party Rule Filter:**
   - Include only specific rules derived from our axioms that apply to agents working in any third-party project and meet the inclusion filter in `specs/enforcement/enforcement-map.md`.
   - Exclude all workflow steps, skill procedures, subsystem feature specs, and `academicOps`-only project rules.
2. **Collapse Redundant Carriers:**
   - Where multiple mechanisms or files enforce the same underlying axiom-derived rule, list all carrier categories and pinpoint coordinates on that rule's row rather than minting duplicate rows.
3. **Exclude Workflows and Functional Specs:**
   - Workflows are not rules and do not enforce rules; creating or modifying a workflow never produces a token enforcement map row (the only applicable rule is "agents must follow workflows given to them" and nothing more than that).
4. **Format State & Drift in `Detail` (No extra columns):**
   - **Disabled mechanisms:** Tag with `[DISABLED]` in `Detail`.
   - **Spec/code drift:** Tag with `[MAP DRIFT]` in `Detail` where code reality contradicts documentation.
