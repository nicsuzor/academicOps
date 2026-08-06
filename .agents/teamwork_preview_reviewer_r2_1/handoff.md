# Milestone R2 Review & Handoff Report: Persistence Verification & Defaults

**Reviewer**: Reviewer 1 (Milestone R2)  
**Date**: 2026-08-06  
**Working Directory**: `/workspace/.agents/teamwork_preview_reviewer_r2_1/`  
**Verdict**: **APPROVE**

---

## 1. Observation

Direct observations from code inspection and test execution:

### 1.1 `_verify_transcript_created` (`lib/polecat/cli.py:400-452`)
- `_verify_transcript_created(session_dir: Path)` accurately resolves transcript paths via `_transcript_paths(session_dir)`.
- It iterates through matching `.jsonl` transcripts, computes file byte sizes (`stat().st_size`), and counts non-empty event lines (`total_event_count`).
- If no transcript is found, or if size <= 0, or if `total_event_count == 0`, it returns `found: False`, `transcript_path: None`, `transcript_bytes: None`, `event_count: 0`.
- If valid events are present, it returns `found: True`, `transcript_path: str(largest)`, `transcript_bytes: largest_size`, `event_count: total_event_count`.
- Legacy keys (`path`, `bytes`, `count`) are preserved alongside the new keys (`transcript_path`, `transcript_bytes`, `event_count`).

### 1.2 `write_run_record` & Degraded Handling (`lib/polecat/cli.py:1098-1170`)
- `write_run_record()` calls `_verify_transcript_created(session_dir)` and records `transcript_path`, `transcript_bytes`, and `event_count` inside the `transcript` object in `run.json`.
- For agent commands (`"claude"` or `"agy"`), if `transcript_missing` is true (missing transcript, 0 bytes, or 0 event count):
  - Adds `{"what": "transcript_missing", "why": "no non-empty agent conversation transcript was persisted under the session directory"}` to `degraded[]`.
  - Sets `status = "degraded"` when exit code is 0 and delivery guard passes.
- Non-agent commands (`"shell"`, `"bash"`, `"sleep"`) do not trigger `transcript_missing` degradation.

### 1.3 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` Default (`lib/polecat/env_contract.py:84-88`)
- Added `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` to `CONTAINER_SET_ENV`.
- Removed `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"` from `FORWARDED_ENV` to prevent duplicate flag generation in `docker_env_args()`.
- Container dispatches and Makefile targets (`docker_env_args()`) automatically include `-e CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

### 1.4 Test Suite Execution (`/home/worker/.venv/bin/pytest tests/polecat/`)
- Command: `/home/worker/.venv/bin/pytest tests/polecat/`
- Result: **123 passed, 9 skipped** in 1.48s.
- Clean execution across all unit test modules in `tests/polecat/`.

---

## 2. Logic Chain

1. **Transcript Verification**:
   - `_verify_transcript_created` guarantees that empty files or files containing only whitespace/newlines are flagged as missing (`found: False`, `event_count: 0`), preventing false positive transcript recordings.

2. **Run Record Integrity**:
   - By populating `transcript_path`, `transcript_bytes`, and `event_count` in `run.json`, every run leaves verifiable proof of agent activity.
   - Flagging `status = "degraded"` and appending `transcript_missing` to `degraded[]` for 0-byte or absent agent transcripts cleanly prevents silent failures.

3. **Default Environment Propagation**:
   - Setting `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` in `CONTAINER_SET_ENV` ensures uniform default support for agent teams across container dispatches.

4. **Integrity & Quality Audit**:
   - No hardcoded test outputs, facade implementations, or integrity violations were detected.

---

## 3. Caveats

- **Opt-in Live Container E2E Test**: `test_a_real_claude_container_persists_a_transcript_to_the_host` in `test_transcript_persistence.py` requires `POLECAT_E2E=1`, a live Docker daemon, local container image, and Claude credentials. It skipped as expected during offline unit test execution (part of the 9 skipped tests).

---

## 4. Conclusion

**Verdict**: **APPROVE**

Worker 3's implementation for Milestone R2 meets all specified requirements:
1. `_verify_transcript_created(session_dir)` correctly checks `.jsonl` transcript existence and line event count (`event_count`).
2. `write_run_record()` accurately logs `transcript_path`, `transcript_bytes`, and `event_count` in `run.json`, and sets `status = "degraded"` + `"transcript_missing"` in `degraded[]` if missing or 0 bytes for agent commands.
3. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set by default in `CONTAINER_SET_ENV`.
4. Test suite (`tests/polecat/`) passes completely (123 passed, 9 skipped).

---

## 5. Verification Method

To independently verify the test suite:

```bash
/home/worker/.venv/bin/pytest tests/polecat/
```

*Expected output*: `123 passed, 9 skipped in ~1.5s`

---

## Review Summary & Verified Claims

| Claim / Verification Item | Verification Method | Status |
|---|---|---|
| `_verify_transcript_created` line event counting & path verification | Code inspection & `test_transcript_metadata_structure`, `test_transcript_evidence_names_the_substantive_transcript` | PASS |
| `write_run_record` degraded status & `transcript_missing` ledger | Code inspection & `test_write_run_record_degraded_status_when_transcript_missing`, `test_write_run_record_degraded_status_when_transcript_zero_bytes` | PASS |
| Non-agent command status non-degradation | Code inspection & `test_write_run_record_non_agent_no_degradation` | PASS |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `CONTAINER_SET_ENV` | Code inspection & `test_default_agent_teams_env_var_in_container_set_env`, `test_default_agent_teams_env_var_in_docker_env_args` | PASS |
| Pytest suite execution | `/home/worker/.venv/bin/pytest tests/polecat/` | PASS (123 passed, 9 skipped) |
