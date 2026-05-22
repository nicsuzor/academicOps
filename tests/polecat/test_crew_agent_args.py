#!/usr/bin/env python3
"""Regression tests for crew command agent_args pass-through (issue #1194).

Root cause: the ``extra`` positional argument shadowed the first flag-shaped
token from ``agent_args``, so ``-- -p "reply OK"`` arrived as
``extra='-p'``, ``agent_args=('reply OK',)`` instead of
``agent_args=('-p', 'reply OK')``.

The fix removes the ``extra`` positional and pulls the repo path from
``agent_args[0]`` when ``target == 'repo'``.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from cli import crew


def _parse_crew(*args):
    """Return the parsed parameters for the crew command without executing it."""
    ctx = crew.make_context("crew", list(args))
    return ctx.params


class TestCrewAgentArgsPassthrough:
    """Verify that flag-shaped tokens after '--' reach agent_args intact."""

    def test_dash_p_reaches_agent_args(self):
        """Regression: -p was stolen by the extra positional before the fix."""
        params = _parse_crew("--model", "gemini", "aops", "--", "-p", "reply OK")
        assert "-p" in params["agent_args"], (
            f"-p missing from agent_args={params['agent_args']!r} — "
            "the extra positional arg is probably stealing flag-shaped tokens again"
        )
        assert "reply OK" in params["agent_args"]

    def test_dash_p_order_preserved(self):
        """Flag must precede its value."""
        params = _parse_crew("--model", "gemini", "aops", "--", "-p", "reply OK")
        args = list(params["agent_args"])
        assert args.index("-p") < args.index("reply OK")

    def test_no_extra_args_gives_empty_agent_args(self):
        """No '--' passthrough → agent_args is empty."""
        params = _parse_crew("aops")
        assert params["agent_args"] == ()

    def test_target_is_correct(self):
        """target receives the project alias, not a flag token."""
        params = _parse_crew("--model", "gemini", "aops", "--", "-p", "reply OK")
        assert params["target"] == "aops"

    def test_multiple_passthrough_flags(self):
        """Multiple flags after '--' are all forwarded."""
        params = _parse_crew("aops", "--", "--approval-mode", "yolo", "-p", "do x")
        args = params["agent_args"]
        assert "--approval-mode" in args
        assert "yolo" in args
        assert "-p" in args
        assert "do x" in args

    def test_repo_path_in_agent_args(self):
        """'repo' target: path token arrives in agent_args (not stolen by extra)."""
        params = _parse_crew("repo", "/some/path", "--", "-p", "hello")
        args = params["agent_args"]
        # All three tokens must be present; the crew function then slices [0]
        # as the path and [1:] as pass-through.
        assert "/some/path" in args
        assert "-p" in args
        assert "hello" in args
