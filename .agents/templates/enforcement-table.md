---

title: Enforcement Map Generation
type: template
category: process
description: Create or audit a flat, actionable 4-column enforcement map mapping rules and affordances to concrete implementation mechanisms and escalation severity.
tags: [enforcement, governance, architecture, audit, template]

# Process: Enforcement Map Generation

A process for creating and maintaining a flat, diagnostically useful enforcement map that maps rules and nudges directly to their concrete implementation mechanisms and severity levels.

## When to use

- Mapping or auditing how a codebase, framework, or multi-agent system enforces its rules, constraints, and steering nudges.
- Evaluating whether rules are appropriately bound (e.g. distinguishing hard structural gates or tool denials from advisory persona prompts).
- Identifying unenforced rules (gaps), disabled mechanisms, and spec drift.

## When NOT to use

- Documenting standard software features or writing functional specifications (a skill performing its stated purpose is a feature spec, not enforcement).
- General architectural overviews that do not require concrete `path:line` verification.

## The Fitness Test

> **A row earns its place only if it supports, on its own, a decision to strengthen an instruction, weaken it, remove a hook, or alter a gate.**

## 1. Rule Formulation & Logical Binding Principles

1. **Explain Operative Intent (What the Rule is Trying to Accomplish):**
   - Rules must clearly state what the system or component is trying to do or prevent, rather than repeating cryptic shorthand slogans (e.g. do not write _"ida parks a thread; only the user ends a conversation"_; write _"Ida must not unilaterally mark an open user thread or request as finished, buffering in-flight work until the user explicitly confirms completion"_).
2. **Logical Accuracy & Binding Scope:**
   - Express general prohibitions accurately across the system (e.g. _"Agents other than ida must not communicate directly with the user"_).
   - Pair general prohibitions with the specific behavioural obligations on the designated agent (e.g. _"Ida must communicate with the user in a concise and accommodating manner"_).
   - **Persona instructions only bind the agent whose file contains them.** Logically, instructions in `ida.md` cannot bind other agents; the mechanism for _"Agents other than ida must not talk to the user"_ must reflect what actually restrains those other agents (or be marked `not enforced`).

## 2. Table Schema & Vocabulary

The deliverable is a **single flat markdown table** with exactly 4 columns:

| Column           | Definition                                                    | Rules & Constraints                                                                                  |
| :--------------- | :------------------------------------------------------------ | :--------------------------------------------------------------------------------------------------- |
| **Rule / nudge** | The operative obligation, constraint, or steering affordance. | One row per `(rule or nudge) × (mechanism that carries it)`. Logically accurate, explaining intent.  |
| **Mechanism**    | The category/carrier kind.                                    | Drawn strictly from the 10-term controlled vocabulary below.                                         |
| **Severity**     | The escalation index within the mechanism.                    | Drawn strictly from the severity index below.                                                        |
| **Detail**       | Pinpoint reference and operative evidence.                    | Verifiable file pointer (`path:line` + operative quote, hook event + handler, or CI workflow + job). |

### Mechanism Controlled Vocabulary (10 Terms)

1. `agent persona instructions` — Guiding text in an agent's persona definition file.
2. `skill instructions` — Operational text in a skill's instruction file (`SKILL.md`).
3. `hook` — Registered handler on a runtime lifecycle event (`PreToolUse`, `PostToolBatch`, `Stop`, etc.).
4. `tool grant` — Frontmatter or config explicitly granting, scoping, or denying tools/models.
5. `structural check` — Hard code-level guarantee (mount permissions, fail-closed configs, native loaders).
6. `workflow gate` — Checkpoint governing work progression across stages (branch protection, task contracts).
7. `CI job` — Named CI pipeline/workflow posting status checks.
8. `observability` — Tracing, logging, or metrics pipeline that records without gating.
9. `doctrine` — Declared principle or policy with no direct automated or code-level enforcement.
10. `not enforced` — A declared rule or desired constraint with no active code, hook, tool-grant, or prompt mechanism enforcing it.

### Severity Index (Escalation within Mechanisms)

- _Instructions:_ `suggestion` · `advisory` · `imperative` · `absolute`
- _Hooks:_ `warning` (advisory notification) · `block` (hard stop/withholding)
- _Tool Grants:_ `scoped` (restricted toolset) · `denial` (explicit block)
- _Structural Checks:_ `hard guarantee` (physical/container boundary) · `fail-closed` (unrecoverable fast-fail)
- _Workflow Gates:_ `checkpoint` (review step) · `blocking gate` (hard barrier)
- _CI Jobs:_ `advisory check` · `required gate`
- _Observability:_ `trace` · `log`
- _Doctrine:_ `declared principle` · `unbacked policy`
- _Not Enforced:_ `none`

## 3. Curation, Slimming & State Rules

1. **Collapse Unenforced Rows / Blanks:**
   - Do NOT create multiple combinatorial empty rows for unenforced rules. Collapse into a single line: `(rule, not enforced, none)` with a clean, concise summary in `Detail`.
   - Avoid verbose negative proofs (e.g. do not write _"not located anywhere in ida.md — full file read"_; write _"Not enforced in persona prompts, hooks, or tool grants"_).
2. **Collapse Redundant Instructions:**
   - Where multiple lines in a persona or across skills enforce the same underlying rule, collapse into a single row listing all citations in `Detail`.
3. **Exclude Functional Specs:**
   - Drop descriptions of a skill or tool simply performing its intended function.
4. **Preserve All Hard Levers (~32 rows):**
   - Retain every `hook`, `tool grant`, `structural check`, `workflow gate`, `CI job`, and `doctrine` row.
5. **Format State & Drift in `Detail` (No extra columns):**
   - **Disabled mechanisms:** Prefix `Detail` with `[DISABLED]` and state the rationale.
   - **Spec/code drift:** Prefix `Detail` with `[MAP DRIFT]` where code reality contradicts documentation.
