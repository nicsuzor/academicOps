"""Tests for the agy `-t <task>` seed-verification/fail-fast path in cli.py.

Background: `polecat run agy -t <task_id>` has repeatedly reproduced as a
silent no-op — a container that starts, exits cleanly, and never actually
delivers the seeded `/pull <task_id>` prompt to agy (aops_5e7c6cc0,
aops_c40125ba). Because `subprocess.run(cmd)`'s return code was previously
discarded entirely, and there was no check that the run actually did
anything, a live/idle/dropped-seed container was indistinguishable from a
completed task at the `polecat run` process-exit level.

These tests cover the two things that changed:
1. `_seed_confirmed()` — the log-based verification heuristic.
2. `run()`'s retry-then-fail-fast wiring around it, and unconditional exit
   code propagation for every other invocation shape.
"""

import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from polecat import cli  # noqa: E402

# --------------------------------------------------------------------------
# _seed_confirmed
# --------------------------------------------------------------------------


def _write_transcript(session_dir, session_uuid, content):
    transcript_dir = Path(session_dir) / "agy-brain" / session_uuid / ".system_generated" / "logs"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    (transcript_dir / "transcript.jsonl").write_text(content)


def test_seed_confirmed_true_when_task_id_in_transcript(tmp_path):
    """Live-verified evidence location (2026-07-20 acceptance run): agy's
    conversation transcript under agy-brain/<uuid>/.system_generated/logs/
    transcript.jsonl contains the seeded prompt verbatim as the first
    USER_INPUT entry."""
    session_dir = tmp_path / "session"
    _write_transcript(
        session_dir,
        "04c2580a-bdb1-4a57-95ae-2d87a08071eb",
        '{"type":"USER_INPUT","content":"<USER_REQUEST>\\n/pull task_abc123\\n</USER_REQUEST>"}\n',
    )

    assert cli._seed_confirmed(session_dir, "task_abc123") is True


def test_seed_confirmed_false_when_no_evidence_anywhere(tmp_path):
    session_dir = tmp_path / "session"
    (session_dir / "agy-logs").mkdir(parents=True)
    # agy-cli.log exists (pre-created by run()) but empty — the exact
    # "CLI ready for user input, then nothing" signature.
    (session_dir / "agy-cli.log").write_text("")

    assert cli._seed_confirmed(session_dir, "task_abc123") is False


def test_seed_confirmed_false_when_task_id_absent_from_transcript(tmp_path):
    session_dir = tmp_path / "session"
    _write_transcript(
        session_dir,
        "some-uuid",
        '{"type":"USER_INPUT","content":"<USER_REQUEST>\\n/pull some_other_task\\n</USER_REQUEST>"}\n',
    )

    assert cli._seed_confirmed(session_dir, "task_abc123") is False


def test_seed_confirmed_checks_agy_cli_log_as_secondary_fallback(tmp_path):
    """agy-cli.log is diagnostic/telemetry, not the conversation — kept only
    as a secondary check in case future agy versions log differently."""
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)
    (session_dir / "agy-cli.log").write_text("...task_xyz789 /pull...\n")

    assert cli._seed_confirmed(session_dir, "task_xyz789") is True


# --------------------------------------------------------------------------
# run() — exit-code propagation + retry/fail-fast around the agy `-t` path
# --------------------------------------------------------------------------


def _base_mocks(monkeypatch, tmp_path):
    """Patch out everything docker/filesystem-heavy so `run()` is exercised
    as a pure control-flow unit. Each test installs its own `subprocess.run`
    and `_seed_confirmed` fakes afterwards.

    `get_env_forwards()` is stubbed to a fixed dummy dict — left unmocked it
    reads real host secrets (GH_TOKEN, GEMINI_API_KEY, etc.) into the `cmd`
    list `run()` builds, which any future assertion that inspects `cmd` (e.g.
    on failure, via pytest's assertion introspection) would print straight
    into the test/CI log. Do not remove this without confirming no test in
    this file ever touches the built `cmd`/`inner_cmd`."""
    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    monkeypatch.setattr(cli, "load_config", lambda: {})
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setattr(cli, "setup_staging", lambda staging_dir, pkb_url: None)
    monkeypatch.setattr(cli, "get_env_forwards", lambda: {"DUMMY_TEST_ENV": "1"})
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("AOPS", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)


def test_non_agy_run_propagates_nonzero_exit(tmp_path, monkeypatch):
    """A plain `claude` dispatch that fails must not report success — this
    was previously masked because subprocess.run()'s return value was
    discarded entirely."""

    def fake_run(cmd, *a, **kw):
        return subprocess.CompletedProcess(cmd, 7)

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["run", "claude", "-d", str(tmp_path / "repo")])

    assert result.exit_code == 7


