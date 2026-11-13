---
trigger: always_on
description: Run enforcement changes through the enforcement pyramid options against specs/enforcement/enforcement.md and update the spec in the same PR.
---

## Enforcement changes run through the pyramid and update the spec

Before proposing, adding, or modifying an enforcement mechanism, run through the enforcement pyramid options against [`specs/enforcement/enforcement.md`](../../specs/enforcement/enforcement.md) first, testing least-invasive options across its controlled vocabulary and strength gradations before escalating. Default to instructions: instructions work in the large majority of cases; the burden of proof is on adding a mechanism.

No new hooks without a full spec. No new mechanical enforcement of any kind without a full spec and a decision history filed to show enforcement map escalation step by step.

Any change that adds, modifies, escalates, or retires an enforcement mechanism updates [`specs/enforcement/enforcement.md`](../../specs/enforcement/enforcement.md) in the same PR, so the spec still describes reality after merge.

An enforcement mechanism is any measure intended to shape how an agent behaves -- hooks, review lenses, branch protection, and equally instructions, project rules, and agent-persona edits. The test is not "which file did I touch?" but "does this diff change what any agent is made to do?"

New rule content carried by a mechanism the spec already describes owes no new section. Touch the spec only when the mechanism itself -- its trigger, surface, or scope -- changed.

When editing the enforcement map ([`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md)), every row must **only** reference a specific rule derived from our axioms ([`plugins/rbg/skills/axioms/`](../../plugins/rbg/skills/axioms/)) and applicable to agents working in any third-party project -- never repository-local project rules, subsystem feature specifications, or workflows. Workflows are not rules and do not enforce rules; creating or modifying workflows (`wf-*.md`, `SKILL.md`, or process templates) must not produce token enforcement map rows, as the only applicable rule is "agents must follow workflows given to them" and nothing more than that.
