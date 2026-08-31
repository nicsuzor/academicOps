"""Credentials are ambient in the container, not scoped to an env file.

Live-verified in aops-crew:latest:

- polecat forwards AOPS_BOT_GH_TOKEN, GH_TOKEN and GITHUB_TOKEN into the
  container's plain process environment on every run, so any tool call sees
  them directly. Nothing is scoped.
- credentials.isolate() builds the env file BY READING those same variables
  out of the process environment, so the file is a second copy of what is
  already there — it cannot be the exclusive source.
"""

import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_HOOKS = str(_REPO_ROOT / "lib" / "hooks")
if _LIB_HOOKS not in sys.path:
    sys.path.insert(0, _LIB_HOOKS)

# `credentials` was one of eight modules the hook-layer rewrite deleted from
# lib/hooks/. Only the env-file test below needs it, so import it defensively
# and let the gap be one named skip rather than a module-scope collection error.
try:
    import credentials
except ModuleNotFoundError:  # pragma: no cover - depends on the hook layer's state
    credentials = None

from lib.polecat import cli  # noqa: E402


def test_tokens_reach_the_container_as_plain_environment(monkeypatch):
    """The fact the message has to be consistent with."""
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "mock-bot-token")
    config = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}

    env = cli.get_env_forwards(config)

    assert env["AOPS_BOT_GH_TOKEN"] == "mock-bot-token"
    assert env["GH_TOKEN"] == "mock-bot-token"
    assert env["GITHUB_TOKEN"] == "mock-bot-token"


@pytest.mark.skipif(
    credentials is None,
    reason="lib/hooks/credentials.py was removed by the hook-layer rewrite; "
    "the SessionStart credential hook has no module to test against here",
)
def test_env_file_is_built_from_the_process_environment(tmp_path, monkeypatch):
    """The file is a copy of the environment, not a replacement for it, so it
    can never be the only place a credential lives."""
    env_file = tmp_path / "session-env.sh"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "mock-bot-token")

    persisted = credentials.isolate({"session_id": "s1"})

    assert persisted["GH_TOKEN"] == "mock-bot-token"
    # Still in the ambient environment afterwards — isolate() reads, never moves.
    assert os.environ["AOPS_BOT_GH_TOKEN"] == "mock-bot-token"
    assert "mock-bot-token" in env_file.read_text()