def test_agy_seeded_dispatch_fails_fast_when_seed_never_confirmed(tmp_path, monkeypatch):
    """The core regression case: container exits 0 every time, but agy's log
    never mentions the task id (seed silently dropped). Must retry once,
    then exit non-zero rather than reporting success."""
    attempts = {"n": 0}

    def fake_run(cmd, *a, **kw):
        attempts["n"] += 1
        return subprocess.CompletedProcess(cmd, 0)  # container "succeeds"

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    # _seed_confirmed always says "no trace of the task" — the silent-drop case
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: False)

    runner = CliRunner()
    result = runner.invoke(
        cli.main, ["run", "agy", "-d", str(tmp_path / "repo"), "-t", "task_deadbeef"]
    )

    assert result.exit_code != 0
    assert attempts["n"] == 2, "expected exactly one retry before failing fast"
    assert "task_deadbeef" in result.output
    assert "could not be" in result.output.lower() or "not confirm" in result.output.lower()


def test_agy_seeded_dispatch_succeeds_when_confirmed_on_first_attempt(tmp_path, monkeypatch):
    attempts = {"n": 0}

    def fake_run(cmd, *a, **kw):
        attempts["n"] += 1
        return subprocess.CompletedProcess(cmd, 0)

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    runner = CliRunner()
    result = runner.invoke(
        cli.main, ["run", "agy", "-d", str(tmp_path / "repo"), "-t", "task_deadbeef"]
    )

    assert result.exit_code == 0
    assert attempts["n"] == 1, "should not retry when the seed is confirmed first try"


def test_agy_seeded_dispatch_recovers_on_retry(tmp_path, monkeypatch):
    """Second attempt confirms the seed — should NOT fail, and should have
    tried exactly twice."""
    attempts = {"n": 0}

    def fake_run(cmd, *a, **kw):
        attempts["n"] += 1
        return subprocess.CompletedProcess(cmd, 0)

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    confirmed_calls = {"n": 0}

    def fake_confirmed(session_dir, task):
        confirmed_calls["n"] += 1
        return confirmed_calls["n"] >= 2  # fails first check, passes second

    monkeypatch.setattr(cli, "_seed_confirmed", fake_confirmed)

    runner = CliRunner()
    result = runner.invoke(
        cli.main, ["run", "agy", "-d", str(tmp_path / "repo"), "-t", "task_deadbeef"]
    )

    assert result.exit_code == 0
    assert attempts["n"] == 2


def test_agy_seeded_dispatch_puts_print_timeout_before_print(tmp_path, monkeypatch):
    """Regression test for aops_0964f17a / aops_87e6964a: agy's Go
    stdlib-`flag`-based parser makes `--print`/`-p` consume the very next
    argv token as the prompt, even if that token looks like another flag.
    `--print --print-timeout 60m "/pull <task>"` silently fed agy the
    literal string "--print-timeout" as its prompt, dropping the real one.
    This asserts the actual argv order built for docker, not just the
    retry/fail-fast wrapper around it — a previous regression here left the
    ordering bug live in the code while these tests still passed."""
    captured_cmd = {}

    def fake_run(cmd, *a, **kw):
        captured_cmd["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    runner = CliRunner()
    result = runner.invoke(
        cli.main, ["run", "agy", "-d", str(tmp_path / "repo"), "-t", "task_deadbeef"]
    )

    assert result.exit_code == 0
    cmd = captured_cmd["cmd"]
    timeout_idx = cmd.index("--print-timeout")
    print_idx = cmd.index("--print")
    assert timeout_idx < print_idx, f"--print-timeout must come before --print: {cmd}"
    assert cmd[print_idx + 1] == "/pull task_deadbeef", (
        f"--print's very next token must be the real prompt, nothing else "
        f"may sit between --print and its value: {cmd}"
    )


def test_agy_with_explicit_prompt_flag_is_not_seed_verified(tmp_path, monkeypatch):
    """When the caller supplies their own prompt/flag (not the `-t` auto-seed
    path), the retry/verification machinery must not kick in — only exit-code
    propagation applies."""
    attempts = {"n": 0}

    def fake_run(cmd, *a, **kw):
        attempts["n"] += 1
        return subprocess.CompletedProcess(cmd, 0)

    _base_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(
        cli,
        "_seed_confirmed",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["run", "agy", "-d", str(tmp_path / "repo"), "-t", "task_deadbeef", "--print", "hi"],
    )

    assert result.exit_code == 0
    assert attempts["n"] == 1
