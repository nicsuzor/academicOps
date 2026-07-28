"""The agent-facing credential message must describe what actually happens.

The message used to tell every session "credentials for this session are
scoped to a session-local environment file ... git and `gh` resolve their own
auth from that file". Both halves were false, and an agent acted on them: a
live container agent refused a diagnostic command, citing that text as reason
to treat the environment as credential-bearing ground it must not inspect.

What actually happens, live-verified in aops-crew:latest:

- polecat forwards AOPS_BOT_GH_TOKEN, GH_TOKEN and GITHUB_TOKEN into the
  container's plain process environment on every run, so any tool call sees
  them directly. Nothing is scoped.
- credentials.isolate() builds the env file BY READING those same variables
  out of the process environment, so the file is a second copy of what is
  already there — it cannot be the exclusive source.

These tests pin the message against the mechanism, so the two cannot drift
apart again.
"""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PLUGINS_DIR = str(_REPO_ROOT / "plugins")
_LIB_HOOKS = str(_REPO_ROOT / "lib" / "hooks")
for _path in (_PLUGINS_DIR, _LIB_HOOKS):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import credentials  # noqa: E402
from aops.polecat import cli  # noqa: E402

_MESSAGE = _REPO_ROOT / "plugins" / "aops" / "hooks" / "messages" / "session-start-isolated.md"
_USER_MESSAGE = _MESSAGE.with_suffix(".user.md")

# Wordings that assert an exclusivity the mechanism does not provide.
_FALSE_CLAIMS = (
    "scoped to",
    "from that file",
    "only what it needs",
    "inherits only",
)


def test_tokens_reach_the_container_as_plain_environment(monkeypatch):
    """The fact the message has to be consistent with."""
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "mock-bot-token")

    env = cli.get_env_forwards()

    assert env["AOPS_BOT_GH_TOKEN"] == "mock-bot-token"
    assert env["GH_TOKEN"] == "mock-bot-token"
    assert env["GITHUB_TOKEN"] == "mock-bot-token"


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


def test_message_claims_no_scoping_it_cannot_deliver():
    text = _MESSAGE.read_text().lower() + _USER_MESSAGE.read_text().lower()

    for claim in _FALSE_CLAIMS:
        assert claim not in text, (
            f"message claims {claim!r}, but the tokens are forwarded as plain "
            "environment and the env file is built from them"
        )


def test_message_still_forbids_handling_credentials():
    """Correcting the false claim must not cost the operative instruction —
    that is the part with real effect on agent behaviour."""
    text = _MESSAGE.read_text().lower()

    assert "read none" in text or "read no" in text
    assert "print none" in text or "store none" in text
