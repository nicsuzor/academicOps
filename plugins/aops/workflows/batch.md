---
title: Batch Processing
type: template
category: process
description: Parallel or sequential execution of independent, homogenous work items within a single session. Select when applying the same transformation or procedure across multiple files, records, or targets. Not for multi-session stateful batches (use `burst`).
tags: [batch, parallel, execution, operations, process]
---

# Process: Batch Processing

Single-session batch execution pattern for processing independent items with failure isolation.

## 1. Item Discovery and Inventory

- Enumerate all target items from `<item-source>` matching criteria.
- Produce a structured item roster with unique IDs and paths.
- Check item count against single-session capacity thresholds.

## 2. Worker Dispatch and Execution

- For each item or partition in the roster, execute the target procedure (`<procedure>`).
- Run operations in parallel or bounded worker concurrency.
- Ensure failure in one item does not abort remaining items.

## 3. Result Aggregation and Error Isolation

- Collect output artifacts, return codes, and logs for each processed item.
- Record successful outcomes under output roster.
- Isolate failed items with verbatim error logs and failure reasons.

## 4. Verification and Summary

- Verify output artifact integrity for completed items.
- Emit structured summary table: total items, succeeded count, failed count, and next-step actions.
