---
id: TBD
title: In-Session Enforcement — The Pyramid (Layers 0–1)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

<!-- DRAFT — new layer-model revision, WIP. Nic-led session (task aops-499e16ab). -->
<!-- Scope: Layer 0 (intra-task) + Layer 1 (turn loop / the pyramid). Wrapping/framing prose deferred. -->
<!-- Interactivity is ORTHOGONAL to these layers — do NOT bake interactive-vs-autonomous distinctions in here; both layers operate identically either way. Parked for a later pass. -->

## Layer 0 — Intra-task loop (harness-internal)

The span **inside a single user-prompt → completion**: the harness's own thinking
turns and internal sub-agent delegation as it works out _how_ to satisfy a
high-level prompt.

- Agent harnesses are continuously improving and change these internal processes
  frequently — more thinking turns, more internal sub-agent delegation — to
  better deliver on high-level user prompts.
- **Posture: not our preferred layer to operate in.** It is fragile and changes
  too fast to build enforcement on. But we do **not** completely refuse to act
  here.
- **Default contract with the agent is outcome, not method:** trust the agent to
  figure out how to do the specific task it was given.

## Layer 1 — Turn loop (the pyramid)

The span from a **user-prompt to a Stop event**; may be recursive (sub-agent
delegation nested within the turn).

- **What it enforces:** the agent gives honest answers and has not been lazy.
- **Sensitivity:** the layer most exposed to model-performance and
  harness-behaviour changes — both outside our control. We adapt to it over time
  through the `/aops-core:learn` system as we go.
- **Mechanism shape:** the enforcement **pyramid** — responsive, proportionate,
  evidence-driven; graduated from a wide cheap base to a rare heavy tip.
  _[pyramid internal structure — base/middle/tip, least-invasion-first,
  escalation discipline — to be carried in from the current design spec.]_
