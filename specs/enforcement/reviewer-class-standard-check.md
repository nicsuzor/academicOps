---
title: Reviewer Class-Standard Verification
status: ready
type: spec
tags: [enforcement, marsha, review, class-spec, doc-taxonomy]
---

# Reviewer Class-Standard Verification

This specification establishes the requirement and procedure for quality and requirement-satisfaction reviewers (such as Marsha) to evaluate every file modified by a change against the governing standard for its document taxonomy class, alongside overall feature specifications and task acceptance criteria. It eliminates the systemic failure mode where multi-file changes pass review because feature criteria and test suites pass, while touched files introduce out-of-class bloat, unneeded system details, or architectural violations.

## User stories

### US-1 Per-File Class-Standard Verification

As a reviewer conducting quality and requirement-satisfaction review, I want to evaluate every file modified by a candidate change against the governing standard for its document taxonomy class, so that files do not violate class-level architectural constraints, instruction density, or document purpose even when overall feature acceptance criteria pass.

- **AC-1.1** Given a pull request or task deliverable touching files across one or more document taxonomy classes (`specs/meta/doc-taxonomy.md`), when a reviewer executes the upfront quality and specification check, then the reviewer enumerates each changed file from the diff, identifies its taxonomy class, and evaluates the file against the governing standard for that class.
- **AC-1.2** Given a change modifying instruction files (`plugins/*/agents/*.md`, `plugins/*/skills/*/SKILL.md`, `plugins/*/workflows/*.md`, `rules/*.md`, `CORE.md`), when a reviewer evaluates those files, then the reviewer verifies compliance with `plugins/ida/skills/craft/SKILL.md` (contract separation, concision, instruction density, no unnecessary external implementation details the agent cannot act upon, no hardcoded workflow rules in task assembly skills, and length budgets) and `specs/meta/doc-taxonomy.md § Instructions`.
- **AC-1.3** Given a change modifying specification files (`specs/<subsystem>/*.md`), when a reviewer evaluates those files, then the reviewer verifies compliance with `specs/meta/writing-specs.md` and `specs/meta/doc-taxonomy.md § Specs` (single feature per spec, Given/When/Then acceptance criteria, behaviour not mechanism, self-contained, no implementation details).
- **AC-1.4** Given a change modifying state documents (`specs/<NAME>.md` including `ENFORCEMENT-MAP.md`, `GATES.md`, `SURFACES.md`, `CAPABILITIES.md`), when a reviewer evaluates those files, then the reviewer verifies compliance with `specs/meta/doc-taxonomy.md § State` and relevant subsystem schemas (for `ENFORCEMENT-MAP.md`, strictly a 4-column cross-reference table mapping active agent rules to their enforcement mechanisms, never summarizing random specs or workflows; for runtime subsystems, the canonical 5-question shape; no proposals or discussion).
- **AC-1.5** Given a change modifying audit-artifact files (`specs/audit/AGENT-*.md`), when a reviewer evaluates those files, then the reviewer verifies compliance with `specs/meta/doc-taxonomy.md § Audit-artifact` (script-generated header, never hand-edited).
- **AC-1.6** Given a change modifying documentation files (`README.md`, `INSTALL.md`, `plugins/*/README.md`), when a reviewer evaluates those files, then the reviewer verifies compliance with `specs/meta/doc-taxonomy.md § Docs` (user-facing, mermaid flowcharts without citations, config tables, no internal jargon).
- **AC-1.7** Given a change where any touched file fails its governing class standard, when a reviewer renders a verdict, then the reviewer records `UNMET` for that file with pinpoint citations and issues `REVISE` (or `FAIL` if foundational), even if the change satisfies its overall feature acceptance criteria and passes test suites.

### US-2 Structured Per-File Review Receipts

As a framework contributor or supervisor receiving review feedback, I want review handbacks to itemize each non-compliant file, its class standard, the violated principle, and the non-compliant lines, so that defect remediation is direct and unambiguous.

- **AC-2.1** Given a candidate change containing files that fail their class standards, when a reviewer outputs the review handback, then the handback itemizes each non-compliant file, its document class, the governing class standard cited with pinpoint section references, and the specific failure reason.

## Design

### 1. Context and the PR #3291 Review Failure

On pull request #3291, an implementation change modified four files across three document classes to retire direct UNIX domain socket (UDS) push expectations and qualify non-PR task QA child task creation:

1. `plugins/ida/agents/sara.md` (Class: Instructions / Agent Persona)
2. `plugins/ida/skills/dispatch/SKILL.md` (Class: Instructions / Skill Body)
3. `plugins/ida/skills/reify/SKILL.md` (Class: Instructions / Skill Body)
4. `specs/ENFORCEMENT-MAP.md` (Class: State Document)

When Marsha reviewed the pull request head commit (`b760d303`), she evaluated the deliverable as a singular artifact against the feature acceptance criteria (Option 1A retired UDS push and Option 2B qualified non-PR task QA child rule) and observed that the pytest suite passed (752 passed). Consequently, Marsha returned `PASS`.

