# Phase 0 Survey Handoff Report — Explorer 2: Polecat Launcher Mechanics, Persistence Verification & Defaults

**Author**: Explorer 2  
**Date**: 2026-08-06  
**Target Requirements**: R1 & R2 (Polecat Launcher Mechanics, Transcript Verification, Environment Contracts & E2E Tests)

---

## 1. Observation

Direct observations from examining the codebase under `/workspace/lib/polecat/` and `/workspace/tests/polecat/`:

### 1.1 `lib/polecat/cli.py` — Parameter Handling & Path Construction
- **Lines 1159, 1162**:
  ```python
  @click.option("--project", "-p", help="Project name, resolved via local.yaml paths.")
  @click.option("--session-name", "-s", help="Session id; names the log and clone directories.")
  ```
- **Lines 1189–1192**:
  ```python
  session_id = session_name or f"session-{uuid.uuid4().hex[:8]}"
  session_date = datetime.now().strftime("%Y%m%d")
  session_dir = sessions_base / "logs" / session_date / session_id / (project or "workspace")
  ```
- **Line 1216**:
  ```python
  container_name = f"polecat-{session_id}"
  ```
- **Line 566** in `resolve_isolated_workspace`:
  ```python
  clone_path = clones_dir / session_id
  ```
- **Line 784** in `_resolve_workspace`:
  ```python
  proj_path = load_local_overlay(polecat_home).get("paths", {}).get(project)
  ```
- **Observation**: `project` and `session_name` strings are accepted directly from CLI options without input sanitization or path traversal filtering.

### 1.2 `lib/polecat/cli.py` — Transcript Verification & `run.json` Schema
- **Lines 400–434**: `transcript_evidence(session_dir)` locates transcripts via `_transcript_paths(session_dir)` (lines 368–398) and returns:
  ```python
  {"found": bool, "path": str | None, "bytes": int | None, "count": int}
  ```
  It does not calculate `event_count` (line count of event records in `.jsonl`), nor does it explicitly flag `"transcript_missing"` as a string key or set `status: "degraded"` when exit code is 0 but transcript is 0 bytes or missing.
- **Lines 1017–1110**: `write_run_record()` builds `run.json` record:
  - Line 1051: `transcript = transcript_evidence(session_dir)`
  - Lines 1073–1080: `status` is derived as `"killed"`, `"failed"`, `"delivery_guard_failed"`, or `"success"`. Missing transcript does not override `"success"` to `"degraded"`.
- **Lines 1327–1346**: `write_run_record()` is called inside the `finally:` block of `run()`.

### 1.3 `lib/polecat/env_contract.py` — Environment Contracts
- **Lines 44–67**: `FORWARDED_ENV` includes `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"` at line 65.
- **Lines 86–88**:
  ```python
  CONTAINER_SET_ENV = {
      "CLAUDE_ENV_FILE": "/tmp/aops-session.env",
  }
  ```
- **Lines 91–106**: `docker_env_args(names=None)` emits `-e NAME` for forwarded variables and `-e NAME=VALUE` for `CONTAINER_SET_ENV`.
- **Observation**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is only forwarded if present in the host environment; it is not currently set to `"1"` by default in `CONTAINER_SET_ENV`.

### 1.4 `tests/polecat/` — Test Suite & E2E Coverage
- Existing test suite contains 11 modules: `test_cli_seed_verification.py`, `test_container_config.py`, `test_container_invocation.py`, `test_container_smoke.py`, `test_credential_claims.py`, `test_delivery_guard.py`, `test_run_record.py`, `test_sessions_root.py`, `test_setup_staging.py`, `test_transcript_persistence.py`, `test_workspace_isolation.py`.
- Running `uv run --group dev pytest tests/polecat/` produces:
  `102 passed, 8 skipped in 4.64s`.
- In `tests/polecat/test_transcript_persistence.py` (lines 381–438), `test_a_real_claude_container_persists_a_transcript_to_the_host` is decorated with `@pytest.mark.e2e` and uses fixture `live_claude_dispatch` (lines 321–379) which skips unless `POLECAT_E2E == "1"`, docker is reachable, and `POLECAT_IMAGE` is built.
- `pyproject.toml` (line 293) registers the marker: `e2e: end-to-end tests requiring live infra (POLECAT_E2E=1 to run)`.

---

## 2. Logic Chain

