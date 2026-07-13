---
description: Project-specific process rules for the academicOps repository. Loaded by rbg (the Judge) alongside global axioms, and by the GHA QA agent for process compliance.
---

# Project Rules

These rules are **project-specific** — they apply to the `academicOps` repository in addition to (not in place of) the universal axioms in [[AXIOMS]]. Each rule targets a **class** of cases, not a single instance (Categorical-Imperative discipline, [[AXIOMS#categorical-imperative]]).

A rule lives here when it (a) governs how this repo's enforcement / authority / governance surfaces operate, AND (b) cannot be derived from the universal axioms alone — it states a project-level commitment whose violation is concrete enough that a reviewer can name the breach from the diff. Anything that is a universal claim belongs in [[AXIOMS]] instead.

## Enforcement-Spec Currency — every mechanism change updates the spec in the same PR {#enforcement-map-currency}

Any PR that **adds, modifies, escalates, or retires** an **enforcement mechanism** MUST update [`specs/enforcement/enforcement.md`](../../specs/enforcement/enforcement.md) (and its sibling docs where the change lands — `task-contract.md`, `workflow.md`, `sign-off.md`, `evidence-contract.md`, `auto-mode-classifier.md`, or the `aops/workflows/gates/` component library) in the **same change**, so the spec still describes reality after merge. An enforcement mechanism is **any measure intended to shape how agents behave** — not only structural isolation, the harness delivery channel, review lenses, and branch-protection checks, but also **instructions, project rules, and agent-persona edits** that change what an agent is directed to do. The test is not "which file did I touch?" but **"does this diff change the regulatory surface — what any agent is made to do?"**

- `enforcement.md` is the single authoritative description of "what currently enforces things" (see [[AXIOMS#single-source-of-truth]] applied to enforcement state) — a mechanism that changes without the spec being updated is silent state drift the next time someone reads it and trusts it.
- "Same change" means same PR, not "follow-up PR." A follow-up has the same failure mode this rule is designed to prevent.
- **New rule/axiom _content_ enforced by an already-described mechanism owes no new section.** e.g. "agents apply repo-local `.agents/rules/RULES.md` in addition to universal axioms" is already described (the rbg boundary-review lens). Touch the spec only if the _mechanism itself_ — its trigger, surface, or scope — actually changed.
- Given how few mechanical mechanisms remain (see `enforcement.md`'s governing principle — agents all the way down, structural prevention only), this is now a light-touch discipline, not a large routing table to maintain. The obligation is: if you touch a mechanism, the spec says so, in the same PR.

## Markdown files MUST NOT include irrelevant text

- Any change to an agent instruction, skill, or documentation file MUST comply with the rules set out in `specs/meta/doc-taxonomy.md`.
- NO CRUFT: All prose must be concise and adapted for the target audience.

## Framework Pre-commit Checks — hooks enforce where possible, agents enforce otherwise {#framework-pre-commit-checks}

These are hard rules for aops framework internals. Enforced by pre-commit hooks where possible; where a hook can't reach (advisory-only checks), the acting agent is responsible for compliance instead.

| Check                    | Script                              | Rule(s)                | Tier       | Behaviour                                                    |
| ------------------------ | ----------------------------------- | ---------------------- | ---------- | ------------------------------------------------------------ |
| `check-orphan-files`     | `scripts/check_orphan_files.py`     | (wikilink orphans)     | `advisory` | Exits 0; reports files with no incoming wikilinks            |
| `check-skill-line-count` | `scripts/check_skill_line_count.py` | (SKILL.md ≤ 500 lines) | `advisory` | Exits 1 when any SKILL.md exceeds 500 lines; lists offenders |
