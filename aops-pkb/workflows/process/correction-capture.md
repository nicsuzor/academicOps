---
id: correction-capture
kind: process
category: meta
description: When a human corrects an agent's understanding mid-session, capture it as a durable hydration-quality improvement, not just a one-off fix
requires: [memory-capture]
pairs-with: []
conflicts: []
version: 1.0.0
permalink: workflows-process-correction-capture
---

# Process: Correction Capture

**When to invoke**: the user corrects a factual assumption, points out
existing work the agent missed, or explains how something actually works
differently from what the agent assumed. Target: under 2 minutes.

## Steps

1. **Acknowledge and record** — immediately; do not defend the wrong
   assumption. Compose [[memory-capture]] to store the correction.
2. **Classify the gap**: missing fact | missing file reference | wrong
   assumption | stale context | missing workflow step.
3. **Create an improvement task** under the hydration-quality epic, with the
   correction, what was wrong, what's correct, the gap type, and a proposed
   fix.
4. **Fix inline if obvious** (a localized doc/config addition) — note it was
   fixed inline, close with evidence. Leave open if it needs investigation.
5. **Continue** the original task with the corrected understanding.

## Key Rules

The corrected agent files the task, not the human — the correction is the
signal, filing is the agent's job. Speed matters: record, classify, file,
continue. Always create the task even if fixed inline, for the audit trail.
Tag consistently.
