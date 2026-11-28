---
alias:
  - wf-qa
  - wf-quality-review
description: "Review: quality lens -- check the real artifact, as its audience meets it, against its requirements and purpose, returning PASS, REVISE or FAIL."
id: wf-qa
tags:
  - wf-template
  - review
  - qa
title: Quality review
type: template
---

## What this step does

Checks that the work actually does what was asked, on the real thing.

## The real artifact

Judge what the real pipeline produced from real inputs, obtained where its audience gets it: the deployed page at its live address, the built file opened, the text as sent. A stand-in (a local server, sample data, a mock, a render made for the review) proves only itself. Which artifact is real comes from the task. If it cannot be reached or built, stop and report the response verbatim.

## Procedure

1. Take the requirements from the ask and acceptance criteria; where none are set, judge against a standard reasonable for the work's purpose and audience.
2. Check each requirement on the real artifact: run it, open it, look at what it renders. Run the repository's existing tests where there are any.
3. Judge whether it serves its purpose, not only whether it looks right.

Where defects are clearly fixable without ambiguity, fix them in place if write permissions and instructions permit; otherwise state the exact fix alongside remaining required changes.

## Output contract

Each requirement `MET` or `UNMET` with its evidence, and one verdict: `PASS` (all met), `REVISE` (works, with specific gaps), `FAIL` (does not work, or was judged on a stand-in).

## When to include

Reviewing a built or testable deliverable.
