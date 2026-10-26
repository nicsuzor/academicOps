---
alias:
  - wf-prompt-objectives
description: Prompt objectives -- reduce a day of user prompts to the objectives pursued, synthesizing dense consolidated summaries, elevating handwritten or emphasized prompts into tracking and work tasks, and capturing unfinished work.
id: wf-prompt-objectives
tags:
  - wf-template
  - template
  - process
  - traces
  - daily
  - prompt-sweep
title: wf-prompt-objectives
type: template
---

## What this step does

Processes a day of user prompts across conversation and trace sources to identify pursued objectives, elevates handwritten or emphasized requests into tracked graph tasks, synthesizes dense consolidated thematic summaries of related items, and recovers unfinished work.

## Obligations

1. **Pull Daily Prompts**: Query user prompts across terminal sessions, channel messages, and interactive client turns within the daily window (00:00 to 24:00 local time).
2. **Filter Agent Traffic**: Strip out automated agent traffic, command dispatches, notifications, compaction summaries, and background execution artifacts. Retain direct user input.
3. **Thread Asks and Elevate High-Signal Prompts**:
   - Fold in-work follow-ups, clarifications, and iterative exchanges into the primary ask they serve.
   - _Elevate detailed handwritten prompts_: Where the user took the time to write a detailed prompt by hand, or used emphatic language stressing importance ("must", "critical", "important", repeated asks), treat as high-priority signals:
     - Check if a tracking task exists on the graph.
     - If not, create a tracking task assigned to the front supervisory agent (`ida`) under `agent_brains/ida` for follow-up.
     - If the work itself lacks a task, create a work task situated under the appropriate parent/epic (marked `status: in_progress`).
4. **Climb to Objectives and Dense Thematic Consolidation**:
   - For each ask, identify what state of the world the prompt aimed to make true.
   - Consolidate related asks into dense thematic summaries rather than outputting a raw, fragmented laundry list.
   - Explicitly capture unfinished work, open loops, and partial progress.
5. **Output and Hand-back Contract**:
   - When running standalone: write `## Today's objectives` into the target daily note and emit an execution report.
   - When running in hand-back mode (invoked by `wf-daily` / `tpl_daily`): return the synthesized objectives block, elevated tracking task IDs, and unfinished work items to the daily note runner to fold into the note atomically.

## Must not

- Must not output raw, uncurated laundry lists of prompts; prompts must be clustered and densified into cohesive objective outcomes.
- Must not ignore detailed or emphatic handwritten user prompts; high-signal prompts must be elevated to tracked tasks.
- Must not include raw session timestamps, span IDs, or telemetry internals in the daily note output.
