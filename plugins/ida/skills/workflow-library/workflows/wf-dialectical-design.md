---
alias:
  - wf-dialectical-design
  - wf-design-dialectic
description: "Multi-agent dialectical design workflow: a supervisor coordinates Pauli and RBG in structured debate over design hypotheses until synthesis or intervention."
id: wf-dialectical-design
tags:
  - wf-template
  - dialectic
  - multi-agent
  - design
  - architecture
title: wf-dialectical-design
type: template
---

## What this step does

Orchestrates a multi-agent dialectical design process to resolve complex architectural decisions, reconcile competing constraints, and prevent task graph accretion before tasks are committed to the graph.

## Agent Structure

1. **Supervisor** (`ida` / coordinator): Drives the design problem, calibrates the altitude of discussion, challenges shaky premises, and synthesizes consensus.
2. **Pauli** (Topology & Memory): Analyzes graph impact, prior art, existing PKB notes/tasks, prevents duplication, and enforces consolidation.
3. **RBG** (Axiomatic Compliance): Evaluates proposals against universal axioms, project rules, enforcement pyramid levels, and invariants.

## Stages

1. **Problem Framing & Hypothesis Initiation**: Supervisor frames the core tension, empirical observations, and draft intervention workstreams.
2. **Dialectical Deliberation**:
   - Supervisor dispatches the initial framing to both Pauli and RBG.
   - Pauli evaluates graph topology, existing task overlaps, and historical precedent.
   - RBG evaluates rule invariants, mechanism invasion levels, and categorical principles.
   - Supervisor prompts each subagent with peer critiques, forcing cross-examination of trade-offs.
3. **Supervisor Calibration & Convergence**:
   - Supervisor monitors the debate and intervenes if agents:
     - Work at too low a level of detail (drifting into keystrokes or premature implementation).
     - Work at too high a level of detail (abstract hand-waving lacking verifiable mechanisms).
     - Stall or loop without making progress within task scope.
   - Supervisor drives the exchange toward an explicit synthesis.
4. **Reconciliation & Graph Mapping**:
   - Fold agreed workstreams into existing ready tasks where possible; isolate novel obligations into minimal distinct tasks.
   - Formally record accepted compromises and rejected mechanisms with explicit reasons.
5. **Approval Boundary**:
   - File the reconciled specification on the record with a dependency map.
   - Cut the composition chain: downstream execution tasks remain blocked until user authorization is recorded via an explicit decision item.

## Output contract

- Reconciled technical design specification resolving the core tension.
- Recorded dialectical consensus between Pauli (graph) and RBG (rules).
- Pruned graph mapping: existing task modifications vs new tasks minted.
- Dependency-wired approval checkpoint blocking downstream execution.

## When to include

Architectural design, system interventions, or cross-cutting framework changes where competing constraints (axioms vs graph state vs execution realities) require rigorous multi-perspective debate.
