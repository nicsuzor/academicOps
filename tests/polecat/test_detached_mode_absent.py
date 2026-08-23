"""Unit tests guarding against detached mode in polecat CLI.

Polecat is strictly a synchronous launcher: one script, result on stdout,
quiet by default. Detaching is the wrapping tmux session's job.

Guards:
1. `polecat run` has no `--detach` or `--detached` option.
2. `polecat run --help` does not advertise detached mode or any detach flag.
3. `-d` flag is exclusively `--repo-dir` (mounting a host repository), not detach.
"""

from click.testing import CliRunner

from lib.polecat import cli


def test_run_help_does_not_contain_detach():
    """`polecat run --help` must not advertise any detach flag or detached mode."""
    runner = CliRunner()
    result = runner.invoke(cli.main, ["run", "--help"])
    assert result.exit_code == 0, result.output
    help_text = result.output.lower()
    assert "--detach" not in help_text
    assert "--detached" not in help_text
    assert "detached mode" not in help_text


def test_run_options_do_not_contain_detach_parameters():
    """`cli.run` parameter definitions must not include any detach options."""
    for param in cli.run.params:
        for opt in getattr(param, "opts", []):
            assert opt not in ("--detach", "--detached"), f"Unexpected detach option found: {opt}"
        for secondary_opt in getattr(param, "secondary_opts", []):
            assert secondary_opt not in ("--detach", "--detached"), (
                f"Unexpected secondary detach option found: {secondary_opt}"
            )


def test_d_flag_is_exclusively_repo_dir():
    """`-d` flag must belong exclusively to `--repo-dir`, mounting a host repository."""
    d_params = [
        param
        for param in cli.run.params
        if "-d" in getattr(param, "opts", []) or "-d" in getattr(param, "secondary_opts", [])
    ]
    assert len(d_params) == 1, f"Expected exactly one param with '-d', found {len(d_params)}"
    param = d_params[0]
    assert param.name == "repo_dir"
    assert "--repo-dir" in param.opts
    assert not param.is_flag, "'-d' must not be a boolean flag (e.g. detach flag)"


def test_d_flag_requires_directory_argument():
    """Invoking `-d` without a path must fail because `-d` is not a standalone boolean detach flag."""
    runner = CliRunner()
    result = runner.invoke(cli.main, ["run", "-d"])
    assert result.exit_code != 0
    assert "requires an argument" in result.output or "Error" in result.output
