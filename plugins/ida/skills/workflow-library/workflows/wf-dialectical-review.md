---
alias:
  - wf-dialectical-review
  - wf-dialectical-design
  - wf-review-dialectic
  - wf-design-dialectic
  - wf-review
  - wf-multi-agent-review
default: true
description: "Universal default dialectical review workflow: Supervisor (james) calibrates proportionality and altitude upfront, coordinates review across strategic direction/congruence (pauli), compliance (rbg), and quality/requirement satisfaction (marsha) into a reconciled PASS, REVISE, or FAIL verdict, and defines the shared review briefing."
id: wf-dialectical-review
tags:
  - wf-template
  - review
  - dialectic
  - multi-agent
  - briefing
  - default
title: Dialectical Review Workflow
type: template
---

## What this step does

Universal default review workflow: coordinated by **`james` as Supervisor**, who explicitly evaluates **proportionality** and **altitude** at intake before dispatching three non-overlapping review components -- **Strategic Direction & Congruence (`pauli`)**, **Compliance (`rbg`)**, and **Quality & Requirements Satisfaction (`marsha`)** -- and defines the one shared review briefing drawn on by all review dispatches. Spawns internal subagents to provide distinct specialist perspectives concurrently under the supervisor.

## Shared Review Briefing

All three review components (`pauli`, `rbg`, `marsha`), whether dispatched as subagents in `/strategic-review`, minted as review tasks in `/reify`, or composed in workflow templates, receive their briefing drawn from this shared structure. The brief presents the originating request and available specifications/requirements/criteria before the artifact or diff under review, so reviewers evaluate intent, requirements, and proportion before inspecting implementation details.

### Structure of the Brief

1. **Originating Request & Governing Standard / Criteria (Read First)**:
   The originating request is quoted verbatim with its source identifier, alongside the format/quality standard governing the artifact's genre (`specs/meta/doc-taxonomy.md` -- e.g., `specs/meta/writing-specs.md` for specifications, `craft` for agent instructions, genre criteria for manuscripts/articles, or task acceptance criteria for task handbacks) and any explicit specifications, requirements, or acceptance criteria, before any link to the pull request, branch name, or diff:
   ```markdown
   ## Originating Request & Requirements

   > [The verbatim text of the user request, commission, or parent task ask authorizing this work]

   - **Source**: `<source-id-or-task-id>`
   - **Artifact Genre & Governing Standard**: `<artifact type + governing standard, e.g. specification per specs/meta/writing-specs.md>`
   - **Specifications / Acceptance Criteria**: `<explicit criteria or spec pointers, or "NONE AVAILABLE">`
   ```

2. **Supervisor Calibration (`james`)**:
   - **Proportionality**: Single-pass sanity check with lighter models (`flash` / `flash_lite`) for low-stakes or routine work, vs multi-round dialectical deliberation with higher-capability models (`pro`) for high-stakes, complex, or critical work. Explicitly specifies whether the request is **high-risk** (authorizing `marsha` to audit primary materials).
   - **Target altitude**: The abstraction focus appropriate to the artifact (preventing drift into micro-implementation or untestable generalities).

3. **Target Artifact**:
   The candidate change or deliverable under review (read only after the originating request and requirements):
   - **Repository**: `<owner/repo>`
   - **Pull Request**: `<PR URL and number>`
   - **Branch / Head Commit**: `<branch-name> / <commit-sha>`
   - **Diff / Content**: `<diff or artifact reference>`

4. **Review Role & Instructions**:
   All reviewers evaluate the artifact against its governing genre standard (never applying task-handback sections like `## Ask` to non-task artifacts) and return verdicts in the unified `PASS`, `REVISE`, or `FAIL` vocabulary:
   - **Strategic Direction & Congruence (`pauli`)**: Evaluates the core premise, strategic direction, and congruence with the "seamless web" of existing material in the PKB (graph topology, prior art, existing specifications, topic notes, parent objectives, active sibling tasks, parsimony, and lifecycle coherence) from an inline graph-only brief (`PASS`, `REVISE`, or `FAIL`).
   - **Compliance (`rbg`)**: Evaluates compliance with universal axioms, project-local rules, scope of delegated authority (_ultra vires_), data boundaries, and the enforcement pyramid (`PASS`, `REVISE`, or `FAIL`). From the quoted request alone, state the non-mechanical baseline before reading the diff: if an agent workflow or instructions meet the request, building executable scripts or test harnesses is an over-engineered defect (`FAIL` under `no-over-engineering` and `proportionate`). State the smallest proportionate mechanism before reading the diff.
   - **Quality & Requirements Satisfaction (`marsha`)**: Evaluates whether the work actually delivers on its stated requirements and governing genre standard to an ambitious quality standard ("amazingly good", not merely working) across actual rendered multimodal outputs (never code alone or simulated renders) and runtime execution (`PASS`, `REVISE`, or `FAIL`), and audits primary materials when calibrated as a **high-risk request**. **If no governing standard, specifications, requirements, or acceptance criteria are available, treats that absence itself as an immediate critical failure signal (`FAIL`).**

