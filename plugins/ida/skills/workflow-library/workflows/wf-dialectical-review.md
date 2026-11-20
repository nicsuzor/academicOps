---
alias:
  - wf-dialectical-review
  - wf-dialectical-design
  - wf-review-dialectic
  - wf-design-dialectic
  - wf-review
  - wf-multi-agent-review
default: true
description: "Universal default dialectical review workflow: coordinator calibrates proportionality and altitude upfront, dispatches independent strategic coherence, compliance, and empirical verification perspectives, and reconciles findings into a single PASS, REVISE, or FAIL verdict."
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

Universal default review workflow. A coordinator calibrates **proportionality**, **altitude**, and the **governing genre standard** upfront, dispatches three non-overlapping review perspectives (**strategic coherence**, **compliance**, and **empirical requirement verification**) using one shared briefing, runs dialectical cross-examination when warranted, and reconciles findings into `PASS`, `REVISE`, or `FAIL`.

## Shared Review Briefing

Every review perspective receives the same briefing structure, placing the commissioning ask and criteria before the artifact or diff so reviewers judge intent and proportion before inspecting implementation details:

1. **Originating Request & Governing Standard (Read First)**: Verbatim commissioning ask with source ID, artifact genre and its governing standard (e.g., specification standard, instruction craft standard, genre criteria, or task acceptance criteria -- never applying task-handback checklists to non-task artifacts), and explicit requirements or criteria (or `"NONE AVAILABLE"`).
2. **Coordinator Calibration**: Proportionality tier (single-pass sanity check with lightweight capability for low-stakes routine work vs. multi-round dialectical deliberation with high-reasoning capability and primary-material audit for high-stakes or high-risk work) and target abstraction altitude.
3. **Target Artifact**: Repository, PR/artifact pointer, branch and head commit, and diff or content reference.
4. **Perspective Mandates & Fix Discipline**:
   - **Strategic coherence reviewer**: Evaluates core premise, problem class, parsimony, lifecycle coherence, and congruence with existing knowledge-base records, specifications, topic notes, parent objectives, and active sibling work from an inline graph brief.
   - **Compliance reviewer**: Evaluates universal axioms, user/project rules, delegated authority scope (_ultra vires_), data boundaries, and the least-invasive intervention hierarchy; states the smallest proportionate non-mechanical baseline from the quoted ask before reading the diff.
   - **Requirement & empirical verification reviewer**: Verifies stated requirements, acceptance criteria, and governing genre/project document standards across live test execution and actual rendered multimodal outputs (never simulated renders or code alone), plus primary-material audit when calibrated high-risk. Absence of any governing standard, specification, or criteria is an immediate `FAIL`.
   - **Fix discipline**: Reviewers apply uncontroversial deterministic fixes (`fix(review): <description>`) ONLY when serialized or explicitly authorized on a writable branch; parallel or read-only review passes report suggested fixes under findings for a dedicated fix pass to prevent concurrent git conflicts. An artifact whose only defects were cleanly self-fixed must not receive `REVISE` solely for those issues; non-deterministic or contested defects require `REVISE` or `FAIL`.

## Stages

1. **Calibrate**: Coordinator sets proportionality, deliberation round budget, capability level, primary-material audit scope, target altitude, and governing standard.
2. **Evaluate independently**: Dispatch the required specialist perspectives concurrently against the shared brief (or run a single-pass check when calibrated for routine low-stakes work). Halt immediately with an explicit error -- never silently fall back to single-perspective review -- if required perspectives are unavailable.
3. **Deliberate** _(scaled by proportionality)_: Skip for routine checks with no critical tensions. For high-stakes or conflicting findings, check warrants, route opposing critiques across reviewers, verify authority of cited PRs or code against current merged/specified state, and require verified completion (`status: done` with evidence) or live state rather than bare doc claims (recording unresolved items as **open questions**).
4. **Reconcile & release**: Synthesize unified findings, itemized self-fixes applied, open questions, and final verdict (`PASS`, `REVISE`, or `FAIL`). A `FAIL` from any specialist perspective forces a combined `FAIL` and is never softened. Release headless review tasks strictly per outcome (`done` on `PASS`; `failed` or `partial` with findings and defect tags on `REVISE` or `FAIL`), never prompting interactively or minting downstream tasks.

## Input contract

- Commissioning ask quoted verbatim with source ID.
- Target artifact, governing genre standard, and explicit specifications/acceptance criteria (or notice of their absence).
- Strategic context (parent objective, related notes, and specifications).

## Output contract

- Unified review report containing calibration summary, itemized `### Reviewer Self-Fixes Applied` (with commit references, if any), itemized findings table with open questions, and exactly one overall verdict (`PASS`, `REVISE`, or `FAIL`), persisted to the task or review record.

## When to include

Any milestone, specification, design proposal, plan, document, or pull request requiring multi-perspective verification prior to merge, execution, or release.
