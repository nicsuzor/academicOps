---
title: Default Dialectical Review Workflow
status: draft
type: spec
category: workflow
tags: [spec, workflow, review, dialectic, composition, default]
---

# Default Dialectical Review Workflow

Establishes the dialectical review as the workflow library's default independent review workflow in place of `wf-review`, ensuring composite workflows default to dialectical multi-agent evaluation while enabling users and projects to seamlessly substitute alternative review systems.

## User stories

### US-1 Default Dialectical Review for Composite Review Stages

As an agent composing tasks from composite workflows, I want a composite review stage to resolve to the dialectical review workflow by default without hardcoding its template name, so that deliverables receive thorough multi-perspective independent review without violating runtime workflow composition.

- **AC-1.1** Given a composite workflow template defining an independent review stage, when a composing agent resolves the workflow and no specific review template has been requested by the user or project, then the review stage resolves to the workflow template tagged `review` marked `default: true` (`wf-dialectical-review`).
- **AC-1.2** Given a review task resolved to the default dialectical review, when the assigned review worker executes the task, then it executes dialectical review by coordinating internal subagents for distinct specialist perspectives (`pauli` for strategic direction and congruence, `rbg` for compliance and authority, `marsha` for quality and requirement satisfaction) under supervisor `james` to deliver a reconciled verdict (`PASS`, `REVISE`, or `FAIL`).

### US-2 User and Project Substitution of Review Systems

As a user or project author, I want to substitute an alternative review workflow for any composite task, so that specialized or lightweight review procedures can replace the default dialectical review when desired.

- **AC-2.1** Given an incoming user ask or task direction that explicitly designates an alternative review template (such as `wf-quick-fix`, a single-persona reviewer, or a specialized check), when the workflow is composed, then the explicitly requested review template overrides and substitutes for the default dialectical review.
- **AC-2.2** Given a project-scoped workflow template tagged `review` and marked `default: true` within a project's knowledge base, when a review stage is composed for tasks within that project, then the project-tier default template shadows and substitutes for the universal default template.

### US-3 Clean Resolution of Legacy Review Template References

As a framework developer, I want all legacy references to `wf-review` in plugins, templates, and specifications resolved to the canonical dialectical review workflow, so that the workflow library maintains a single source of truth for review workflows and shared review briefings.

- **AC-3.1** Given the workflow library, when querying universal review templates, then `wf-dialectical-review.md` is the single canonical review template carrying `default: true` and the shared review briefing, and legacy duplicate variants are retired.
- **AC-3.2** Given all plugin files and agent instructions that previously referenced `wf-review`, when inspected, then every reference is updated to point to `wf-dialectical-review` or the abstract shared review briefing contract.

## Design

### 1. Default Review Resolution and Substitution Architecture

The framework enforces the invariant that workflow templates name no other template directly (`runtime-workflow-composition`). To support default workflows without hardcoded template coupling, the workflow library adopts frontmatter-based default selection, matching the established precedent for plan views (`default: true` paired with a category tag):

1. **Category Tagging and Default Flag**:
   - The canonical dialectical review template (`wf-dialectical-review.md`) declares `tags: [..., review, ...]` and `default: true` in its YAML frontmatter.
   - When a composite template defines a review stage (e.g. stage 8 in `wf-research-output`), the stage contract specifies its requirements as an independent evaluation rather than naming an implementation file.
   - The stage text documents that the stage defaults to the dialectic review (utilizing internal subagents for multi-perspective evaluation) unless an alternative review system is specified.

2. **Resolution Hierarchy**:
   When `/reify` or a composing agent resolves a review stage:
   - **Explicit Request (Highest Precedence)**: If the user's ask, parent epic, or briefing names a specific review template (e.g., `wf-quick-fix`, `wf-fact-check`, or a custom reviewer), that named template is composed.
   - **Project-Tier Default**: If the project's knowledge base defines a template tagged `review` with `default: true`, that template shadows the universal tier.
   - **Universal-Tier Default**: In the absence of an explicit request or project override, the composing agent selects the universal template tagged `review` marked `default: true` (`wf-dialectical-review`).

3. **Outcome-Level Build Criteria for Stage 2**:
   - The composite base templates (`wf-code-task-base`, `wf-doc-base`) state that review stages default to the dialectic review (drawing on the shared review briefing, quoting the originating request with its source ID before the PR, and spawning internal subagents for distinct perspectives), while permitting user substitution of alternative review systems.
   - The canonical template `wf-dialectical-review.md` is created at universal tier, consolidating `wf-dialectical-design.md` and `wf-review.md`, declaring `default: true`, incorporating the Shared Review Briefing, and explicitly noting that internal subagent spawning is intended.
   - `/reify` composition instructions state how review follow-up tasks resolve via the `review` tag and `default: true` attribute when no specific review template is designated.
   - `wf-review.md` is retired from universal templates, and all plugin files referencing it are updated cleanly.

