# Test Infrastructure Specification (TEST_INFRA.md)

## Executive Summary

This document defines the test architecture, methodology, feature inventory, coverage goals, and execution protocol for the opaque-box E2E test suite covering requirements **R1** through **R5** in the `academicOps` framework.

---

## 1. Feature Inventory & Mapping

| Req #     | Feature Description             | Assigned Component / Module                             | Test File Location                    | Target Behavior                                                                                                                                                             |
| --------- | ------------------------------- | ------------------------------------------------------- | ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R1**    | Email Triage Workflow Component | `plugins/pkb/workflows/wf-email-triage.md` & `INDEX.md` | `tests/test_wf_email_triage.py`       | Frontmatter schema (`id: wf-email-triage`, `kind: obligation`, `permalink: wf-email-triage`, `requires: [task-tracking]`), routing index, dist artifact packaging.          |
| **R2**    | Fix Dangling Plugin References  | `plugins/` & `dist/` shipped plugin set                 | `tests/test_dangling_plugin_refs.py`  | 0 dangling `/email` slash command references across all source plugins and build artifacts.                                                                                 |
| **R3**    | Fix list_tasks Timestamps       | `lib/py/transcripts/domain/tasks.py`                    | `tests/test_list_tasks_timestamps.py` | Explicit ISO-8601 UTC timestamp serialization (`YYYY-MM-DDTHH:MM:SS.ffffff+00:00`) on task mutations; accurate `since`/`before` staleness filtering without mtime fallback. |
| **R4**    | Fix Due-date Bucketing          | `lib/py/transcripts/domain/time.py`                     | `tests/test_due_date_bucketing.py`    | Brisbane local date evaluation (`Australia/Brisbane`, UTC+10:00); correct bucketing across 10-hour boundary window (14:00-24:00 UTC).                                       |
| **R5**    | Clarify /daily Skill Status     | `lib/py/transcripts/domain/skills.py`                   | `tests/test_daily_skill_status.py`    | Retaining `deliberately_removed` status for retired `/daily` skill; preventing false positive `install_failure` or `missing` reports.                                       |
| **Cross** | Cross-Feature & E2E Suite       | Multi-module integration                                | `tests/test_e2e_integration_r1_r5.py` | End-to-end task lifecycles, build pipeline verification, cross-timezone task evaluation, ecosystem diagnostic sweeps.                                                       |

---

## 2. Test Architecture & Multi-Tier Methodology

The test suite is structured into four distinct test tiers to ensure complete coverage, isolation, and robustness:

### Tier 1: Feature Coverage (Happy Path)

- Validates the primary functional contract for each requirement under standard operating conditions.
- Verifies exact field values, return types, schema frontmatter, and file paths.

### Tier 2: Boundary & Corner Cases

- Exercises edge conditions, including:
  - **R1**: Invalid frontmatter, missing required keys, trailing slashes/whitespace.
  - **R2**: Unbuilt vs built `dist/` trees, code block escaping, separating bare slash commands from valid URLs or package names (`email_validator`).
  - **R3**: Tasks with `None` timestamps, sub-second comparisons, boundary timestamp equality in `since`/`before` filters, markdown formatting.
  - **R4**: Critical 10-hour boundary window (14:00:00 - 23:59:59 UTC / 00:00:00 - 09:59:59 AEST next day), month/year boundary transitions, invalid due date string parsing.
  - **R5**: Command variants (`/daily`, `daily`, `aops-core:daily`, `/daily-note-template`), active installed skills (`analyst`, `brief`), unknown non-existent skills.

### Tier 3: Cross-Feature Integration

- Tests interaction between multiple components:
  - Task mutation (`create_task`/`update_task`) + Brisbane timezone due date evaluation + `list_tasks` staleness range filtering.
  - Workflow obligations (`wf-email-triage`) paired with skill diagnostic status validation.

### Tier 4: Real-World Scenarios (End-to-End)

- Full build pipeline execution (`build_all`), packaging dist plugins, and scanning generated artifacts for reference cleanliness and workflow file presence.
- Multi-step task lifecycle transitioning across UTC midnight into Brisbane next-day local time.

---

## 3. Test Runner & Environment Protocol

### Python Environment

- Python version: `>= 3.11` (CPython 3.12.13)
- Virtual Environment: `/workspace/.venv`
- Invocation command:
  ```bash
  UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run pytest tests/
  ```

### Isolated Module Commands

To run individual requirement test modules:

```bash
# Requirement 1 (Email Triage Workflow Component)
UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run pytest tests/test_wf_email_triage.py

# Requirement 2 (Dangling Plugin References)
UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run pytest tests/test_dangling_plugin_refs.py

# Requirement 3 (list_tasks Timestamps)
UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run pytest tests/test_list_tasks_timestamps.py

# Requirement 4 (Due-date Bucketing)
UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run pytest tests/test_due_date_bucketing.py

# Requirement 5 (/daily Skill Status)
UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run pytest tests/test_daily_skill_status.py

# Cross-Feature & E2E Integration (Tiers 3 & 4)
UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run pytest tests/test_e2e_integration_r1_r5.py
```

---

## 4. Coverage Goals & Acceptance Criteria

1. **Pass Rate**: 100% pass rate across all 32 tests covering R1 to R5.
2. **No False Positives / Negatives**: Tests use authoritative expected output derivation and strict assertions.
3. **Build Artifact Validation**: Automated checks assert built `dist/` artifacts match source specifications.
