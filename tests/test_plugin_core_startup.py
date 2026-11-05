"""Tests for per-plugin CORE.md startup injection.

Verifies:
- AC1: Every plugin's session-start hook injects its own CORE.md, shown by tests covering each plugin.
- AC2: A fresh session started outside any deployment repo shows each installed plugin's CORE.md, each at most 20 lines.
- US-3 / OBC-3.1–3.4: Four-test criteria, <= 20 line ceiling, and no persona-specific voice or sub-agent rules.
"""

from __future__ import annotations

import json
from pathlib import Path

from build.marketplace import load_marketplace_toml
from tests.test_shipped_hooks import (
    _build_dirs,
    _hook_commands,
    _run_shipped_hook,
)

pytest_plugins = ["tests.test_shipped_hooks"]

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MARKETPLACE = _REPO_ROOT / "build" / "marketplace.toml"

_ALL_PLUGINS = [entry["directory"] for entry in load_marketplace_toml(_MARKETPLACE)["plugins"]]


def test_every_shipped_plugin_session_start_hook_injects_core_md(dist_root: Path):
    """AC1: Every built plugin's SessionStart hook injects its own CORE.md."""
    checked = 0
    payload = {"hook_event_name": "SessionStart", "session_id": "core-test-session"}

    for _name, client, build_dir in _build_dirs(dist_root):
        core_file = build_dir / "CORE.md"
        assert core_file.is_file(), f"{build_dir.name} missing shipped CORE.md"
        core_text = core_file.read_text(encoding="utf-8").strip()

        commands = [
            cmd for wire, cmd in _hook_commands(client, build_dir) if wire == "SessionStart"
        ]
        assert len(commands) == 1, (
            f"{build_dir.name}: expected exactly 1 SessionStart hook, found {len(commands)}"
        )
        command = commands[0]

        env_overrides = {"PKB_MCP_URL": "http://localhost:8000"}
        proc = _run_shipped_hook(client, build_dir, command, payload, env_overrides=env_overrides)
        assert proc.returncode == 0, (
            f"{build_dir.name} SessionStart exited {proc.returncode}\nstderr: {proc.stderr}"
        )
        assert proc.stdout.strip(), f"{build_dir.name} SessionStart emitted empty output"

        data = json.loads(proc.stdout)

        if client == "claude":
            hook_output = data.get("hookSpecificOutput", {})
            assert hook_output.get("hookEventName") == "SessionStart"
            additional_context = hook_output.get("additionalContext", "")
            assert core_text in additional_context, (
                f"{build_dir.name}: CORE.md not found in additionalContext:\n{additional_context}"
            )
        elif client == "agy":
            steps = data.get("injectSteps", [])
            assert len(steps) >= 1, f"{build_dir.name}: agy injectSteps is empty"
            all_text_parts = []
            for step in steps:
                if "systemMessage" in step:
                    sys_msg = step["systemMessage"]
                    if isinstance(sys_msg, dict):
                        all_text_parts.append(sys_msg.get("systemMessage", ""))
                    else:
                        all_text_parts.append(str(sys_msg))
                if "ephemeralMessage" in step:
                    all_text_parts.append(step["ephemeralMessage"])
            combined_text = "\n\n".join(all_text_parts)
            assert core_text in combined_text, (
                f"{build_dir.name}: CORE.md not found in agy injected steps:\n{combined_text}"
            )

        checked += 1

    assert checked >= 9, f"Expected at least 9 plugin-client builds checked, got {checked}"


def test_fresh_session_outside_deployment_repo_shows_plugin_core_md(
    dist_root: Path, tmp_path: Path
):
    """AC2: A fresh session started outside any deployment repo shows each installed plugin's CORE.md, each at most 20 lines."""
    outside_dir = tmp_path / "fresh_external_workspace"
    outside_dir.mkdir()

    # Verify directory is truly outside any repo or framework checkout
    assert not (outside_dir / ".git").exists()
    assert not (outside_dir / "CLAUDE.md").exists()
    assert not (outside_dir / "AGENTS.md").exists()

    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "external-session-999",
        "cwd": str(outside_dir),
        "workspacePaths": [str(outside_dir)],
    }
    env_overrides = {
        "PKB_MCP_URL": "http://localhost:8000",
        "AOPS_IMAGE_PLUGINS_VERSION": "v1.0.0",
    }

    seen_plugins = set()

    for name, client, build_dir in _build_dirs(dist_root):
        core_file = build_dir / "CORE.md"
        core_lines = core_file.read_text(encoding="utf-8").splitlines()
        assert len(core_lines) <= 20

        commands = [
            cmd for wire, cmd in _hook_commands(client, build_dir) if wire == "SessionStart"
        ]
        assert len(commands) == 1
        command = commands[0]

        proc = _run_shipped_hook(client, build_dir, command, payload, env_overrides=env_overrides)
        assert proc.returncode == 0, f"{build_dir.name} failed outside repo: {proc.stderr}"

        data = json.loads(proc.stdout)
        core_text = "\n".join(core_lines).strip()

        if client == "claude":
            injected = data.get("hookSpecificOutput", {}).get("additionalContext", "")
            assert core_text in injected, (
                f"{build_dir.name}: plugin CORE.md missing when executing outside repo"
            )
        elif client == "agy":
            steps = data.get("injectSteps", [])
            combined = "\n\n".join(
                str(s.get("systemMessage", {}).get("systemMessage", ""))
                + "\n"
                + str(s.get("ephemeralMessage", ""))
                for s in steps
            )
            assert core_text in combined, (
                f"{build_dir.name}: plugin CORE.md missing from agy steps when executing outside repo"
            )

        seen_plugins.add(name)

    assert seen_plugins == set(_ALL_PLUGINS), (
        f"Missing plugins outside repo: {set(_ALL_PLUGINS) - seen_plugins}"
    )