### 2. Quoted Inventory of Affected Plugin Files

Every plugin file in the repository referencing `wf-review` is accounted for below, specifying current text and the exact target state:

1. `plugins/ida/agents/james.md` (Line 20):
   - **Current**:
     ```markdown
     When supervising a review (`/strategic-review`, `wf-dialectical-design`, `wf-review`):
     ```
   - **Target**:
     ```markdown
     When supervising a review (`/strategic-review`, `wf-dialectical-review`):
     ```

2. `plugins/ida/skills/reify/SKILL.md` (Line 96):
   - **Current**:
     ```markdown
     3. Compose the review follow-up task drawing its brief from the shared review briefing in `wf-review` and the designated review template (`wf-qa`, `wf-rbg`, `wf-strategic-fit`, `wf-signoff`, or `wf-fact-check`): instructions direct the reviewer to independently verify the deliverable and claims against literal acceptance criteria; if verification fails, the reviewer releases the task as `failed` with documented failure evidence; confirm tier against the taxonomy; for verified Tier 1 PRs, merge to base branch on a verified pass; for Tier 2 and Tier 3 PRs, post verification receipts to the PR and leave open for reviewer sign-off without releasing to review. A reviewer that changes code delivers it through its workflow and hands off for independent review.
     ```
   - **Target**:
     ```markdown
     3. Compose the review follow-up task drawing its brief from the shared review briefing in `wf-dialectical-review` (or the review template designated by the caller or project): instructions direct the reviewer to independently verify the deliverable and claims against literal acceptance criteria; review stages resolve to the default dialectical review template (`default: true`) unless an alternative review template is specified; if verification fails, the reviewer releases the task as `failed` with documented failure evidence; confirm tier against the taxonomy; for verified Tier 1 PRs, merge to base branch on a verified pass; for Tier 2 and Tier 3 PRs, post verification receipts to the PR and leave open for reviewer sign-off without releasing to review. A reviewer that changes code delivers it through its workflow and hands off for independent review.
     ```

3. `plugins/ida/skills/strategic-review/SKILL.md` (Line 28):
   - **Current**:
     ```markdown
     Dispatch all three specialist reviewers concurrently in a single turn using the calibrated `Model` selection. Every reviewer's brief is drawn from the shared review briefing defined in `wf-review` (quoting the originating request, governing genre standard, and available specifications/requirements/criteria before the artifact or diff) and returns a verdict in the unified `PASS` / `REVISE` / `FAIL` vocabulary:
     ```
   - **Target**:
     ```markdown
     Dispatch all three specialist reviewers concurrently in a single turn using the calibrated `Model` selection. Every reviewer's brief is drawn from the shared review briefing defined in `wf-dialectical-review` (quoting the originating request, governing genre standard, and available specifications/requirements/criteria before the artifact or diff) and returns a verdict in the unified `PASS` / `REVISE` / `FAIL` vocabulary:
     ```

4. `plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md` (Line 22):
   - **Current**:
     ```markdown
     4. **Review and verdict** -- in a separate task, by a fresh worker that did not write the code. The review task draws its brief from the shared review briefing in `wf-review` (quoting the originating request verbatim with its source ID before the PR). Run `/strategic-review` on the PR, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict:
     ```
   - **Target**:
     ```markdown
     4. **Review and verdict** -- in a separate task, by a fresh worker that did not write the code. Defaults to the dialectic review (drawing its brief from the shared review briefing in `wf-dialectical-review`, quoting the originating request verbatim with its source ID before the PR, and spawning internal subagents to provide different perspectives), unless a different review system is specified. Run `/strategic-review` on the PR, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict:
     ```

5. `plugins/ida/skills/workflow-library/workflows/wf-doc-base.md` (Line 19):
   - **Current**:
     ```markdown
     3. **Review and verdict** -- in a separate task, by a fresh worker that did not write the change. The review task draws its brief from the shared review briefing in `wf-review` (quoting the originating request verbatim with its source ID before the PR). Review the PR against the acceptance criteria and the project's rules, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict:
     ```
   - **Target**:
     ```markdown
     3. **Review and verdict** -- in a separate task, by a fresh worker that did not write the change. Defaults to the dialectic review (drawing its brief from the shared review briefing in `wf-dialectical-review`, quoting the originating request verbatim with its source ID before the PR, and spawning internal subagents to provide different perspectives), unless a different review system is specified. Review the PR against the acceptance criteria and the project's rules, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict:
     ```

