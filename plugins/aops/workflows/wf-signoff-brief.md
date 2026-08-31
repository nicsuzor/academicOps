---
title: Sign-off Brief
type: template
category: gate
description: Author a concise, one-page human-facing summary digest for decision or release sign-off. Select when presenting completed work or high-stakes choices to the principal. Not for automated agent handovers (use `wf-handover`).
tags: [signoff, brief, digest, principal, review, gate]
---

# Gate: Sign-off Brief

Structured summary format for presenting verified deliverables or decisions to the human principal.

## 1. Bottom-Line Verdict First

- Open with the bottom-line result, verifier verdict, and the specific decision requested from `<principal>`.
- State clearly whether the artifact passed all acceptance criteria.

## 2. Acceptance Criteria and Machine Evidence

- List the agreed acceptance criteria.
- Provide verbatim, quoted evidence for each criterion: test outputs, exit codes, screenshot references, or diff citations.
- Include no hearsay or unverified assertions.

## 3. Identified Gaps and Caveats

- Honestly report any unverified areas, known edge cases, or non-blocking follow-up items.

## 4. Singular Open Question

- End the digest with a single, clear open question for the principal.
- Halt execution and await response.

## Exit Condition

Formatted sign-off digest delivered with explicit open question.
