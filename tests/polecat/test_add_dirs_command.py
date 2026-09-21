"""Tests for `polecat add-dirs`: the dynamic `--add-dir` list a directly-invoked
agent CLI (e.g. `agy`, outside any polecat container) needs on this machine.

Project slugs are the registry in polecat.yaml (`projects`); each slug's host
checkout path is this machine's own mapping in `<polecat_home>/local.yaml`
(`paths`) — the same lookup `_resolve_workspace` uses for `--project`. There is
never a hard-coded list: a project with no local mapping is silently skipped,
and `$AOPS_SESSIONS` is always included.
"""

from click.testing import CliRunner

from lib.polecat import cli


def _invoke(monkeypatch, tmp_path, config, paths, sessions="sessions"):
    polecat_home = tmp_path / "polecat-home"
    polecat_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {"paths": paths})
    monkeypatch.setenv("POLECAT_HOME", str(polecat_home))
    sessions_dir = tmp_path / sessions
    sessions_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))
    runner = CliRunner()
    return runner.invoke(cli.main, ["add-dirs"])


def test_resolves_registered_project_paths_and_sessions_root(monkeypatch, tmp_path):
    repo_a = tmp_path / "repo-a"
    repo_a.mkdir()
    config = {"projects": {"aops": {"repo": "academicOps"}}}
    res = _invoke(monkeypatch, tmp_path, config, {"aops": str(repo_a)})
    assert res.exit_code == 0, res.output
    lines = set(res.output.strip().splitlines())
    assert str(repo_a.resolve()) in lines
    assert str((tmp_path / "sessions").resolve()) in lines
    assert len(lines) == 2


def test_skips_registered_project_with_no_local_mapping(monkeypatch, tmp_path):
    config = {"projects": {"aops": {"repo": "academicOps"}, "mem": {"repo": "mem"}}}
    res = _invoke(monkeypatch, tmp_path, config, {})
    assert res.exit_code == 0, res.output
    lines = set(res.output.strip().splitlines())
    assert lines == {str((tmp_path / "sessions").resolve())}


def test_skips_local_mapping_for_unregistered_project(monkeypatch, tmp_path):
    unregistered = tmp_path / "not-a-project"
    unregistered.mkdir()
    config = {"projects": {"aops": {"repo": "academicOps"}}}
    res = _invoke(monkeypatch, tmp_path, config, {"not-registered": str(unregistered)})
    assert res.exit_code == 0, res.output
    lines = set(res.output.strip().splitlines())
    assert str(unregistered.resolve()) not in lines
    assert lines == {str((tmp_path / "sessions").resolve())}


def test_skips_path_that_does_not_exist_on_disk(monkeypatch, tmp_path):
    config = {"projects": {"aops": {"repo": "academicOps"}}}
    res = _invoke(monkeypatch, tmp_path, config, {"aops": str(tmp_path / "missing")})
    assert res.exit_code == 0, res.output
    lines = set(res.output.strip().splitlines())
    assert lines == {str((tmp_path / "sessions").resolve())}


def test_fails_loudly_without_polecat_home(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "load_config", lambda: {"projects": {}})
    monkeypatch.delenv("POLECAT_HOME", raising=False)
    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path))
    runner = CliRunner()
    res = runner.invoke(cli.main, ["add-dirs"])
    assert res.exit_code != 0
    assert "polecat home" in res.output.lower() or "polecat home" in str(res.exception).lower()


def test_fails_loudly_without_sessions_root(monkeypatch, tmp_path):
    polecat_home = tmp_path / "polecat-home"
    polecat_home.mkdir()
    monkeypatch.setattr(cli, "load_config", lambda: {"projects": {}})
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setenv("POLECAT_HOME", str(polecat_home))
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    runner = CliRunner()
    res = runner.invoke(cli.main, ["add-dirs"])
    assert res.exit_code != 0
