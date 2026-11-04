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

### 1. Upfront Review Procedure

When a quality reviewer initiates an evaluation, the upfront check executes before evaluating overall deliverable polish, line-by-line repo changes, or executing test suites:

1. **Diff enumeration**: The reviewer extracts all modified files from the diff (`git diff --name-only` or candidate PR file list).
2. **Taxonomy classification**: Each modified file is mapped to its document taxonomy class per `specs/meta/doc-taxonomy.md`:
   - _Instructions_: `plugins/*/agents/*.md`, `plugins/*/skills/*/SKILL.md`, `plugins/*/workflows/*.md`, `rules/*.md`, `CORE.md`
   - _Specs_: `specs/<subsystem>/*.md`
   - _State_: `specs/<NAME>.md` (such as `ENFORCEMENT-MAP.md`, `GATES.md`, `SURFACES.md`, `CAPABILITIES.md`)
   - _Audit-artifact_: `specs/audit/AGENT-*.md`
   - _Docs_: `README.md`, `INSTALL.md`, `plugins/*/README.md`
3. **Class standard evaluation**: Each file is verified against the quality and architectural standard governing its class:
   - Instructions are verified against `plugins/ida/skills/craft/SKILL.md` (contract separation, concision, instruction density, no unnecessary external implementation details, single responsibility, length budgets) and `specs/meta/doc-taxonomy.md § Instructions` (no hardcoded workflow mechanics in task assembly skills).
   - Specs are verified against `specs/meta/writing-specs.md` and `specs/meta/doc-taxonomy.md § Specs` (single feature per spec, Given/When/Then acceptance criteria, behaviour not mechanism, self-contained, no implementation details).
   - State documents are verified against `specs/meta/doc-taxonomy.md § State` and relevant subsystem schemas (for `ENFORCEMENT-MAP.md`, strictly a 4-column cross-reference table mapping active agent rules to their enforcement mechanisms; no proposals or discussion).
   - Audit artifacts are verified against `specs/meta/doc-taxonomy.md § Audit-artifact` (script-generated header, never hand-edited).
   - Docs are verified against `specs/meta/doc-taxonomy.md § Docs` (user-facing, mermaid flowcharts without citations, config tables, no internal jargon).

### 2. Failure Disposition & Early Stopping

Reviewers evaluate touched files under early stopping:

- If any touched file violates its class standard, the reviewer records `UNMET` for that file with pinpoint citations and issues `REVISE` (or `FAIL` if foundational).
- This failure is non-waivable: passing overall feature criteria or green test suites does not compensate for out-of-class bloat or architectural violations.
- Review handbacks output structured receipts itemizing each failing file, its document class, the governing class standard cited with pinpoint sections, and the specific failure reason.

### 3. Enforcement Architecture

Reviewer class-standard verification is enforced at Level 2 (`instructions`, `imperative`) across quality reviewer instructions (`marsha.md`, `wf-qa.md`, `verify/SKILL.md`) and registered in `specs/ENFORCEMENT-MAP.md`. Following the enforcement pyramid (`specs/enforcement/enforcement.md`), imperative instructions are the least-invasive intervention that establishes the requirement across reviewer agents, reserving mechanical linters or AST parsers unless instruction adherence fails.
