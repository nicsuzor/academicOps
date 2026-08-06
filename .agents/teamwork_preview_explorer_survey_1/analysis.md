# Analysis Report — Requirements R1 & R2 Investigation

## Executive Summary

This investigation analyzes requirements R1 (Email Triage Workflow Component `aops_7ea0f95f`) and R2 (Fix Dangling Plugin References `aops_4bc0dfea`) from `/workspace/ORIGINAL_REQUEST.md`. We present full file locations, code structures, schema specifications, proposed implementations, and test verification strategies for the implementer phase.

---

## 1. Requirement R1: Email Triage Workflow Component (`aops_7ea0f95f`)

### 1.1 Objective & Acceptance Criteria

- **Objective**: Build the email triage workflow as a reusable `wf-*` component.
- **Acceptance Criteria**:
  - The email triage workflow is available as a reusable `wf-*` component.
  - An independent test script verifies its functionality, schema, and presence across build outputs.

### 1.2 Current Codebase State

- Existing process template: `/workspace/plugins/pkb/workflows/process/email-triage.md`
  - Frontmatter: `id: email-triage`, `kind: process`, `permalink: workflows-process-email-triage`.
- Catalogue & Routing: `/workspace/plugins/pkb/workflows/INDEX.md`
  - Routes `Email or communications?` to `[[email-triage]]`.
  - Listed in Process templates table (`| [[email-triage]] | Classify an inbox into task, FYI, skip, unsure | task-tracking | [[wf-handover]] |`).
- Composition Mechanism: `/workspace/plugins/pkb/skills/brief/SKILL.md` §5
  - Dynamic workflow composition resolves templates across three layers:
    1. Shipped library: `plugins/pkb/workflows/` (`process/` and `wf-*.md` obligation/reusable component templates).
    2. User layer: `$ACA_DATA/.agents/workflows/`.
    3. PKB layer: dynamic templates tagged `wf-template`.
  - Every obligation / reusable component template resolves by its `wf-` permalink or filename (e.g., `wf-email-triage`).

### 1.3 Proposed Component Architecture & Specifications

#### 1. Target File Location

Create reusable workflow component at:
`/workspace/plugins/pkb/workflows/wf-email-triage.md`

#### 2. Component Frontmatter Schema

```yaml
---
id: wf-email-triage
kind: obligation
category: email
description: Classify incoming emails into Task/FYI/Skip/Uncertain with priority inference
requires: [task-tracking]
pairs-with: [wf-handover]
recommends: []
conflicts: []
version: 1.0.0
permalink: wf-email-triage
---
```

#### 3. Component Content Specifications

- **Critical Precondition**: Check sent mail first (if matching reply already exists -> classify as Skip).
- **Classification Rules**:
  - **Task**: "please review...", decisions needed, deadlines, invitations -> Create task, compose `[[task-tracking]]`.
  - **FYI**: "awarded", "approved", outcomes, thank-yous -> Archive.
  - **Skip**: `noreply@`, newsletters, already replied to -> Archive.
  - **Uncertain**: mixed signals, unknown sender -> Ask user.
- **Priority Inference**:
  - **P0**: contains "URGENT" or deadline < 48h
  - **P1**: deadline < 1 week, or collaborator request
  - **P2**: deadline < 2 weeks, or general request
  - **P3**: no deadline, administrative
- **Inter-workflow Links**:
  - Full task extraction with attachments -> `[[email-capture]]`
  - Drafting replies -> `[[email-reply]]`

#### 4. Catalogue Updates in `plugins/pkb/workflows/INDEX.md`

- Update routing tree to route email triage asks to `[[wf-email-triage]]`.
- Update obligation templates table in `plugins/pkb/workflows/INDEX.md` to include `wf-email-triage`.

#### 5. Verification Method & Test Script (`tests/test_wf_email_triage.py`)

Create independent pytest script `tests/test_wf_email_triage.py` that verifies:

