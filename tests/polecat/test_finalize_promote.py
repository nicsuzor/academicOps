"""Tests for the `promote` path in polecat/finalize.py and polecat/cli.py."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from click.testing import CliRunner

from polecat.cli import run
from polecat.finalize import finish_cmd

FINALIZE_SRC = (REPO_ROOT / "polecat" / "finalize.py").read_text()
CLI_SRC = (REPO_ROOT / "polecat" / "cli.py").read_text()


def _option_names(command) -> set[str]:
    names: set[str] = set()
    for param in command.params:
        names.update(param.opts)
        names.update(param.secondary_opts)
    return names


def test_promote_flag_is_registered_on_finish():
    """`finish` must expose a `--promote` option."""
    assert "--promote" in _option_names(finish_cmd)


def test_promote_flag_is_registered_on_run():
    """`run` must expose a `--promote` option."""
    assert "--promote" in _option_names(run)


def test_help_documents_promote():
    """`finish --help` and `run --help` must document the promote behaviour."""
    finish_result = CliRunner().invoke(finish_cmd, ["--help"])
    assert finish_result.exit_code == 0
    assert "--promote" in finish_result.output
    assert "promotion" in finish_result.output.lower()

    run_result = CliRunner().invoke(run, ["--help"])
    assert run_result.exit_code == 0
    assert "--promote" in run_result.output
    assert "promotion" in run_result.output.lower()


def test_promote_logic_in_finalize_source():
    """Verify that is_draft resolution is implemented correctly in finalize.py source.
    is_draft = is_partial or (is_shared and not promote)
    """
    assert "is_draft = is_partial or (is_shared and not promote)" in FINALIZE_SRC
    assert 'create_args.append("--draft")' in FINALIZE_SRC
    assert '["gh", "pr", "ready"' in FINALIZE_SRC or "['gh', 'pr', 'ready'" in FINALIZE_SRC


def test_promote_propagation_in_cli_source():
    """Verify that promote flag is propagated when invoking _finish_cmd in cli.py."""
    assert "promote=promote" in CLI_SRC