### 2.1 Project & Session Name Sanitization (R1)
1. **From Observation 1.1**: `project` and `session_name` (assigned to `session_id`) are concatenated into filesystem paths (`sessions_base / "logs" / session_date / session_id / (project or "workspace")` and `clones_dir / session_id`) and Docker container names (`polecat-{session_id}`).
2. **Step**: If input contains path traversal characters (`/`, `\`, `..`), whitespace, unescaped characters, or option flags, it alters path construction.
3. **Inference**: An un-sanitized `session_name` like `../../tmp/exploit` will break out of `$AOPS_SESSIONS/logs/YYYYMMDD/` and corrupt directory structure on the host or fail Docker container creation due to illegal container names.
4. **Conclusion**: Introduce a helper function `_sanitize_path_component(value: str | None, default: str = "") -> str` using regex `re.sub(r"[^a-zA-Z0-9_.-]", "_", val)` and stripping leading/trailing separators. Apply sanitization to `project` and `session_name` at the top of `run()` before any path or container name construction occurs.

### 2.2 Transcript Persistence Verification & `run.json` Enhancements (R2)
1. **From Observation 1.2**: `transcript_evidence()` returns `found`, `path`, `bytes`, and `count`. However, Requirement R2 requires:
   - A dedicated `_verify_transcript_created(session_dir, agent_cmd)` call prior to writing `run.json`.
   - Recording explicit metadata fields: `transcript_path`, `transcript_bytes`, `event_count`.
   - If 0 bytes or missing: flag `"transcript_missing"` in `degraded[]` and set `status: "degraded"`.
2. **Inference**: A container exiting with code 0 that wrote an empty 0-byte transcript file currently gets `status: "success"`.
3. **Conclusion**:
   - Add `_verify_transcript_created(session_dir: Path)` which opens discovered `.jsonl` files and counts line events (`event_count`).
   - Enhance `transcript_evidence()` / `write_run_record()` to populate `transcript_path`, `transcript_bytes`, and `event_count` in `run.json`.
   - Update `write_run_record()` status resolution logic: if `exit_code == 0` and delivery guard passed, but transcript is missing or `bytes == 0` or `event_count == 0` (for agent commands `claude`/`agy`), set `status = "degraded"` and append `{"what": "transcript_missing", "why": "no non-empty agent conversation transcript was persisted"}` to `degraded[]`.

### 2.3 Environment Contract Defaults (R2)
1. **From Observation 1.3**: `CONTAINER_SET_ENV` currently only contains `{"CLAUDE_ENV_FILE": "/tmp/aops-session.env"}`. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is in `FORWARDED_ENV`.
2. **Inference**: If the host environment does not export `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, containers launched via `polecat run` or Makefile targets run without agent teams enabled.
3. **Conclusion**: Move or add `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` into `CONTAINER_SET_ENV` in `lib/polecat/env_contract.py`. This ensures it is passed as `-e CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` by default across all invocation paths (`cli.py` and Makefile `docker_env_args`).

### 2.4 Opt-in E2E Test Re-introduction & Assertion Verification (R2)
1. **From Observation 1.4**: An `@pytest.mark.e2e` test `test_a_real_claude_container_persists_a_transcript_to_the_host` already exists in `tests/polecat/test_transcript_persistence.py`.
2. **Inference**: The existing test verifies basic transcript creation, but needs to be updated to assert the new Requirement R2 metadata fields (`transcript_path`, `transcript_bytes`, `event_count`) and verify that zero-byte/missing transcripts produce `status: "degraded"` with `"transcript_missing"` in `degraded[]`.
3. **Conclusion**: Enhance `tests/polecat/test_transcript_persistence.py` and `tests/polecat/test_run_record.py` with test cases verifying both valid transcript persistence and degraded behavior when transcripts are missing/0-bytes under E2E and unit test conditions.

---

## 3. Caveats

- **Docker Daemon Availability**: E2E tests (`@pytest.mark.e2e`) require a local Docker daemon and a pre-built container image (`aops-crew:latest` or `$POLECAT_IMAGE`). Unit tests mock Docker subprocess calls and run without Docker.
- **Agent CLI Specific Transcript Layouts**: `claude` writes transcripts as `<uuid>.jsonl` at the root of `session_dir`, while `agy` writes under `agy-brain/<uuid>/.system_generated/logs/transcript*.jsonl`. `_transcript_paths()` handles both, but non-agent CLI dispatches (`shell`, `sleep`) legitimately write no transcripts.

---

## 4. Conclusion

The required changes for Requirements R1 & R2 in Phase 1 implementation are clearly scoped and directly supported by the codebase structure:

1. **`lib/polecat/cli.py`**:
   - Implement `_sanitize_path_component()` to sanitize `project` and `session_name` prior to path/container resolution.
   - Implement `_verify_transcript_created()` and update `write_run_record()` to set `transcript_path`, `transcript_bytes`, `event_count` in `run.json`, and set `status: "degraded"` + `"transcript_missing"` in `degraded[]` when transcripts are missing or zero bytes.
2. **`lib/polecat/env_contract.py`**:
   - Update `CONTAINER_SET_ENV` to include `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"`.
3. **`tests/polecat/`**:
   - Update unit and `@pytest.mark.e2e` integration tests in `test_run_record.py` and `test_transcript_persistence.py` to assert the new metadata schema, degraded handling, and agent teams env var propagation.

---

## 5. Verification Method

To verify these findings and subsequent implementations independently:

1. **Run Polecat Test Suite**:
   ```bash
   uv run --group dev pytest tests/polecat/
   ```
   *Expected outcome*: All unit tests pass cleanly (102+ tests).

2. **Verify Opt-in E2E Test Execution**:
   ```bash
   POLECAT_E2E=1 uv run --group dev pytest tests/polecat/test_transcript_persistence.py -m e2e
   ```
   *Expected outcome*: Runs the real container test (if Docker and credentials are set) or skips with explicit reason.

3. **Inspect Modified Files**:
   - `lib/polecat/cli.py`
   - `lib/polecat/env_contract.py`
   - `tests/polecat/test_run_record.py`
   - `tests/polecat/test_transcript_persistence.py`
