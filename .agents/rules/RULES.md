---
description: Project-specific process rules for the academicOps repository. Loaded by rbg (the Judge) alongside global axioms, and by the GHA QA agent for process compliance.
---

# Project Rules

These rules are **project-specific** — they apply to the `academicOps` repository in addition to (not in place of) the universal axioms in [[AXIOMS]]. Each rule targets a **class** of cases, not a single instance (Categorical-Imperative discipline, [[AXIOMS#categorical-imperative]]).

Identity scheme: each rule has a durable **slug** (`{#slug}` heading anchor). Cite by slug, never by ordinal. Rules may be added, merged, retired, or reordered without invalidating cross-references.

A rule lives here when it (a) governs how this repo's enforcement / authority / governance surfaces operate, AND (b) cannot be derived from the universal axioms alone — it states a project-level commitment whose violation is concrete enough that a reviewer can name the breach from the diff. Anything that is a universal claim belongs in [[AXIOMS]] instead.

## Enforcement-Map Currency — every mechanism change updates the map in the same PR {#enforcement-map-currency}

Any PR that **adds, modifies, escalates, or retires** an enforcement mechanism (a gate, hook, chokepoint, classifier rule, review agent, branch-protection check, or any other surface enumerated in [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md)) MUST update `specs/ENFORCEMENT-MAP.md` in the **same change** — the row that names the mechanism, its trigger, and its workflow impact.

- The map is the routing table for "how is each rule currently enforced?" — a mechanism that ships without a row is an unmapped surface, and an unmapped surface degrades to silent state drift the next time someone reads the map and trusts it.
- This rule is **derivative of [[AXIOMS#single-source-of-truth]] applied to enforcement state**: the map is the single authoritative copy; a mechanism not listed there exists in two contradictory states (the source + the absent map row).
- The map's own header states the rule: _"Any PR that adds, escalates, or retires a mechanism updates a row here in the same change (P#65); `rbg` blocks on currency."_ This rule operationalises that header.
- "Same change" means same PR, not "follow-up PR". A follow-up has the same failure mode the rule is designed to prevent.
- _E.g._ PR #1824 (`feat(junior): replace PKB wildcard with explicit allowlist`) changed an agent's `tools:` list — a chokepoint/funnel (L4) enforcement-mechanism change per the Pyramid in `ENFORCEMENT-MAP.md`. It shipped without a row update. Under this rule, `rbg` returns `REVISE`: "missing enforcement-map row for chokepoint change to junior PKB scope".

_When applying:_ if the diff touches any agent persona's `tools:` frontmatter, any file under `aops-core/hooks/`, `.github/workflows/agent-*.yml`, `.github/agents/*.agent.md`, `.github/rulesets/`, `templates/*.plugin.json` `autoMode`, or `specs/enforcement/`, check whether `specs/ENFORCEMENT-MAP.md` was updated in the same diff. If not → `REVISE`.

## Bot-facing instructions comply with `/craft` best practices {#bot-instructions-craft}

Any change that adds or modifies **bot-facing instructions** — agent definitions (`aops-core/agents/*.md`), skill bodies and references (`skills/**`), task/workflow prose, hook/gate prompt templates, or any text a framework agent reads as direction — MUST comply with the instruction best practices set out in the `/craft` skill (`aops-core/skills/craft/SKILL.md`): concise, unambiguous, no shallow-execution vulnerabilities, excellence over mere compliance.

- Reviewers hold the **content** of such changes to the `/craft` bar, not only their runtime behaviour. A doctrine/instruction PR with nothing executable to run is still reviewed against this rule — verbose, ambiguous, or shallow-execution-prone instruction text is a `REVISE`.
- This is a repo-level commitment, not a universal axiom: instructions are this framework's primary product surface, so their quality is a gating concern that a reviewer can name from the diff.
- _When applying:_ if the diff adds or edits any bot-facing instruction text, check it against `/craft` (run the skill in audit mode where useful). If it falls short of the bar → `REVISE`, citing the specific defect class.
