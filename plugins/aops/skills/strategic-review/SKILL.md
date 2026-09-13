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

### 2. Strategic Fit Check

Before reviewing implementation detail, `pauli` runs its Strategic Fit Check (see `pauli.md`'s Reviewer Mode) and returns an explicit `FIT`/`MISFIT` verdict, distinct from `rbg`'s compliance verdict and `marsha`'s quality verdict.

### 3. Deploy Parallel Reviewers

Dispatch all three reviewers concurrently in a single message with neutral prompts:

- **`rbg`**: Axiom and rule compliance.
- **`pauli`**: Strategic Fit Check (step 2).
- **`marsha`**: Runtime quality, user ask satisfaction, and excellence.

Reviewers select 3-4 relevant lenses (e.g. Scope discipline, Self-consistency, Assumption hygiene, Attribution, Feasibility).

### 4. Reconcile Findings

Synthesize reviewer outputs into a unified findings table:

| Agent | Issue | Feedback | Severity |
| ----- | ----- | -------- | -------- |

- Collapse concordant findings across reviewers into a single row.
- Give `pauli`'s fit verdict its own row (`FIT`/`MISFIT`), even when concordant with other rows.
- **Severities**: `REJECT` (fundamental redesign), `REVISE` (substantial rework), `FIX` (straightforward resolution), `TRIVIAL` (cosmetic polish), `ADVISORY` (non-blocking).
- **Overall verdict**: `APPROVE`, `MINOR CHANGES`, `REVISE`, or `REJECT`. A `MISFIT` from `pauli` forces `REVISE` or `REJECT` even when `rbg` and `marsha` both pass.

### 5. Action and Reporting

- **Default**: Return the synthesis table and overall verdict to the caller.
- **`comment`**: Post the reconciled feedback to the PR review or task note.
- **`fix`**: Apply `FIX` and `TRIVIAL` remedies immediately.
- Write the final verdict and evidence to the artifact's task record.
