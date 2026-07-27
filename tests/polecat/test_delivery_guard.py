"""Regression tests for polecat harness delivery guard.

Ensures a polecat run that ends with uncommitted changes or unpushed local commits
exits FAILED and reverts any task status marked done/merge_ready in PKB back to in_progress.
"""

import json
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_POLECAT_DIR = str(_REPO_ROOT / "plugins" / "aops" / "polecat")
if _POLECAT_DIR not in sys.path:
    sys.path.insert(0, _POLECAT_DIR)

from cli import (  # noqa: E402
    _get_git_head,
    _revert_task_if_terminal,
    _verify_workspace_delivery,
    main,
)


def _init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True
    )
    (path / "file.txt").write_text("initial\n")
    subprocess.run(["git", "add", "file.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"], cwd=path, check=True, capture_output=True
    )


def test_verify_workspace_delivery_clean_repo(tmp_path):
    repo = tmp_path / "clean_repo"
    _init_repo(repo)
    head = _get_git_head(repo)

    ok, err = _verify_workspace_delivery(repo, initial_head=head)
    assert ok is True
    assert err is None


def test_verify_workspace_delivery_uncommitted_changes(tmp_path):
    repo = tmp_path / "dirty_repo"
    _init_repo(repo)
    head = _get_git_head(repo)

    (repo / "file.txt").write_text("modified content\n")

    ok, err = _verify_workspace_delivery(repo, initial_head=head)
    assert ok is False
    assert "uncommitted changes" in err.lower()


def test_verify_workspace_delivery_unpushed_commits(tmp_path):
    repo = tmp_path / "unpushed_repo"
    _init_repo(repo)
    initial_head = _get_git_head(repo)

    # Create local commit
    (repo / "file2.txt").write_text("new file\n")
    subprocess.run(["git", "add", "file2.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "second commit"], cwd=repo, check=True, capture_output=True
    )

    ok, err = _verify_workspace_delivery(repo, initial_head=initial_head)
    assert ok is False
    assert "local commits created" in err.lower() or "no pushed branch" in err.lower()


def test_verify_workspace_delivery_non_git_dir(tmp_path):
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()

    ok, err = _verify_workspace_delivery(plain_dir)
    assert ok is True
    assert err is None


def test_revert_task_if_terminal(monkeypatch):
    calls = []

    def fake_call_tool(tool_name, args):
        calls.append((tool_name, args))
        if "get_task" in tool_name:
            return {
                "content": [
                    {"type": "text", "text": json.dumps({"id": "task-123", "status": "done"})}
                ]
            }
        return {"result": "ok"}

    # Mock urllib.request inside _revert_pkb_task_if_done by patching urllib.request.urlopen
    class FakeResponse:
        def __init__(self, data, headers=None):
            self._data = data
            self.headers = headers or {}

        def read(self):
            return self._data.encode("utf-8")

    def fake_urlopen(req, timeout=5):
        body = json.loads(req.data.decode("utf-8"))
        method = body.get("method")
        if method == "initialize":
            return FakeResponse('{"jsonrpc":"2.0","id":1,"result":{}}', {"Mcp-Session-Id": "sess1"})
        elif method == "notifications/initialized":
            return FakeResponse('{"jsonrpc":"2.0"}')
        elif method == "tools/call":
            params = body.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            res = fake_call_tool(name, args)
            return FakeResponse(
                f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'id': 2, 'result': res})}\n\n"
            )
        return FakeResponse("{}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    reverted = _revert_task_if_terminal("http://mock-pkb-url", "task-123")
    assert reverted == "done"
    assert any("update_task" in c[0] and c[1].get("status") == "in_progress" for c in calls)


def test_run_fails_and_reverts_pkb_on_uncommitted_changes(tmp_path, monkeypatch):
    _repo = tmp_path / "repo"
    _init_repo(_repo)

    monkeypatch.setenv("AOPS_SESSIONS", str(tmp_path / "sessions"))
    monkeypatch.setenv("POLECAT_HOME", str(tmp_path / "polecat-home"))
    monkeypatch.setenv("POLECAT_IMAGE", "test-image:latest")
    monkeypatch.setattr("cli._image_available_locally", lambda image: True)
    monkeypatch.setattr("cli.load_config", lambda: {})
    monkeypatch.setattr("cli.load_local_overlay", lambda home: {})
    monkeypatch.setattr("cli.setup_staging", lambda staging_dir, mcp_url, agent_home: None)

    real_run = subprocess.run

    def fake_subprocess_run(cmd, *a, **kw):
        if cmd[0] == "docker" and cmd[1] == "run":
            (_repo / "dirty.txt").write_text("dirty\n")
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr("cli.subprocess.run", fake_subprocess_run)

    reverted_tasks = []
    monkeypatch.setattr(
        "cli._revert_task_if_terminal",
        lambda url, task_id: reverted_tasks.append(task_id) or "done",
    )

    runner = CliRunner()
    result = runner.invoke(main, ["run", "claude", "-d", str(_repo), "-t", "task-dirty"])

    assert result.exit_code != 0
    assert "delivery guard failed" in result.output.lower()
    assert "task-dirty" in reverted_tasks
