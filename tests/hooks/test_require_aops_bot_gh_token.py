"""Tests for require_aops_bot_gh_token gate."""

from __future__ import annotations

import os

from aops.hooks.gates.event import Event
from aops.hooks.gates.require_aops_bot_gh_token import require_aops_bot_gh_token


def test_ignores_non_pretooluse_events():
    event = Event("Stop", session_id="s1")
    assert require_aops_bot_gh_token(event, {}) is None


def test_ignores_non_bash_tools():
    event = Event("PreToolUse", tool="ViewFile", command="git push", session_id="s1")
    assert require_aops_bot_gh_token(event, {}) is None


def test_ignores_non_push_commands():
    event = Event("PreToolUse", tool="Bash", command="git status", session_id="s1")
    assert require_aops_bot_gh_token(event, {}) is None


def test_allows_git_push_when_token_set(monkeypatch):
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "ghp_test123456789")
    event = Event("PreToolUse", tool="Bash", command="git push origin dev", session_id="s1")
    assert require_aops_bot_gh_token(event, {}) is None


def test_denies_git_push_when_token_unset(monkeypatch):
    monkeypatch.delenv("AOPS_BOT_GH_TOKEN", raising=False)
    event = Event("PreToolUse", tool="Bash", command="git push origin dev", session_id="s1")
    verdict = require_aops_bot_gh_token(event, {})
    assert verdict is not None
    assert verdict.outcome == "deny"
    assert "AOPS_BOT_GH_TOKEN is unset" in verdict.inject_text


def test_denies_gh_pr_create_when_token_unset(monkeypatch):
    monkeypatch.delenv("AOPS_BOT_GH_TOKEN", raising=False)
    event = Event("PreToolUse", tool="Bash", command="gh pr create --title 'test'", session_id="s1")
    verdict = require_aops_bot_gh_token(event, {})
    assert verdict is not None
    assert verdict.outcome == "deny"
