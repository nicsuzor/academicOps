# Final Milestone Gate Verification Handoff Report

**Reviewer**: Reviewer 2 (`teamwork_preview_reviewer_final_2`)\
**Roles**: Reviewer, Critic\
**Working Directory**: `/workspace/.agents/teamwork_preview_reviewer_final_2/`\
**Verdict**: `REQUEST_CHANGES`

---

## 1. Observation

Direct observations from codebase inspection, command execution, and test runs:

1. **R1-R5 Specific Test Suite**:
   - Command: `/workspace/.venv/bin/pytest tests/test_wf_email_triage.py tests/test_dangling_plugin_refs.py tests/test_list_tasks_timestamps.py tests/test_due_date_bucketing.py tests/test_daily_skill_status.py tests/test_e2e_integration_r1_r5.py`
   - Result: `35 passed in 2.38s` (100% pass rate for feature tests).

2. **Ruff Lint Check**:
   - Command: `UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run ruff check .`
   - Result: Exit code `1`. Output: `Found 17 errors.`
   - Violations:
     - `tests/test_dangling_email_refs.py:7:1` — `I001 [*] Import block is un-sorted or un-formatted`
     - `tests/test_dangling_email_refs.py:12:8` — `F401 [*] 'pytest' imported but unused`
     - `tests/test_dangling_plugin_refs.py:7:1` — `I001 [*] Import block is un-sorted or un-formatted`
     - `tests/test_e2e_integration_r1_r5.py:8:1` — `I001 [*] Import block is un-sorted or un-formatted`
     - `tests/test_e2e_integration_r1_r5.py:12:8` — `F401 [*] 'pytest' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:16:31` — `F401 [*] 'build.marketplace.load_marketplace_toml' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:18:5` — `F401 [*] 'SkillStatus' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:19:5` — `F401 [*] 'diagnose_skill' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:20:5` — `F401 [*] 'diagnose_skill_status' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:22:5` — `F401 [*] 'is_deliberately_removed' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:28:5` — `F401 [*] 'validate_task_timestamps' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:31:5` — `F401 [*] 'BRISBANE_TZ' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:35:5` — `F401 [*] 'format_iso_utc' imported but unused`
     - `tests/test_e2e_integration_r1_r5.py:129:5` — `F841 Local variable 'artifacts' is assigned to but never used`
     - `tests/test_wf_email_triage.py:7:1` — `I001 [*] Import block is un-sorted or un-formatted`
     - `tests/test_wf_email_triage.py:8:8` — `F401 [*] 'pytest' imported but unused`
     - `tests/test_wf_email_triage.py:12:31` — `F401 [*] 'load_marketplace_toml' imported but unused`

3. **Full Workspace Pytest Run**:
   - Command: `PYTHONPATH=lib/py /workspace/.venv/bin/pytest tests/ -o addopts=""`
   - Result: Exit code `1`. Output: `47 failed, 655 passed, 13 skipped, 2 xfailed, 17 errors in 68.81s`.
   - Root cause: Pre-existing file `/workspace/plugins/rbg/hooks/handlers.py` lines 323-328 has `HANDLERS` dictionary commented out (`# "Stop": [rule_check]`), breaking `test_rbg_stop_gate.py` and dependent hook tests.

4. **Acceptance Criteria R1-R5 Domain Code Verification**:
   - **R1 (Email Triage Workflow)**: Component file `/workspace/plugins/pkb/workflows/wf-email-triage.md` exists with required frontmatter (`id: wf-email-triage`, `kind: obligation`, `permalink: wf-email-triage`, `requires: [task-tracking]`), overview, classification rules, priority engine, post-triage steps; routed in `/workspace/plugins/pkb/workflows/INDEX.md` lines 43, 79, 142.
   - **R2 (Fix Dangling Plugin References)**: Zero dangling `/email` slash command references in `/workspace/plugins/` and `/workspace/dist/`. Handled cleanly in `test_dangling_plugin_refs.py`.
   - **R3 (Fix list_tasks Timestamps)**: Domain module `/workspace/lib/py/transcripts/domain/tasks.py` implements explicit ISO-8601 UTC timestamp serialization (`YYYY-MM-DDTHH:MM:SS.ffffff+00:00`), `validate_task_timestamps` eliminates `mtime` fallbacks, and `list_tasks` correctly filters by `since` and `before` range parameters.
   - **R4 (Fix Due-date Bucketing)**: Domain module `/workspace/lib/py/transcripts/domain/time.py` uses `ZoneInfo("Australia/Brisbane")` (`UTC+10:00`). `get_brisbane_today()`, `parse_due_date()`, and `bucket_due_date()` correctly handle the 10-hour boundary window (14:00-24:00 UTC / 00:00-10:00 AEST).
   - **R5 (Clarify /daily Skill Status)**: Domain module `/workspace/lib/py/transcripts/domain/skills.py` defines `SkillStatus.DELIBERATELY_REMOVED`, categorizing `/daily` and retired skills distinctly from `install_failure` and `missing`.

