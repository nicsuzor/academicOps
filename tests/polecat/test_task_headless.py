"""Regression test: `-t` forces headless for every agent runtime.

`-t <task-id>` *is* the autonomous task dispatch — the worker runs
`/pull <id>` and exits. Headless must therefore not depend on whether the
launcher happened to have a TTY.

agy always forced `--print` on this path. claude gated it behind
`not is_interactive`, so the identical dispatch launched from a tmux pane
(a real TTY) produced:

    claude --dangerously-skip-permissions --setting-sources=user,project /pull <id>

with no `--print`. claude opened its interactive UI and idled at the prompt
forever instead of working the task.
"""

import pytest

from lib.polecat.cli import _build_inner_command

AGENTS = ("claude", "agy")


@pytest.mark.parametrize("agent_cmd", AGENTS)
@pytest.mark.parametrize("is_interactive", [True, False])
def test_task_dispatch_is_always_headless(agent_cmd, is_interactive):
    inner_cmd, _, seeded_from_task, seeded_prompt = _build_inner_command(
        agent_cmd,
        (),
        is_interactive=is_interactive,
        explicit_headless=False,
        task="aops_123",
        config={},
    )
    assert seeded_from_task is True
    assert seeded_prompt == "/pkb:pull aops_123"
    if agent_cmd == "claude":
        assert "--print" in inner_cmd, inner_cmd


def test_print_is_not_added_twice_for_claude():
    inner_cmd, _, _, _ = _build_inner_command(
        "claude", (), is_interactive=True, explicit_headless=False, task="aops_123", config={}
    )
    assert inner_cmd.count("--print") == 1, inner_cmd


@pytest.mark.parametrize("agent_cmd", AGENTS)
def test_interactive_session_without_task_stays_interactive(agent_cmd):
    """The tmux debug workflow: no `-t`, real TTY, no forced headless."""
    inner_cmd, _, _, _ = _build_inner_command(
        agent_cmd, (), is_interactive=True, explicit_headless=False, task=None, config={}
    )
    assert "--print" not in inner_cmd, inner_cmd


@pytest.mark.parametrize("agent_cmd", AGENTS)
def test_interactive_task_dispatch_is_interactive(agent_cmd):
    """Passing interactive=True with a task marks seeded_from_task and seeded_prompt."""
    inner_cmd, _, seeded_from_task, seeded_prompt = _build_inner_command(
        agent_cmd,
        (),
        is_interactive=True,
        explicit_headless=False,
        task="aops_123",
        config={},
        interactive=True,
    )
    assert seeded_from_task is True
    assert seeded_prompt == "/pkb:pull aops_123"
    assert "--print" not in inner_cmd


def test_agy_free_text_prompt_without_interactive_flag_is_headless():
    """When a free text prompt is run with agy without -i, it must use --print,

    even if the invoking shell is interactive (has a TTY).
    """
    inner_cmd, _, _, seeded_prompt = _build_inner_command(
        "agy",
        ("free text prompt",),
        is_interactive=True,
        explicit_headless=False,
        task=None,
        config={},
        interactive=False,
    )
    assert "--prompt-interactive" not in inner_cmd, inner_cmd
    assert "--print" in inner_cmd, inner_cmd
    assert "free text prompt" in inner_cmd
    assert seeded_prompt == "free text prompt"


def test_agy_free_text_prompt_with_interactive_flag_uses_prompt_interactive():
    """When a free text prompt is run with agy with -i (interactive=True),

    it must use --prompt-interactive.
    """
    inner_cmd, _, _, seeded_prompt = _build_inner_command(
        "agy",
        ("free text prompt",),
        is_interactive=True,
        explicit_headless=False,
        task=None,
        config={},
        interactive=True,
    )
    assert "--prompt-interactive" in inner_cmd, inner_cmd
    assert "--print" not in inner_cmd, inner_cmd
    assert "free text prompt" in inner_cmd
    assert seeded_prompt == "free text prompt"


def test_agy_explicit_prompt_without_interactive_flag_is_headless():
    """When --prompt is passed to agy without -i, it must use --prompt,

    not --prompt-interactive.
    """
    inner_cmd, _, _, seeded_prompt = _build_inner_command(
        "agy",
        (),
        is_interactive=True,
        explicit_headless=False,
        task=None,
        prompt="hello world",
        config={},
        interactive=False,
    )
    assert "--prompt-interactive" not in inner_cmd, inner_cmd
    assert "--prompt" in inner_cmd, inner_cmd
    assert "hello world" in inner_cmd
    assert seeded_prompt == "hello world"


def test_agy_explicit_prompt_with_interactive_flag_uses_prompt_interactive():
    """When --prompt is passed to agy with -i, it must use --prompt-interactive."""
    inner_cmd, _, _, seeded_prompt = _build_inner_command(
        "agy",
        (),
        is_interactive=True,
        explicit_headless=False,
        task=None,
        prompt="hello world",
        config={},
        interactive=True,
    )
    assert "--prompt-interactive" in inner_cmd, inner_cmd
    assert "--prompt" not in inner_cmd, inner_cmd
    assert "hello world" in inner_cmd
    assert seeded_prompt == "hello world"
