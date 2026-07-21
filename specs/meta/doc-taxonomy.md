---
title: Documentation in aops — where things go
---

# Documentation in aops — where things go

Five kinds of document, partitioned by who reads them.

**How to choose**: ask "who reads this?" — an agent at runtime (instructions), a dev or auditor changing the system (specs), both agents and devs looking up the current truth (state), a script consuming machine output (audit-artifact), or a human using the framework (docs).

## Instructions — for agents executing

Live in `aops/agents/<name>.md` (personas, loaded via the `Agent` tool), `aops/skills/<name>/SKILL.md` (skills, loaded via the `Skill` tool), and `.agents/CORE.md` + `rules/*.md` (always-on context loaded by the harness).

**Generally contain**: who the agent is or what the skill does, what tools and permissions it has, what to do in common situations.

**Shouldn't contain**: dated log entries (git knows), spec-style "how could this work differently" debate (that's a spec), SSoT claims about system facts (that's state), or pasted-in generator output (that's an audit-artifact).

This spec answers _which file_ by audience. For _which injection tier_ and enforcement mechanism applies by type and frequency, see [ENFORCEMENT-MAP.md](../ENFORCEMENT-MAP.md) §Pyramid.

<!-- NS: We should make some brief quality and substance notes about what info each doc should and shouldn't contain and how to know it's good. -->

## Specs — for devs and auditors

Live in `specs/<subsystem>/<name>.md` at the academicOps root.

**Generally contain**: what the subsystem is for, what design choices were made and why, how it should behave, what enacts it. Statused (`inbox` / `draft` / `ready` / `in_progress` / `superseded`) and supersedable.

