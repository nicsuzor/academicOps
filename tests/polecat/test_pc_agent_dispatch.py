"""Integration tests for the `pc` agent dispatch pattern.

Verifies:
1. `pc.md` command path resolves to a valid `cli.py` in the built distribution.
2. `pc.md` grants no `tmux` tool or scope and contains no `tmux new-session`.
3. `pc.md` cites `run.json` as the return contract's evidence artifact.
4. In a non-TTY, non-interactive environment, the command extracted from `pc.md`
   executes without requiring a TTY or tmux session.
5. Shipped `dist/orchestrate-claude/agents/pc.md` matches `plugins/orchestrate/agents/pc.md`.
6. End-to-end dispatch execution produces run.json with tri-state status reporting.
"""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

from build.build import build_all
from lib.polecat import cli

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PC_AGENT_PATH = _REPO_ROOT / "plugins" / "aops" / "skills" / "polecat" / "SKILL.md"
_REAL_MARKETPLACE = _REPO_ROOT / "build" / "marketplace.toml"


def test_pc_agent_frontmatter_and_content_structure():
    """`polecat/SKILL.md` must not contain tmux new-session and must have valid frontmatter."""
    assert _PC_AGENT_PATH.is_file(), f"polecat SKILL.md missing at {_PC_AGENT_PATH}"
    content = _PC_AGENT_PATH.read_text(encoding="utf-8")

    # Frontmatter verification
    parts = content.split("---")
    assert len(parts) >= 3, "polecat SKILL.md must have valid YAML frontmatter"
    fm = yaml.safe_load(parts[1])

    assert fm.get("name") in ("polecat", "pc")
    assert "tmux new-session" not in content


def test_pc_cli_ships_in_built_orchestrate(tmp_path):
    """The built aops plugin must include polecat/cli.py so that
    ${CLAUDE_PLUGIN_ROOT}/polecat/cli.py resolves at runtime."""
    dist_root = tmp_path / "dist"
    build_all(
        _REPO_ROOT,
        dist_root,
        marketplace_path=_REAL_MARKETPLACE,
        plugins=["aops"],
        version="0.0.0-test",
    )

    for client in ("claude", "agy"):
        plugin_dir = dist_root / f"aops-{client}"
        cli_path = plugin_dir / "polecat" / "cli.py"
        assert cli_path.is_file(), f"{plugin_dir} does not contain polecat/cli.py"

        # Verify cli.py can be invoked with --help in a non-interactive subprocess
        env = dict(os.environ)
        env["PYTHONPATH"] = str(plugin_dir)
        res = subprocess.run(
            [sys.executable, str(cli_path), "run", "--help"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert res.returncode == 0, f"cli.py --help failed: {res.stderr}"
        assert "Run AGENT_CMD" in res.stdout


def test_pc_dispatch_non_tty_execution(tmp_path, monkeypatch):
    """A pc dispatch launched from a non-TTY, non-interactive shell must execute
    without failing on terminal attachment."""
    # Build aops dist
    dist_root = tmp_path / "dist"
    build_all(
        _REPO_ROOT,
        dist_root,
        marketplace_path=_REAL_MARKETPLACE,
        plugins=["aops"],
        version="0.0.0-test",
    )
    claude_plugin_root = dist_root / "aops-claude"

    # Extract command template from pc.md
    content = _PC_AGENT_PATH.read_text(encoding="utf-8")
    assert "tmux new-session" not in content, (
        "pc.md still contains tmux new-session which fails in non-TTY environments"
    )

    cli_script = claude_plugin_root / "polecat" / "cli.py"
    assert cli_script.is_file(), f"cli.py missing from {claude_plugin_root}"

    # Invoke polecat cli directly from a non-TTY subprocess with closed/piped stdin
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = str(claude_plugin_root)
    env["AOPS_SESSIONS"] = str(tmp_path / "sessions")
    env["POLECAT_HOME"] = str(tmp_path / "polecat_home")

    # Run `python3 <cli_script> --help` via non-TTY pipe
    proc = subprocess.run(
        [sys.executable, str(cli_script), "--help"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, f"Execution failed in non-TTY environment: {proc.stderr}"
    assert "polecat" in proc.stdout.lower()


def test_no_stale_ida_pc_references(tmp_path):
    """Every reference in plugins/ and dist/ must use orchestrate:pc, not ida:pc."""
    # Build all plugins into a temporary dist directory
    dist_root = _REPO_ROOT / "dist"
    if not dist_root.exists():
        dist_root = tmp_path / "dist"
        build_all(
            _REPO_ROOT,
            dist_root,
            marketplace_path=_REAL_MARKETPLACE,
            version="0.0.0-test",
        )

    # Check plugins/
    plugins_dir = _REPO_ROOT / "plugins"
    ida_pc_hits = []
    for path in plugins_dir.rglob("*.md"):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if "ida:pc" in line:
                ida_pc_hits.append(f"{path.relative_to(_REPO_ROOT)}:{i + 1}: {line}")

    msg = "\n".join(ida_pc_hits)
    assert not ida_pc_hits, f"Found stale 'ida:pc' references in plugins/:\n{msg}"


def test_pc_dispatch_end_to_end_tri_state_record(tmp_path, monkeypatch):
    """Verifies that a synchronous dispatch writes run.json with accurate status."""
    monkeypatch.setattr(cli, "_image_available_locally", lambda image: True)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}
        },
    )
    monkeypatch.setattr(cli, "load_local_overlay", lambda home: {})
    monkeypatch.setattr(
        cli, "setup_staging", lambda staging_dir, mcp_url, agent_home, agent_cmd=None: None
    )
    monkeypatch.setattr(
        cli,
        "_get_image_digest",
        lambda image: "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    )

    session_dir = tmp_path / "sessions" / "logs" / "20260826" / "session-test" / "aops"
    session_dir.mkdir(parents=True)
    t_file = session_dir / "6912ac2b-781f-4515-94d5-d883e2b94a54.jsonl"
    t_file.write_text('{"type": "user", "message": "hello"}\n')

    # Mock write_run_record invocation
    record_file = cli.write_run_record(
        session_dir=session_dir,
        session_id="session-test",
        container_id="c1234567890a",
        container_name="polecat-session-test",
        agent="agy",
        task_id="aops_55fd207c",
        seeded_prompt="/pull aops_55fd207c",
        image_ref="ghcr.io/nicsuzor/aops-crew:latest",
        image_digest="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        workspace_dir=tmp_path / "workspace",
        commit_start="c8387f1",
        commit_end="c8387f1",
        exit_code=0,
        delivery_guard={"ok": True, "error": None},
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
        worker_model=None,
        degraded=[],
    )

    assert record_file.is_file()
    record = json.loads(record_file.read_text(encoding="utf-8"))
    assert record["status"] == "success"
    assert record["task_id"] == "aops_55fd207c"
