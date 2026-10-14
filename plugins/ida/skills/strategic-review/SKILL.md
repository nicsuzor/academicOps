---
name: strategic-review
description: Multi-agent review of an artifact (document, plan, PR). Deploys a rule-compliance reviewer, a strategic-fit reviewer, and a quality reviewer in parallel and reconciles their findings into a single verdict. Pass comment or fix flags to write results back.
---

# Strategic Review

Coordinate multi-agent review across expert lenses and synthesize findings into one reconciled verdict.

## Inputs

- **Artifact**: File path, PKB note ID, inline text, or PR reference (`owner/repo#N`).
- **Flags** (optional): `comment` (post findings to review surface), `fix` (apply minor fixes directly). Without flags, review is advisory.

## Review Process

### 1. Gather Context

Load the artifact, its diff (for PRs), and relevant quality standards. If originating from a brief, verify against its acceptance criteria and evidence requirements.

### 2. Strategic Fit Check

Before implementation detail is reviewed, the strategic-fit reviewer (TypeName `pauli`) situates the artifact against the objectives it claims to serve in the PKB graph using the analytical lenses in `../strategize/SKILL.md` and returns an explicit `FIT`/`MISFIT` verdict, distinct from the compliance verdict and the quality verdict.

### 3. Deploy Parallel Reviewers

Dispatch all three reviewers concurrently via `invoke_subagent` in a single message with neutral prompts: the artifact and its acceptance criteria, with no lenses or verdict scale of your own. Each reviewer returns its verdict on its own definition's scale.

- **Rule compliance** (TypeName `rbg`): Axiom and rule compliance.
- **Strategic fit** (TypeName `pauli`): Strategic Fit Check (step 2).
- **Quality** (TypeName `marsha`): Runtime quality, user ask satisfaction, and excellence.

Reviewers select 3-4 relevant lenses (e.g. Scope discipline, Self-consistency, Assumption hygiene, Attribution, Feasibility). Every reviewer also judges proportion: whether the artifact is larger than the request needs, and whether each fix it asks for is worth its cost given the failure's likelihood and consequence.

### 4. Reconcile Findings

Synthesize reviewer outputs into a unified findings table:

| Reviewer | Issue | Feedback | Severity |
| -------- | ----- | -------- | -------- |

- Collapse concordant findings across reviewers into a single row that keeps each reviewer's own severity; where they differ, state the severity adopted and why.
- Give the fit verdict its own row (`FIT`/`MISFIT`), even when concordant with other rows.
- **Severities**: `REJECT` (fundamental redesign, or work out of proportion to the request), `REVISE` (substantial rework), `FIX` (straightforward resolution), `TRIVIAL` (cosmetic polish), `ADVISORY` (non-blocking).
- **Overall verdict**: `APPROVE`, `MINOR CHANGES`, `REVISE`, or `REJECT`. A `MISFIT` forces `REVISE` or `REJECT` even when the compliance and quality reviews both pass. A reviewer's `REJECT` stands unless the synthesis names the finding that overrules it.

### 5. Action and Reporting

- **Default**: Return the synthesis table and overall verdict to the caller.
- **`comment`**: Post the reconciled feedback to the PR review or task note.
- **`fix`**: Apply `FIX` and `TRIVIAL` remedies immediately.
- Write the final verdict and evidence to the artifact's task record.
