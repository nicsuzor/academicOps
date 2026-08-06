# Empirical Verification Report & Handoff — Milestone R1: Discovery & Launcher Path Sanitization

**Challenger**: Challenger 2 (Empirical Challenger / Critic / Specialist)  
**Working Directory**: `/workspace/.agents/teamwork_preview_challenger_r1_2/`  
**Date**: 2026-08-06  
**Verdict**: **REJECT**  

---

## 1. Observation

### 1.1 Standard Test Suite Execution
Executed standard test suite across transcript discovery and polecat CLI tests:
```bash
PYTHONPATH=/workspace/lib/py:/workspace/lib /home/worker/.venv/bin/pytest -o addopts="" tests/transcripts/ tests/polecat/
```
*Result*: **227 passed, 9 skipped in 5.57s**.

### 1.2 Subagent Exclusion Filter Flaw (`lib/py/transcripts/runner.py`)
Direct code inspection of `lib/py/transcripts/runner.py` reveals the following check in `find_session_files()`:
* Line 53 (`claude_dir` search): `and "subagents" not in p.parts`
* Line 69 (`agy_dirs` search): `and "subagents" not in p.parts`
* Line 82 & 90 (`logs_dir` search): `and "subagents" not in p.parts`

`p` is an absolute `Path` object representing the discovered file (e.g. `PosixPath('/workspace/subagents/sessions/logs/20260806/session-1/project/trunk.jsonl')`).

### 1.3 Empirical Stress Test Failure
Created empirical stress test suite at `/workspace/.agents/teamwork_preview_challenger_r1_2/test_stress_r1.py` and executed:
```bash
PYTHONPATH=/workspace/lib/py:/workspace/lib /home/worker/.venv/bin/pytest -o addopts="" /workspace/.agents/teamwork_preview_challenger_r1_2/test_stress_r1.py
```
*Results*: **2 FAILED, 5 PASSED**.

Verbatim error output from pytest:
```
___________________ test_stress_aops_sessions_in_subagents_directory ___________________
    def test_stress_aops_sessions_in_subagents_directory(tmp_path: Path) -> None:
        base_dir = tmp_path / "subagents" / "my_sessions"
        logs_dir = base_dir / "logs" / "20260806" / "session-1" / "project"
        logs_dir.mkdir(parents=True)
        session_file = logs_dir / "trunk-session.jsonl"
        shutil.copy(CLAUDE_FIXTURE, session_file)
        found = find_session_files(sessions_dir=base_dir)
>       assert session_file in found
E       AssertionError: Valid session file was excluded because base directory path contained 'subagents'!

__________________ test_stress_home_directory_containing_subagents __________________
    def test_stress_home_directory_containing_subagents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_home = tmp_path / "subagents" / "user"
        fake_claude = fake_home / ".claude" / "projects" / "my-project"
        fake_claude.mkdir(parents=True)
        session_file = fake_claude / "claude-session.jsonl"
        shutil.copy(CLAUDE_FIXTURE, session_file)
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        found = find_session_files()
>       assert session_file in found
E       AssertionError: Claude session file excluded because home dir contains 'subagents'! Found: []
```

---

## 2. Logic Chain

1. **Subagent Exclusion Mechanism**:
   * *Observation*: `find_session_files()` evaluates `"subagents" not in p.parts` where `p` is an absolute path.
   * *Reasoning*: `p.parts` contains every path segment from `/` down to the filename. If any ancestor directory in `$AOPS_SESSIONS`, `Path.home()`, or the workspace contains the segment `"subagents"` (e.g. `/home/user/subagents/academicOps` or `/tmp/subagents/sessions`), `"subagents"` is present in `p.parts`.
   * *Impact*: `"subagents" not in p.parts` evaluates to `False` for ALL files under that root, causing `find_session_files()` to silently discard every session transcript file without error or warning.

2. **Launcher Path Sanitization (`lib/polecat/cli.py`)**:
   * *Observation*: `_sanitize_path_component()` in `lib/polecat/cli.py` correctly strips leading/trailing `._-` and replaces invalid characters with `_`.
   * *Reasoning*: Empirically verified across path traversal attempts (`../../etc/passwd`), null bytes, whitespace, and option flag inputs (`-p --rm`). Sanitization is properly applied to `project` and `session_name` at entry in `run()`.

---

## 3. Caveats

* The launcher path sanitization logic (`_sanitize_path_component`) in `lib/polecat/cli.py` is sound and passes all stress tests.
* The issue is isolated to path filtering logic in `lib/py/transcripts/runner.py` where checking `p.parts` instead of `p.relative_to(search_root).parts` (or relative to `logs_dir` / `claude_dir`) creates a path false-positive vulnerability.

---

## 4. Conclusion & Verdict

**Verdict**: **REJECT**

Milestone R1 cannot be approved in its current state because `find_session_files()` suffers from a high-severity path filtering bug where any system or session repository path containing `"subagents"` completely breaks transcript discovery.

### Required Remediation:
In `lib/py/transcripts/runner.py`, update `find_session_files()` so that subagent directory filtering is relative to the search root (e.g., `not "subagents" in p.relative_to(search_root).parts`) rather than inspecting the full absolute path `p.parts`.

---

## 5. Verification Method

To verify the failure empirically, run:
```bash
PYTHONPATH=/workspace/lib/py:/workspace/lib /home/worker/.venv/bin/pytest -o addopts="" /workspace/.agents/teamwork_preview_challenger_r1_2/test_stress_r1.py
```
*Expected Result*: 2 tests fail (`test_stress_aops_sessions_in_subagents_directory` and `test_stress_home_directory_containing_subagents`).

---

## Adversarial Review Challenge Report

## Challenge Summary

**Overall risk assessment**: HIGH

## Challenges

### [HIGH] Challenge 1: Absolute Path Component Check for `subagents`

- **Assumption challenged**: Assuming `"subagents" not in p.parts` on an absolute path `p` will only match actual subagent subdirectories created under session trunks.
- **Attack scenario**: Deploy academicOps or `$AOPS_SESSIONS` inside any directory path that includes a folder named `subagents` (e.g. `/home/developer/subagents_workspace/academicOps`).
- **Blast radius**: Complete breakdown of transcript processing. 0 session transcripts will be discovered or rendered.
- **Mitigation**: Calculate relative path from the search root before checking directory parts: `rel_parts = p.relative_to(root_dir).parts; if "subagents" in rel_parts: ...`

## Stress Test Results

- `test_stress_aops_sessions_in_subagents_directory` -> AOPS_SESSIONS in directory named `subagents` -> Excludes all valid transcripts -> **FAIL**
- `test_stress_home_directory_containing_subagents` -> User home dir containing `subagents` -> Excludes all valid Claude transcripts -> **FAIL**
- `test_stress_subagent_filename_containing_subagents_word` -> Project named `subagents_project` -> Correctly included -> **PASS**
- `test_stress_subagents_directory_relative_to_logs` -> Standard subagent dir filtering -> Correctly excludes subagents -> **PASS**
- `test_stress_hooks_jsonl_variations` -> `-hooks.jsonl` filtering -> Correctly excludes hooks -> **PASS**
- `test_stress_sanitization_extreme_inputs` -> `_sanitize_path_component()` extreme inputs -> Correctly sanitizes -> **PASS**
- `test_stress_cli_sanitization_integration` -> Integration path traversal checks -> Correctly sanitizes -> **PASS**

## Unchallenged Areas

- Docker runtime execution — out of scope for R1 static launcher & transcript discovery unit tests (requires live Docker daemon).
