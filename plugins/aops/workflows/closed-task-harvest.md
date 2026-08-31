---
title: Closed Task Knowledge Harvest
type: template
category: process
description: Harvest durable knowledge, architectural decisions, and operational findings from closed tasks into permanent notes. Select when cleaning up completed work or maintaining graph hygiene. Not for creating new tasks or executing work in flight.
tags: [pkb, knowledge-harvest, hygiene, graph-maintenance, process]
---

# Process: Closed Task Knowledge Harvest

Extraction workflow to convert completed task records into permanent, searchable knowledge notes.

## 1. Candidate Task Identification

- Enumerate closed tasks with substantial bodies, findings, or post-mortem notes (`<task-batch>`).
- Filter out trivial tasks or tasks whose learnings are already captured.

## 2. Durable Finding Extraction

- Extract transferable insights into three categories:
  - **Architectural Decisions**: Decisions, trade-offs, and invariants established.
  - **Operational Patterns**: Diagnostic tricks, commands, or workflow nuances discovered.
  - **Empirical Findings**: Benchmark results, bug root causes, or system behaviors.

## 3. Knowledge Note Synthesis

- Author or update permanent knowledge notes in the PKB or docs (`remember`).
- Ensure notes follow the craft standard: concise, modular, and cross-linked.

## 4. Task Body Stubbing

- Replace verbose narrative in closed task bodies with a concise summary and link to permanent notes.
- Verify that the graph index remains clean and searchable.
