# Milestone R2 Handoff Report: Persistence Verification & Defaults

**Worker**: Worker 3 (Milestone R2)  
**Date**: 2026-08-06  
**Working Directory**: `/workspace/.agents/teamwork_preview_worker_r2/`  

---

## 1. Observation

Direct observations from examining and implementing changes in the codebase:

### 1.1 `lib/polecat/cli.py`
- Implemented `_verify_transcript_created(session_dir: Path)` helper which checks `.jsonl` transcript existence and counts non-empty line events (`event_count`).
- `_verify_transcript_created` returns a structured dictionary containing:
  ```python
  {
      "found": bool,
      "path": str | None,
      "bytes": int | None,
      "count": int,
      "transcript_path": str | None,
      "transcript_bytes": int | None,
      "event_count": int,
  }
  ```
- Updated `transcript_evidence(session_dir)` to delegate to `_verify_transcript_created(session_dir)`.
- Updated `write_run_record()` to:
  - Invoke `_verify_transcript_created(session_dir)` prior to writing `run.json`.
  - Populate `transcript_path`, `transcript_bytes`, and `event_count` inside the `transcript` object in `run.json`.
  - Check if `agent` is an agent command (`"claude"` or `"agy"`). If a transcript is 0 bytes or missing or has 0 event count for agent commands:
    - Sets `status = "degraded"` (when exit code is 0 and delivery guard passes).
    - Appends `{"what": "transcript_missing", "why": "no non-empty agent conversation transcript was persisted under the session directory"}` to `degraded[]`.
  - Non-agent commands (`"shell"`, `"sleep"`) do not degrade or populate `transcript_missing` when transcripts are absent.

### 1.2 `lib/polecat/env_contract.py`
- Added `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` to `CONTAINER_SET_ENV`.
- Removed `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"` from `FORWARDED_ENV` tuple to avoid duplicate entries in `docker_env_args()`.
- Container dispatches via `cli.py` (`cli.get_env_forwards()`) and Makefile targets (`docker_env_args()`) now automatically propagate `-e CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

### 1.3 `tests/polecat/`
- `tests/polecat/test_run_record.py`:
  - Updated `test_write_run_record_schema_and_keys` and `test_run_command_creates_run_json_on_clean_run` to include transcripts for clean run assertions.
  - Added unit tests:
    - `test_write_run_record_degraded_status_when_transcript_missing`
    - `test_write_run_record_degraded_status_when_transcript_zero_bytes`
    - `test_write_run_record_non_agent_no_degradation`
    - `test_transcript_metadata_structure`
- `tests/polecat/test_container_config.py`:
  - Added unit tests asserting default agent teams env var propagation:
    - `test_default_agent_teams_env_var_in_container_set_env`
    - `test_default_agent_teams_env_var_forwarded_by_default`
    - `test_default_agent_teams_env_var_in_docker_env_args`
- `tests/polecat/test_transcript_persistence.py`:
  - Updated deterministic tests (`test_polecats_own_jsonl_files_are_not_mistaken_for_a_transcript`, `test_transcript_evidence_names_the_substantive_transcript`, `test_run_record_names_the_transcript_a_run_persisted`, `test_a_run_that_persisted_nothing_is_not_indistinguishable_from_one_that_did`) to assert new transcript metadata fields (`transcript_path`, `transcript_bytes`, `event_count`) and degraded status handling.
  - Updated `@pytest.mark.e2e` `test_a_real_claude_container_persists_a_transcript_to_the_host` to assert `transcript_path`, `transcript_bytes`, and `event_count`.

---

## 2. Logic Chain

1. **Transcript Evidence & Verification**:
   - `_verify_transcript_created` scans discovered transcripts via `_transcript_paths(session_dir)`, finds the largest `.jsonl` file, measures its byte size, and counts valid non-empty lines (`event_count`).
   - If no valid transcript is present or size <= 0 or event_count == 0, `found` is set to `False` and metadata fields (`transcript_path`, `transcript_bytes`, `event_count`) reflect `None` / `0`.

2. **Degraded State & Run Record Ledger**:
   - Agent CLI containers (`claude` and `agy`) are expected to persist non-empty transcripts. If an agent command completes with exit code 0 but wrote an empty or missing transcript, marking `status = "degraded"` and recording `transcript_missing` in `degraded[]` prevents false-positive `"success"` records.
   - Shell and utility containers (`shell`, `sleep`) do not run agent CLIs, so absence of a transcript is normal and expected; their status remains `"success"`.

3. **Default Agent Teams Environment Variable**:
   - Including `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` in `CONTAINER_SET_ENV` ensures that every container invocation receives `-e CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` without requiring explicit host export.

---

## 3. Caveats

- **Opt-in E2E Test Prerequisites**: `test_a_real_claude_container_persists_a_transcript_to_the_host` marked `@pytest.mark.e2e` requires `POLECAT_E2E=1`, a reachable Docker daemon, local built image (`aops-crew:latest`), and valid Claude credentials. Under standard `pytest` invocations without `POLECAT_E2E=1`, the test skips cleanly.

---

## 4. Conclusion

Milestone R2 (Persistence Verification & Defaults) is fully implemented and verified:
- Transcript verification, line event counting, and metadata population are integrated in `lib/polecat/cli.py`.
- Missing/0-byte transcripts for agent commands set `status = "degraded"` and populate `transcript_missing` in `degraded[]`.
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS="1"` is default in `CONTAINER_SET_ENV`.
- Comprehensive unit and E2E test coverage updated under `tests/polecat/`.
- All 123 pytest unit tests pass cleanly.

---

## 5. Verification Method

Run the pytest suite to verify all unit tests pass:

```bash
/home/worker/.venv/bin/pytest tests/polecat/
```

*Expected output*:
`123 passed, 9 skipped in ~1.6s`

To run the opt-in E2E test when Docker and credentials are environment-ready:

```bash
POLECAT_E2E=1 /home/worker/.venv/bin/pytest tests/polecat/test_transcript_persistence.py -m e2e
```
