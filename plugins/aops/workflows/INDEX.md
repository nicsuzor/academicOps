---
id: workflows-index
title: Workflow Template Library
type: index
description: Canonical index and routing tree for universal workflow templates shipped with the framework.
permalink: workflows-index
---

# Workflow Template Library

Modular markdown workflow components describing how classes of work proceed. Components are read and composed **in context, by comprehension** per [specs/workflows/workflow.md](../../../specs/workflows/workflow.md).

## Routing

Match incoming requests to the appropriate workflow component:

```
Request
  |
  +-- Framework modification intent (checked FIRST)? ---------> [[framework-gate]]
  |
  +-- Simple factual question only? ---------------------------> [[simple-question]]
  +-- Continuation of active session work? --------------------> [[interactive-followup]]
  +-- Batch processing?
  |       +-- Single session parallel/sequential items --------> [[batch]]
  |       +-- Multi-session stateful batch lifecycle ----------> [[burst]]
  |       +-- External cloud batch API (LLM/inference) --------> [[external-batch-submission]]
  +-- Email and communications?
  |       +-- Inbox triage & classification -------------------> [[email-triage]]
  |       +-- Task & context extraction -----------------------> [[email-capture]]
  |       +-- Draft reply in user voice -----------------------> [[email-reply]]
  +-- Academic and research?
  |       +-- Paper from idea to submission -------------------> [[academic-paper]]
  |       +-- Extract aims, method, theory, contribution ------> [[structural-map-extraction]]
  |       +-- Reference letter drafting & review --------------> [[reference-letter]]
  |       +-- Finalize report after stakeholder feedback ------> [[finalize-report]]
  |       +-- Point-by-point reviewer rebuttal ----------------> [[review-response]]
  +-- Development and debugging?
  |       +-- Known root cause or new feature -----------------> [[feature-dev]]
  |       +-- Unknown cause diagnosis -------------------------> [[investigation]]
  |       +-- Live runtime or container reproduction ----------> [[live-fix-loop]]
  |       +-- Prompt / instruction defect repair --------------> [[prompt-repair]]
  +-- Specification and architecture? -------------------------> [[develop-specification]]
  +-- Blocked decision needing options & trade-offs? ----------> [[decision-briefing]]
  +-- Pull request and git operations?
  |       +-- Multi-lens PR review & verdict synthesis --------> [[pr-review]]
  |       +-- Safe worktree branch merge ----------------------> [[worktree-merge]]
  +-- Governance and hygiene?
  |       +-- Specifications and repository audit -------------> [[audit]]
  |       +-- Closed task knowledge harvest -------------------> [[closed-task-harvest]]
```

## Process Templates

| Template | What it covers | Composes / Pairs with |
| --- | --- | --- |
| [[feature-dev]] | Test-first feature development and known-cause bugfixes | [[tdd]], [[wf-verification]], [[wf-handover]] |
| [[investigation]] | Hypothesis-probe-conclude cycle for unknown causes | [[feature-dev]], [[wf-verification]] |
| [[live-fix-loop]] | Defect diagnosis and verification in deployed runtimes | [[investigation]], [[wf-verification]], [[wf-handover]] |
| [[develop-specification]] | Authoring or revising technical and governance specs | [[wf-qa]], [[wf-signoff-loop]] |
| [[email-triage]] | Sorting incoming messages into actionable buckets | [[email-capture]], [[email-reply]] |
| [[email-capture]] | Extracting structured tasks and context from messages | [[task-tracking]] |
| [[email-reply]] | Drafting context-aware replies for user approval | [[wf-signoff-brief]] |
| [[academic-paper]] | Research paper authoring and submission pipeline | [[structural-map-extraction]], [[wf-fact-check]], [[wf-signoff-loop]] |
| [[reference-letter]] | Drafting and verifying letters of recommendation | [[wf-signoff-loop]] |
| [[finalize-report]] | Revising reports against reviewer feedback | [[wf-signoff-brief]] |
| [[review-response]] | Point-by-point response to reviewer critiques | [[wf-verification]] |
| [[batch]] | Single-session parallel/sequential item processing | [[task-tracking]] |
| [[burst]] | Multi-session stateful batch lifecycle | [[task-tracking]], [[wf-handover]] |
| [[external-batch-submission]] | Submitting and retrieving cloud batch API jobs | [[task-tracking]], [[wf-verification]] |
| [[pr-review]] | Reviewing PR diffs across multiple quality lenses | [[worktree-merge]] |
| [[worktree-merge]] | Merging verified branches and cleaning up worktrees | [[wf-handover]] |
| [[simple-question]] | Direct information lookup and clean exit | — |
| [[interactive-followup]] | Incremental edits within an active session | [[wf-verification]] |
| [[framework-gate]] | Pre-execution governance for framework changes | [[develop-specification]], [[audit]], [[wf-signoff-loop]] |
| [[decision-briefing]] | Structuring options and trade-offs for blocked decisions | [[wf-signoff-brief]] |
| [[audit]] | Repository integrity and rule compliance audit | [[wf-qa]] |
| [[prompt-repair]] | Evidence-based repair of prompts and agent instructions | [[wf-blind-proof]] |
| [[structural-map-extraction]] | Extracting 4-pillar research maps from papers | [[academic-paper]] |
| [[closed-task-harvest]] | Harvesting durable knowledge from closed tasks | [[wf-memory-capture]] |

## Gates and Obligations

| Gate | Type | What it enforces |
| --- | --- | --- |
| [[wf-verification]] | Gate | Baseline verification floor: lock criteria before, verify evidence after |
| [[wf-qa]] | Gate | Structured quality grading with review lenses and depth modes |
| [[wf-refine-loop]] | Gate | Drafter-reviewer convergence loop on review failure |
| [[wf-blind-proof]] | Gate | Three-role blind capability demonstration (Author, Executor, Verifier) |
| [[wf-blind-dupe]] | Gate | Blind comparative evaluation of independent agent runs |
| [[wf-visual-qa-loop]] | Gate | Automated visual UI screenshot judging and revision with failsafes |
| [[wf-capstone-verify]] | Gate | Final completeness and regression audit before milestone closure |
| [[wf-decompose]] | Gate | Expanding high-level objectives into dependency-wired sub-goals |
| [[wf-fact-check]] | Gate | Verifying factual assertions and citations against primary sources |
| [[wf-hydrate]] | Gate | Context assembly, scope locking, and prerequisite check |
| [[wf-memory-capture]] | Gate | Capturing durable findings into permanent knowledge notes |
| [[wf-signoff-brief]] | Gate | One-page human-facing summary digest for decision sign-off |
| [[wf-signoff-loop]] | Gate | Principal review-until-approval loop before closing critical work |

## Composable Fragments

| Fragment | Type | Role |
| --- | --- | --- |
| [[task-tracking]] | Fragment | Duplicate checking, parent resolution, claiming, and logging |
| [[tdd]] | Fragment | Red-green-refactor cycle for testable code changes |
| [[dispatch-cycle]] | Fragment | Formulating briefs, dispatching isolated subagents, auditing evidence |
