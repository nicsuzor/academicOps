---
title: Durable Memory Capture
type: template
category: gate
description: Extract and record cross-session findings, architectural decisions, and operational insights into permanent knowledge notes. Select at task completion or session exit. Not for ephemeral task status updates (use `task-tracking`).
tags: [memory, pkb, capture, knowledge, learning, gate]
---

# Gate: Durable Memory Capture

Knowledge extraction obligation to prevent durable insights from being trapped in ephemeral session transcripts.

## 1. Insight Identification

- Review session execution logs and findings for `<task>`.
- Identify insights with cross-task or cross-session value:
  - Architectural invariants or system constraints discovered.
  - Diagnostic patterns or tool quirks resolved.
  - Reusable empirical results or benchmark findings.

## 2. Knowledge Note Synthesis

- Author or update permanent note in PKB or repository docs (`remember`).
- Structure note with concise context, core finding, and functional rationale.
- Adhere to the craft standard: modular, concise, and free of episodic diary narrative.

## 3. Cross-Linking

- Add wikilinks connecting the note to relevant specs, axioms, and task records.

## Exit Condition

Durable findings recorded in permanent knowledge notes and cross-linked.
