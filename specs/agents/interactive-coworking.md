---
id: interactive-coworking
title: Interactive Co-Working — polecat vs interactive posture, self-contained agents
type: spec
status: approved
tier: core
depends_on: [polecat-system, agent-definition-content, agent-authority]
tags: [spec, agents, interactive-mode, ida, agent-doctrine]
created: 2026-06-26
---

# Interactive Co-Working — settled doctrine

**Status**: Settled (Nic, 2026-06-26). Full design-dialogue and provenance trail: [[mem-438429c5]] (consolidates [[mem-47da1659]], [[mem-d241b0c2]], [[mem-f164fc68]], [[note-36c15a69]]; mechanism note [[mem-e7b976da]]). Git history preserves the deliberation in full; this note states only the settled outcome.

**Revision (2026-07-01)**: Junior — one of the two head agents this doctrine was originally written against — has moved into userspace, out of this plugin (it is now a user-level tool; see `specs/SURFACES.md`'s `~/junior` SDK launcher). Ida is now the plugin's sole head personality. The doctrine below is unchanged in substance — it was always a rule about _how any head agent must be shaped_, not a rule specific to having exactly two — updated only to stop naming Junior as a currently-shipped example.

## Doctrine

Agents are **not subclassed**. Each head agent — currently just Ida within this plugin — is a fully self-contained agent definition: it carries its own disposition, quality floor, and (where relevant) domain disposition inline, in its own file. This holds for any future head agent added to the roster, too. Duplicated prose across agents is the accepted cost of self-containment, not a bug to be DRY'd away. A shared "disposition skill" referenced by multiple agents is subclassing by another name: it makes agents non-portable and forces framework-coupled items to be kept "conditional" for stranger repos. Reusable _procedures_ (dispatch mechanics, supervision, task lifecycle) are the exception — agents may invoke `/supervisor`, `/dispatch`, `/task-lifecycle`, etc., because invoking a procedure is not the same as inheriting a disposition.

The one universal exception is safety: Safety Invariants + PKB-HALT live in the session-start SSoT and are injected into every surface, including polecats, because they must reach agent-less surfaces — not for DRY.

The real behavioural axis is **polecat vs interactive**, not agent identity — a rule established when the framework shipped two head agents (Junior, Ida) side by side and needed to keep their behavioural contract independent of which one was running:

- **Polecat (autonomous)**: drive-to-completion; hard block-until-resolved handover gate.
- **Interactive (non-polecat)**: hold between steps, user drives the sequence, don't front-run a plan or deflect self-answerable questions to the user; soft block-once-then-release handover gate.

Both postures share the same quality floor and the same non-negotiable safety invariants; only the drive-to-completion behaviour and the handover gate's blocking strictness differ, and both are resolved per-surface from `polecat.yaml` — never from a `session_type` classifier or a launch-time mode switch.

This doctrine is implemented in `aops-core/agents/ida.md`, self-contained per the rule above. Any future in-plugin head agent (or Junior, if it is ever reintroduced here) must satisfy the same rule rather than sharing a disposition base with Ida. See also [[polecat-system]] (the dispatch surface the axis keys on), [[agent-definition-content]] (content-boundary rules), and [[agent-authority]] (non-subclassing rules each agent file must satisfy).
