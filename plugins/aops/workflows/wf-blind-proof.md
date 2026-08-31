---
title: Blind Capability Demonstration Protocol
type: template
category: gate
description: Three-role demonstration protocol (Author, Executor, Verifier) for proving a capability works without execution bias. Select when proving an agent or system capability where knowledge of pass conditions would bias the test. Not for standard self-contained tests (use `tdd`).
tags: [blind-test, capability-proof, three-role, evaluation, gate]
---

# Gate: Blind Capability Demonstration Protocol

Rigorous demonstration protocol enforcing strict identity separation between author, executor, and verifier.

## 1. Specification Authoring (Author Role)

- Author drafts task instructions and independent acceptance tests for `<capability>`.
- Tests and grading criteria are locked and hidden from the executor.

## 2. Blind Execution (Executor Role)

- Executor receives only the task prompt and input data in an isolated context.
- Executor performs the task without seeing test implementation or grading rubrics.
- Capture full execution transcript and output artifact.

## 3. Independent Verification (Verifier Role)

- Verifier executes the hidden acceptance tests against the executor's output artifact.
- Inspect logs, exit codes, and verbatim outputs.
- Emit binary pass/fail verdict with machine evidence.

## Exit Condition

Verified pass on hidden test suite executed by independent verifier.