5. **Integrity & Adversarial Audit**:
   - Checked for facade implementations, mock overrides, hardcoded outputs, and self-certifying shortcuts.
   - Result: NO integrity violations found. The core logic in `time.py`, `tasks.py`, `skills.py`, and `wf-email-triage.md` is genuine, complete, and robust.

---

## 2. Logic Chain

1. Requirements R1 through R5 are functionally implemented with high quality:
   - R1: `wf-email-triage.md` meets schema standards and is integrated into `INDEX.md`.
   - R2: Source and dist plugins are clean of dangling `/email` slash command calls.
   - R3: `list_tasks` uses strict ISO-8601 UTC timestamps with zero filesystem `mtime` fallback.
   - R4: Due-date bucketing operates in Brisbane local time (`UTC+10:00`), eliminating the 10-hour mis-bucketing window.
   - R5: `/daily` skill misdiagnosis is clarified as `deliberately_removed`.
2. All 35 feature-specific tests in `tests/test_*.py` for R1-R5 pass 100%.
3. However, task requirement 2 specifies executing `uv run ruff check .` and `uv run pytest tests/`.
4. `uv run ruff check .` fails with 17 lint errors in the newly added test files.
5. `uv run pytest tests/` fails due to pre-existing commented out `HANDLERS` in `plugins/rbg/hooks/handlers.py`.
6. Therefore, while the core domain functionality (R1-R5) is correct and has no integrity violations, the task acceptance criteria require clean linting and test suite runs before gate approval.

---

## 3. Caveats

- `plugins/rbg/hooks/handlers.py` had `HANDLERS` commented out prior to this milestone branch; fixing it would require editing code outside the feature scope of R1-R5.
- The 17 lint errors in `tests/` are safe auto-fixable formatting/unused-import issues (`uv run ruff check --fix .`).

---

## 4. Conclusion & Verdict

**Verdict**: `REQUEST_CHANGES`

**Rationale**:

- **Major Finding 1 (Lint Violations)**: `uv run ruff check .` fails with 17 errors across 4 newly added test files. Running `uv run ruff check --fix .` resolves 16 of the 17 errors, with 1 unused variable (`artifacts` in `tests/test_e2e_integration_r1_r5.py:129`) requiring manual removal.
- **Major Finding 2 (Full Test Suite Execution)**: `uv run pytest tests/` fails on `tests/test_rbg_stop_gate.py` and hook test files due to disabled `HANDLERS` in `plugins/rbg/hooks/handlers.py`.

---

## 5. Verification Method

To independently verify this report:

1. **Feature Test Suite**:
   ```bash
   /workspace/.venv/bin/pytest tests/test_wf_email_triage.py tests/test_dangling_plugin_refs.py tests/test_list_tasks_timestamps.py tests/test_due_date_bucketing.py tests/test_daily_skill_status.py tests/test_e2e_integration_r1_r5.py
   ```
   _Expected_: 35 passed.

2. **Ruff Check**:
   ```bash
   UV_PROJECT_ENVIRONMENT=/workspace/.venv uv run ruff check .
   ```
   _Expected_: 17 lint errors reported.

3. **Full Pytest Suite**:
   ```bash
   PYTHONPATH=lib/py /workspace/.venv/bin/pytest tests/ -o addopts=""
   ```
   _Expected_: Failures reported in `test_rbg_stop_gate.py`.
