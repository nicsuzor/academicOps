---
alias:
  - wf-dialectical-review
  - wf-dialectical-design
  - wf-review-dialectic
  - wf-design-dialectic
  - wf-review
  - wf-multi-agent-review
default: true
description: "Universal default dialectical review workflow: coordinator calibrates proportionality and altitude upfront, dispatches independent strategic coherence, compliance, and verification branches under separation of powers, and reconciles findings without softening an expert FAIL."
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

Universal default review workflow grounded in separation of powers: a coordinator calibrates **proportionality**, **altitude**, and the **governing genre standard** upfront, issues a neutral shared review briefing, dispatches independent specialist branches (strategic coherence, judicial compliance, and quality/empirical verification) concurrently, conducts dialectical cross-examination when warranted, and reconciles findings into `PASS`, `REVISE`, or `FAIL`.

## Shared Review Briefing

Every branch receives the same neutrally framed briefing, quoting the commissioning mandate, governing genre standard, and acceptance criteria cleanly before the target artifact, PR, or diff without priming toward a verdict:

1. **Originating Request & Governing Standard (Read First, Neutral Framing)**: Verbatim commissioning mandate with source ID, artifact genre and its governing standard (when present -- e.g., specification standard, instruction craft standard, genre criteria, or task acceptance criteria; never applying task-handback checklists to non-task artifacts), and explicit requirements or criteria (or `"NONE AVAILABLE"`), presented neutrally before any PR, branch, or diff pointer.
2. **Coordinator Calibration**: Proportionality tier (single-pass sanity check with `mid-tier` capability for low-stakes routine work vs. multi-round dialectical deliberation with `flagship` capability and primary-material audit for high-stakes or high-risk work) and target abstraction altitude.
3. **Target Artifact**: Repository, PR/artifact pointer, branch and head commit, and diff or content reference.
4. **Branch Jurisdictions & Fix Discipline**:
   - **Strategic coherence reviewer**: Evaluates core premise, problem class, parsimony, lifecycle coherence, and congruence with the **seamless web** of knowledge-base records, specifications, topic notes, parent objectives, and active sibling work from an inline graph brief.
   - **Compliance reviewer**: Adjudicates universal axioms, user/project rules, delegated authority scope (_ultra vires_), _abdication_, data boundaries, and the least-invasive enforcement hierarchy independently (reading zero prior reviews first); states the smallest proportionate non-mechanical baseline from the quoted mandate before reading the diff.
   - **Quality & verification reviewer**: Verifies stated requirements, acceptance criteria, and whether delivered work is amazingly good against governing genre and project document standards across live test execution and actual rendered multimodal outputs (never simulated renders or code alone), plus primary-material audit when calibrated high-risk. Absence of any governing standard, specification, or criteria is an immediate `FAIL`.
   - **Applied fixes & `HEAD` parity**: Apply uncontroversial deterministic fixes (`fix(review): <description>`) only when serialized or explicitly authorized on a writable branch; parallel or read-only passes report suggested fixes under `### Suggested Fixes` for single-writer application. Commit, push, and verify every `fix(review):` edit against `HEAD` before issuing `PASS` (never issuing `REVISE` solely for cleanly self-fixed items); non-deterministic defects go under `### Required Changes`.

## Stages

1. **Calibrate**: Coordinator sets proportionality, deliberation round budget, capability tier, primary-material audit scope, target altitude, and governing standard.
2. **Evaluate independently**: Dispatch specialist branches concurrently against the neutral shared brief (or run a single-pass check when calibrated for routine low-stakes work). Halt verbatim without silently falling back to single-perspective review if required branches are unavailable.
3. **Deliberate** _(scaled by proportionality)_: Skip for routine checks with no critical tensions. For high-stakes or conflicting findings, interrogate warrants, route opposing critiques across reviewers, verify cited PRs or code against current merged/specified state, and require verified completion (`status: done` with evidence) or live state rather than bare doc claims (recording unresolved items as **open questions**).
4. **Reconcile & release**:
   - Synthesize unified findings, itemized self-fixes applied, open questions, and reconciled verdict (`PASS`, `REVISE`, or `FAIL`), matching posted PR headers to the reviewed head commit SHA when permitted by `data-boundaries`.
   - Preserve per-finding risk-vs-cost proportionality while enforcing separation of powers: **an expert `FAIL` stands unsoftened** -- the coordinator holds no authority to downgrade or overrule another branch's `FAIL`.
   - Verify all `fix(review):` edits are committed, pushed, and matched to `HEAD` before issuing `PASS`.
   - Release headless review tasks strictly per outcome (`done` on `PASS`; `failed` or `partial` with findings and defect tags on `REVISE` or `FAIL`), never prompting interactively or minting downstream tasks.

## Input contract

- Commissioning ask quoted verbatim with source ID and neutral framing.
- Target artifact, governing genre standard, and explicit specifications/acceptance criteria (or notice of their absence).
- Strategic context (parent objective, related notes, and specifications).

## Output contract

- Unified review report containing calibration summary, itemized `### Reviewer Self-Fixes Applied` (with commit references verified at `HEAD`, if any), itemized findings table with open questions, and exactly one overall verdict (`PASS`, `REVISE`, or `FAIL`), persisted to the task or review record.

## When to include

Any milestone, specification, design proposal, plan, document, or pull request requiring multi-perspective verification prior to merge, execution, or release.
