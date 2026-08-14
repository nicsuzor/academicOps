"""The completion line, proven against the properties it has to hold.

Every test here corresponds to a way this mechanism could produce a line that
cannot be trusted unread, which is the only failure mode that matters: a
suppressed channel and a channel with nothing to say look identical from the
reader's side, so the line has to be right without anyone checking it.

The four that carry the design are:

- ``test_a_marker_the_graph_disagrees_with_renders_nothing`` — worker self-report
  is inadmissible. This is the test that makes the other three worth anything.
- ``test_two_writers_at_once_both_land`` — the daily note has been corrupted by
  concurrent whole-file writes before. Real processes, real contention.
- ``test_running_twice_yields_one_line`` — the trigger fires per tool batch, so a
  mechanism that appends on every fire would fill the note in a minute.
- ``test_the_write_is_surgical`` — everything except the inserted line is
  byte-identical, asserted on the bytes rather than on a claim about them.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "lib" / "hooks"))

import landed  # noqa: E402

DAY = date(2026, 8, 13)

NOTE_BODY = """---
title: "Daily Summary - 2026-08-13"
type: daily
date: 2026-08-13
---

# Daily Summary - 2026-08-13

## Focus

### My priorities

some content Nic wrote himself

## Today's Log

narrative that must not move

## Instrument notes

