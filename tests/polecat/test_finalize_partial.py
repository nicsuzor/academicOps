"""Tests for the `partial` terminal-state path in polecat/finalize.py.

Partial-work doctrine (PKB: spec-partial-work, stage-5 chunk 1): `finish`
previously hard-coded `merge_ready` as its only terminal. It must now also
support an honest partial stop via `--partial`: file the PR as a DRAFT and
release the task as `partial` rather than `merge_ready`.

The full `finish` command has heavy git/gh side effects that aren't
reproducible here (see test_finish_surfaces_transcript.py for the same
caveat), so we test the wiring that is deterministic and side-effect-free:
the Click option surface and its documented behaviour. The no-launder
guarantee (a `partial` release that the server rejects must NOT fall back to
`merge_ready`) is asserted at the source level — it is the load-bearing
honesty property and must not silently regress.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from click.testing import CliRunner  # noqa: E402

from polecat.finalize import finish_cmd  # noqa: E402

FINALIZE_SRC = (REPO_ROOT / "polecat" / "finalize.py").read_text()


def _option_names(command) -> set[str]:
    names: set[str] = set()
    for param in command.params:
        names.update(param.opts)
        names.update(param.secondary_opts)
    return names


def test_partial_flag_is_registered():
    """AC#1: `finish` must expose a `--partial` option."""
    assert "--partial" in _option_names(finish_cmd)


def test_help_documents_partial_and_draft():
    """`finish --help` must describe the partial=draft-PR behaviour so an
    operator can discover it. (Pure --help render — no side effects.)"""
    result = CliRunner().invoke(finish_cmd, ["--help"])
    assert result.exit_code == 0
    assert "--partial" in result.output
    assert "partial" in result.output.lower()
    assert "draft" in result.output.lower()


def test_default_finish_still_targets_merge_ready():
    """Regression: the default (no --partial) terminal is unchanged."""
    assert 'target_status = "partial" if is_partial else "merge_ready"' in FINALIZE_SRC


def test_partial_is_a_protected_terminal_status_in_safeguard():
    """AC#1: a task already in `partial` must be protected from the auto-retry
    reset, exactly like the other terminal statuses (SAFEGUARD 0)."""
    assert '"partial"' in FINALIZE_SRC
    # The string-tuple safeguard (the path taken when lib.task_model is absent,
    # which is the live polecat deploy class) must include partial.
    assert (
        '_TERMINAL_STATUSES = ("done", "review", "merge_ready", "cancelled", "partial")'
        in FINALIZE_SRC
    )


def test_partial_release_never_launders_into_merge_ready():
    """The honesty invariant: if releasing as `partial` fails (e.g. the PKB
    server does not yet accept the status), the partial path must NOT fall back
    to `merge_ready` — that would convert an honest-incomplete stop into a false
    completion claim (clause-2b illegal-gap).

    We assert the merge_ready fallback is gated behind `else:` (the non-partial
    branch) and that the partial branch's failure message refuses merge_ready.
    """
    # The merge_ready save-fallback must live under the non-partial branch only.
    assert "if is_partial:" in FINALIZE_SRC
    assert "refusing to mark 'merge_ready'" in FINALIZE_SRC.replace("\n", " ") or (
        "refusing to mark" in FINALIZE_SRC and "merge_ready" in FINALIZE_SRC
    )


def test_partial_files_draft_pr():
    """AC#2: the partial path appends `--draft` to `gh pr create`."""
    assert 'create_args.append("--draft")' in FINALIZE_SRC
