---
title: Triage Open GitHub Issues
type: template
category: process
description: Work down a repository open-issue backlog in bounded batches — close verified fixes, land small live fixes, annotate the rest. Select when triaging backlog issues.
tags: [github, issues, triage, backlog, maintenance, process]
---

# Process: Triage Open GitHub Issues

Batch triage procedure for managing and clearing open issue backlogs.

## 1. Backlog Ingestion and Slicing

- Fetch batch of N open issues from repository tracker (`<issue-batch>`).
- Filter by label, age, or component area.

## 2. Issue Evaluation

- For each issue, inspect description, reproduction steps, and discussion history:
  - **Already Resolved**: Issue is fixed in latest main branch -> Verify fix, quote commit/PR, and close.
  - **Quick Fix**: Bug is reproducible with obvious local fix -> Implement fix (`feature-dev`), open PR, reference issue.
  - **Actionable Task**: Legitimate bug/feature requiring planned work -> Add tags, clarify acceptance criteria, wire to parent epic.
  - **Incomplete / Stale**: Missing reproduction steps or abandoned -> Request specific clarification.

## 3. Action Execution

- Apply labels, post comments, or close issues with concise evidence notes.
- Do not close issues on speculative assumptions.

## 4. Triage Batch Summary

- Emit summary ledger: closed count, quick-fixes landed, tasks formulated, and pending inquiries.
