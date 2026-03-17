import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def get_git_commit_sha(aops_root: Path) -> str:
    """Get the current git commit SHA."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=aops_root, text=True
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def write_plugin_version(plugin_dir: Path, commit_sha: str) -> Path:
    """Write the current version and commit to the plugin directory.

    Returns:
        Path to the created version file.
    """
    version_file = plugin_dir / ".claude-plugin" / ".aops-version"
    version_file.parent.mkdir(parents=True, exist_ok=True)

    version_data = {
        "source_commit": commit_sha,
        "build_timestamp": subprocess.run(
            ["date", "-Iseconds"], capture_output=True, text=True
        ).stdout.strip(),
    }

    version_file.write_text(json.dumps(version_data, indent=2))
    return version_file


def safe_copy(src: Path, dst: Path) -> None:
    """Copy file or directory, handling existing destinations."""
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def safe_symlink(src: Path, dst: Path) -> None:
    """Create symlink, handling existing destinations."""
    if dst.is_dir() and not dst.is_symlink():
        shutil.rmtree(dst)
    elif dst.exists() or dst.is_symlink():
        dst.unlink()
    dst.symlink_to(src)


def convert_mcp_to_gemini(mcp_config: dict[str, Any]) -> dict[str, Any]:
    """Convert Claude-style MCP config to Gemini CLI extension format."""
    gemini_mcp = {}
    for server_name, server_config in mcp_config.items():
        # Gemini uses 'command' and 'args' keys directly
        gemini_mcp[server_name] = {
            "command": server_config.get("command"),
            "args": server_config.get("args", []),
            "env": server_config.get("env", {}),
        }
    return gemini_mcp


def convert_gemini_to_antigravity(gemini_mcps: dict[str, Any]) -> dict[str, Any]:
    """Convert Gemini MCP config to Antigravity format (adding 'args' as empty if missing)."""
    ag_mcps = {}
    for name, config in gemini_mcps.items():
        ag_mcps[name] = {
            "command": config.get("command"),
            "args": config.get("args", []),
            "env": config.get("env", {}),
        }
    return ag_mcps


def emit_version_mismatch_warning(
    source_commit: str,
    installed_commit: str,
) -> None:
    """Emit a warning about version mismatch between source and installed plugin."""
    print("", file=sys.stderr)
    print("⚠️  PLUGIN VERSION MISMATCH", file=sys.stderr)
    print(f"   Source commit:    {source_commit}", file=sys.stderr)
    print(f"   Installed commit: {installed_commit[:8]}...", file=sys.stderr)
    print("   The installed Claude plugin may be outdated.", file=sys.stderr)
    print("   Consider reinstalling the plugin in Claude Desktop.", file=sys.stderr)
    print("", file=sys.stderr)


def generate_gemini_hooks(
    claude_hooks: dict[str, Any], aops_path: str, router_script_path: str
) -> dict[str, Any]:
    """Generate Gemini hooks configuration from Claude hooks."""

    CLAUDE_TO_GEMINI = {
        "PreToolUse": ["BeforeTool"],
        "PostToolUse": ["AfterTool"],
        "UserPromptSubmit": ["BeforeAgent"],
        "Stop": ["SessionEnd", "AfterAgent"],
        "SessionStart": ["SessionStart"],
        "SessionEnd": ["SessionEnd"],
        "SubagentStart": ["BeforeTool"],
        "SubagentStop": ["AfterTool"],
        "Notification": ["BeforeAgent"],
        "PreCompact": ["BeforeAgent"],
    }
    MATCHERS = {"SessionStart": "startup", "SessionEnd": "*", "BeforeAgent": "*", "AfterAgent": "*"}

    VALID_GEMINI_EVENTS = (
        "SessionStart",
        "BeforeAgent",
        "AfterAgent",
        "BeforeTool",
        "AfterTool",
        "SessionEnd",
    )
    gemini_hooks = {}

    for claude_event, hook_list in claude_hooks.items():
        if claude_event.endswith("-disabled"):
            continue

        target_events = CLAUDE_TO_GEMINI.get(claude_event, [claude_event])
        for gemini_event in target_events:
            if gemini_event not in VALID_GEMINI_EVENTS:
                continue

            if gemini_event not in gemini_hooks:
                gemini_hooks[gemini_event] = []

            for hook_entry in hook_list:
                new_entry = {}
                if "matcher" not in hook_entry:
                    new_entry["matcher"] = MATCHERS.get(gemini_event, "*")

                for key, value in hook_entry.items():
                    if key == "hooks":
                        new_hooks = []
                        for hook in value:
                            new_hook = dict(hook)
                            if "command" in new_hook:
                                cmd = f"bash {router_script_path} --client gemini {gemini_event}"
                                new_hook["command"] = cmd
                            new_hooks.append(new_hook)
                        new_entry[key] = new_hooks
                    else:
                        new_entry[key] = value
                gemini_hooks[gemini_event].append(new_entry)

    return gemini_hooks

def check_installed_plugin_version(
    plugin_name: str,
    source_commit: str,
    installed_plugins_path: Path | None = None,
) -> tuple[bool, str | None]:
    """Check if installed plugin matches source version.

    Args:
        plugin_name: Name of plugin (e.g., "aops-core")
        source_commit: Current git commit SHA of source
        installed_plugins_path: Path to installed_plugins.json.
            Defaults to ~/.claude/plugins/installed_plugins.json

    Returns:
        Tuple of (version_matches: bool, installed_commit: Optional[str])
        If plugin not installed, returns (True, None) - no mismatch to report.
    """
    if installed_plugins_path is None:
        installed_plugins_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"

    if not installed_plugins_path.exists():
        return (True, None)  # No installed plugins file, nothing to compare

    try:
        with open(installed_plugins_path) as f:
            data = json.load(f)

        # Claude uses "aops-core@aops" format for plugin keys
        plugin_key = f"{plugin_name}@aops"
        plugins = data.get("plugins", {})

        if plugin_key not in plugins:
            return (True, None)  # Plugin not installed

        # Get the first (and usually only) installation
        installs = plugins[plugin_key]
        if not installs:
            return (True, None)

        installed_commit = installs[0].get("gitCommitSha")
        if not installed_commit:
            return (True, None)

        # Compare: installed commit should start with source commit (or vice versa)
        # since one might be short and one long
        if installed_commit.startswith(source_commit) or source_commit.startswith(
            installed_commit[:8]
        ):
            return (True, installed_commit)

        return (False, installed_commit)

    except (json.JSONDecodeError, KeyError, IndexError):
        return (True, None)  # Can't determine, assume OK