1. File existence: `plugins/pkb/workflows/wf-email-triage.md`.
2. Frontmatter validity: YAML parses cleanly; contains required keys `id`, `kind`, `category`, `description`, `requires`, `pairs-with`, `permalink`.
3. Permalink match: `permalink == "wf-email-triage"`.
4. Index wiring: `plugins/pkb/workflows/INDEX.md` contains `wf-email-triage`.
5. Build output verification: Running `python -m build.build` packages `dist/pkb-claude/workflows/wf-email-triage.md` and `dist/pkb-agy/workflows/wf-email-triage.md`.

---

## 2. Requirement R2: Fix Dangling Plugin References (`aops_4bc0dfea`)

### 2.1 Objective & Acceptance Criteria

- **Objective**: Resolve divergence between source and distribution by fixing or removing dangling `/email` references in the shipped plugin set.
- **Acceptance Criteria**:
  - A search (e.g., `grep`) confirms there are no longer any dangling `/email` references in the shipped plugin set.

### 2.2 Forensic Findings & Analysis

- **Source Inspection (`plugins/`)**:
  - Analyzed all 7 plugin source directories (`plugins/pkb`, `plugins/ida`, `plugins/orchestrate`, `plugins/rbg`, `plugins/ts`, `plugins/tools`, `plugins/aops-debug`).
  - Ran exact string grep for `/email` across `plugins/`.
  - Result: No occurrences of `/email` slash command exist in the source plugins.
- **Distribution Inspection (`dist/`)**:
  - Executed `uv run python -m build.build` to assemble plugin distributions.
  - Searched `dist/` for `/email`.
  - Result: No occurrences of `/email` slash command exist in generated distributions.
- **Git History Forensics**:
  - Commit `a2e8d94f`: Historical `/email` skill merged into `email-triage` and `email-capture` workflows.
  - Commit `77d0958c`: Legacy `/email` command merged into workflow components.

### 2.3 Proposed Fix & Verification Strategy

1. **Verification Test Script**: Add a dedicated automated test in `tests/test_dangling_email_refs.py` (or `tests/test_plugin_manifests.py`) that performs a search over all `.md`, `.json`, `.toml`, `.py` files in `plugins/` and built `dist/` outputs.
2. **Assertion Rule**: The test asserts that zero instances of `/email` slash command references exist in any shipped plugin file.
3. **Workflow Reference Hygiene**: Ensure that any new documentation or workflow components added for R1 use canonical wikilinks (`[[wf-email-triage]]`, `[[email-capture]]`, `[[email-reply]]`) and do not introduce dangling `/email` slash command references.

---

## 3. Implementation Action Plan

| Task   | File Path                                  | Modification Summary                                                                                              |
| ------ | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| **R1** | `plugins/pkb/workflows/wf-email-triage.md` | Create reusable `wf-*` component with `id: wf-email-triage` and frontmatter.                                      |
| **R1** | `plugins/pkb/workflows/INDEX.md`           | Update routing tree & table to reference `[[wf-email-triage]]`.                                                   |
| **R1** | `tests/test_wf_email_triage.py`            | Create independent test script to verify `wf-email-triage.md` schema, presence, and build distribution inclusion. |
| **R2** | `tests/test_dangling_email_refs.py`        | Create test script verifying 0 dangling `/email` references in `plugins/` and `dist/`.                            |

---

## 4. Evidence & Verification Log

- `view_file` on `/workspace/ORIGINAL_REQUEST.md`: Confirmed R1 and R2 scope and acceptance criteria.
- `view_file` on `plugins/pkb/workflows/process/email-triage.md`: Inspected existing process template.
- `view_file` on `plugins/pkb/workflows/INDEX.md`: Confirmed workflow library structure and routing.
- `run_command` `uv run python -m build.build`: Confirmed build execution and distribution directory structure.
- `run_command` `git log -S /email`: Traced history of `/email` command deprecation/merge into workflows.
