import json
import re
import subprocess
from pathlib import Path

import pytest

# Locate the dist directory containing the built plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_ROOT = PROJECT_ROOT / "dist"


def get_plugin_dirs():
    """Returns a list of all built plugin directories in dist/."""
    if not DIST_ROOT.exists():
        return []

    plugin_dirs = []
    for d in DIST_ROOT.iterdir():
        if d.is_dir() and (d.name.endswith("-claude") or d.name.endswith("-antigravity")):
            plugin_dirs.append(d)
    return sorted(plugin_dirs)


@pytest.mark.parametrize("plugin_dir", get_plugin_dirs(), ids=lambda d: d.name)
def test_plugin_validates_against_cli(plugin_dir):
    """
    Checks each built plugin package against the native CLI plugin validate command.
    """
    # Determine which CLI to use based on the plugin's target platform
    if plugin_dir.name.endswith("-claude"):
        cli_command = ["claude", "plugin", "validate", str(plugin_dir)]
    elif plugin_dir.name.endswith("-antigravity"):
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


@pytest.mark.parametrize("plugin_dir", get_plugin_dirs(), ids=lambda d: d.name)
def test_hooks_json_script_paths_resolve_to_shipped_files(plugin_dir):
    """Every hook command/args script path declared in a built plugin's hooks.json
    must resolve to a real file shipped inside that same plugin artifact.

    Structural-prevention regression test for the v0.5 core-plugin BLOCKER found
    by marsha's QA review (epic_21042b5f): `aops/templates/hooks.template.json`
    wired PreToolUse/Stop to `hooks/gate_dispatch.py`, a script that never
    shipped in the built core package (it moved to aops-jr in the jr/ida
    extraction, PR #2326, and core's own manifest was never repointed). Neither
    `claude plugin validate` nor the rest of the pytest suite caught this
    because nothing checked that a declared hook command resolves to a real
    file on disk — this test closes that coverage gap so the same class of
    defect fails a build instead of shipping silently.
    """
    if plugin_dir.name.endswith("-claude"):
        hooks_json_path = plugin_dir / "hooks" / "hooks.json"
    elif plugin_dir.name.endswith("-antigravity"):
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