6. `plugins/ida/skills/workflow-library/workflows/wf-dialectical-design.md`:
   - **Current**: Standalone template `wf-dialectical-design` (with alias `wf-review-dialectic`).
   - **Target**: Consolidated into `wf-dialectical-review.md` (id: `wf-dialectical-review`, aliases: `[wf-dialectical-review, wf-dialectical-design, wf-review-dialectic, wf-design-dialectic]`), adding frontmatter `default: true`, incorporating `## Shared Review Briefing`, and retiring separate `wf-dialectical-design.md`.

7. `plugins/ida/skills/workflow-library/workflows/wf-review.md`:
   - **Current**: Standalone template `wf-review` (Multi-Agent Review Workflow).
   - **Target**: Retired and removed; its Shared Review Briefing is consolidated into `wf-dialectical-review.md`.

### 3. Enforcement-Map Extract and Regulatory Evidence

#### Enforcement-Map Extract (`specs/ENFORCEMENT-MAP.md`)

The following rows in `specs/ENFORCEMENT-MAP.md` govern review workflows and will be updated in Stage 2 to reflect `wf-dialectical-review`:

| Section / Rule | Current Mechanism & Detail | Target Detail after Update |
| - | - | - |
| Baseline: Rule-compliance review lens (Line 13) | `process`, `required gate` via `wf-rbg.md`, `wf-review.md`, and `/strategic-review` | Replace `wf-review.md` with `wf-dialectical-review.md` as the default multi-agent review workflow. |
| Axiom: Cite Sources (Line 18) | `wf-review.md:19-42` & `wf-fact-check.md:1-40`: Shared review brief quotes originating ask with source ID before diffs. | Update citation pointer from `wf-review.md` to `wf-dialectical-review.md` holding the shared review brief. |
| Axiom: Data Boundaries (Line 21) | `wf-rbg.md:24-38`, `wf-review.md:30-55`, & `strategic-review`: Rule-compliance review checks destination repository visibility and scrubs diffs. | Update pointer from `wf-review.md` to `wf-dialectical-review.md`. |
| Axiom: Excellence (Line 27) | `wf-qa.md:1-45`, `wf-qa-visual.md:1-40`, `wf-review.md:1-55`, & `wf-strategic-fit.md:1-40`: Multi-lens review and runtime QA gates verify substantive rigor. | Update pointer from `wf-review.md` to `wf-dialectical-review.md`. |
| Review Discipline: Supervisor Calibration (Line 62) | `james.md:18-26`, `wf-dialectical-design.md:24-31`, `wf-review.md:20-53`, `strategic-review`: Supervisor calibrates proportionality and altitude upfront. | Update pointers to `james.md`, `wf-dialectical-review.md`, and `strategic-review`. |

#### Regulatory Evidence for the Move

1. **Originating User Direction**:
   Explicit directive from user consultation (2026-10-30):
   > "wf-review should at this stage be replaced by the dialectic review, which I think we've proven works really well now. If users want to sub in a different review system, though, they should be able to, so in the main template, just say we default to dialectic. And the dialectic review spawns internal subagents to provide different perspecctives, which is fine."

2. **Empirical Failure Pattern of Predecessor Mechanism (`wf-review`)**:
   In previous framework runs, decomposing review tasks with `wf-review` failed to deliver multi-perspective review in practice. Because `wf-review` lacked built-in supervisor-orchestrated subagent execution, task runners executed review tasks as a single worker doing a monolithic, shallow sweep (observed in the Coles project review stage).

3. **Demonstrated Efficacy of Dialectical Review**:
   The dialectical review architecture refined in PR #3179 (`/strategic-review` under `james` coordinating `pauli`, `rbg`, and `marsha` with explicit proportionality calibration and dialectical deliberation) demonstrated substantive rigor, clean role boundaries, and reliable synthesis across diverse artifact genres. Permitting internal subagent spawning satisfies the need for multi-perspective critique within a single assigned review worker session.

4. **Proportionality and Enforcement Hierarchy**:
   The change operates at Level 2 (`instructions`, `imperative`) and Level 5 (`process`, `required gate`). It avoids creating new mechanical locks or static scripts, adhering to `default to instructions`. Utilizing `default: true` frontmatter preserves runtime workflow composition (`runtime-workflow-composition`) while ensuring the framework defaults to the proven standard. Consolidating `wf-review` and `wf-dialectical-design` into `wf-dialectical-review` satisfies `single-source-of-truth` and `categorical-imperative`.

## Open questions

None. The design directly implements the user directive, adopts the established `default: true` workflow convention, and resolves all legacy template references.
