---
description: Project-specific process rules for the academicOps repository. Loaded by rbg (the Judge) alongside global axioms, and by the GHA QA agent for process compliance.
---

# Project Rules

These rules are **project-specific** — they apply to the `academicOps` repository in addition to (not in place of) the universal axioms in [[AXIOMS]]. Each rule targets a **class** of cases, not a single instance (Categorical-Imperative discipline, [[AXIOMS#categorical-imperative]]).

Identity scheme: each rule has a durable **slug** (`{#slug}` heading anchor). Cite by slug, never by ordinal. Rules may be added, merged, retired, or reordered without invalidating cross-references.

A rule lives here when it (a) governs how this repo's enforcement / authority / governance surfaces operate, AND (b) cannot be derived from the universal axioms alone — it states a project-level commitment whose violation is concrete enough that a reviewer can name the breach from the diff. Anything that is a universal claim belongs in [[AXIOMS]] instead.

## Enforcement-Map Currency — every mechanism change updates the map in the same PR {#enforcement-map-currency}

Any PR that **adds, modifies, escalates, or retires** an **enforcement mechanism** MUST update `specs/ENFORCEMENT-MAP.md` in the **same change**, so the map still describes reality after merge. An enforcement mechanism is **any measure intended to shape how agents behave** — not only gates, hooks, chokepoints, classifier rules, review agents, and branch-protection checks, but also **instructions, project rules, and agent-persona edits** that change what an agent is directed to do. The test is not "which file did I touch?" but **"does this diff change the regulatory surface — what any agent is made to do?"**

- The map is the routing table for "how is each rule currently enforced?" — a mechanism that ships without a row (or with a now-inaccurate row) is an unmapped/stale surface, and that degrades to silent state drift the next time someone reads the map and trusts it.
- This rule is **derivative of [[AXIOMS#single-source-of-truth]] applied to enforcement state**: the map is the single authoritative copy of the regulatory surface.
- The map's own header states the rule: _"Any PR that adds, escalates, or retires a mechanism updates a row here in the same change (P#65); `rbg` blocks on currency."_ This rule operationalises that header.
- "Same change" means same PR, not "follow-up PR". A follow-up has the same failure mode the rule is designed to prevent.

_When applying:_ if the diff touches any agent persona's `tools:` frontmatter, any file under `aops-core/hooks/`, `.github/workflows/agent-*.yml`, `.github/agents/*.agent.md`, `.github/rulesets/`, `templates/*.plugin.json` `autoMode`, or `specs/enforcement/`, check whether `specs/ENFORCEMENT-MAP.md` was updated in the same diff. If not → `REVISE`.

## Bot-facing instructions comply with `/craft` best practices {#bot-instructions-craft}

Any change that adds or modifies **bot-facing instructions** — agent definitions (`aops-core/agents/*.md`), skill bodies and references (`skills/**`), task/workflow prose, hook/gate prompt templates, or any text a framework agent reads as direction — MUST comply with the instruction best practices set out in the `/craft` skill (`aops-core/skills/craft/SKILL.md`): concise, unambiguous, no shallow-execution vulnerabilities, excellence over mere compliance.

- Reviewers hold the **content** of such changes to the `/craft` bar, not only their runtime behaviour. A doctrine/instruction PR with nothing executable to run is still reviewed against this rule — verbose, ambiguous, or shallow-execution-prone instruction text is a `REVISE`.
- This is a repo-level commitment, not a universal axiom: instructions are this framework's primary product surface, so their quality is a gating concern that a reviewer can name from the diff.
- _When applying:_ if the diff adds or edits any bot-facing instruction text, check it against `/craft` (run the skill in audit mode where useful). If it falls short of the bar → `REVISE`, citing the specific defect class.

**Granularity — map the mechanism class, not the change.** Represent each measure at the level of its **generic injection type / mechanism class**, never per-PR, per-rule, or per-agent. Row-proliferation is the standing failure mode: one line per generic injection type keeps the map readable; a row per change makes it useless.

- **New rule/axiom _content_ on an already-mapped mechanism owes no new row.** A new project rule (or axiom) is _content carried by_ the review mechanisms that already have rows — e.g. "agents apply repo-local `.agents/rules/RULES.md` in addition to universal axioms" is already mapped (the rbg + qa rows). Rules are content, not mechanisms (see the map's pyramid note: axioms do not appear as rows). Touch the map only if the _mechanism's_ trigger, surface, or workflow-impact actually changed.
- **Refining an already-mapped persona's prose** (clarifying scope, tightening wording) updates the **existing row's** workflow-impact cell only if that cell is now inaccurate; it does not spawn a new row.
- **Add a new row only for a genuinely new mechanism class** — a generic injection type / surface that no existing row describes.

- _Example — a real new mechanism (illustrative, NOT an exhaustive trigger list):_ PR #1824 (`feat(junior): replace PKB wildcard with explicit allowlist`) changed an agent's `tools:` allowlist — a chokepoint/funnel (L4) mechanism per the Pyramid — and shipped without a row; `rbg` returns `REVISE`. _Counter-example — no row owed:_ adding the `{#bot-instructions-craft}` rule below adds _content_ to the already-mapped "agents apply repo-local RULES.md" mechanism.

_When applying:_ ask first **"does this diff change the regulatory surface — what any agent is made to do?"** If yes, confirm the map describes the post-merge reality at the **mechanism-class grain**: update the existing generic row if its trigger/surface/impact changed; add a row only for a new mechanism class; add nothing for new rule/axiom _content_ on an already-mapped mechanism. If the surface changed and the map does not reflect it → `REVISE`.
