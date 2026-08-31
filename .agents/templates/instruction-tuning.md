---
title: Interactive Agent Instruction Tuning
type: template
category: process
description: Step-by-step interactive tuning and calibration of agent instruction files and skills. Select when refining prompts with live human-in-the-loop validation. Not for automated prompt repair (use `prompt-repair`).
tags: [instruction-tuning, prompt-engineering, calibration, interactive, process]
---

# Process: Interactive Agent Instruction Tuning

Iterative calibration workflow for agent instructions and system prompts with live evaluation.

## 1. Target and Baseline Specification

- Identify the target instruction file or skill to calibrate (`<target-instruction>`).
- Establish test scenarios and expected behavioral outcomes (`<test-scenarios>`).
- Record baseline performance and specific failure modes on current instructions.

## 2. Interactive Step-by-Step Execution

- Drive candidate agent through test scenarios one step at a time.
- Inspect agent reasoning, tool call selection, and output formatting at each step.
- Note exact divergence points where agent deviates from desired behavior.

## 3. Real-Time Instruction Revision

- Adjust instruction text following the craft standard (concise imperatives, clear outcomes, no clutter).
- Provide functional rationale for constraints to help the agent generalize.

## 4. Regression Check and Calibration

- Rerun previously passed test scenarios to ensure revisions did not cause regressions.
- Verify agent performance across boundary cases.

## 5. Delivery and Checkpoint

- Save calibrated instruction file.
- Document key insights and boundary conditions in permanent knowledge notes (`remember`).
