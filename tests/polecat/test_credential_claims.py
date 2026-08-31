"""Credentials are ambient in the container, not scoped to an env file.

Live-verified in aops-crew:latest: polecat forwards AOPS_BOT_GH_TOKEN, GH_TOKEN
and GITHUB_TOKEN into the container's plain process environment on every run, so
any tool call sees them directly. Nothing is scoped.
"""

from lib.polecat import cli


def test_tokens_reach_the_container_as_plain_environment(monkeypatch):
    """The fact the message has to be consistent with."""
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "mock-bot-token")
    config = {"git_identity": {"name": "botnicbot", "email": "botnicbot@users.noreply.github.com"}}

    env = cli.get_env_forwards(config)

    assert env["AOPS_BOT_GH_TOKEN"] == "mock-bot-token"
    assert env["GH_TOKEN"] == "mock-bot-token"
    assert env["GITHUB_TOKEN"] == "mock-bot-token"
