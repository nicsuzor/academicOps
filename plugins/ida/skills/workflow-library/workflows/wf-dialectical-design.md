---
alias:
  - wf-dialectical-design
  - wf-design-dialectic
  - wf-dialectical-review
  - wf-review-dialectic
description: "Universal multi-agent dialectical review workflow: Supervisor (james) calibrates proportionality and altitude upfront and coordinates Pauli (strategic direction, core premise, and congruence with existing material), RBG (compliance and scope of authority), and Marsha (ambitious quality and requirement satisfaction across rendered multimodal outputs) to evaluate any artifact into a reconciled PASS, REVISE, or FAIL verdict."
id: wf-dialectical-design
tags:
  - wf-template
  - dialectic
  - multi-agent
  - review
  - design
  - evaluation
title: Dialectical Review and Design Workflow
type: template
---

## What this step does

Orchestrates a modular, universal multi-agent dialectical review of any target artifact (specification, design proposal, plan, document, pull request, or task graph change). Rather than running fixed-depth checklists in isolation, the Supervisor (`james`) explicitly calibrates proportionality and altitude at intake, dispatches three distinct review components in parallel, drives cross-examination only where stakes and tensions warrant, and synthesizes a reconciled verdict (`PASS`, `REVISE`, or `FAIL`).

## Review Components

1. **Supervisor (`james`)**: Explicitly evaluates **proportionality** and **altitude** before dispatching reviewers, directs deliberation rounds, holds tensions across specialist frames, and synthesizes the reconciled verdict (`PASS`, `REVISE`, or `FAIL`).
   - **Proportionality**: Weighs the artifact's stakes, blast radius, and reversibility at the start. For high-stakes, architectural, or critically important work, allocates deeper refinement, multi-round dialectical debate, and higher-capability models (`pro`). For low-stakes, routine, or easily reversible work, restricts review to a fast, single-pass sanity check with lighter models (`flash` / `flash_lite`) so time and budget are not wasted.
   - **Altitude calibration**: Sets and enforces the abstraction focus appropriate to the artifact, intervening immediately if reviewers drift too low (into premature micro-implementation or keystrokes) or too high (into untestable platitudes).
2. **Strategic Direction & Congruence (`pauli`)**: Evaluates the **core premise, strategic direction, and congruence with the "seamless web" of existing material** -- questioning the premise, naming the class of problem, probing for flawed reasoning, untested load-bearing assumptions, negative space, and missing edge cases, and situating the artifact within PKB graph topology, prior art, existing specifications, topic notes, parent strategic objectives, parsimony, and lifecycle coherence (`PASS`, `REVISE`, or `FAIL`).
3. **Compliance (`rbg`)**: Evaluates **compliance and scope of authority** -- testing the artifact's mechanisms and published surface against universal axioms, project-local rules, _ultra vires_ boundaries, data boundaries, and the enforcement pyramid's least-invasive hierarchy (`PASS`, `REVISE`, or `FAIL`).
4. **Quality & Requirements Satisfaction (`marsha`)**: Evaluates **whether the work actually delivers on its stated requirements to an ambitious quality standard ("amazingly good", not merely working)** across actual rendered multimodal outputs (never code alone or simulated renders), runtime execution, and primary sources against whatever specifications, requirements, or acceptance criteria are available (`PASS`, `REVISE`, or `FAIL`). **If no specifications, requirements, or acceptance criteria are available, treats that absence itself as an immediate critical failure signal (`FAIL`)** rather than guessing intent or grading on intuition.

## Input contract

- **Originating request**: The commissioning ask with its source identifier, quoted verbatim.
- **Target artifact**: The specification, design proposal, plan, document, diff, or PR under review.
- **Available specifications, requirements & criteria**: Explicit specifications, requirements, or acceptance criteria governing the artifact (or explicit notice that none exist).
- **Strategic context**: Parent objectives, active tasks, and related PKB notes or specifications.

## Stages

1. **Proportionality & Altitude Calibration (`james`)**:
   - Assess the artifact's importance, blast radius, and reversibility from the originating request and context.
   - Select review depth (single-pass sanity check vs multi-round dialectical deliberation) and model selection (`flash_lite`/`flash` for low-stakes sanity checks; `pro` for high-stakes or complex work), and state the target altitude.
2. **Independent Component Evaluation**:
   - Supervisor dispatches `pauli` (inline graph-only brief), `rbg` (artifact text/diff and rule/spec sources), and `marsha` (artifact, rendered outputs, test surface, and available specifications/requirements/criteria) in parallel at the calibrated model selection.
   - Each reviewer evaluates strictly within its component jurisdiction and returns a verdict (`PASS`, `REVISE`, or `FAIL`) and findings. If no specifications, requirements, or criteria are available, `marsha` immediately returns `FAIL`.
3. **Dialectical Deliberation & Cross-Examination** _(scaled by proportionality)_:
   - For low-stakes sanity checks without critical tensions, proceed directly to synthesis.
   - For high-stakes work or conflicting component findings (e.g. compliance constraint vs strategic parsimony; congruence with existing specs vs proposed mechanism), Supervisor (`james`) reads outputs critically and routes opposing peer critiques across reviewers, forcing explicit defense, concession, or synthesis across rounds while maintaining altitude discipline.
4. **Synthesis & Reconciled Verdict**:
   - Supervisor reconciles component outputs into a single unified findings table and overall verdict (`PASS`, `REVISE`, or `FAIL`), recording resolved tensions and accepted trade-offs on the artifact's tracking record.

## Output contract

- Calibration summary recording chosen proportionality (depth, rounds, model selection) and target altitude.
- Reconciled findings table mapping issues across Strategic Direction & Congruence (`pauli`), Compliance (`rbg`), and Quality & Requirements Satisfaction (`marsha`), with resolved tensions and accepted trade-offs.
- Final unified verdict (`PASS`, `REVISE`, or `FAIL`) written to the artifact's tracking record.

## When to include

Any review of a specification, architectural design, plan, document, or pull request requiring calibrated multi-perspective evaluation across strategic congruence, rule compliance, and requirement satisfaction.
