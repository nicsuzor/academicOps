---
alias:
  - wf-review
  - wf-multi-agent-review
description: Universal composite review workflow -- Supervisor (james) calibrates proportionality and altitude upfront, coordinates review across strategic direction/congruence (pauli), compliance (rbg), and quality/requirement satisfaction (marsha), and defines the shared review briefing.
id: wf-review
tags:
  - wf-template
  - review
  - composite
  - dialectic
  - briefing
  - gate
title: Multi-Agent Review Workflow
type: template
---

## What this step does

Universal review workflow: coordinated by **`james` as Supervisor**, who explicitly evaluates **proportionality** and **altitude** at intake before dispatching three non-overlapping review components -- **Strategic Direction & Congruence (`pauli`)**, **Compliance (`rbg`)**, and **Quality & Requirements Satisfaction (`marsha`)** -- and defines the one shared review briefing drawn on by all review dispatches.

## Shared Review Briefing

All three review components (`pauli`, `rbg`, `marsha`), whether dispatched as subagents in `/strategic-review`, minted as review tasks in `/reify`, or composed in workflow templates, receive their briefing drawn from this shared structure. The brief presents the originating request and available specifications/requirements/criteria before the artifact or diff under review, so reviewers evaluate intent, requirements, and proportion before inspecting implementation details.

### Structure of the Brief

1. **Originating Request & Available Specifications / Criteria (Read First)**:
   The originating request is quoted verbatim with its source identifier, alongside the governing specifications, requirements, or acceptance criteria (or explicit notice that none are available), before any link to the pull request, branch name, or diff:
   ```markdown
   ## Originating Request & Requirements

   > [The verbatim text of the user request, commission, or parent task ask authorizing this work]

   - **Source**: `<source-id-or-task-id>`
   - **Specifications / Acceptance Criteria**: `<explicit criteria or spec pointers, or "NONE AVAILABLE">`
   ```

2. **Supervisor Calibration (`james`)**:
   - **Proportionality tier**: Single-pass sanity check with lighter models (`flash` / `flash_lite`) for low-stakes or routine work, vs multi-round dialectical deliberation with higher-capability models (`pro`) for high-stakes, complex, or critical work.
   - **Target altitude**: The abstraction level appropriate to the artifact (preventing drift into micro-implementation or untestable generalities).

3. **Target Artifact**:
   The candidate change or deliverable under review (read only after the originating request and requirements):
   - **Repository**: `<owner/repo>`
   - **Pull Request**: `<PR URL and number>`
   - **Branch / Head Commit**: `<branch-name> / <commit-sha>`
   - **Diff / Content**: `<diff or artifact reference>`

4. **Review Role & Instructions**:
   The review criteria and obligations specific to the assigned component:
   - **Strategic Direction & Congruence (`pauli`)**: Evaluates strategic direction and congruence with existing material in the PKB (graph topology, prior art, existing specifications, topic notes, parent objectives, parsimony, and lifecycle coherence) from an inline graph-only brief (`FIT` or `MISFIT`).
   - **Compliance (`rbg`)**: Evaluates compliance with universal axioms, project-local rules, data boundaries, and the enforcement pyramid (`APPROVE`, `SUGGEST`, `REVISE`, or `REJECT`). From the quoted request alone, state the smallest proportionate mechanism before reading the diff.
   - **Quality & Requirements Satisfaction (`marsha`)**: Evaluates quality, runtime execution, and satisfaction of stated requirements against whatever specifications, requirements, or acceptance criteria are available (`PASS`, `REVISE`, or `FAIL`). **If no specifications, requirements, or acceptance criteria are available, treats that absence itself as a critical failure signal (`FAIL` / `REJECT`).**

## Input contract

The invoking workflow provides:

1. **Originating request** -- the commissioning ask with its source id, quoted verbatim.
2. **Target artifact** -- the file, diff, PR reference, or specification under review.
3. **Available specifications, requirements & acceptance criteria** -- explicit requirements and constraints governing the artifact (or explicit notice of their absence).
4. **Strategic context** -- parent task, target objectives, and related PKB notes or specifications.

## Composite Stages

A composite review workflow specifies its stages by contract expectations in order:

1. **Supervisor proportionality and altitude calibration (`james`)**: Upfront assessment of task importance, blast radius, and reversibility to determine review depth, number of deliberation rounds, subagent model tier (`pro` vs `flash`/`flash_lite`), and target discussion altitude.
2. **Strategic direction and congruence evaluation (`pauli`)**: An independent evaluation situating the artifact against parent strategic direction and testing congruence with existing PKB material (specifications, topic notes, prior art, parsimony, and lifecycle coherence), returning an explicit `FIT` or `MISFIT` verdict.
3. **Compliance evaluation (`rbg`)**: An independent compliance evaluation testing mechanisms and published surface against universal axioms, project rules, and the enforcement pyramid without running test suites or probes, returning `APPROVE`, `SUGGEST`, `REVISE`, or `REJECT`.
4. **Quality and requirement satisfaction evaluation (`marsha`)**: An independent evaluation testing substantive quality, runtime execution, and satisfaction of stated requirements against available specifications, requirements, and acceptance criteria, returning `PASS`, `REVISE`, or `FAIL` -- and returning `FAIL` immediately if no specifications, requirements, or criteria are available.
5. **Dialectical deliberation, reconciliation, and write-back (`james`)**: Cross-examination across reviewers when warranted by stakes and tensions, synthesis of findings into a unified findings table and final verdict (`APPROVE`, `MINOR CHANGES`, `REVISE`, or `REJECT`), and persistent write-back to the artifact's tracking record. A review that returns `REJECT` or `REVISE` (`MISFIT` for strategic congruence) schedules the next step in the same handback: the reviewer files a subtask of the primary task (`parent: <primary-task-id>`, status `queued`) whose body names each required change from the verdict, and records that subtask's id on the review task.

### Handback on a failing verdict

A review that returns `REJECT` or `REVISE` (`MISFIT` for strategic congruence) schedules the next step in the same handback: the reviewer files a subtask of the primary task (`parent: <primary-task-id>`, status `queued`) whose body names each required change from the verdict, and records that subtask's id on the review task. `/reify` carries this obligation into each review task it mints.

## Output contract

A unified review report containing:

- Supervisor calibration summary (proportionality tier, model selection, rounds, and altitude).
- The itemized findings table mapping issues to reviewer components, feedback, and severities.
- The reconciled overall verdict (`APPROVE`, `MINOR CHANGES`, `REVISE`, or `REJECT`).
- Persistent write-back to the artifact's task record or review surface.
- On a failing verdict (`REJECT`, `REVISE`, or `MISFIT`), the queued subtask scheduled under the primary task (`parent: <primary-task-id>`, status `queued`) recorded on the review task.

## When to include

Any milestone, specification, design proposal, plan, document, or pull request requiring multi-perspective verification prior to merge, execution, or release.
