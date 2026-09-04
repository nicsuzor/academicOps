import json
import os
import re
import subprocess
from pathlib import Path

import pytest

# Locate the dist directory containing the built plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_ROOT = PROJECT_ROOT / "dist"


def get_plugin_dirs():
    """Returns a list of all built plugin directories in dist/.

    Never returns [] on an unbuilt tree: an empty parametrize list reports the
    whole module as green, silently voiding the manifest checks. Instead:

    - dist/ absent on a developer checkout: skip the module explicitly, with a
      reason naming the command that would enable it. A collection *error* here
      makes ``pytest tests/`` exit non-zero on any source-only tree, which
      destroys the suite's exit code as a signal for every other test.
      Nothing is lost: CI builds dist/ (``uv run python -m build.build``) before
      invoking pytest — see .github/workflows/pytest.yml — and pr-pipeline.yml
      runs that workflow on every PR, so these checks still gate every merge.
    - dist/ absent under CI: still a hard error. The build step is supposed to
      have run, so a missing dist/ there is a broken pipeline, not a source
      checkout, and must not degrade to a silent skip.
    - dist/ present but containing no plugin directories: always a hard error,
      in CI or not. That is a broken build, not an unbuilt tree.
    """
    if not DIST_ROOT.exists():
        if os.environ.get("CI"):
            raise RuntimeError(
                f"{DIST_ROOT} does not exist under CI — the build step must run before pytest"
            )
        pytest.skip(
            f"{DIST_ROOT} does not exist — run 'make build' to enable the manifest checks",
            allow_module_level=True,
        )

    plugin_dirs = []
    for d in DIST_ROOT.iterdir():
        if d.is_dir() and (
            d.name.endswith("-claude") or d.name.endswith("-agy") or d.name.endswith("-openclaw")
        ):
            plugin_dirs.append(d)
    cowork_dir = DIST_ROOT / "cowork"
    if cowork_dir.is_dir():
        for d in cowork_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                plugin_dirs.append(d)
    if not plugin_dirs:
        raise RuntimeError(f"{DIST_ROOT} contains no built plugin directories — run 'make build'")
    return sorted(plugin_dirs)


@pytest.mark.parametrize(
    "plugin_dir",
    get_plugin_dirs(),
    ids=lambda d: f"cowork/{d.name}" if d.parent.name == "cowork" else d.name,
)
def test_plugin_validates_against_cli(plugin_dir):
    """
    Checks each built plugin package against the native CLI plugin validate command.
    """
    # Determine which CLI to use based on the plugin's target platform
    if (
        plugin_dir.name.endswith("-claude")
        or plugin_dir.name.endswith("-openclaw")
        or plugin_dir.parent.name == "cowork"
    ):
        cli_command = ["claude", "plugin", "validate", str(plugin_dir)]
    elif plugin_dir.name.endswith("-agy"):
        cli_command = ["agy", "plugin", "validate", str(plugin_dir)]
    else:
        pytest.skip(f"Unrecognized plugin platform for directory: {plugin_dir.name}")

    try:
        # Execute the native CLI validation command
        result = subprocess.run(cli_command, capture_output=True, text=True, check=False)

        # Ensure the CLI considers the plugin manifest format valid
        assert result.returncode == 0, (
            f"Native plugin validation failed for {plugin_dir.name}.\n"
            f"Command: {' '.join(cli_command)}\n"
            f"Exit Code: {result.returncode}\n"
            f"Stdout:\n{result.stdout}\n"
            f"Stderr:\n{result.stderr}"
        )

    except FileNotFoundError:
        # Gracefully skip if the CLI tool is not installed in the current environment
        pytest.skip(
            f"CLI tool '{cli_command[0]}' not found on the system. Skipping native validation test."
        )


def _extract_hook_script_paths(hooks_config: dict) -> set[str]:
    """Pull every ``.py`` script path referenced by a hooks.json's command/args fields.

    Raw command strings can be a bare ``${CLAUDE_PLUGIN_ROOT}/hooks/foo.py`` arg,
    or a quoted path embedded in a ``bash -c '...'`` string (Claude Code's
    template shape). Either way, a real script path is a whitespace/quote-free
    token ending in ``.py``.
    """
    paths: set[str] = set()
    for event_entries in hooks_config.get("hooks", {}).values():
        for entry in event_entries:
            for hook in entry.get("hooks", []):
                pieces = []
                if "command" in hook:
                    pieces.append(hook["command"])
                pieces.extend(hook.get("args", []))
                for piece in pieces:
                    paths.update(re.findall(r'[^\s"\']+\.py', piece))
    return paths


def _resolve_hook_path(plugin_dir: Path, raw_path: str) -> Path:
    cleaned = raw_path.replace("${CLAUDE_PLUGIN_ROOT}", "").replace("${AGY_PLUGIN_ROOT}", "")
    cleaned = cleaned.lstrip("/")
    return plugin_dir / cleaned


