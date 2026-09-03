"""Tests for project aliases defined in polecat.yaml globally and canonicalization
across polecat dispatch, workspace resolution, and OTEL attribution.
"""

import subprocess

from click.testing import CliRunner

from lib.polecat import cli


def test_resolve_canonical_project_direct_match():
    config = {
        "projects": {
            "aops": {"repo": "academicOps"},
            "mem": {"repo": "mem"},
        }
    }
    assert cli.resolve_canonical_project("aops", config) == "aops"
    assert cli.resolve_canonical_project("mem", config) == "mem"


def test_resolve_canonical_project_per_project_aliases_list():
    config = {
        "projects": {
            "aops": {
                "repo": "academicOps",
                "aliases": ["academicOps", "academicops", "academic_ops"],
            }
        }
    }
    assert cli.resolve_canonical_project("academicOps", config) == "aops"
    assert cli.resolve_canonical_project("academicops", config) == "aops"
    assert cli.resolve_canonical_project("academic_ops", config) == "aops"
    assert cli.resolve_canonical_project("aops", config) == "aops"


def test_resolve_canonical_project_per_project_single_alias():
    config = {
        "projects": {
            "aops": {
                "alias": "academicOps",
            }
        }
    }
    assert cli.resolve_canonical_project("academicOps", config) == "aops"
    assert cli.resolve_canonical_project("aops", config) == "aops"


def test_resolve_canonical_project_top_level_aliases_map():
    config = {
        "projects": {
            "aops": {"repo": "academicOps"},
        },
        "aliases": {
            "academicOps": "aops",
            "academicops": "aops",
        },
    }
    assert cli.resolve_canonical_project("academicOps", config) == "aops"
    assert cli.resolve_canonical_project("academicops", config) == "aops"
    assert cli.resolve_canonical_project("aops", config) == "aops"


def test_resolve_canonical_project_top_level_aliases_list():
    config = {
        "aliases": {
            "aops": ["academicOps", "academicops"],
        }
    }
    assert cli.resolve_canonical_project("academicOps", config) == "aops"
    assert cli.resolve_canonical_project("academicops", config) == "aops"


def test_resolve_canonical_project_case_insensitive():
    config = {
        "projects": {
            "aops": {
                "aliases": ["academicOps"],
            }
        }
    }
    assert cli.resolve_canonical_project("ACADEMICOPS", config) == "aops"
    assert cli.resolve_canonical_project("Aops", config) == "aops"


def test_resolve_canonical_project_task_id_prefix():
    config = {
        "projects": {
            "aops": {
                "aliases": ["academicOps"],
            }
        }
    }
    assert (
        cli.resolve_canonical_project("academicOps-aops_fe8e4d2e", config) == "aops-aops_fe8e4d2e"
    )
    assert cli.resolve_canonical_project("aops-aops_fe8e4d2e", config) == "aops-aops_fe8e4d2e"
    assert cli.resolve_canonical_project("unknown-task_123", config) == "unknown-task_123"


def test_resolve_canonical_project_unknown_and_empty():
    config = {"projects": {"aops": {}}}
    assert cli.resolve_canonical_project("other-project", config) == "other-project"
    assert cli.resolve_canonical_project("", config) == ""
    assert cli.resolve_canonical_project(None, config) is None


def test_resolve_workspace_with_project_alias(tmp_path, monkeypatch):
    repo_dir = tmp_path / "academicOps"
    repo_dir.mkdir()
    polecat_home = tmp_path / "polecat-home"
    polecat_home.mkdir()

    config = {
        "projects": {
            "aops": {
                "aliases": ["academicOps"],
            }
        }
    }
    # local.yaml maps the canonical slug 'aops'
    monkeypatch.setattr(
        cli,
        "load_local_overlay",
        lambda home: {"paths": {"aops": str(repo_dir)}},
    )

    resolved = cli._resolve_workspace(None, "academicOps", polecat_home, config=config)
    assert resolved == repo_dir.resolve()


def test_run_normalizes_project_alias_for_otel_and_session(tmp_path, monkeypatch):
    """Verify `polecat run -p academicOps` resolves to canonical 'aops' for
    OTEL resource attributes, task identifiers, log directories, and sessions_access."""
    repo = tmp_path / "academicOps"
    repo.mkdir()
    (repo / ".git").mkdir()

    config = {
        "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"},
        "projects": {
            "aops": {
                "aliases": ["academicOps"],
                "sessions_access": True,
            }
        },
    }

    captured_run = []

    def fake_run(cmd, *a, **kw):
        if cmd and ("sbx" in cmd or "run" in cmd):
            captured_run.append((list(cmd), kw.get("env")))
        return subprocess.CompletedProcess(cmd, 0, stdout="")

    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(
        cli,
        "load_local_overlay",
        lambda home: {"paths": {"aops": str(repo)}},
    )
    monkeypatch.setattr(
        cli, "setup_staging", lambda staging_dir, mcp_url, agent_home, agent_cmd=None: None
    )
    monkeypatch.setattr(
        cli,
        "resolve_isolated_workspace",
        lambda ws, sid, home, **kw: (ws, None),
    )
    monkeypatch.setattr(cli, "_get_git_head", lambda ws: "deadbeef")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "_seed_confirmed", lambda session_dir, task: True)

    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    monkeypatch.setenv("PKB_MCP_URL", "http://test-pkb.invalid:8026/mcp")

    runner = CliRunner()
    res = runner.invoke(
        cli.main,
        [
            "run",
            "sleep",
            "-p",
            "academicOps",
            "-t",
            "task_fe8e4d2e",
            "--session-name",
            "test-session",
            "--quiet",
        ],
    )
    assert res.exit_code == 0, res.output
    assert len(captured_run) == 1

    cmd, _ = captured_run[0]
    env_args = {}
    for i, arg in enumerate(cmd):
        if arg == "-e" and i + 1 < len(cmd):
            kv = cmd[i + 1]
            if "=" in kv:
                k, v = kv.split("=", 1)
                env_args[k] = v
            else:
                env_args[kv] = ""

    assert "polecat.project=aops" in env_args["OTEL_RESOURCE_ATTRIBUTES"]
    assert "polecat.task_id=task_fe8e4d2e" in env_args["OTEL_RESOURCE_ATTRIBUTES"]
    assert env_args["GENAI_ENGINE_TASK_ID"] == "task_fe8e4d2e"
    assert env_args["OTEL_SERVICE_NAME"] == "aops"
    assert env_args["PHOENIX_PROJECT_NAME"] == "aops"

    # Check sessions record is written under aops
    session_records = list((tmp_path / "sessions").glob("logs/aops/test-session/*/run.json"))
    assert len(session_records) > 0, f"Expected session record under aops, got {session_records}"
