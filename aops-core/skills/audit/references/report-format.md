---
name: audit-report-format
category: reference
description: Template and format specification for simplified audit reports
---

# Audit Report Format

Output a structured report with YAML frontmatter:

```markdown
---
title: Framework Audit Report
date: YYYY-MM-DD HH:MM:SS
duration_minutes: N
summary:
  indices_updated: N
  acceptance_tests_run: N
  acceptance_tests_passed: N
  issues_found: N
status: PASS | ISSUES_FOUND
---

# Audit Report

## Executive Summary

High-level findings and overall status.

## Phase 1: Structure Audit

- Files missing from INDEX.md: [list]
- Stale entries removed from INDEX.md: [list]
- Broken wikilinks: [list]

## Phase 2: Index Curation

Status of updated indices:

- [ ] AXIOMS.md
- [ ] HEURISTICS.md
- [ ] SKILLS.md
- [ ] WORKFLOWS.md
- [ ] enforcement-map.md

## Phase 3: Documentation Accuracy

- README.md flowchart status: [Updated/No change]
- README.md tables status: [Updated/No change]

## Phase 4: Acceptance Tests

| Test ID | Description | Status | Notes |
| ------- | ----------- | ------ | ----- |
| v1.1-x  | ...         | PASS   | ...   |
| v1.1-y  | ...         | FAIL   | ...   |

**Summary**: N passed, M failed.

## Human Review Queue

List of items requiring manual intervention:
- Broken wikilinks that couldn't be auto-resolved.
- Acceptance test failures.
- Other discrepancies.
```

## Validation Criteria

- INDEX.md accurately reflects the filesystem.
- All root-level index files are up to date.
- README.md flowchart matches the current hook architecture.
- All acceptance tests in `tests/acceptance/` have been executed and recorded.