@pytest.mark.parametrize(
    "plugin_dir",
    get_plugin_dirs(),
    ids=lambda d: f"cowork/{d.name}" if d.parent.name == "cowork" else d.name,
)
def test_hooks_json_script_paths_resolve_to_shipped_files(plugin_dir):
    """Every hook command/args script path declared in a built plugin's hooks.json
    must resolve to a real file shipped inside that same plugin artifact.

    Structural-prevention regression test for the v0.5 core-plugin BLOCKER found
    by marsha's QA review: `aops/templates/hooks.template.json`
    wired PreToolUse/Stop to `hooks/gate_dispatch.py`, a script that never
    shipped in the built core package (it moved to aops-jr in the jr/ida
    extraction, PR #2326, and core's own manifest was never repointed). Neither
    `claude plugin validate` nor the rest of the pytest suite caught this
    because nothing checked that a declared hook command resolves to a real
    file on disk — this test closes that coverage gap so the same class of
    defect fails a build instead of shipping silently.
    """
    if (
        plugin_dir.name.endswith("-claude")
        or plugin_dir.name.endswith("-openclaw")
        or plugin_dir.parent.name == "cowork"
    ):
        hooks_json_path = plugin_dir / "hooks" / "hooks.json"
    elif plugin_dir.name.endswith("-agy"):
        hooks_json_path = plugin_dir / "hooks.json"
    else:
        pytest.skip(f"Unrecognized plugin platform for directory: {plugin_dir.name}")

    if not hooks_json_path.exists():
        pytest.skip(f"No hooks.json shipped for {plugin_dir.name} (plugin declares no hooks)")

    with open(hooks_json_path) as f:
        hooks_config = json.load(f)

    script_paths = _extract_hook_script_paths(hooks_config)
    missing = []
    for raw_path in sorted(script_paths):
        resolved = _resolve_hook_path(plugin_dir, raw_path)
        if not resolved.is_file():
            missing.append(f"  {raw_path} -> {resolved} (does not exist)")

    assert not missing, (
        f"{plugin_dir.name}: hooks.json declares hook script(s) that do not exist "
        f"in the built artifact:\n" + "\n".join(missing)
    )


# ---------------------------------------------------------------------------
# Stop/SubagentStop gate wiring, asserted against the *built* artifact rather
# than the source manifest — a template can be right while the build drops it.
# pkb ships neither: its stop gate is blocked server-side, and this pins that
# it stays unwired rather than being swept in by accident.
# ---------------------------------------------------------------------------


def _claude_hook_events(plugin_dir_name: str) -> set[str]:
    hooks_json = DIST_ROOT / plugin_dir_name / "hooks" / "hooks.json"
    if not hooks_json.exists():
        return set()
    return set(json.loads(hooks_json.read_text())["hooks"].keys())


def _agy_hook_events(plugin_dir_name: str) -> set[str]:
    hooks_json = DIST_ROOT / plugin_dir_name / "hooks.json"
    if not hooks_json.exists():
        return set()
    return set(
        json.loads(hooks_json.read_text()).get(plugin_dir_name.removesuffix("-agy"), {}).keys()
    )


@pytest.mark.skipif(not DIST_ROOT.exists(), reason=f"{DIST_ROOT} does not exist — run 'make build'")
def test_rbg_ships_the_stop_gate_on_claude_only():
    """rbg's Stop-side ``rule_check`` handler is entirely commented out
    (plugins/rbg/hooks/handlers.py — "TEMPORARY... do not delete the
    entries", pending aops_d27c7aea), so there is nothing on agy for it to
    advise. agy's ``PostInvocation`` — the only wire event that used to
    alias onto canonical ``Stop`` — no longer maps to anything at all
    (aops_73e25af2: it fired once per internal invocation/tool-call
    round-trip, not once per turn), so rbg no longer registers it."""
    assert {"Stop", "SubagentStop"} <= _claude_hook_events("rbg-claude")
    assert "PostInvocation" not in _agy_hook_events("rbg-agy")


@pytest.mark.skipif(not DIST_ROOT.exists(), reason=f"{DIST_ROOT} does not exist — run 'make build'")
def test_ida_ships_the_quiet_gate_on_claude_only():
    """ida's quiet gate directs the face to strip its own reply before it
    speaks to the person. Registered on claude ``PostToolBatch`` only:
    claude ``SubagentStop`` fires on the *stopping subagent's* own context, so
    wiring it there would nag a worker about a reply it never sends to the
    person — the fix for the defect the superseded gate-wiring-v07 branch
    shipped. ida ships no agy hooks.json at all: its only prior agy wiring was
    ``PostInvocation``, which dispatch.py no longer maps to anything
    (aops_73e25af2 — it fired once per internal invocation/tool-call
    round-trip, not once per turn), and ``be_quiet`` was never wired to
    canonical ``Stop`` in the first place (only to the commented-out
    ``PostToolBatch`` key), so nothing on agy was ever live.

    ida is an agent hosted inside the aops plugin (plugins/aops/agents/ida.md),
    so its gate ships from ``aops-claude``, not a standalone ``ida`` plugin."""
    events = _claude_hook_events("aops-claude")
    assert "PostToolBatch" in events
    assert "SubagentStop" not in events
    assert "PostToolBatch" not in _agy_hook_events("aops-agy")


@pytest.mark.skipif(not DIST_ROOT.exists(), reason=f"{DIST_ROOT} does not exist — run 'make build'")
def test_aops_ships_the_handback_reminders():
    """``PostToolBatch`` binds the receiver; ``Stop`` binds the worker at handback.
    Both surfaces ship from aops, which owns dispatch and the handback doctrine."""
    assert {"PostToolBatch", "Stop"} <= _claude_hook_events("aops-claude")
    assert "PostInvocation" not in _agy_hook_events("aops-agy")