However, all four changed files contained critical defects under their respective class standards:

- `plugins/ida/agents/sara.md` inlined unnecessary external daemon implementation details (Docker exit listener, daemon bridge, OTel spans, `polecat_events` queue) that Sara cannot act upon, violating `plugins/ida/skills/craft/SKILL.md` § First Principles ("State the contract, not the neighbour", "One component, one job") and § Concision and Instruction Density.
- `plugins/ida/skills/dispatch/SKILL.md` inlined identical external daemon implementation details, violating `craft` § Concision and the Deletion Test.
- `plugins/ida/skills/reify/SKILL.md` inlined hardcoded workflow selection criteria into the reification skill instead of composing modular workflow templates from `workflows/`, violating `specs/meta/doc-taxonomy.md § Instructions` and the project rule `runtime-workflow-composition.md`.
- `specs/ENFORCEMENT-MAP.md` added a row summarizing a specification guarantee ("Polecat Completion Reporting & Session Waking") rather than an active agent rule, violating `specs/meta/doc-taxonomy.md § State` and `specs/enforcement/enforcement.md`.

Human review caught all four failures and requested changes. The review gap stemmed directly from Marsha's instruction text, which directed her to identify the genre of "the artifact" as a single entity rather than checking every touched file in the diff against the standard for its class.

### 2. Enforcement Audit and Proportionality Analysis

#### Current Enforcement Status

An audit of the single source of truth for enforcement (`specs/ENFORCEMENT-MAP.md`) and the full reviewer instruction files reveals:

- **`specs/ENFORCEMENT-MAP.md`**:
  - Row 59 (`[Persona: Marsha]`) enforces verifying deliverables for ambitious quality across actual rendered multimodal outputs against requester meaning, distinctions, and available specifications/requirements/criteria, treating the absence of any criteria as an immediate `FAIL` (`plugins/ida/agents/marsha.md:11-20`, `plugins/ida/skills/workflow-library/workflows/wf-qa.md:29-33`, `plugins/ida/skills/verify/SKILL.md:14,19,29-30`).
  - Rows 65 (`[Review Discipline: Upfront Stopping & Per-Claim Fail-Fast]`), 66 (`[Review Discipline: Supervisor Calibration, Unified Verdicts & Reviewer Lane Boundaries]`), and 67 (`[QA Inspection: Targeted Grep-First Verification]`) govern upfront stopping, role boundaries, and search discipline.
  - **Missing Row**: There is no entry in `specs/ENFORCEMENT-MAP.md` requiring reviewers to check each changed file against its document taxonomy class standard. This requirement is currently **unenforced** in the enforcement map.
- **Reviewer Instruction Files**:
  - `plugins/ida/agents/marsha.md:15-17` (§ 1 "Governing standard and specification existence"): Mentions identifying the format and quality standard governing "the artifact's genre (`specs/meta/doc-taxonomy.md`...)", framing the deliverable as a singular artifact with one genre.
  - `plugins/ida/skills/workflow-library/workflows/wf-qa.md:30-32` (§ 1 "Upfront standard and specification check"): Similarly directs the reviewer to identify the governing standard for "the artifact's genre".
  - `plugins/ida/skills/verify/SKILL.md:12-15` (§ 1 "Upfront Standard & Specification Check"): Matches format requirements to "the artifact's genre".
  - `plugins/ida/agents/james.md`, `wf-review.md`, and `strategic-review/SKILL.md`: Direct Marsha to evaluate whether work delivers on stated requirements and governing genre standards, without instructing reviewers to inspect diffs file by file against class standards.

#### Proportional Intervention Options Pass

Per `specs/enforcement/enforcement.md` § Proportionality and force of intervention, proposed measures are evaluated from least-invasive to most-invasive:

1. `doctrine only`: Declaring the requirement in design documents alone failed; the principle in `doc-taxonomy.md` was ignored during PR #3291 review.
2. `instructions` (`imperative`): **Target placement**. Default to instructions. Adding an explicit imperative instruction to Marsha's reviewer files (`marsha.md`, `wf-qa.md`, `verify/SKILL.md`) to enumerate all files in the diff and evaluate each against its class spec is the least-invasive intervention. The burden of proof is on adding heavier mechanisms, which is not met because instructions have not yet been attempted for this requirement.
3. `JIT injection`: Adding pre-review hook injections or linters is premature and excessive before attempting instructions.
4. `structural`: Mechanical linters or AST parsers cannot assess qualitative instruction density, unnecessary detail, or document purpose, and would violate `judgment-non-delegable`.
5. `process` / 6. `post-hoc`: Fits naturally into the existing required QA review process gate.

### 3. Specification of the Instruction Changes

In Stage 2 (Build task `aops_8012b713`), the following updates will be applied across Marsha's instruction files:

