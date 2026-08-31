---
title: Subagent Dispatch Cycle
type: template
category: fragment
description: Formulate a self-contained brief, dispatch a subagent in an isolated context, monitor execution, and audit returned evidence. Composed into multi-agent workflows. Not a standalone workflow.
tags: [subagent, dispatch, multi-agent, delegation, fragment]
---

# Fragment: Subagent Dispatch Cycle

Procedure for delegating bounded work units to isolated subagents.

## 1. Brief Formulation

- Author a self-contained task brief for `<subagent-role>`.
- Include explicit task objective, input files, constraints, and machine-checkable acceptance criteria.
- Specify model (`<model>`, default sonnet).

## 2. Isolated Dispatch

- Dispatch subagent with formulated brief in isolated workspace/branch context.
- Ensure subagent has required tool permissions and reference paths.

## 3. Execution Monitoring

- Await subagent completion notification without busy-loop polling.
- Handle timeout, tool denial, or subagent errors gracefully.

## 4. Handback and Evidence Audit

- Inspect returned subagent output and verbatim execution logs.
- Audit output against locked acceptance criteria from step 1.
- Reject output if evidence is missing, fabricated, or unverified.