trailing content that must not move
"""


def _task(
    aca_data: Path,
    task_id: str,
    *,
    status: str,
    marker: str | None = None,
    title: str = "a delegated unit",
) -> Path:
    body = f"---\nid: {task_id}\nstatus: {status}\ntitle: {title}\ntype: task\n---\n\n## Goal\n\nsomething\n"
    if marker is not None:
        body += f"\n{marker}\n"
    path = aca_data / "tasks" / f"{task_id}-{title.replace(' ', '-')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def aca_data(tmp_path: Path) -> Path:
    root = tmp_path / "brain"
    (root / "tasks").mkdir(parents=True)
    (root / "daily").mkdir(parents=True)
    (root / "daily" / "20260813-daily.md").write_text(NOTE_BODY, encoding="utf-8")
    return root


def _note(aca_data: Path) -> str:
    return (aca_data / "daily" / "20260813-daily.md").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# The two keys
# --------------------------------------------------------------------------


def test_a_marker_the_graph_disagrees_with_renders_nothing(aca_data: Path):
    """The refusal that makes worker self-report inadmissible.

    The task's own body claims it landed. The graph has it in_progress. Four
    records on this surface are agents reporting a success they had not achieved,
    so the marker is treated as wording and the status as truth — and when they
    disagree, nothing is written at all.
    """
    _task(
        aca_data, "aops_liar01", status="in_progress", marker="LANDED: shipped the thing (nowhere)"
    )
    before = _note(aca_data)
    report = landed.sweep(aca_data, day=DAY)
    assert report.written == ()
    assert _note(aca_data) == before
    assert any("graph has status 'in_progress'" in s.reason for s in report.skipped)


def test_a_status_with_no_marker_renders_nothing_in_a_sweep(aca_data: Path):
    """The other half of the two-key rule: a status alone is not a completion.

    Tasks reach ``done`` all day for reasons that were never a delegated unit —
    a reconcile sweep, a duplicate being closed. Without a marker the sweep has
    no wording and no evidence anything was delegated, so it stays silent.
    """
    _task(aca_data, "aops_bare01", status="done")
    report = landed.sweep(aca_data, day=DAY)
    assert report.written == ()
    assert "[aops_bare01]" not in _note(aca_data)


def test_an_explicitly_named_task_falls_back_to_its_title(aca_data: Path):
    """``--task`` is a caller naming the unit, so a missing marker is not fatal."""
    _task(aca_data, "aops_named1", status="done", title="did a specific thing")
    report = landed.render_tasks(aca_data, ["aops_named1"], day=DAY)
    assert [r.line for r in report.written] == ["- [x] did a specific thing [aops_named1]"]


# --------------------------------------------------------------------------
# The line
# --------------------------------------------------------------------------


def test_the_landed_line_is_the_shape_nic_dictated(aca_data: Path):
    _task(
        aca_data,
        "aops_33c99996",
        status="review",
        marker=(
            "LANDED: configured Claude Code user-scoped settings to prevent worktrees "
            "blah blah (edits in dotfiles repo, committed and pushed)"
        ),
    )
    report = landed.sweep(aca_data, day=DAY)
    assert [r.line for r in report.written] == [
        "- [x] configured Claude Code user-scoped settings to prevent worktrees blah blah "
        "(edits in dotfiles repo, committed and pushed) [aops_33c99996]"
    ]


@pytest.mark.parametrize(
    ("marker", "status", "expected"),
    [
        ("LANDED: shipped it (in a PR)", "done", "- [x] shipped it (in a PR) [aops_three1]"),
        (
            "BLOCKED-ON-YOU: needs your ruling on the token scope",
            "blocked",
            "- [ ] **blocked on you** — needs your ruling on the token scope [aops_three1]",
        ),
        (
            "FAILED: the container never started (docker daemon down)",
            "failed",
            "- [ ] **failed** — the container never started (docker daemon down) [aops_three1]",
        ),
    ],
)
def test_all_three_outcomes_render_one_line_in_the_same_place(
    aca_data: Path, marker: str, status: str, expected: str
):
    """A capability that can only report success is one that hides its failures."""
    _task(aca_data, "aops_three1", status=status, marker=marker)
    report = landed.sweep(aca_data, day=DAY)
    assert [r.line for r in report.written] == [expected]
    body = _note(aca_data)
    assert expected in body
    assert body.count("## Landed today") == 1


def test_a_marker_written_through_pkb_append_is_still_found(aca_data: Path):
    """``pkb append`` stamps ``**<ts> UTC** —`` on what it writes.

    That is the sanctioned PKB write path, so the marker has to survive being
    written through it or the only way to set one is an unsanctioned edit.
    """
    _task(
        aca_data,
        "aops_stamp1",
        status="done",
        marker="**2026-08-13 10:47 UTC** — LANDED: did the thing (in a PR)",
    )
    report = landed.sweep(aca_data, day=DAY)
    assert [r.line for r in report.written] == ["- [x] did the thing (in a PR) [aops_stamp1]"]


def test_the_last_marker_wins(aca_data: Path):
    """A task body is appended to over its life; the newest marker is current."""
    _task(
        aca_data,
        "aops_last01",
        status="done",
        marker="LANDED: first attempt\n\nsome prose\n\nLANDED: what actually landed (a PR)",
    )
    report = landed.sweep(aca_data, day=DAY)
    assert [r.line for r in report.written] == ["- [x] what actually landed (a PR) [aops_last01]"]


# --------------------------------------------------------------------------
# The write
# --------------------------------------------------------------------------


def test_the_write_is_surgical(aca_data: Path):
    """Everything except the inserted line is byte-identical.

    Asserted on the bytes, because "surgical" is exactly the kind of claim that
    reads as true and is not — the daily note has been clobbered by whole-file
    writes before.
    """
    _task(aca_data, "aops_surg01", status="done", marker="LANDED: a thing (somewhere)")
    before = _note(aca_data)
    landed.sweep(aca_data, day=DAY)
    after = _note(aca_data)
    added = [line for line in after.splitlines() if line not in before.splitlines()]
    assert added == ["## Landed today", "- [x] a thing (somewhere) [aops_surg01]"]
    for line in before.splitlines():
        assert line in after.splitlines()


def test_running_twice_yields_one_line(aca_data: Path):
    """The trigger fires per tool batch, so appending on every fire would flood."""
    _task(aca_data, "aops_idem01", status="done", marker="LANDED: a thing (somewhere)")
    landed.sweep(aca_data, day=DAY)
    second = landed.sweep(aca_data, day=DAY)
    assert second.written == ()
    assert len(second.unchanged) == 1
    assert _note(aca_data).count("[aops_idem01]") == 1


def test_a_line_already_parked_elsewhere_is_corrected_in_place(aca_data: Path):
    """A human may have put the line under another heading already.

    Today's real note has exactly that: one ``- [x] … [aops_33c99996]`` line under
    ``### My priorities``. Appending a second copy below the fold would be a
    visible duplicate, so replacement is searched over the whole note.
    """
    note = aca_data / "daily" / "20260813-daily.md"
    note.write_text(
        NOTE_BODY.replace(
            "some content Nic wrote himself",
            "some content Nic wrote himself\n- [x] an old wording [aops_park01]",
        ),
        encoding="utf-8",
    )
    _task(aca_data, "aops_park01", status="done", marker="LANDED: the corrected wording (a PR)")
    landed.sweep(aca_data, day=DAY)
    body = _note(aca_data)
    assert body.count("[aops_park01]") == 1
    assert "- [x] the corrected wording (a PR) [aops_park01]" in body
    assert "## Landed today" not in body
    assert body.index("[aops_park01]") < body.index("## Today's Log")


def test_the_section_is_created_below_the_fold(aca_data: Path):
    _task(aca_data, "aops_fold01", status="done", marker="LANDED: a thing (somewhere)")
    landed.sweep(aca_data, day=DAY)
    body = _note(aca_data)
    assert body.index("## Landed today") > body.index("## Instrument notes")


def test_a_missing_daily_note_is_created_with_type_daily(tmp_path: Path):
    """Never through the PKB ``create`` path, whose type enum has no ``daily``.

    Six historical dailies sit in ``brain/notes/`` from exactly that mistake, so
    the canonical path is written directly with the right type instead.
    """
    root = tmp_path / "brain"
    (root / "tasks").mkdir(parents=True)
    _task(root, "aops_new001", status="done", marker="LANDED: a thing (somewhere)")
    landed.sweep(root, day=DAY)
    note = root / "daily" / "20260813-daily.md"
    assert note.exists()
    text = note.read_text(encoding="utf-8")
    assert "type: daily" in text
    assert "- [x] a thing (somewhere) [aops_new001]" in text


def test_two_writers_at_once_both_land(aca_data: Path):
    """Real processes, real contention.

    Two workers finishing in the same second is the ordinary case for a fleet, and
    a lost update here is silent: the note looks fine and one completion has
    simply never been recorded. Run as subprocesses so the ``flock`` is actually
    exercised across processes rather than within one.
    """
    for i in range(2):
        _task(aca_data, f"aops_race0{i}", status="done", marker=f"LANDED: unit {i} (somewhere)")
    script = str(_REPO_ROOT / "lib" / "hooks" / "landed.py")
    env = {**os.environ, "AOPS_PKB_BIN": ""}
    procs = [
        subprocess.Popen(
            [
                sys.executable,
                script,
                "--task",
                f"aops_race0{i}",
                "--aca-data",
                str(aca_data),
                "--day",
                "2026-08-13",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for i in range(2)
    ]
    outs = [p.communicate() for p in procs]
    for proc, (out, err) in zip(procs, outs, strict=True):
        assert proc.returncode == 0, f"stdout={out!r} stderr={err!r}"
    body = _note(aca_data)
    assert "- [x] unit 0 (somewhere) [aops_race00]" in body
    assert "- [x] unit 1 (somewhere) [aops_race01]" in body


def test_a_task_the_day_did_not_touch_is_not_swept(aca_data: Path):
    """The sweep is bounded by mtime so it stays cheap enough for every batch."""
    path = _task(aca_data, "aops_old001", status="done", marker="LANDED: last week (somewhere)")
    old = date(2026, 8, 1)
    stamp = landed.datetime.combine(old, landed.datetime.min.time()).timestamp()
    os.utime(path, (stamp, stamp))
    report = landed.sweep(aca_data, day=DAY)
    assert report.written == ()


def test_dry_run_writes_nothing(aca_data: Path):
    _task(aca_data, "aops_dry001", status="done", marker="LANDED: a thing (somewhere)")
    before = _note(aca_data)
    report = landed.sweep(aca_data, day=DAY, dry_run=True)
    assert len(report.written) == 1
    assert _note(aca_data) == before


# --------------------------------------------------------------------------
# The handler
# --------------------------------------------------------------------------


def test_the_built_plugin_ships_the_renderer_beside_its_handler(tmp_path_factory):
    """The renderer reaches the plugin the client loads, not just this repo.

    `landed.py` lives in `lib/hooks/` and gets there by `plugins/ida/manifest/
    plugin.toml` declaring the shared injection. A handler that imports a module
    the build does not carry fails at runtime inside a `try/except` that is
    deliberately silent — so this would be invisible without a build-level check.
    """
    from build.build import build_all

    root = tmp_path_factory.mktemp("ida-dist")
    build_all(
        _REPO_ROOT,
        root,
        marketplace_path=_REPO_ROOT / "build" / "marketplace.toml",
        plugins=["ida"],
        version="0.0.0.dev0",
    )
    hooks = root / "ida-claude" / "hooks"
    assert (hooks / "landed.py").is_file(), "landed.py did not ship into the built plugin"
    assert "render_landed" in (hooks / "handlers.py").read_text(encoding="utf-8")
    assert not (hooks / "messages" / "quiet.user.md").exists()


def test_the_renderer_runs_as_the_hook_runs_it(aca_data: Path):
    """The renderer through a real subprocess, with the note read back off disk.

    The unit tests above call `sweep` in-process, which proves the logic. This
    proves the *artifact*: a separate interpreter, invoked the way the hook
    invokes it, with the evidence coming from the filesystem afterwards rather
    than from anything the run reported about itself. Both keys are exercised in
    the same run — one task the graph agrees with, one it does not.
    """
    _task(aca_data, "aops_real01", status="done", marker="LANDED: wrote the thing (in a PR)")
    _task(
        aca_data,
        "aops_liar02",
        status="in_progress",
        marker="LANDED: claimed a success it had not achieved (nowhere)",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "lib" / "hooks" / "landed.py"),
            "--sweep",
            "--aca-data",
            str(aca_data),
            "--day",
            "2026-08-13",
        ],
        env={**os.environ, "AOPS_PKB_BIN": ""},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    body = _note(aca_data)
    assert "- [x] wrote the thing (in a PR) [aops_real01]" in body
    assert "aops_liar02" not in body


def test_the_handler_is_silent_on_every_path(aca_data: Path, monkeypatch):
    """It exists to make a record, not to say anything.

    A renderer that returns a ``Result`` becomes an ``additionalContext``
    injection, and one with a ``user_text`` becomes a ``systemMessage`` the person
    reads — either of which is the leak the capability exists to close. Checked on
    the success path, the disabled path, and the exploding path.
    """
    sys.path.insert(0, str(_REPO_ROOT / "plugins" / "ida" / "hooks"))
    import importlib

    handlers = importlib.import_module("handlers")
    importlib.reload(handlers)
    ctx = landed  # any object; the handler reads nothing off it

    # Every other test here drives `sweep` with an explicit `day=DAY`; the handler
    # is the one caller that asks the clock instead, which is correct in
    # production and means this test would otherwise only pass on the single real
    # date DAY names. Freeze the clock the handler reads so it agrees with the
    # fixture note.
    class _FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return DAY

    monkeypatch.setattr(handlers, "date", _FrozenDate)

    monkeypatch.setenv("ACA_DATA", str(aca_data))
    _task(aca_data, "aops_hand01", status="done", marker="LANDED: a thing (somewhere)")
    assert handlers.render_landed(ctx) is None
    assert "[aops_hand01]" in _note(aca_data)

    monkeypatch.setenv("AOPS_LANDED_DISABLE", "1")
    _task(aca_data, "aops_hand02", status="done", marker="LANDED: another (somewhere)")
    assert handlers.render_landed(ctx) is None
    assert "[aops_hand02]" not in _note(aca_data)
    monkeypatch.delenv("AOPS_LANDED_DISABLE")

    monkeypatch.setattr(
        landed, "sweep", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert handlers.render_landed(ctx) is None
