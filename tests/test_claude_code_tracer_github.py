"""Spans from a GitHub Actions run carry the run's identity, and no other spans do."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer

_GITHUB_ENV = {
    "GITHUB_ACTIONS": "true",
    "GITHUB_REPOSITORY": "nicsuzor/academicOps",
    "GITHUB_RUN_ID": "1234567890",
    "GITHUB_RUN_ATTEMPT": "2",
    "GITHUB_WORKFLOW": "Claude Code",
    "GITHUB_JOB": "claude",
    "GITHUB_EVENT_NAME": "issue_comment",
    "GITHUB_REF": "refs/heads/dev",
    "GITHUB_SHA": "0123456789abcdef0123456789abcdef01234567",
    "GITHUB_SERVER_URL": "https://github.com",
}


def test_github_resource_attrs_empty_outside_actions():
    with patch.dict("os.environ", {"GITHUB_RUN_ID": "1"}, clear=True):
        assert claude_code_tracer._github_resource_attrs() == {}


def test_github_resource_attrs_identify_the_run():
    with patch.dict("os.environ", _GITHUB_ENV, clear=True):
        attrs = claude_code_tracer._github_resource_attrs()

    assert attrs == {
        "github.repository": "nicsuzor/academicOps",
        "github.run_id": "1234567890",
        "github.run_attempt": "2",
        "github.workflow": "Claude Code",
        "github.job": "claude",
        "github.event_name": "issue_comment",
        "github.ref": "refs/heads/dev",
        "github.sha": "0123456789abcdef0123456789abcdef01234567",
        "github.run_url": "https://github.com/nicsuzor/academicOps/actions/runs/1234567890/attempts/2",
    }


def test_github_resource_attrs_skip_unset_values():
    env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "o/r"}
    with patch.dict("os.environ", env, clear=True):
        assert claude_code_tracer._github_resource_attrs() == {"github.repository": "o/r"}
