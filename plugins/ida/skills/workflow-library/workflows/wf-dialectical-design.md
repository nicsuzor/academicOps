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

1. **Supervisor (`james`)**: Explicitly evaluates **proportionality**, **altitude**, and the **governing artifact standard** before dispatching reviewers, directs deliberation rounds, checks reviewer warrants and authority claims, holds tensions across specialist frames, and synthesizes the reconciled verdict (`PASS`, `REVISE`, or `FAIL`). A `FAIL` from any expert reviewer makes the combined verdict `FAIL`; the supervisor never downgrades or softens it (recalibrating an over-harsh reviewer is the user's job by reviewing that reviewer agent).
   - **Proportionality**: Weighs the artifact's stakes, blast radius, and reversibility at the start. For high-stakes, high-risk, or architectural work, allocates deeper refinement, multi-round dialectical debate, higher-capability models (`pro`), and instructs `marsha` to audit primary materials. For low-stakes, routine, or easily reversible work, restricts review to a fast, single-pass sanity check with lighter models (`flash` / `flash_lite`) and without primary-material expeditions so time and budget are not wasted.
   - **Altitude calibration & artifact-matched standard**: Sets and enforces the abstraction focus appropriate to the artifact (intervening immediately if reviewers drift into premature micro-implementation or untestable platitudes) and matches the format and evaluation standard to the artifact's genre (`specs/meta/doc-taxonomy.md` -- e.g., `specs/meta/writing-specs.md` for a specification, `craft` for agent instructions, disciplinary/genre standards for a scholarly or law review article, or task acceptance criteria for a task handback). Reviewers must never apply task-handback formatting (`## Ask`, task checklists) to non-task artifacts.
2. **Strategic Direction & Congruence (`pauli`)**: Evaluates the **core premise, strategic direction, and congruence with the "seamless web" of existing material** -- questioning the premise, naming the class of problem, probing for flawed reasoning, untested load-bearing assumptions, negative space, and missing edge cases, and situating the artifact within PKB graph topology, prior art, existing specifications, topic notes, parent strategic objectives, active sibling tasks, parsimony, and lifecycle coherence (`PASS`, `REVISE`, or `FAIL`).
3. **Compliance (`rbg`)**: Evaluates **compliance and scope of authority** -- testing the artifact's mechanisms and published surface against universal axioms, project-local rules, _ultra vires_ boundaries, data boundaries, and the enforcement pyramid's least-invasive hierarchy (`PASS`, `REVISE`, or `FAIL`).
4. **Quality & Requirements Satisfaction (`marsha`)**: Evaluates **whether the work actually delivers on its stated requirements and governing genre standard to an ambitious quality standard ("amazingly good", not merely working)** across actual rendered multimodal outputs (never code alone or simulated renders) and runtime execution against whatever governing standard, specifications, requirements, or acceptance criteria apply (`PASS`, `REVISE`, or `FAIL`). On **high-risk requests** (as calibrated by `james`), `marsha` also audits primary materials (git history, underlying source files, raw data). **If no governing standard, specifications, requirements, or acceptance criteria are available, treats that absence itself as an immediate critical failure signal (`FAIL`)** rather than guessing intent or grading on intuition.

## Input contract

- **Originating request**: The commissioning ask with its source identifier, quoted verbatim.
- **Target artifact & genre standard**: The specification, design proposal, manuscript, plan, document, diff, or PR under review, together with the format/quality standard governing that artifact type (e.g., `specs/meta/writing-specs.md` for specs).
- **Available specifications, requirements & criteria**: Explicit specifications, requirements, or acceptance criteria governing the artifact (or explicit notice that none exist).
- **Strategic context**: Parent objectives, active tasks, and related PKB notes or specifications.

## Stages

1. **Proportionality, Altitude & Standard Calibration (`james`)**:
   - Assess the artifact's importance, risk, blast radius, and reversibility from the originating request and context.
   - Select review depth (single-pass sanity check vs multi-round dialectical deliberation), model selection (`flash_lite`/`flash` for low-stakes sanity checks; `pro` for high-stakes or complex work), whether `marsha` should audit primary materials (reserved for high-risk requests), the target altitude, and the governing artifact standard.
2. **Independent Component Evaluation**:
   - Supervisor dispatches `pauli` (inline graph-only brief), `rbg` (artifact text/diff and rule/spec sources), and `marsha` (artifact, rendered outputs, test surface, governing genre standard/criteria, and -- on high-risk requests only -- primary materials) in parallel at the calibrated model selection.
   - Each reviewer evaluates strictly within its component jurisdiction against the artifact's governing standard and returns a verdict (`PASS`, `REVISE`, or `FAIL`) and findings. If no governing standard, specifications, requirements, or criteria are available, `marsha` immediately returns `FAIL`.
3. **Dialectical Deliberation, Epistemic Audit & Cross-Examination** _(scaled by proportionality)_:
   - For low-stakes sanity checks without critical tensions, proceed directly to synthesis.
   - For high-stakes work or conflicting component findings (e.g. compliance constraint vs strategic parsimony; congruence with existing specs vs proposed mechanism), Supervisor (`james`) reads outputs critically, checks warrants, and routes opposing peer critiques and factual falsifications across reviewers, forcing explicit defense, concession, or synthesis across rounds while maintaining altitude discipline:
     - **Documentation claims vs current state**: A documentation note (`README.md`, knowledge note) stating a behaviour proves only what the document says, not current working state. Require a completed task record (`status: done` with verification evidence) or verified live state before accepting a claim that a problem or mechanism is obsolete; if it cannot be established definitively, record it as an **open question** rather than settled fact.
     - **Authority of cited PRs or code**: Before aligning an artifact with a cited PR or code reference, verify that it is authoritative -- whether it is the most recent merged change, reflects current working behaviour, and is supported by an authoritative specification or decision record.
4. **Synthesis & Reconciled Verdict**:
   - Supervisor reconciles component outputs into a single unified findings table, unresolved open questions (if any), and overall verdict (`PASS`, `REVISE`, or `FAIL`), recording resolved tensions and accepted trade-offs on the artifact's tracking record. A `FAIL` from any expert reviewer (`pauli`, `rbg`, `marsha`) makes the combined verdict `FAIL`; the consolidating agent never downgrades or softens an expert's `FAIL`. If an expert reviewer is judged too harsh, that is the user's responsibility to fix by reviewing the underlying review agent, not the consolidating agent's job to soften.

## Output contract

- Calibration summary recording chosen proportionality (depth, rounds, model selection, and whether primary-material auditing was enabled), target altitude, and governing artifact standard.
- Reconciled findings table mapping issues across Strategic Direction & Congruence (`pauli`), Compliance (`rbg`), and Quality & Requirements Satisfaction (`marsha`), with resolved tensions, accepted trade-offs, and any still-open questions.
- Final unified verdict (`PASS`, `REVISE`, or `FAIL`) written to the artifact's tracking record. Any expert reviewer's `FAIL` makes the combined verdict `FAIL`; the supervisor never downgrades or softens it.

## When to include

Any review of a specification, architectural design, plan, document, or pull request requiring calibrated multi-perspective evaluation across strategic congruence, rule compliance, and requirement satisfaction.
