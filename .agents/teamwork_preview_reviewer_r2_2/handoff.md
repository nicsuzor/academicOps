# Reviewer Handoff Report — Milestone R2: Persistence Verification & Defaults

**Reviewer**: Reviewer 2 (`reviewer_r2_2`)  
**Roles**: Reviewer, Critic  
**Date**: 2026-08-06  
**Working Directory**: `/workspace/.agents/teamwork_preview_reviewer_r2_2/`  
**Verdict**: **APPROVE**

---

## 1. Review Summary

- **Verdict**: **APPROVE**
- **Integrity Status**: PASS — No hardcoded test results, facade implementations, or bypasses detected.
- **Test Results**: All 123 unit tests under `tests/polecat/` passed cleanly (9 skipped for opt-in E2E or missing optional preconditions). All 170 unit tests across `tests/` passed cleanly.

---

## 2. Findings

### Minor Finding 1: Line Event Count Accumulation Across Resumed Session Transcripts
- **What**: In `_verify_transcript_created(session_dir)`, when multiple transcripts exist in `session_dir` (e.g. in a resumed session), `total_event_count` accumulates non-empty line events across *all* matching `.jsonl` transcripts, while `transcript_path` and `transcript_bytes` reflect only the *largest* single transcript.
- **Where**: `lib/polecat/cli.py`, lines 415–430.
- **Why**: For single-transcript runs (the primary pattern), `event_count` exactly matches the file's line events. In multi-transcript sessions, `event_count` represents total session line events across all files rather than only the largest file.
- **Suggestion**: This is harmless for persistence verification since any non-empty transcript proves agent conversation activity. If per-file event accounting is ever desired, `event_count` could be calculated for `largest` specifically.

---

## 3. Verified Claims

1. **Claim**: `_verify_transcript_created(session_dir)` checks `.jsonl` transcript existence, byte size, and non-empty line event count (`event_count`).
   - *Verification method*: Inspected `lib/polecat/cli.py` (lines 400–453). Tested empty, missing, whitespace-only, valid, and multi-file transcript scenarios.
   - *Result*: **PASS**

2. **Claim**: `write_run_record()` logs `transcript_path`, `transcript_bytes`, and `event_count` in `run.json`, setting `status = "degraded"` and appending `"transcript_missing"` to `degraded[]` if missing/0 bytes/0 events for agent commands (`claude`, `agy`).
   - *Verification method*: Inspected `lib/polecat/cli.py` (lines 1101–1141). Verified unit tests `test_write_run_record_degraded_status_when_transcript_missing`, `test_write_run_record_degraded_status_when_transcript_zero_bytes`, and `test_write_run_record_non_agent_no_degradation` in `tests/polecat/test_run_record.py`.
   - *Result*: **PASS**

3. **Claim**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set by default in `CONTAINER_SET_ENV` and propagated through `docker_env_args()` and `get_env_forwards()`.
   - *Verification method*: Inspected `lib/polecat/env_contract.py` (lines 85–88, 98–107) and `lib/polecat/cli.py` (line 303). Verified unit tests in `tests/polecat/test_container_config.py`.
   - *Result*: **PASS**

4. **Claim**: Unit test suite under `tests/polecat/` runs cleanly without regressions.
   - *Verification method*: Executed `/home/worker/.venv/bin/pytest tests/polecat/ -o addopts=""`.
   - *Result*: **PASS** (123 passed, 9 skipped in 2.05s).

---

## 4. Adversarial Review & Stress Testing

### Challenge Summary
- **Overall risk assessment**: **LOW**

### Assumption Stress-Testing
1. **Assumption**: A missing or 0-byte or 0-event transcript indicates an agent CLI execution failure or dropped seed.
   - *Stress Scenario*: Agent CLI exits 0 without writing any conversation entries (e.g. process crashes before first turn).
   - *Result*: Correctly caught; `status` is set to `"degraded"` and `"transcript_missing"` is recorded in `degraded[]`.

2. **Assumption**: Non-agent commands (`shell`, `bash`, `sleep`) do not produce agent transcripts.
   - *Stress Scenario*: Execution of `polecat run shell` without transcript generation.
   - *Result*: Handled correctly; `status` remains `"success"` and no false degradation is reported.

3. **Assumption**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env var is not duplicated when forwarded.
   - *Stress Scenario*: Running container dispatches with `docker_env_args()` and `get_env_forwards()`.
   - *Result*: Variable was removed from `FORWARDED_ENV` and placed exclusively in `CONTAINER_SET_ENV`, preventing duplicate `-e` flag pollution.

### Stress Test Results

| Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| Agent run with missing transcript | `status: "degraded"`, `transcript_missing` in `degraded[]` | Matches expectation | **PASS** |
| Agent run with 0-byte transcript file | `status: "degraded"`, `transcript_missing` in `degraded[]` | Matches expectation | **PASS** |
| Agent run with 0 non-empty lines (whitespace file) | `status: "degraded"`, `transcript_missing` in `degraded[]` | Matches expectation | **PASS** |
| Shell command run with no transcript | `status: "success"`, no degradation | Matches expectation | **PASS** |
| Container env dispatch | Includes `-e CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | Matches expectation | **PASS** |

### Unchallenged Areas
- Opt-in live container E2E execution (`test_a_real_claude_container_persists_a_transcript_to_the_host` marked `@pytest.mark.e2e`): Requires live host Docker daemon and active API key credentials; skipped cleanly as expected when `POLECAT_E2E` is unset.

---

## 5. Coverage Gaps & Unverified Items

- **Coverage Gaps**: None identified for Milestone R2 scope.
- **Unverified Items**: Live container execution requires `POLECAT_E2E=1` and Docker daemon + API keys, which is skipped by design in offline unit test runs.

---

## 6. Logic Chain

1. **Code Inspection**:
   - `_verify_transcript_created` in `lib/polecat/cli.py` scans `session_dir` and `agy-brain` for `.jsonl` files matching `_CLAUDE_TRANSCRIPT_NAME` or `transcript*.jsonl`. It calculates file sizes and iterates through lines counting non-empty entries. If no valid file is found or line count is 0, it returns `found: False`.
   - `write_run_record` invokes `_verify_transcript_created` prior to saving `run.json`. If `agent` is an agent command (`claude` or `agy`) and `transcript_missing` is True, it flags `"transcript_missing"` in `degraded[]` and sets `status = "degraded"` (if exit code is 0).
   - `CONTAINER_SET_ENV` in `lib/polecat/env_contract.py` defines `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"`, ensuring every container dispatch receives this setting by default.

2. **Verification & Test Execution**:
   - Running the test suite `/home/worker/.venv/bin/pytest tests/polecat/ -o addopts=""` passes all 123 unit tests.
   - Independent inspection confirms no integrity violations, facade implementations, or hardcoded shortcuts exist.

---

## 7. Caveats

- **Opt-in E2E Test**: The live-container test `test_a_real_claude_container_persists_a_transcript_to_the_host` is marked `@pytest.mark.e2e` and skips cleanly when `POLECAT_E2E=1` is not set.

---

## 8. Conclusion

Milestone R2 (Persistence Verification & Defaults) has been implemented correctly, thoroughly, and without integrity violations or regressions.

Verdict: **APPROVE**

---

## 9. Verification Method

To independently verify the test suite:

```bash
/home/worker/.venv/bin/pytest tests/polecat/ -o addopts=""
```

*Expected output*: `123 passed, 9 skipped in ~2s`.
