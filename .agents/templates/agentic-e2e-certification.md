---
title: Agentic E2E Certification
type: template
category: process
description: Multi-turn end-to-end certification of autonomous subagents on realistic multi-step benchmarks. Select when certifying subagent models and prompts before deployment.
tags: [certification, e2e, agentic, benchmarks, evaluation, process]
---

# Process: Agentic E2E Certification

End-to-end benchmark certification protocol for autonomous agent capabilities.

## 1. Benchmark Suite Selection

- Select representative task scenarios spanning coding, debugging, research, and planning (`<benchmark-suite>`).
- Lock evaluation criteria, input datasets, and ground-truth validation scripts.

## 2. Autonomous Multi-Turn Execution

- Dispatch candidate agent in isolated test container with no human intervention.
- Allow agent to execute multi-step tool calls, shell commands, and file edits.
- Record full execution trajectory, wall-clock time, and token consumption.

## 3. Objective Artifact Grading

- Execute automated grading scripts against output artifacts produced by the agent.
- Evaluate correctness, completeness, and adherence to negative constraints.

## 4. Trajectory and Efficiency Audit

- Analyze tool call efficiency, error recovery loops, and redundant operations.
- Identify prompt ambiguities or tool schema weaknesses.

## 5. Certification Verdict

- Emit benchmark scorecard: pass rate percentage, median steps to completion, cost per task.
- Grant certification badge or route failure modes to `prompt-repair`.
