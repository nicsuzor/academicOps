---
id: TBD
title: In-Session Enforcement — The Work-Unit Contract (Layer 2)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

<!-- DRAFT — new layer-model revision, WIP. Nic-led session (task aops-499e16ab). -->
<!-- Scope: Layer 2 (work-unit loop / the task contract). Wrapping/framing prose deferred. -->
<!-- Interactivity is ORTHOGONAL — do NOT bake interactive-vs-autonomous distinctions in here. Parked for a later pass. -->

## Layer 2 — Work-unit loop (the task contract)

Operative from PKB **`claim_task` → `release_task`**. That pair **is** the
contract for a single agent session's single unit of work.

- Fires **after a full Stop event** — the point at which the agent has finished a
  chunk of work.
- One session, one claimed unit of work, released under contract.
- **Completion is not a claim — it is a claim carrying verification.** The
  release binds evidence to the state of the work.
  _[evidence-contract detail to be carried in.]_