## Input contract

The invoking workflow provides:

1. **Originating request** -- the commissioning ask with its source id, quoted verbatim.
2. **Target artifact & governing genre standard** -- the file, diff, PR reference, manuscript, or specification under review and the standard that governs its format (`specs/meta/doc-taxonomy.md`).
3. **Available specifications, requirements & acceptance criteria** -- explicit requirements and constraints governing the artifact (or explicit notice of their absence).
4. **Strategic context** -- parent task, target objectives, and related PKB notes or specifications.

## Review Perspectives

1. **Supervisor (`james`)**: Explicitly evaluates **proportionality**, **altitude**, and the **governing artifact standard** before dispatching reviewers, directs deliberation rounds, checks reviewer warrants and authority claims, holds tensions across specialist frames, and synthesizes the reconciled verdict (`PASS`, `REVISE`, or `FAIL`). A `FAIL` from any expert reviewer makes the combined verdict `FAIL`; the supervisor never downgrades or softens it (recalibrating an over-harsh reviewer is the user's job by reviewing that reviewer agent).
   - **Proportionality**: Weighs the artifact's stakes, blast radius, and reversibility at the start. For high-stakes, high-risk, or architectural work, allocates deeper refinement, multi-round dialectical debate, higher-capability models (`pro`), and instructs `marsha` to audit primary materials. For low-stakes, routine, or easily reversible work, restricts review to a fast, single-pass sanity check with lighter models (`flash` / `flash_lite`) and without primary-material expeditions so time and budget are not wasted.
   - **Altitude calibration & artifact-matched standard**: Sets and enforces the abstraction focus appropriate to the artifact (intervening immediately if reviewers drift into premature micro-implementation or untestable platitudes) and matches the format and evaluation standard to the artifact's genre (`specs/meta/doc-taxonomy.md` -- e.g., `specs/meta/writing-specs.md` for a specification, `craft` for agent instructions, disciplinary/genre standards for a scholarly or law review article, or task acceptance criteria for a task handback). Reviewers must never apply task-handback formatting (`## Ask`, task checklists) to non-task artifacts.
2. **Strategic Direction & Congruence (`pauli`)**: Evaluates the **core premise, strategic direction, and congruence with the "seamless web" of existing material** -- questioning the premise, naming the class of problem, probing for flawed reasoning, untested load-bearing assumptions, negative space, and missing edge cases, and situating the artifact within PKB graph topology, prior art, existing specifications, topic notes, parent strategic objectives, active sibling tasks, parsimony, and lifecycle coherence (`PASS`, `REVISE`, or `FAIL`).
3. **Compliance (`rbg`)**: Evaluates **compliance and scope of authority** -- testing the artifact's mechanisms and published surface against universal axioms, project-local rules, _ultra vires_ boundaries, data boundaries, and the enforcement pyramid's least-invasive hierarchy (`PASS`, `REVISE`, or `FAIL`).
4. **Quality & Requirements Satisfaction (`marsha`)**: Evaluates **whether the work actually delivers on its stated requirements and governing genre standard to an ambitious quality standard ("amazingly good", not merely working)** across actual rendered multimodal outputs (never code alone or simulated renders) and runtime execution against whatever governing standard, specifications, requirements, or acceptance criteria apply (`PASS`, `REVISE`, or `FAIL`). On **high-risk requests** (as calibrated by `james`), `marsha` also audits primary materials (git history, underlying source files, raw data). **If no governing standard, specifications, requirements, or acceptance criteria are available, treats that absence itself as an immediate critical failure signal (`FAIL`)** rather than guessing intent or grading on intuition.

## Stages

1. **Supervisor proportionality, altitude, and standard calibration (`james`)**: Upfront assessment of task importance, risk, blast radius, and reversibility to determine review depth, number of deliberation rounds, subagent model selection (`pro` vs `flash`/`flash_lite`), whether `marsha` audits primary materials (high-risk requests only), target discussion altitude, and the governing genre standard.
2. **Independent Perspective Evaluation**:
   - The default review workflow coordinates multiple specialist review perspectives concurrently as internal subagents (`pauli`, `rbg`, `marsha`) under supervisor `james`.
   - Supervisor dispatches `pauli` (inline graph-only brief), `rbg` (artifact text/diff and rule/spec sources), and `marsha` (artifact, rendered outputs, test surface, governing genre standard/criteria, and -- on high-risk requests only -- primary materials) in parallel at the calibrated model selection.
   - For low-stakes or routine tasks where the supervisor calibrates review proportionality upfront to a single-pass sanity check, review may execute without spawning concurrent subagents.
   - In an environment where subagent spawning is required but unavailable, execution halts immediately with an explicit error without silent single-agent fallback (`fail-fast`, `no-fallbacks`).
   - Each reviewer evaluates strictly within its component jurisdiction against the artifact's governing standard and returns a verdict (`PASS`, `REVISE`, or `FAIL`) and findings. If no governing standard, specifications, requirements, or criteria are available, `marsha` immediately returns `FAIL`.
3. **Dialectical Deliberation, Epistemic Audit & Cross-Examination** _(scaled by proportionality)_:
   - For low-stakes sanity checks without critical tensions, proceed directly to synthesis.
   - For high-stakes work or conflicting component findings (e.g. compliance constraint vs strategic parsimony; congruence with existing specs vs proposed mechanism), Supervisor (`james`) reads outputs critically, checks warrants, and routes opposing peer critiques and factual falsifications across reviewers, forcing explicit defense, concession, or synthesis across rounds while maintaining altitude discipline:
     - **Documentation claims vs current state**: A documentation note (`README.md`, knowledge note) stating a behaviour proves only what the document says, not current working state. Require a completed task record (`status: done` with verification evidence) or verified live state before accepting a claim that a problem or mechanism is obsolete; if it cannot be established definitively, record it as an **open question** rather than settled fact.
     - **Authority of cited PRs or code**: Before aligning an artifact with a cited PR or code reference, verify that it is authoritative -- whether it is the most recent merged change, reflects current working behaviour, and is supported by an authoritative specification or decision record.
4. **Synthesis, Reconciled Verdict & Headless Release**:
   - Supervisor reconciles component outputs into a single unified findings table, unresolved open questions (if any), and overall verdict (`PASS`, `REVISE`, or `FAIL`), recording resolved tensions and accepted trade-offs on the artifact's tracking record.
   - A `FAIL` from any expert reviewer (`pauli`, `rbg`, `marsha`) makes the combined verdict `FAIL`; the consolidating supervisor never downgrades or softens an expert's `FAIL`. If an expert reviewer is judged too harsh, that is the user's responsibility to fix by reviewing the underlying review agent, not the consolidating agent's job to soften.
   - **Headless Release Contract**: A review worker executing the default review workflow releases its task with terminal status strictly matching the review outcome:
     - A `PASS` verdict releases the task as `done` with the structured review report and verification evidence.
     - A `REVISE` or `FAIL` verdict releases the task as `failed` (or `partial`), recording findings and defect tags in the release reason. The worker never prompts interactively, pauses for user input, or mints downstream tasks on the graph.

## Output contract

A unified review report containing:

- Supervisor calibration summary (proportionality, model selection, rounds, primary-material audit scope, altitude, and governing genre standard).
- The itemized findings table mapping issues to reviewer components, feedback, dispositions, and any unresolved open questions.
- The reconciled overall verdict (`PASS`, `REVISE`, or `FAIL`). Any expert reviewer's `FAIL` makes the combined verdict `FAIL`; the supervisor never downgrades or softens it.
- Persistent write-back to the artifact's task record or review surface.

## When to include

Any milestone, specification, design proposal, plan, document, or pull request requiring multi-perspective verification prior to merge, execution, or release. Selected as the default review workflow for independent review stages across the workflow library when no alternative review template is designated.
