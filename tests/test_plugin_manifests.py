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
