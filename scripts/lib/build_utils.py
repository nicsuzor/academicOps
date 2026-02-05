import os
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def format_path_for_json(path: str) -> str:
    """Ensure path is absolute and normalized."""
    return str(Path(path).resolve())


def convert_mcp_server_to_gemini(
    name: str, config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Convert a single MCP server config from Claude to Gemini format."""
    server_type = config.get("type", "stdio")
    result: Dict[str, Any] = {}

    if server_type == "http":
        if "url" not in config:
            print(f"  ⚠️  {name}: HTTP server missing 'url', skipping", file=sys.stderr)
            return None
        result["url"] = config["url"]
        if "headers" in config:
            result["headers"] = config["headers"]

    elif server_type == "stdio":
        if "command" not in config:
            print(
                f"  ⚠️  {name}: stdio server missing 'command', skipping",
                file=sys.stderr,
            )
            return None
        result["command"] = config["command"]
        if "args" in config:
            result["args"] = config["args"]
        if "env" in config and config["env"]:
            result["env"] = config["env"]
    else:
        # Fallback: if it already looks like a gemini config (no type, has command/url)
        if "command" in config or "url" in config:
            return config
        print(
            f"  ⚠️  {name}: Unknown server type '{server_type}', skipping",
            file=sys.stderr,
        )
        return None

    return result


def convert_mcp_to_gemini(servers: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a dictionary of MCP servers to Gemini format."""
    gemini_servers = {}
    for name, config in servers.items():
        converted = convert_mcp_server_to_gemini(name, config)
        if converted:
            gemini_servers[name] = converted
    return gemini_servers


def convert_gemini_to_antigravity(servers: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Gemini MCP config to Antigravity format (url -> serverUrl)."""
    ag_servers = {}
    for name, config in servers.items():
        new_config = config.copy()
        if "url" in new_config:
            new_config["serverUrl"] = new_config.pop("url")
        ag_servers[name] = new_config
    return ag_servers


def safe_symlink(src: Path, dst: Path):
    """Create a symlink, removing the destination if it exists."""
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    if not dst.parent.exists():
        dst.parent.mkdir(parents=True)

    os.symlink(src, dst)
    print(f"  Linked {src.name} -> {dst}")


def safe_copy(src: Path, dst: Path):
    """Copy file or directory, removing the destination if it exists.

    Use this instead of safe_symlink when you need isolated copies
    (e.g., for Gemini dist to avoid polluting Claude canonical source).
    """
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    if not dst.parent.exists():
        dst.parent.mkdir(parents=True)

    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    print(f"  Copied {src.name} -> {dst}")


def get_git_commit_sha(repo_path: Optional[Path] = None) -> Optional[str]:
    """Get the current git commit SHA for version tracking.

    Args:
        repo_path: Path to the git repository. If None, uses current directory.

    Returns:
        The short commit SHA (8 chars) or None if not a git repo.
    """
    try:
        cmd = ["git", "rev-parse", "--short=8", "HEAD"]
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def write_plugin_version(plugin_dir: Path, commit_sha: str) -> Path:
    """Write version info to plugin directory for tracking.

    Creates .aops-version file with git commit SHA.
    This enables install-time warnings when installed plugins drift from source.

    Args:
        plugin_dir: Path to plugin directory (e.g., aops-core/)
        commit_sha: Git commit SHA to record

    Returns:
        Path to the created version file.
    """
    version_file = plugin_dir / ".claude-plugin" / ".aops-version"
    version_file.parent.mkdir(parents=True, exist_ok=True)

    version_data = {
        "source_commit": commit_sha,
        "build_timestamp": subprocess.run(
            ["date", "-Iseconds"],
            capture_output=True,
            text=True,
        ).stdout.strip(),
    }

    with open(version_file, "w") as f:
        json.dump(version_data, f, indent=2)

    print(f"  ✓ Wrote version info: {commit_sha}")
    return version_file


def check_installed_plugin_version(
    plugin_name: str,
    source_commit: str,
    installed_plugins_path: Optional[Path] = None,
) -> tuple[bool, Optional[str]]:
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

        installed_commit = installs[0].get("gitCommitSha", "")

        # Compare: installed commit should start with source commit (or vice versa)
        # since one might be short and one long
        if installed_commit.startswith(source_commit) or source_commit.startswith(installed_commit[:8]):
            return (True, installed_commit)

        return (False, installed_commit)

    except (json.JSONDecodeError, KeyError, IndexError):
        return (True, None)  # Can't determine, assume OK


def emit_version_mismatch_warning(
    plugin_name: str,
    source_commit: str,
    installed_commit: str,
) -> None:
    """Emit a warning about version mismatch between source and installed plugin.

    This is informational only - does not block installation.
    """
    print(f"\n⚠️  VERSION MISMATCH: {plugin_name}", file=sys.stderr)
    print(f"   Source commit:    {source_commit}", file=sys.stderr)
    print(f"   Installed commit: {installed_commit[:8]}...", file=sys.stderr)
    print("   The installed Claude plugin may be outdated.", file=sys.stderr)
    print("   Consider reinstalling the plugin in Claude Desktop.", file=sys.stderr)
    print("", file=sys.stderr)


def generate_gemini_hooks(
    claude_hooks: Dict[str, Any], aops_path: str, router_script_path: str
) -> Dict[str, Any]:
    """Generate Gemini hooks configuration from Claude hooks."""

    CLAUDE_TO_GEMINI = {
        "SessionStart": ["SessionStart"],
        "PreToolUse": ["BeforeTool"],
        "PostToolUse": ["AfterTool"],
        "UserPromptSubmit": ["BeforeAgent"],
        "Stop": ["SessionEnd", "AfterAgent"],
        "Notification": ["Notification"],
        "PreCompact": ["PreCompress"],
    }
    MATCHERS = {"SessionStart": "startup", "SessionEnd": "*"}

    gemini_hooks = {}

    # Ensure paths are absolute (converts /home/nic/src/... to /home/nic/src/...)
    # But router_script_path passed in should already be the dist path usually

    for c_event, g_events in CLAUDE_TO_GEMINI.items():
        if c_event in claude_hooks:
            # Extract timeout from the first hook definition in Claude config
            # Claude format: { "SessionStart": [{"hooks": [{"timeout": 5000}]}] } or similar deep nesting
            try:
                # Based on create_extension.py interrogation of structure
                timeout = (
                    claude_hooks[c_event][0].get("hooks", [{}])[0].get("timeout", 5000)
                )
            except (IndexError, KeyError, TypeError):
                timeout = 5000  # Default

            for g_event in g_events:
                matcher = MATCHERS.get(g_event, "*")
                if g_event not in gemini_hooks:
                    gemini_hooks[g_event] = []

                # Convert CamelCase to kebab-case for the name suffix
                # e.g., SessionStart -> session-start
                slug = "".join(
                    ["-" + c.lower() if c.isupper() else c for c in g_event]
                ).lstrip("-")

                gemini_hooks[g_event].append(
                    {
                        "matcher": matcher,
                        "hooks": [
                            {
                                "name": f"aops-router-{slug}",
                                "type": "command",
                                "command": f"uv run --directory {aops_path} python {router_script_path} {g_event}",
                                "timeout": timeout,
                            }
                        ],
                    }
                )
    return gemini_hooks
