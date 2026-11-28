---
alias:
  - wf-dialectical-review
  - wf-dialectical-design
  - wf-review-dialectic
  - wf-design-dialectic
  - wf-review
  - wf-multi-agent-review
default: true
description: "Universal default dialectical review workflow: coordinator calibrates proportionality, altitude, and contextual standards upfront, dispatches warranted strategic coherence, compliance, and quality/verification branches under separation of powers, and reconciles valid in-jurisdiction findings without softening a substantive expert FAIL."
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

Universal review workflow grounded in separation of powers: a coordinator calibrates **proportionality**, **altitude**, **warranted branches**, and the **applicable standard** upfront, issues a neutral shared brief, dispatches warranted review branches concurrently, deliberates when needed, and reconciles valid in-jurisdiction findings into `PASS`, `REVISE`, or `FAIL`.

## Shared Review Briefing

Every dispatched branch receives the same neutrally framed briefing in unfenced prose Argdown blocks per `premise-check`, quoting the commissioning mandate, applicable standard, and explicit requirements cleanly before the target artifact, PR, or diff without priming toward a verdict:

1. **Originating Request & Applicable Standard (Read First, Neutral Framing)**: Verbatim mandate with source ID, any principal-set standard or explicit requirements (when unset, reviewers evaluate under a standard reasonable and appropriate in all the circumstances for the artifact's purpose, audience, and stakes -- never applying task checklists to non-task artifacts, and never substituting rigid genre lookup tables or arbitrary numeric thresholds for qualitative judgment), placed before any PR or diff pointer.
2. **Coordinator Calibration**: Proportionality tier (single-pass check with `mid-tier` capability for low-stakes defeasible work vs. multi-round dialectical deliberation with `flagship` capability and primary-source verification on empirical, code, or citation claims for high-stakes work), warranted specialist branches (omitting rendered-quality review when no audience-facing artifact was built), and target abstraction altitude.
3. **Target Artifact**: Repository, PR/artifact pointer, branch and head commit, and diff or content reference.
4. **Branch Jurisdictions, Deference & Fix Discipline**:
   - **Strategic coherence reviewer**: Evaluates core premise, problem class, parsimony, lifecycle coherence, and congruence with the **seamless web** of knowledge-base records, specifications, topic notes, parent objectives, and active sibling work from an inline graph brief.
   - **Compliance reviewer**: Adjudicates universal axioms, user/project rules, delegated authority scope (_ultra vires_), _abdication_, data boundaries, and the least-invasive enforcement hierarchy independently (reading zero prior reviews first); states the smallest proportionate non-mechanical baseline from the quoted mandate before reading the diff.
   - **Quality & verification reviewer** _(dispatched when an audience-facing artifact or testable deliverable was built)_: Evaluates explicit requirements and whether the work is genuinely excellent for its audience and purpose in all the circumstances across live runs and actual rendered outputs (never simulated renders or raw markup alone), plus primary sources on empirical, code, or citation claims. Evaluates qualitative standards directly with reasons (never demanding fake numeric proxies), defers to reasonable authorial discretion (`REVISE` requires material defects, never mere phrasing preference), and reserves `FAIL` for failing intended purpose, applying a standard inappropriate in the circumstances, or severe visual/cognitive clutter.
   - **Applied fixes & `HEAD` parity**: Apply uncontroversial `fix(review):` edits only when serialized or explicitly authorized on a writable branch, itemizing applied fixes; parallel passes itemize suggested fixes instead. Commit, push, and verify fixes at `HEAD` before `PASS` (no `REVISE` solely for fixed items), and itemize contested material defects as required changes.

## Stages

1. **Calibrate**: Coordinator sets proportionality, deliberation round budget, capability tier, primary-source audit scope, target altitude, contextual standard (principal-set or reasonable and appropriate in all the circumstances), and warranted branches (skipping rendered-quality review on non-build, lookup, or diagnostic replies).
2. **Evaluate independently**: Dispatch warranted specialist branches concurrently against the neutral shared brief and await all child runs before reporting once at the stopping point. Halt verbatim on any guard, tool, or harness refusal (never bypassing via `SendMessage` or silently falling back when a required branch fails).
3. **Deliberate** _(scaled by proportionality)_: Skip on routine checks with no tensions. Otherwise:
   - Run `premise-check` judicial review on handbacks on the message alone (zero outside substantive checks; proportionate depth, material remands only).
   - Reject reviewer findings that act outside jurisdiction, police layout or phrasing preferences within reasonable discretion, demand fake numeric proxies for qualitative judgment, or impose a standard of proof inappropriate in the circumstances.
   - Route opposing in-jurisdiction critiques across reviewers, requiring cited PRs/code to be shown current and backed by spec/decision authority and doc claims to carry `status: done` evidence or quoted live state (else mark **open questions**).
4. **Reconcile & release**:
   - Synthesize unified findings, itemized self-fixes applied, open questions, and reconciled verdict (`PASS`, `REVISE`, or `FAIL`), scrubbing private PKB IDs/PII on public repositories per `data-boundaries` when posting PR headers matched to the reviewed head commit SHA.
   - Preserve per-finding risk-vs-cost proportionality and separation of powers: **a valid substantive expert `FAIL` within jurisdiction stands unsoftened** -- the coordinator strikes out-of-jurisdiction, layout-policing, fake-proxy, or wrong-standard findings with recorded reasons, and never downgrades a valid substantive in-jurisdiction `FAIL`.
   - Verify all `fix(review):` edits are committed, pushed, and matched to `HEAD` before issuing `PASS`.
   - Release headless review tasks strictly per outcome (`done` on `PASS`; `failed` or `partial` with findings and defect reasons on `REVISE` or `FAIL`), never prompting interactively or minting downstream tasks.

## Input contract

- Commissioning ask quoted verbatim with source ID and neutral framing.
- Target artifact and any principal-set standard or explicit specifications/acceptance criteria (when unset, reviewers apply a standard reasonable and appropriate in all the circumstances).
- Strategic context (parent objective, related notes, and specifications).

## Output contract

- **Format boundary**: All internal agent-to-agent review messages (briefings, cross-examinations, and handbacks) use unfenced prose Argdown blocks only per `premise-check` (upfront ask and verdict, self-contained load-bearing premises; readable scaffolding inside blocks passes unless support relations are ambiguous); Markdown headings (`### Reviewer Self-Fixes Applied`, `### Suggested Fixes`, `### Required Changes`) and tables apply strictly to published PR/issue or user-facing summaries.
- **Required content**: Every unified review covers calibration, itemized self-fixes (verified at `HEAD`), suggested fixes, required changes, reconciled findings with open questions, and one overall verdict (`PASS`, `REVISE`, or `FAIL`), persisted to the task or review record.

## When to include

Any milestone, specification, design proposal, plan, document, or pull request requiring multi-perspective verification prior to merge, execution, or release.
