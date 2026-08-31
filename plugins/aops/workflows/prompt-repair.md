---
title: Prompt Repair
type: template
category: process
description: Causal diagnosis, evaluation, and repair for reusable prompts, skills, or agent instructions that produce unsatisfactory output. Select when revising an instruction set based on failure evidence. Not for one-off editing of a single document.
tags: [prompt-engineering, instruction-tuning, repair, evaluation, craft, process]
---

# Process: Prompt Repair

Evidence-based diagnosis and revision loop for agent prompts and instruction files.

## 1. Failure Evidence Capture

- Collect verbatim examples of failed output alongside the prompt and task input (`<failed-examples>`).
- Record reader feedback or supervisor critiques pinpointing exact failure modes.

## 2. Causal Diagnosis

- Trace each failure mode to specific prompt root causes:
  - Ambiguous terminology or underspecified constraints.
  - Conflicting rules or bloated prose diluting attention.
  - Keystroke-prescriptive steps causing rigid execution failure.

## 3. Instruction Revision under Craft Standard

- Apply `/aops:craft` principles to revise the prompt file:
  - Formulate positive imperatives with functional reasons.
  - State outcomes with named blanks instead of keystroke scripts.
  - Cut non-operational prose, history, and anecdotes.

## 4. Blind Validation

- Dispatch the revised prompt to a clean agent instance on test inputs (`<test-inputs>`).
- Evaluate output against acceptance criteria without coaching the agent.

## 5. Deployment and Verification

- Update prompt file in place.
- Run regression checks to ensure no unintended behavioral regressions.
