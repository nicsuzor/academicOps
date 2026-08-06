# Forensic Audit Report — Milestone R2: Persistence Verification & Defaults

**Work Product**: Milestone R2 (`lib/polecat/cli.py`, `lib/polecat/env_contract.py`, and `tests/polecat/`)  
**Profile**: General Project  
**Integrity Mode**: Development (from `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**

---

## Forensic Audit Verdict

```markdown
## Forensic Audit Report

**Work Product**: Milestone R2 (`lib/polecat/cli.py`, `lib/polecat/env_contract.py`, `tests/polecat/`)
**Profile**: General Project
**Verdict**: CLEAN

### Phase Results
- [Hardcoded test results check]: PASS — No hardcoded test strings, dummy constants, or fake return values found in production code.
- [Facade detection]: PASS — Implementation of `_verify_transcript_created`, input sanitization, and `write_run_record` contains genuine, functional logic.
- [Pre-populated artifact detection]: PASS — No pre-existing test output artifacts or logs were present in the repository prior to testing.
- [Behavioral verification & test suite execution]: PASS — 123 unit tests pass cleanly in pytest (`123 passed, 9 skipped`).
- [Dependency & mock bypass check]: PASS — Test mocks are standard pytest fixtures and isolate environment calls appropriately without bypassing implementation logic.
- [Test file authenticity]: PASS — Test suites under `tests/polecat/` accurately test non-empty line counting, transcript byte validation, path sanitization, and degraded status handling.
```

---

## 1. Observation

Direct observations from forensic inspection and empirical execution:

1. **`lib/polecat/cli.py`**:
   - `_verify_transcript_created(session_dir: Path)` scans `session_dir` via `_transcript_paths(session_dir)` (matching UUID format `<uuid>.jsonl` or `agy-brain/*/transcript*.jsonl`).
   - Opens each discovered transcript, measures `st_size`, and counts non-empty lines (`if line.strip(): total_event_count += 1`).
   - Returns a structured dictionary containing `found` (bool), `path` (str), `bytes` (int), `count` (int), `transcript_path` (str), `transcript_bytes` (int), and `event_count` (int).
   - If size <= 0, no transcripts found, or event_count == 0, returns `found: False`, `transcript_bytes: None`, `event_count: 0`.
   - `write_run_record()` evaluates `is_agent_cmd = agent and agent.lower() in ("claude", "agy")`. If `is_agent_cmd` and transcript is missing/empty/0-event, sets `status = "degraded"` and appends `transcript_missing` to `degraded[]`.
   - `_sanitize_path_component(val, default)` uses regex `re.sub(r"[^a-zA-Z0-9_.-]", "_", str(val))` and `.strip("._-")` to prevent directory traversal or invalid container name characters.

2. **`lib/polecat/env_contract.py`**:
   - Added `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` to `CONTAINER_SET_ENV`.
   - Removed `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"` from `FORWARDED_ENV` to prevent duplicate `-e` flags in container dispatch.

3. **`tests/polecat/`**:
   - `test_cli_sanitization.py`: Validates path sanitization edge cases (`../..`, unsafe characters, custom defaults).
   - `test_container_config.py`: Validates container configuration, rules mounts, loopback rehosting, and default agent teams env flag propagation.
   - `test_run_record.py`: Validates schema compliance, clean runs, non-zero exits, delivery guard failures, and degraded status on missing/0-byte transcripts.
   - `test_transcript_persistence.py`: Validates transcript discovery, substantive transcript selection, seed confirmation, zero-byte degradation, and opt-in E2E container persistence.

4. **Test Suite Execution**:
   - Executed `/home/worker/.venv/bin/pytest tests/polecat/` -> `123 passed, 9 skipped in 1.45s`.

---

## 2. Logic Chain

1. **Empirical Verification of Event Counting and Degradation**:
   - Inspected `_verify_transcript_created` line-by-line. Confirmed that line counts are calculated dynamically from non-empty line reads (`if line.strip(): total_event_count += 1`).
   - Verified that `write_run_record` checks both `is_agent_cmd` and `transcript_missing`. If an agent container completes exit 0 without writing events, it correctly records `status = "degraded"` and `transcript_missing` in `degraded[]`.
   - Verified non-agent commands (`shell`, `sleep`) do not degrade on absent transcripts, matching specifications.

2. **Absence of Prohibited Patterns**:
   - No hardcoded test outputs or fixed return values match specific test parameters.
   - No fake facades or placeholder returns exist in `cli.py` or `env_contract.py`.
   - Test files test authentic behavior with temporary directories (`tmp_path`) and isolated subprocess mocks.

3. **Sanitization and Environment Default Verification**:
   - Verified regex pattern in `_sanitize_path_component` cleans path traversal tokens (`..`, `/`, `\`) and strips leading/trailing punctuation.
   - Verified default environment injection of `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` via `docker_env_args()` and `get_env_forwards()`.

---

## 3. Caveats

- **Opt-in E2E Tests**: The E2E test `test_a_real_claude_container_persists_a_transcript_to_the_host` requires `POLECAT_E2E=1`, a local Docker daemon, built `aops-crew:latest` image, and valid credentials. Under unit test runs without `POLECAT_E2E=1`, it skips cleanly as designed.

---

## 4. Conclusion

Milestone R2 implementations in `lib/polecat/cli.py`, `lib/polecat/env_contract.py`, and `tests/polecat/` are authentic, fully tested, and free of integrity violations. The forensic verdict is **CLEAN**.

---

## 5. Verification Method

To independently verify this audit:

1. Run the test suite:
   ```bash
   /home/worker/.venv/bin/pytest tests/polecat/
   ```
   *Expected output*: `123 passed, 9 skipped in ~1.5s`

2. Verify path sanitization and transcript line event counting interactively:
   ```bash
   /home/worker/.venv/bin/python -c "
   from lib.polecat.cli import _sanitize_path_component, _verify_transcript_created
   from pathlib import Path
   import tempfile

   assert _sanitize_path_component('../../etc/passwd') == 'etc_passwd'

   with tempfile.TemporaryDirectory() as td:
       p = Path(td)
       f = p / '6912ac2b-781f-4515-94d5-d883e2b94a54.jsonl'
       f.write_text('{\"event\": 1}\n\n{\"event\": 2}\n')
       res = _verify_transcript_created(p)
       assert res['found'] is True
       assert res['event_count'] == 2
       assert res['transcript_bytes'] == f.stat().st_size
   print('Verification complete: ALL PASSED')
   "
   ```
