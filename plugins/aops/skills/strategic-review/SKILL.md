---
name: strategic-review
description: Multi-agent review of an artifact (document, plan, PR). Deploys rbg, pauli, and marsha in parallel and reconciles their findings into a single verdict. Pass comment or fix flags to write results back.
---

# Strategic Review

Coordinate multi-agent review across expert lenses and synthesize findings into one reconciled verdict. Bound to `james`.

## Inputs

- **Artifact**: File path, PKB note ID, inline text, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Gather Context

Load the artifact, its diff (for PRs), and relevant quality standards. If originating from a brief, verify against its acceptance criteria and evidence requirements.

### 2. The Premise Test

Before reviewing detailed implementations, evaluate the foundational premise:

- Record one prose sentence: Was this worth doing, and is the overall architecture sound?
- Verify if the mechanism already exists or if the decision contradicts established precedent.
- A flawed premise fails the review regardless of test results.

### 3. Deploy Parallel Reviewers

Dispatch all three reviewers concurrently in a single message with neutral prompts:

- **`rbg`**: Axiom and rule compliance.
- **`pauli`**: Strategic fit, premise validity, and architectural alignment.
- **`marsha`**: Runtime quality, user ask satisfaction, and excellence.

Reviewers select 3-4 relevant lenses (e.g. Scope discipline, Self-consistency, Assumption hygiene, Attribution, Feasibility).

### 4. Reconcile Findings

Synthesize reviewer outputs into a unified findings table:

| Agent | Issue | Feedback | Severity |
| ----- | ----- | -------- | -------- |

- Collapse concordant findings across reviewers into a single row.
- **Severities**: `REJECT` (fundamental redesign), `REVISE` (substantial rework), `FIX` (straightforward resolution), `TRIVIAL` (cosmetic polish), `ADVISORY` (non-blocking).
- **Overall verdict**: `APPROVE`, `MINOR CHANGES`, `REVISE`, or `REJECT`.

### 5. Action and Reporting

- **Default**: Return the synthesis table and overall verdict to the caller.
- **`comment`**: Post the reconciled feedback to the PR review or task note.
- **`fix`**: Apply `FIX` and `TRIVIAL` remedies immediately.
- Write the final verdict and evidence to the artifact's task record.
