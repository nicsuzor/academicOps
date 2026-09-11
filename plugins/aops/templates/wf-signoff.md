---
alias:
  - wf-signoff
description: Author a concise, one-page human-facing summary digest for decision or release sign-off.
id: wf-signoff
tags:
  - wf-template
  - gate
title: wf-signoff
type: template
---

## What this step does

Produces a one-page synthesis digest for human sign-off upon completion of an epic or major task. Consolidates verified results from preceding QA gates into an executive summary.

## Output Contract

The sign-off brief must:

- **Fit on one screen**: Cohesive prose summary rather than an exhaustive subtask dump.
- **Link deliverables**: Provide direct links to pull requests, documents, or deployed artifacts.
- **Evidence claims**: Accompany load-bearing assertions with resolving pointers (file:line, test logs, review verdicts).
- **Disclose gaps**: Plainly identify incomplete scope or unverified edge cases.

## When to Include

Include on tasks requiring principal sign-off or release authorization. Skip for internal subtasks that feed into an epic-level digest.
