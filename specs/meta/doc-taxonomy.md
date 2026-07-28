---
title: Documentation in aops — where things go
---

# Documentation in aops — where things go

Five kinds of document, partitioned by who reads them.

**How to choose**: ask "who reads this?" — an agent at runtime (instructions), a dev or auditor changing the system (specs), both agents and devs looking up the current truth (state), a script consuming machine output (audit-artifact), or a human using the framework (docs).

## Instructions — for agents executing

Live in `plugins/<plugin>/agents/<name>.md` (personas, loaded via the `Agent` tool), `plugins/<plugin>/skills/<name>/SKILL.md` (skills, loaded via the `Skill` tool), and `.agents/CORE.md` + `rules/*.md` (always-on context loaded by the harness).

**Generally contain**: who the agent is or what the skill does, what tools and permissions it has, what to do in common situations.

**Shouldn't contain**: dated log entries (git knows), spec-style "how could this work differently" debate (that's a spec), SSoT claims about system facts (that's state), or pasted-in generator output (that's an audit-artifact).

This spec answers _which file_ by audience. For how enforcement mechanisms apply (the levers, and the delivery-channel-vs-verdict split), see [enforcement.md](../enforcement/enforcement.md).

<!-- NS: We should make some brief quality and substance notes about what info each doc should and shouldn't contain and how to know it's good. -->

## Specs — for devs and auditors

Live in `specs/<subsystem>/<name>.md` at the academicOps root.

**Generally contain**: what the subsystem is for, what design choices were made and why, how it should behave, what enacts it. Statused (`inbox` / `draft` / `ready` / `in_progress` / `superseded`) and supersedable.

> **Note — document status, not task status.** This `draft`/`superseded` vocabulary is the _document_ lifecycle for specs; it is distinct from the canonical _task_ status set (the SSoT is [[TAXONOMY#status-values-and-transitions]]). Do not conflate the two: `draft` and `superseded` are not valid task statuses, and the task lifecycle does not govern spec documents.

**Shouldn't contain**: per-agent log entries, imperative agent instructions (those go in instructions), generated tables (audit-artifact), or provenance.

**No provenance.** A spec states what's true and why, not who decided it, where, or when. PKB task/session IDs, ruling numbers, and "ruled by X on date Y" citations belong in git commit messages and task files — cite them there, not in the spec body. A reference-only section that just enumerates adjacent task IDs with no other content (a "related work" list) belongs in the tracking task, not the spec; if a spec genuinely depends on another spec's content, link that spec by name, not a PKB ID.

**A spec declares intended behavior — for any subsystem, including this repo's own tooling — and it may be aspirational.** A spec is a _specification_: what a subsystem is designed to do and why, not a live telemetry feed of what the code happens to do today. Drift between a spec and the code is an expected, ordinary state of the world (it means there's a bug or an unfinished migration to fix — it is not evidence the doc is miscategorized). That's the axis that actually separates a spec from a **state** doc: a state doc claims to be the current-truth SSoT ("this IS what the system does right now"); a spec claims to be the designed target ("this is what the subsystem is for and how it should behave"), and is allowed to be ahead of, or drift from, reality.

Nothing about that test cares whether the subsystem is "the shipped system" or "this repo's own process." This repo's own build, packaging, install, and release tooling — the Makefile, `build/build.py`, the CI publish pipeline — is a designed subsystem exactly like a runtime gate or a hook client-translation layer, and its intended behavior belongs in a spec the same way: see [`specs/build-and-install.md`](../build-and-install.md).

What still stays OUT of `specs/` is pure **procedure for a human contributor** — a step list with no design intent to state, e.g. `git clone` + `uv sync`, which command to run before committing, PR-template mechanics. That lives in `CONTRIBUTING.md` at the repo root, which cross-references the relevant specs for _why_ rather than restating their content.

**One fact, one file.** Before adding a fact to a spec, check whether an already-mapped file — a state doc, another spec, a rule — owns it already. This generalises the enforcement-map-currency principle in [RULES.md](../../.agents/rules/RULES.md#enforcement-map-currency): a fact should have exactly one authoritative home, and every other mention should reference that home rather than restate it.

If an already-mapped file owns it, extend or link that file instead of duplicating the fact here. A second copy of the same fact isn't a clarification — it's a duplication liability that drifts the moment one copy is edited and the other isn't.

## State — the SSoT for what the system IS right now

Read by both agents (at runtime, for lookups) and devs (at design time, when changing the system). **One canonical location per slice.**

**Default location**: `specs/<NAME>.md` at the repo root (e.g. GATES, SURFACES, ENFORCEMENT-MAP, CAPABILITIES, CONSTRAINTS). May live outside the repo in PKB or machine config when the slice depends on user or machine conditions. May be `.md` or `.yaml` (e.g. `polecat.yaml`).

**Generally contain**: the current truth about one thing — concepts, rules, schemas, routing tables.

**Shouldn't contain**: proposals or "should we" (those are specs), dated log entries.

**Pattern for runtime-subsystem state docs.** Each element of a runtime subsystem gets the same five-question shape: **what is it** (one-sentence definition + class of failure caught), **where does it live** (source path, plugin-cache location at runtime, which agent/skill loads it), **how is it configured** (config keys, env vars, cache invalidation cadence), **how do I verify it's firing** (commands, log paths, expected output), **how do I debug it when it isn't** (top failure modes + diagnostics). Adjacent docs that retain non-overlapping content get a header note framing their role and a cross-reference back to the canonical; docs whose content is wholly subsumed by the canonical become redirect stubs (frontmatter `status: superseded`, `supersedes_target: <path>`).

## Audit-artifact — generated by scripts, never hand-edited

Live in-repo at `specs/audit/AGENT-*.md`.

**Generally contain**: a script-produced snapshot, with a `Generated on X from Y` header at the top so a reader knows it's not authored content.

**Shouldn't contain**: anything edited by hand between regenerations.

## Docs — for humans using the framework

Top-level entry points: README.md, INSTALL.md, CHANGELOG.md. Per plugin: `plugins/<plugin>/README.md`.

**Generally contain**: how to install, how to use, what's changed, where to find more.

**Shouldn't contain**: internal jargon without a glossary, agent persona voice, SSoT claims.

**Plugin README.** One audience: the person using the plugin. Its job is to show exactly how the plugin works, in this order: **what it is for** (one sentence), **how it works** (a mermaid flowchart of the real path from a trigger — a user prompt, a hook event, an agent invocation — through its agents, skills, and hooks to an outcome, showing the flow that exists rather than an idealised one), **what it provides** (agents, skills, commands, hooks — a table, one line each), **how it is configured** (every environment variable and `userConfig` field it reads, what each is for, and that there are no defaults), and **what it depends on**. Source-level citation and file-path naming are not required of it — the reader it serves is using the plugin, not extending it. The flowchart is derived from the source and verified against it; it simply does not cite it.

**The split with `specs/`.** Design rationale, why a choice was made, and the seams and gaps go to `specs/`, which serves the developer extending the plugin. A README that argues for the plugin's design is a spec in the wrong place; so is a history, a roadmap, or a changelog.

---

Checking whether a document fits its category is a judgement an experienced reader can make — not a mechanical contract. Marsha or any reviewer asks: _is this in the right place, does it contain roughly the right kind of thing, does it leave out the kinds of thing it shouldn't have?_ If those answers are clear, it's compliant.