> **Note — document status, not task status.** This `draft`/`superseded` vocabulary is the _document_ lifecycle for specs; it is distinct from the canonical _task_ status set (the SSoT is [[TAXONOMY#status-values-and-transitions]]). Do not conflate the two: `draft` and `superseded` are not valid task statuses, and the task lifecycle does not govern spec documents.

**Shouldn't contain**: per-agent log entries, imperative agent instructions (those go in instructions), generated tables (audit-artifact), or provenance.

**No provenance.** A spec states what's true and why, not who decided it, where, or when. PKB task/session IDs, ruling numbers, and "ruled by X on date Y" citations belong in git commit messages and task files — cite them there, not in the spec body. A reference-only section that just enumerates adjacent task IDs with no other content (a "related work" list) belongs in the tracking task, not the spec; if a spec genuinely depends on another spec's content, link that spec by name, not a PKB ID.

**A spec declares intended behavior — for any subsystem, including this repo's own tooling — and it may be aspirational.** A spec is a _specification_: what a subsystem is designed to do and why, not a live telemetry feed of what the code happens to do today. Drift between a spec and the code is an expected, ordinary state of the world (it means there's a bug or an unfinished migration to fix — it is not evidence the doc is miscategorized). That's the axis that actually separates a spec from a **state** doc: a state doc claims to be the current-truth SSoT ("this IS what the system does right now"); a spec claims to be the designed target ("this is what the subsystem is for and how it should behave"), and is allowed to be ahead of, or drift from, reality.

Nothing about that test cares whether the subsystem is "the shipped system" or "this repo's own process." This repo's own build, packaging, install, and release tooling — the Makefile, `scripts/build.py`, `scripts/install.py`, the CI publish pipeline — is a designed subsystem exactly like a runtime gate or a hook client-translation layer, and its intended behavior belongs in a spec the same way: see [`specs/build-and-install.md`](../build-and-install.md).

(This corrects an earlier version of this doc, which carved build/release tooling out of `specs/` entirely and pointed at a since-retired `aops-core/BUILD.md` as the correct home. That was wrong on the merits — BUILD.md's content was spec-shaped from the start, described design choices and behavior, not a checklist — and it had also gone stale relative to the actual code without anyone noticing, which is exactly the failure mode `specs/`'s supersession/status discipline exists to catch.)

What still stays OUT of `specs/` is pure **procedure for a human contributor** — a step list with no design intent to state, e.g. `git clone` + `uv sync`, which command to run before committing, PR-template mechanics. That lives in `CONTRIBUTING.md` at the repo root, which cross-references the relevant specs for _why_ rather than restating their content.

**One fact, one file.** Before adding a fact to a spec, check whether an already-mapped file — a state doc, another spec, a rule — owns it already. This generalises the enforcement-map-currency principle in [RULES.md](../../.agents/rules/RULES.md#enforcement-map-currency): a fact should have exactly one authoritative home, and every other mention should reference that home rather than restate it.

If an already-mapped file owns it, extend or link that file instead of duplicating the fact here. A second copy of the same fact isn't a clarification — it's a duplication liability that drifts the moment one copy is edited and the other isn't.

## State — the SSoT for what the system IS right now

Read by both agents (at runtime, for lookups) and devs (at design time, when changing the system). **One canonical location per slice.**

**Default location**: `specs/<NAME>.md` at the repo root (e.g. GATES, SURFACES, ENFORCEMENT-MAP, CAPABILITIES, CONSTRAINTS). May live outside the repo in PKB or machine config when the slice depends on user or machine conditions. May be `.md` or `.yaml` (e.g. `polecat.yaml`).

**Generally contain**: the current truth about one thing — concepts, rules, schemas, routing tables.

**Shouldn't contain**: proposals or "should we" (those are specs), dated log entries.

**Pattern for runtime-subsystem state docs** (worked example: [`specs/enforcement/GATES.md`](../enforcement/GATES.md)). Each element of a runtime subsystem gets the same five-question shape: **what is it** (one-sentence definition + class of failure caught), **where does it live** (source path, plugin-cache location at runtime, which agent/skill loads it), **how is it configured** (config keys, env vars, cache invalidation cadence), **how do I verify it's firing** (commands, log paths, expected output), **how do I debug it when it isn't** (top failure modes + diagnostics). Adjacent docs that retain non-overlapping content get a header note framing their role and a cross-reference back to the canonical; docs whose content is wholly subsumed by the canonical become redirect stubs (frontmatter `status: superseded`, `supersedes_target: <path>`).

## Audit-artifact — generated by scripts, never hand-edited

Live in-repo at `specs/audit/AGENT-*.md`.

**Generally contain**: a script-produced snapshot, with a `Generated on X from Y` header at the top so a reader knows it's not authored content.

**Shouldn't contain**: anything edited by hand between regenerations.

## Release evidence — a dated acceptance ledger for one release, hand-authored

Live in `specs/releases/<version>-<slug>.md`.

**Generally contain**: for a named release, per headline feature: the
governing spec, the user story, the acceptance criteria, and a citation to
the concrete evidence each criterion was met (PR, commit, or a directly
quoted agent-dispatch transcript) — plus an explicit list of what the
release does not cover. This is the one deliberate exception to the specs
tree's "no provenance" rule (below): a release evidence ledger's entire
purpose is dated, citable provenance for a point-in-time acceptance
decision, not a description of designed subsystem behavior.

**Shouldn't contain**: raw PKB task IDs or copied task titles (the PKB
egress-guard rule still applies in full — cite PRs, commits, file paths, and
quoted transcripts, never a bare internal tracking ID); narrative design
rationale that belongs in an ordinary spec (link it instead); anything about
a release that hasn't shipped yet as though it had.

**Distinct from Audit-artifact**: an audit-artifact is script-generated and
never hand-edited between regenerations; a release evidence ledger is
hand-authored once, for one release, and is not regenerated — closer to a
dated snapshot report than a machine-maintained state doc. It does not fit
State either (no single canonical "current truth," and it does not update as
the system changes — it is frozen to what was true at release time).

**Provenance note**: `specs/releases/` previously held free-form,
occasionally-duplicative release narrative that PR #2035 (2026-06-xx)
removed in a specs-simplification pass, folding surviving content into
`RELEASING.md`. That removal targeted narrative prose that duplicated other
specs; it did not consider (and this category did not exist at the time) a
structured, citation-only acceptance ledger. Reviving the directory for this
narrower, more disciplined purpose is a deliberate decision, not a silent
reversal — if it turns out to reproduce the same bloat, retire it the same
way, but that's a call for the next doc-hygiene pass to make with real
instances in hand, not a reason to avoid ever using the directory again.

## Docs — for humans using the framework

Top-level entry points: README.md, INSTALL.md, CHANGELOG.md.

**Generally contain**: how to install, how to use, what's changed, where to find more.

**Shouldn't contain**: internal jargon without a glossary, agent persona voice, SSoT claims.

---

Checking whether a document fits its category is a judgement an experienced reader can make — not a mechanical contract. Marsha or any reviewer asks: _is this in the right place, does it contain roughly the right kind of thing, does it leave out the kinds of thing it shouldn't have?_ If those answers are clear, it's compliant.
