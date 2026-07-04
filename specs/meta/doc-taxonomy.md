---
title: Documentation in aops — where things go
---

# Documentation in aops — where things go

Five kinds of document, partitioned by who reads them.

**How to choose**: ask "who reads this?" — an agent at runtime (instructions), a dev or auditor changing the system (specs), both agents and devs looking up the current truth (state), a script consuming machine output (audit-artifact), or a human using the framework (docs).

## Instructions — for agents executing

Live in `aops-core/agents/<name>.md` (personas, loaded via the `Agent` tool), `aops-core/skills/<name>/SKILL.md` (skills, loaded via the `Skill` tool), and `.agents/CORE.md` + `rules/*.md` (always-on context loaded by the harness).

**Generally contain**: who the agent is or what the skill does, what tools and permissions it has, what to do in common situations.

**Shouldn't contain**: dated log entries (git knows), spec-style "how could this work differently" debate (that's a spec), SSoT claims about system facts (that's state), or pasted-in generator output (that's an audit-artifact).

**Quality bar**: every line should change what the agent does on a task it will actually run — if removing it wouldn't change behaviour, cut it. Reads as a decision procedure ("when X, do Y"), not a description of the system.

This spec answers _which file_ by audience. For _which injection tier_ and enforcement mechanism applies by type and frequency, see [ENFORCEMENT-MAP.md](../ENFORCEMENT-MAP.md) §Pyramid.

## Specs — for devs and auditors

Live in `specs/<subsystem>/<name>.md` at the academicOps root.

**Generally contain**: what the subsystem is for, what design choices were made and why, how it should behave, what enacts it. Statused (`inbox` / `draft` / `ready` / `in_progress` / `superseded`) and supersedable.

> **Note — document status, not task status.** This `draft`/`superseded` vocabulary is the _document_ lifecycle for specs; it is distinct from the canonical _task_ status set (the SSoT is [[TAXONOMY#status-values-and-transitions]]). Do not conflate the two: `draft` and `superseded` are not valid task statuses, and the task lifecycle does not govern spec documents.

**Shouldn't contain**: per-agent log entries, imperative agent instructions (those go in instructions), generated tables (audit-artifact).

**Quality bar**: answers _why_ the subsystem is built this way for a reader who wasn't there — the trade-off, not just the choice. If a reader can't tell what decision it's defending, it's notes, not a spec.

**Specs describe the shipped system, not this repo's own process.** A spec's audience is a dev or auditor extending or auditing academicOps-as-installed — the software's behavior once installed and running. It is not about how this repository itself is built, tested, released, or contributed to.

That's contributor practice, and it lives in the conventional top-level files a dev already knows to look for, not in `specs/`:

- `CONTRIBUTING.md` — dev setup, testing, PR workflow.
- `RELEASING.md` — the release/publish pipeline.
- Already-correctly-placed co-located docs, e.g. [`aops-core/BUILD.md`](../../aops-core/BUILD.md), whose opening line draws exactly this distinction: "end-users want `INSTALL.md`... this doc is for developers changing the build."

If a doc's reader is "someone building, testing, or releasing this repo" rather than "someone running or auditing the shipped system," it isn't a spec — even when it sits next to specs and looks the same shape.

**One fact, one file.** Before adding a fact to a spec, check whether an already-mapped file — a state doc, another spec, a rule — owns it already. This generalises the enforcement-map-currency principle in [RULES.md](../../.agents/rules/RULES.md#enforcement-map-currency): a fact should have exactly one authoritative home, and every other mention should reference that home rather than restate it.

If an already-mapped file owns it, extend or link that file instead of duplicating the fact here. A second copy of the same fact isn't a clarification — it's a duplication liability that drifts the moment one copy is edited and the other isn't.

**Pattern for runtime-subsystem specs** (worked example: [`specs/enforcement/GATES.md`](../enforcement/GATES.md)). Each element of a runtime subsystem gets the same five-question shape: **what is it** (one-sentence definition + class of failure caught), **where does it live** (source path, plugin-cache location at runtime, which agent/skill loads it), **how is it configured** (config keys, env vars, cache invalidation cadence), **how do I verify it's firing** (commands, log paths, expected output), **how do I debug it when it isn't** (top failure modes + diagnostics). Adjacent docs that retain non-overlapping content get a header note framing their role and a cross-reference back to the canonical; docs whose content is wholly subsumed by the canonical become redirect stubs (frontmatter `status: superseded`, `supersedes_target: <path>`).

## State — the SSoT for what the system IS right now

Read by both agents (at runtime, for lookups) and devs (at design time, when changing the system). **One canonical location per slice.**

**Default location**: `specs/<NAME>.md` at the repo root (e.g. SURFACES, ENFORCEMENT-MAP, CAPABILITIES, CONSTRAINTS). May live outside the repo in PKB or machine config when the slice depends on user or machine conditions. May be `.md` or `.yaml` (e.g. `polecat.yaml`).

**Generally contain**: the current truth about one thing — concepts, rules, schemas, routing tables.

**Shouldn't contain**: proposals or "should we" (those are specs), dated log entries.

**Quality bar**: answers _what X does right now_ without reading code — no hedges, no "we could," no proposals. Conditional language is a sign it drifted into spec territory.

## Audit-artifact — generated by scripts, never hand-edited

Live in-repo at `specs/audit/AGENT-*.md`.

**Generally contain**: a script-produced snapshot, with a `Generated on X from Y` header at the top so a reader knows it's not authored content.

**Shouldn't contain**: anything edited by hand between regenerations.

**Quality bar**: byte-for-byte reproducible by re-running the generator. If a hand edit would survive the next regeneration unnoticed, it's become a hand-maintained doc wearing a generated-file header.

## Docs — for humans using the framework

Top-level entry points: README.md, INSTALL.md, CHANGELOG.md.

**Generally contain**: how to install, how to use, what's changed, where to find more.

**Shouldn't contain**: internal jargon without a glossary, agent persona voice, SSoT claims.

**Quality bar**: gets a new user to a working install or a completed task without reading specs or source. A step that assumes insider jargon or an insider's mental model isn't done yet.

---

Checking whether a document fits its category is a judgement an experienced reader can make — not a mechanical contract. Marsha or any reviewer asks: _is this in the right place, does it contain roughly the right kind of thing, does it leave out the kinds of thing it shouldn't have?_ If those answers are clear, it's compliant.
