---
alias:
  - wf-review
  - wf-multi-agent-review
description: Universal composite review workflow -- Supervisor (james) calibrates proportionality and altitude upfront, coordinates review across strategic direction/congruence (pauli), compliance (rbg), and quality/requirement satisfaction (marsha) into a unified PASS, REVISE, or FAIL verdict, and defines the shared review briefing.
id: wf-review
tags:
  - wf-template
  - review
  - composite
  - dialectic
  - briefing
title: Multi-Agent Review Workflow
type: template
---

## What this step does

Universal review workflow: coordinated by **`james` as Supervisor**, who explicitly evaluates **proportionality** and **altitude** at intake before dispatching three non-overlapping review components -- **Strategic Direction & Congruence (`pauli`)**, **Compliance (`rbg`)**, and **Quality & Requirements Satisfaction (`marsha`)** -- and defines the one shared review briefing drawn on by all review dispatches.

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
   - **Compliance (`rbg`)**: Evaluates compliance with universal axioms, project-local rules, scope of delegated authority (_ultra vires_), data boundaries, and the enforcement pyramid (`PASS`, `REVISE`, or `FAIL`). From the quoted request alone, state the smallest proportionate mechanism before reading the diff.
   - **Quality & Requirements Satisfaction (`marsha`)**: Evaluates whether the work actually delivers on its stated requirements and governing genre standard to an ambitious quality standard ("amazingly good", not merely working) across actual rendered multimodal outputs (never code alone or simulated renders) and runtime execution (`PASS`, `REVISE`, or `FAIL`), and audits primary materials when calibrated as a **high-risk request**. **If no governing standard, specifications, requirements, or acceptance criteria are available, treats that absence itself as an immediate critical failure signal (`FAIL`).**

## Input contract

The invoking workflow provides:

1. **Originating request** -- the commissioning ask with its source id, quoted verbatim.
2. **Target artifact & governing genre standard** -- the file, diff, PR reference, manuscript, or specification under review and the standard that governs its format (`specs/meta/doc-taxonomy.md`).
3. **Available specifications, requirements & acceptance criteria** -- explicit requirements and constraints governing the artifact (or explicit notice of their absence).
4. **Strategic context** -- parent task, target objectives, and related PKB notes or specifications.

## Composite Stages

A composite review workflow specifies its stages by contract expectations in order:

1. **Supervisor proportionality, altitude, and standard calibration (`james`)**: Upfront assessment of task importance, risk, blast radius, and reversibility to determine review depth, number of deliberation rounds, subagent model selection (`pro` vs `flash`/`flash_lite`), whether `marsha` audits primary materials (high-risk requests only), target discussion altitude, and the governing genre standard.
2. **Strategic direction and congruence evaluation (`pauli`)**: An independent evaluation questioning the core premise, situating the artifact against parent strategic direction, and testing congruence with existing PKB material (specifications, topic notes, prior art, active sibling tasks, parsimony, and lifecycle coherence), returning `PASS`, `REVISE`, or `FAIL`.
3. **Compliance evaluation (`rbg`)**: An independent compliance evaluation testing mechanisms, scope of authority (_ultra vires_), and published surface against universal axioms, project rules, and the enforcement pyramid without running test suites or probes, returning `PASS`, `REVISE`, or `FAIL`.
4. **Quality and requirement satisfaction evaluation (`marsha`)**: An independent evaluation testing whether the deliverable achieves ambitious quality across actual rendered multimodal outputs and runtime execution against its governing genre standard and available specifications, requirements, and acceptance criteria (plus primary-material auditing on high-risk requests), returning `PASS`, `REVISE`, or `FAIL` -- and returning `FAIL` immediately if no governing standard, specifications, requirements, or criteria are available.
5. **Dialectical deliberation, epistemic check, reconciliation, and write-back (`james`)**: Critical evaluation of reviewer reports (verifying that doc citations are not mistaken for proofs of live state and that cited PRs/code are authoritative), cross-examination across reviewers when warranted by stakes and tensions, synthesis of findings into a unified findings table and final verdict (`PASS`, `REVISE`, or `FAIL`), and persistent write-back to the artifact's tracking record.

## Output contract

A unified review report containing:

- Supervisor calibration summary (proportionality, model selection, rounds, primary-material audit scope, altitude, and governing genre standard).
- The itemized findings table mapping issues to reviewer components, feedback, dispositions, and any unresolved open questions.
- The reconciled overall verdict (`PASS`, `REVISE`, or `FAIL`).
- Persistent write-back to the artifact's task record or review surface.

## When to include

Any milestone, specification, design proposal, plan, document, or pull request requiring multi-perspective verification prior to merge, execution, or release.
