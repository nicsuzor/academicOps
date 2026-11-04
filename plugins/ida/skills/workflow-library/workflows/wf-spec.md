---
alias:
  - wf-spec
description: Author a comprehensive technical specification covering architecture, interfaces, acceptance criteria, and, for code that executes, test design before implementation.
id: wf-spec
tags:
  - wf-template
  - spec
title: wf-spec
type: template
---

## What this step does

Authors a complete, unambiguous technical specification grounded in the evidence available to it. Establishes system architecture, data models, public interfaces, observable acceptance criteria, and, for code that executes, integration test plans before any implementation code is written.

## One PR, opened by the build

- Stage 1 records its design, any drafted spec change, and its independent agent review verdicts in a PKB note the Stage 2 task points to. Stage 1 commits no plan or design file and opens no PR.
- Stage 2 opens the PR into the base branch as a draft, carrying the build and any spec change. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review (`gh pr ready`) only after the proportionate review on the build is posted to the PR thread by independent agents. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Procedure

1. **Problem statement and target** -- define the problem, caller/system context, and required capabilities.
2. **Architecture and data flow** -- describe the components and what each owns, and external integration points.
3. **Interface contracts** -- define data types, function signatures, schemas, or protocols with precision.
4. **Acceptance criteria** -- formulate concrete, observable, and falsifiable acceptance criteria for completion.
5. **Test and verification strategy** -- for code that executes, specify test cases (unit, integration, regression) validating each criterion; for any other criterion, how it is verified.
6. **Rule-compliance review** -- obtain an independent agent review of the draft specification against governing axioms (proportionality, single source of truth, closure) and specification standards, and remediate any `REVISE` findings before delivery.
7. **Submit and PR lifecycle** -- for a Stage 1 design or spec task preceding a build, record the drafted spec change and the independent agent review verdicts in a PKB note the Stage 2 task points to, open no PR, and release the task as `done` once independent agent review passes (or release as `partial` where an explicit user decision on competing design alternatives is required), never releasing as `review` and never putting a spec to the user for approval on its own. The Stage 2 build (or a bounded single-task change updating spec and code together) opens the single PR into the base branch as a draft carrying the build and any spec change, keeping the spec editable; once the feature is written, mark the draft PR ready for review (`gh pr ready`) only after proportionate review by independent agents is posted to the PR thread, without waiting for approval; spec and feature reach the user on that single PR and merge together after full review.

## Output contract

A complete specification artifact (full spec, not a summary) that someone other than its author can judge, containing:

- Problem statement and architectural design.
- Concrete interface definitions and signatures.
- Itemized acceptance criteria, each mapped to its test where code executes, or to its verification otherwise.
- Independent agent rule-compliance review verdict (`PASS` or resolved `REVISE`).
- For a Stage 1 design or spec task: the drafted spec change and the independent agent review verdicts recorded in a PKB note the Stage 2 task points to, with no PR opened.
- For Stage 2 or bounded single-task builds: the complete spec committed on the feature branch together with implementation code on a single PR, with independent agent review verdicts posted to the PR thread.

## When to include

Any non-trivial feature, architectural overhaul, or integration where implementation without an agreed specification invites scope creep or architectural divergence.
