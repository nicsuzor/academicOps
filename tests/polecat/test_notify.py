"""The dispatch-completion notification: one line, two sinks, never fatal."""

import json

from lib.polecat import notify

RECORD = {
    "session_id": "sess-1",
    "agent": "agy",
    "task_id": "task_f8374e75",
    "status": "success",
    "exit_code": 0,
    "duration_seconds": 42,
    "ended_at": "2026-08-16T04:00:00Z",
}


def _write_record(tmp_path, **overrides):
    path = tmp_path / "run.json"
    path.write_text(json.dumps({**RECORD, **overrides}))
    return path


def test_line_names_the_task_and_the_outcome():
    assert notify.format_line(RECORD) == "polecat agy task_f8374e75 success (exit 0, 42s)"
    assert notify.format_line({**RECORD, "status": "failed", "exit_code": 2}) == (
        "polecat agy task_f8374e75 failed (exit 2, 42s)"
    )


def test_both_sinks_get_the_line(tmp_path, monkeypatch):
    posted = []
    monkeypatch.setattr(notify, "_post_discord", posted.append)

    line = notify.notify_run_complete(_write_record(tmp_path), tmp_path)

    assert line == "polecat agy task_f8374e75 success (exit 0, 42s)"
    assert posted == [line]
    log = tmp_path / "state" / "polecat_runs.log"
    assert log.read_text() == f"2026-08-16T04:00:00Z {line}\n"


def test_log_is_appended_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(notify, "_post_discord", lambda line: None)
    record = _write_record(tmp_path)

    notify.notify_run_complete(record, tmp_path)
    notify.notify_run_complete(record, tmp_path)

    assert len((tmp_path / "state" / "polecat_runs.log").read_text().splitlines()) == 2


def test_a_broken_sink_never_raises(tmp_path, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("sink is down")

    monkeypatch.setattr(notify, "_post_discord", boom)

    # Unreachable Discord: the log still gets the line and the call returns.
    assert notify.notify_run_complete(_write_record(tmp_path), tmp_path) is not None
    assert (tmp_path / "state" / "polecat_runs.log").exists()

    # Unwritable log directory, and a missing run record.
    monkeypatch.setattr(notify.Path, "mkdir", boom)
    assert notify.notify_run_complete(_write_record(tmp_path), tmp_path) is not None
    assert notify.notify_run_complete(tmp_path / "absent.json", tmp_path) is None


def test_discord_config_falls_back_to_the_provisioned_files(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_CHANNEL_ID", raising=False)
    (tmp_path / ".env").write_text("DISCORD_BOT_TOKEN=tok-123\n")
    (tmp_path / "access.json").write_text(json.dumps({"groups": {"chan-9": {}}}))
    monkeypatch.setattr(notify, "CHANNEL_DIR", tmp_path)

    assert notify._discord_config() == ("tok-123", "chan-9")

    monkeypatch.setenv("DISCORD_CHANNEL_ID", "override")
    assert notify._discord_config() == ("tok-123", "override")
