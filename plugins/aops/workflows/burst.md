---
title: Burst (Multi-Session Batch)
type: template
category: process
description: Stateful multi-session batch processing lifecycle for large or long-running tasks. Select when batch volume exceeds single-session token budgets or time limits. Not for single-session batch jobs (use `batch`).
tags: [burst, multi-session, batch, stateful, operations, process]
---

# Process: Burst

Stateful multi-session lifecycle for distributing large-scale batch tasks across session boundaries.

## 1. State Manifest Initialization

- Create or load persistent JSON/YAML manifest at `<manifest-path>`.
- Initialize roster of all work items with statuses: `pending`, `claimed`, `completed`, `failed`.

## 2. Partitioning and Worker Claim

- Partition pending items into bounded slices for current session execution.
- Atomically update claimed item statuses with worker session ID and timestamp.

## 3. Slice Execution and Checkpointing

- Execute target procedure for claimed slice items (`<slice-procedure>`).
- Verify each item output immediately upon completion.
- Write progress checkpoints back to manifest after each verified item.

## 4. Failure Handling and Release

- Record permanent failure reasons for failed items.
- Release expired claims back to `pending` if an interrupted worker failed to complete.

## 5. Session Handover and Progress Ledger

- Emit progress ledger: overall completion percentage, remaining items, and failure count.
- If pending items remain, prepare next session claim instructions (`wf-handover`).
