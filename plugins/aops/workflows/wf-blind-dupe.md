---
title: Blind Comparison and Transcript Audit
type: template
category: gate
description: Compare multiple independent agent executions or model runs on the same task without evaluator bias. Select when benchmarking prompts, models, or implementations side-by-side. Not for single-agent quality checks (use `wf-qa`).
tags: [blind-comparison, benchmark, multi-agent, evaluation, gate]
---

# Gate: Blind Comparison and Transcript Audit

Side-by-side comparative evaluation of independent agent runs on identical tasks.

## 1. Parallel Independent Execution

- Dispatch identical prompt `<task-prompt>` to N independent candidate agents/models in isolated sessions.
- Record full execution transcripts, token usage, tool calls, and output artifacts.

## 2. Transcript Anonymization

- Strip model names, agent IDs, and identifying metadata from transcripts and outputs.
- Assign randomized anonymous identifiers (e.g. Candidate A, Candidate B).

## 3. Blind Comparative Grading

- Independent judge evaluates candidates side-by-side against locked evaluation dimensions:
  - Adherence to constraints and prompt instructions.
  - Quality, accuracy, and completeness of final artifact.
  - Tool usage efficiency and error recovery behavior.

## 4. Synthesis and Unblinding

- Collate rankings, unblind candidate identities, and document relative strengths and failure modes.

## Exit Condition

Completed comparative ranking table with evidence citations.
