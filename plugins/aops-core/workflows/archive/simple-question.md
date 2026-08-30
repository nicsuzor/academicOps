---
id: simple-question
type: template
kind: process
category: routing
description: Pure information request — answer and halt, no modifications, no task, no regime
requires: []
pairs-with: []
conflicts: []
version: 1.0.0
permalink: workflows-process-simple-question
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---
> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process: Simple Question

The degenerate case: zero process. Answer, then HALT and await the next
instruction. No file modifications, no task creation, no unsolicited actions,
no suggested next steps.

## When to Use

"What is...", "How does...", "Where is..." — pure information request, no
action required.

## NOT this template

- "Can you...", "Please...", "Fix..." — action requested, route elsewhere.
- A question that leads to investigation → [[investigation]].
- A question that needs file modification → the appropriate process template.

## Fast-Track Detection

A pure question (no action verbs, no "can you"/"please") can skip full
hydration and route directly here — this saves tokens and latency. A question
containing action language ("what should I add", "can you create") needs full
hydration first, because it isn't actually pure.