1. **`plugins/ida/agents/marsha.md`**:
   Update Section 1 ("Governing standard and specification existence") to include per-file class-standard verification:
   - Enumerate all modified files from the diff (`git diff --name-only` or PR file list).
   - Identify each touched file's taxonomy class per `specs/meta/doc-taxonomy.md`.
   - Verify each file against its class standard:
     - Instructions -> `plugins/ida/skills/craft/SKILL.md` (contract separation, concision, no unnecessary external implementation details, single responsibility, length budgets) and `specs/meta/doc-taxonomy.md § Instructions` (no hardcoded workflow mechanics in assembly skills).
     - Specs -> `specs/meta/writing-specs.md` and `specs/meta/doc-taxonomy.md § Specs` (single feature per spec, Given/When/Then acceptance criteria, behaviour not mechanism, self-contained, no implementation details).
     - State -> `specs/meta/doc-taxonomy.md § State` and subsystem spec (concise SSoT table; for `ENFORCEMENT-MAP.md`, strictly a 4-column cross-reference table mapping active agent rules to their enforcement mechanisms, never summarizing random specs or workflows; 5-question shape for runtime subsystems; no proposals).
     - Audit-artifact -> `specs/meta/doc-taxonomy.md § Audit-artifact` (script-generated header, never hand-edited).
     - Docs -> `specs/meta/doc-taxonomy.md § Docs` (user-facing, mermaid flowcharts without citations, config tables, no internal jargon).
   - If any changed file fails its class standard, record `UNMET` for that file and issue `REVISE` (or `FAIL`), even if feature criteria and test suites pass.
2. **`plugins/ida/skills/workflow-library/workflows/wf-qa.md`**:
   Update Step 1 ("Upfront standard and specification check") to mandate diff-level per-file class-standard verification alongside overall deliverable checks.
3. **`plugins/ida/skills/verify/SKILL.md`**:
   Update Section 1 ("Upfront Standard & Specification Check") and Section 3 ("Immediate Fail Triggers") to add class-standard violation as a trigger for `REVISE` / `FAIL`.

### 4. Planned Observation: Verification Against PR #3291

The effectiveness of this change will be demonstrated by evaluating the reviewed head commit of PR #3291 (`b760d303`) against the updated instructions:

| Touched File | Document Class | Governing Standard | Evaluation & Observed Finding | Status |
| :- | :- | :- | :- | :- |
| `plugins/ida/agents/sara.md` | Instructions (Agent Persona) | `plugins/ida/skills/craft/SKILL.md` § 1.3, 1.4, 1.10, § Length Budgets; `specs/meta/doc-taxonomy.md § Instructions` | Inlines unnecessary external daemon implementation details (`polecat_events` queue, Docker exit listener, daemon bridge, OTel spans) that Sara cannot act upon. Sara's role is task delegation and verification, not daemon bridge internals. | `UNMET` |
| `plugins/ida/skills/dispatch/SKILL.md` | Instructions (Skill Body) | `plugins/ida/skills/craft/SKILL.md` § 1.10, § The Deletion Test | Inlines identical external daemon architecture and listener mechanics into the dispatch procedure, injecting unnecessary detail that does not change dispatch behavior. | `UNMET` |
| `plugins/ida/skills/reify/SKILL.md` | Instructions (Skill Body) | `plugins/ida/skills/craft/SKILL.md` § 1.3, 1.4; `specs/meta/doc-taxonomy.md § Instructions`; `.agents/rules/RULES.md` (`runtime-workflow-composition.md`) | Inlines hardcoded workflow selection criteria into the reification skill rather than composing modular workflow templates from `workflows/`. Workflows come from workflow templates, not task assembly skills. | `UNMET` |
| `specs/ENFORCEMENT-MAP.md` | State Document | `specs/meta/doc-taxonomy.md § State`; `specs/enforcement/enforcement.md` | Inserts a row summarizing an architectural specification guarantee ("Polecat Completion Reporting & Session Waking") rather than an active agent rule and its enforcement mechanism. | `UNMET` |

**Expected Outcome**: Marsha rejects the PR with `REVISE` (or `FAIL`), itemizing the four class-standard violations with pinpoint citations, exactly matching the human review findings.

### 5. Enforcement Map Update (Stage 2)

Upon implementation in Stage 2 (`aops_8012b713`), the following row will be added to `specs/ENFORCEMENT-MAP.md`:

```markdown
| [Reviewer Class-Standard Verification](enforcement/reviewer-class-standard-check.md) -- Reviewers check every file a change touches against the governing standard for its document taxonomy class (craft for instructions, writing-specs for specs, doc-taxonomy for state/docs), recording UNMET for any file that violates its class standard regardless of feature acceptance criteria. | instructions | imperative | `plugins/ida/agents/marsha.md:15-18`, `plugins/ida/skills/workflow-library/workflows/wf-qa.md:30-33`, `plugins/ida/skills/verify/SKILL.md:12-16`, `specs/enforcement/reviewer-class-standard-check.md`: Mandates per-file class-standard checking across git diffs; reviewers fail/revise PRs touching files that violate their class standards (e.g. craft violations in instructions, spec summaries in ENFORCEMENT-MAP.md). Observation: PR #3291 head commit b760d303 evaluated under class-standard check correctly flagged all 4 changed files as UNMET under craft and doc-taxonomy. |
```
