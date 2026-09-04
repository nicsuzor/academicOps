"""Tests for the UserPromptSubmit hook in plugins/aops/hooks/handlers.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_HOOKS = REPO_ROOT / "lib" / "hooks"
AOPS_HOOKS = REPO_ROOT / "plugins" / "aops" / "hooks"

if str(LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(LIB_HOOKS))
if str(AOPS_HOOKS) not in sys.path:
    sys.path.insert(0, str(AOPS_HOOKS))

import handlers  # type: ignore[import-not-found]
from dispatch import HookContext  # type: ignore[import-not-found]


def test_user_prompt_submit_registered_in_handlers():
    """Verify that user_prompt_submit and search_the_pkb are wired to UserPromptSubmit."""
    assert "UserPromptSubmit" in handlers.HANDLERS
    registered = handlers.HANDLERS["UserPromptSubmit"]
    assert handlers.user_prompt_submit in registered
    assert handlers.agy_user_prompt_submit in registered
    assert handlers.search_the_pkb in registered


def test_user_prompt_submit_pkb_search_success():
    """When pkb search succeeds, output is wrapped in <academicOps PKB search results> tags."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "what are the axioms of academicOps?"},
        hooks_dir=AOPS_HOOKS,
        cwd="/workspace",
    )

    mock_search_results = (
        "1. Rule sets and axioms ████████ 0.85\n   specs/AXIOMS.md\n   Found 1 match."
    )

    with patch.object(handlers, "_run_pkb_search", return_value=mock_search_results) as mock_search:
        res = handlers.search_the_pkb(ctx)
        mock_search.assert_called_once_with("what are the axioms of academicOps?", cwd="/workspace")
        assert res is not None
        expected_text = (
            "<academicOps PKB search results>\n"
            f"{mock_search_results}\n"
            "</academicOps PKB search results>"
        )
        assert res.inject_text == expected_text
        assert res.user_text is None


def test_user_prompt_submit_truncates_prompt_to_200():
    """Prompt query is truncated to 200 characters when passed to pkb search."""
    long_prompt = "a" * 350
    with (
        patch("shutil.which", return_value="/usr/bin/pkb"),
        patch("subprocess.run") as mock_run,
    ):
        mock_proc = subprocess.CompletedProcess(
            args=["/usr/bin/pkb", "search", "a" * 200],
            returncode=0,
            stdout="result line\n",
            stderr="",
        )
        mock_run.return_value = mock_proc
        out = handlers._run_pkb_search(long_prompt)
        assert out == "result line"
        assert mock_run.call_args[0][0] == ["/usr/bin/pkb", "search", "a" * 200]


def test_find_pkb_bin_on_path():
    """_find_pkb_bin resolves pkb when found on PATH."""
    with patch("shutil.which", return_value="/usr/bin/pkb"):
        assert handlers._find_pkb_bin() == "/usr/bin/pkb"


def test_find_pkb_bin_in_cwd(tmp_path):
    """_find_pkb_bin resolves pkb from hook cwd when not on PATH."""
    fake_pkb = tmp_path / "pkb"
    fake_pkb.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_pkb.chmod(0o755)

    with patch("shutil.which", return_value=None):
        found = handlers._find_pkb_bin(cwd=str(tmp_path))
        assert found == str(fake_pkb.resolve())


def test_find_pkb_bin_not_found(tmp_path):
    """_find_pkb_bin returns None when pkb is not on PATH or in cwd."""
    with patch("shutil.which", return_value=None):
        assert handlers._find_pkb_bin(cwd=str(tmp_path)) is None


def test_user_prompt_submit_fallback_when_prompt_is_empty():
    """When prompt is empty, search_the_pkb falls back to existing messages (honesty)."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": ""},
        hooks_dir=AOPS_HOOKS,
        agent_type="worker",
    )

    res = handlers.search_the_pkb(ctx)
    assert res is not None
    assert "<academicOps PKB search results>" not in res.inject_text
    assert "<id>honesty.md</id>" in res.inject_text
    assert res.user_text is not None
    assert "Honesty floor" in res.user_text


def test_user_prompt_submit_fallback_when_pkb_search_fails():
    """When pkb search returns None (binary missing or failure), falls back to existing messages."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "check status"},
        hooks_dir=AOPS_HOOKS,
        agent_type="worker",
    )

    with patch.object(handlers, "_run_pkb_search", return_value=None):
        res = handlers.search_the_pkb(ctx)
        assert res is not None
        assert "<academicOps PKB search results>" not in res.inject_text
        assert "<id>honesty.md</id>" in res.inject_text


def test_user_prompt_submit_fallback_with_pkb_context_message(tmp_path):
    """If pkb-context.md exists, fallback returns that message pair instead of honesty."""
    messages_dir = tmp_path / "messages"
    messages_dir.mkdir(parents=True)
    (messages_dir / "pkb-context.md").write_text("Custom PKB context message", encoding="utf-8")
    (messages_dir / "pkb-context.user.md").write_text("User notice", encoding="utf-8")

    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        raw={"prompt": "something"},
        hooks_dir=tmp_path,
        agent_type="worker",
    )

    with patch.object(handlers, "_run_pkb_search", return_value=None):
        res = handlers.search_the_pkb(ctx)
        assert res is not None
        assert res.inject_text == "Custom PKB context message"
        assert res.user_text == "User notice"


def test_dispatch_claude_userpromptsubmit_end_to_end():
    """End-to-end dispatch for Claude Code UserPromptSubmit with search success."""
    proc = subprocess.run(
        [
            sys.executable,
            str(LIB_HOOKS / "dispatch.py"),
            "claude",
            "UserPromptSubmit",
        ],
        input=json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "survey release"}),
        text=True,
        capture_output=True,
        cwd=str(AOPS_HOOKS),
    )
    assert proc.returncode == 0
    if proc.stdout.strip():
        data = json.loads(proc.stdout)
        specific = data.get("hookSpecificOutput", {})
        assert specific.get("hookEventName") == "UserPromptSubmit"
        content = specific.get("additionalContext", "")
        # Either PKB search result or fallback honesty message
        assert (
            content.startswith("<academicOps PKB search results>")
            or "<id>honesty.md</id>" in content
        )


def test_dispatch_agy_preinvocation_end_to_end():
    """End-to-end dispatch for AGY PreInvocation (mapped to UserPromptSubmit) with search success."""
    proc = subprocess.run(
        [
            sys.executable,
            str(LIB_HOOKS / "dispatch.py"),
            "agy",
            "PreInvocation",
        ],
        input=json.dumps({"hook_event_name": "PreInvocation", "prompt": "survey release"}),
        text=True,
        capture_output=True,
        cwd=str(AOPS_HOOKS),
    )
    assert proc.returncode == 0
    if proc.stdout.strip():
        data = json.loads(proc.stdout)
        steps = data.get("injectSteps", [])
        assert len(steps) > 0
        msg = steps[0].get("ephemeralMessage", "")
        assert msg.startswith("<academicOps PKB search results>") or "<id>honesty.md</id>" in msg
