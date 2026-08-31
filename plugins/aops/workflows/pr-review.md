---
title: Pull Request Review
type: template
category: process
description: Triage open pull requests, dispatch reviewer lenses, and synthesize a structured verdict table. Select when conducting systematic PR reviews across a repository. Not for creating PRs (use `wf-handover`) or merging without review (use `worktree-merge`).
tags: [git, pr, review, pull-request, operations, process]
---

# Process: Pull Request Review

Multi-lens review procedure to evaluate open pull requests and synthesize actionable verdicts.

## 1. PR Inventory and Scope

- Fetch target open pull request (`<pr-identifier>`) and associated issue/task context.
- Verify CI status, mergeability, and inspect the changed file diff.

## 2. Review Lens Dispatch

- Evaluate the PR diff against core review dimensions:
  - **Correctness & Tests**: Are behavioral changes covered by comprehensive tests?
  - **Architecture & Rules**: Does the change adhere to codebase axioms and style standards?
  - **Security & Performance**: Are there security risks, data mutations, or performance regressions?

## 3. Verdict Synthesis

- Synthesize findings into a structured review verdict:
  - `APPROVE`: All criteria met, tests pass, no architectural regressions.
  - `REQUEST_CHANGES`: Specific blocking defects identified with required remediation diffs.
  - `COMMENT`: Non-blocking observations or suggestions.

## 4. Feedback Delivery and Routing

- Post review comments with pinpoint file and line citations.
- Route approved PRs to `worktree-merge` or notify author for requested changes.
