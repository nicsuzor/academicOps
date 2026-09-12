"""Tests for `polecat default-branch`: the dispatcher-side lookup of a
project's configured active line (`projects.<slug>.default_branch` in
polecat.yaml).

This command is deliberately NOT consulted by `resolve_isolated_workspace()`
itself (spec-base-ref-resolution.md rule 1 — see
test_workspace_isolation.py::test_isolated_workspace_always_captures_canonical_head_when_base_unspecified).
It exists so a dispatcher (e.g. the `polecat` SKILL) can resolve a project's
active line and pass it as an explicit `--base` to `polecat run`.
"""

from click.testing import CliRunner

from lib.polecat import cli


def _invoke(monkeypatch, config, project):
    monkeypatch.setattr(cli, "load_config", lambda: config)
    runner = CliRunner()
    return runner.invoke(cli.main, ["default-branch", "-p", project])


def test_prints_configured_default_branch(monkeypatch):
    config = {"projects": {"academicOps": {"default_branch": "v0.10"}}}
    res = _invoke(monkeypatch, config, "academicOps")
    assert res.exit_code == 0, res.output
    assert res.output.strip() == "v0.10"


def test_resolves_alias_before_lookup(monkeypatch):
    config = {"projects": {"academicOps": {"default_branch": "v0.10"}}}
    res = _invoke(monkeypatch, config, "aops")
    assert res.exit_code == 0, res.output
    assert res.output.strip() == "v0.10"


def test_prints_nothing_when_project_has_no_default_branch(monkeypatch):
    config = {"projects": {"academicOps": {"repo": "academicOps"}}}
    res = _invoke(monkeypatch, config, "academicOps")
    assert res.exit_code == 0, res.output
    assert res.output.strip() == ""


def test_prints_nothing_when_project_unknown(monkeypatch):
    config = {"projects": {}}
    res = _invoke(monkeypatch, config, "some-other-project")
    assert res.exit_code == 0, res.output
    assert res.output.strip() == ""


def test_prints_nothing_with_empty_config(monkeypatch):
    res = _invoke(monkeypatch, {}, "academicOps")
    assert res.exit_code == 0, res.output
    assert res.output.strip() == ""
