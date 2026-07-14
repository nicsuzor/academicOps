#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import click
import yaml


def load_config():
    """Load configuration from $AOPS_POLECAT_CONFIG, $AOPS_SESSIONS/polecat.yaml, or home fallback."""
    cfg_path = os.environ.get("AOPS_POLECAT_CONFIG")
    if not cfg_path:
        sessions = os.environ.get("AOPS_SESSIONS")
        if sessions:
            cfg_path = os.path.join(sessions, "polecat.yaml")

    if cfg_path and os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            click.echo(f"Warning: Failed to load config from {cfg_path}: {e}", err=True)
    return {}


def load_local_overlay(polecat_home):
    """Load per-machine overrides from <polecat_home>/local.yaml."""
    local_path = os.path.join(polecat_home, "local.yaml")
    if os.path.exists(local_path):
        try:
            with open(local_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            click.echo(f"Warning: Failed to load overlay from {local_path}: {e}", err=True)
    return {}


def get_env_forwards():
    """Build the dictionary of environment variables to forward into the container."""
    env = {}

    # 1. Claude OAuth tokens (host source: AOPS_CC_OAUTH_TOKEN)
    if os.environ.get("AOPS_CC_OAUTH_TOKEN"):
        env["CLAUDE_CODE_OAUTH_TOKEN"] = os.environ["AOPS_CC_OAUTH_TOKEN"]
    elif os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        env["CLAUDE_CODE_OAUTH_TOKEN"] = os.environ["CLAUDE_CODE_OAUTH_TOKEN"]

    # 2. GitHub Token (host source: AOPS_BOT_GH_TOKEN)
    if os.environ.get("AOPS_BOT_GH_TOKEN"):
        val = os.environ["AOPS_BOT_GH_TOKEN"]
        env["GH_TOKEN"] = val
        env["GITHUB_TOKEN"] = val
        env["AOPS_BOT_GH_TOKEN"] = val
    else:
        for k in ["GH_TOKEN", "GITHUB_TOKEN"]:
            if os.environ.get(k):
                env[k] = os.environ[k]

    # 3. Gemini / Antigravity key and other standard forwards
    standard_keys = [
        "GEMINI_API_KEY",
        "PKB_MCP_URL",
        "PKB_MCP_TOKEN",
        "AGY_API_KEY",
        "COLORTERM",
        "FORCE_COLOR",
        "NO_COLOR",
        "CI",
        "NONINTERACTIVE",
    ]
    for k in standard_keys:
        if os.environ.get(k):
            env[k] = os.environ[k]

    # 4. Standard secure git configurations
    env["GIT_ASKPASS"] = "true"
    env["SSH_AUTH_SOCK"] = ""
    env["GIT_SSH_COMMAND"] = "false"
    env["GIT_TERMINAL_PROMPT"] = "0"

    # 5. Local machine timezone
    env["TZ"] = os.environ.get("TZ") or "UTC"

    return env


def setup_staging(staging_dir, pkb_url):
    """Stage settings and credentials in staging directory."""
    staging_dir = Path(staging_dir)

    # Stage Claude settings with the resolved PKB MCP URL pre-configured
    if pkb_url:
        claude_dir = staging_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings = {
            "model": "sonnet",
            "pluginConfigs": {"aops@academicOps": {"options": {"pkb_mcp_url": pkb_url}}},
        }
        with open(claude_dir / "settings.json", "w") as f:
            json.dump(settings, f, indent=2)

    # Replicate Gemini credentials
    gemini_src = Path.home() / ".gemini"
    if gemini_src.is_dir():
        gemini_dst = staging_dir / ".gemini"
        gemini_dst.mkdir(parents=True, exist_ok=True)
        for f in ["settings.json", "google_accounts.json", "oauth_creds.json", "installation_id"]:
            src_file = gemini_src / f
            if src_file.exists():
                shutil.copy2(src_file, gemini_dst / f)

        # Replicate Antigravity CLI configs
        agy_src = gemini_src / "antigravity-cli"
        if agy_src.is_dir():
            agy_dst = gemini_dst / "antigravity-cli"
            agy_dst.mkdir(parents=True, exist_ok=True)
            for f in ["antigravity-oauth-token", "settings.json", "installation_id"]:
                src_file = agy_src / f
                if src_file.exists():
                    shutil.copy2(src_file, agy_dst / f)

        # Write trustedFolders.json to bypass trust prompt inside /workspace
        trusted_folders = {
            "/workspace": "TRUST_FOLDER",
            "/home/worker/.gemini/extensions/aops-core": "TRUST_FOLDER",
            "/home/worker/.gemini/extensions/aops-tools": "TRUST_FOLDER",
        }
        with open(gemini_dst / "trustedFolders.json", "w") as f:
            json.dump(trusted_folders, f, indent=2)


@click.group()
def main():
    """Polecat-Lite: Lightweight containerized agent wrapper."""
    pass


@main.command()
@click.argument("agent_cmd", default="claude")
@click.option("--project", "-p", help="Project name to run on (resolves via config/local.yaml).")
@click.option(
    "--repo-dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Direct host path to a repository worktree.",
)
@click.option(
    "--session-name",
    "-s",
    help="Name/ID for the session (directories under sessions/ will use this).",
)
@click.option("--mcp-url", help="Override the PKB MCP URL forwarded into the container.")
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def run(agent_cmd, project, repo_dir, session_name, mcp_url, extra_args):
    """Spin up the polecat container and run CLIs (claude, agy, shell, sleep)."""
    config = load_config()

    # 1. Resolve POLECAT_HOME
    raw_home = config.get("polecat_home", "~/.polecat")
    polecat_home = Path(os.path.expandvars(os.path.expanduser(raw_home)))

    # 2. Resolve Workspace Directory
    workspace_dir = None
    if repo_dir:
        workspace_dir = repo_dir.resolve()
    elif project:
        local_cfg = load_local_overlay(polecat_home)
        proj_path = local_cfg.get("paths", {}).get(project)
        if proj_path:
            workspace_dir = Path(os.path.expandvars(os.path.expanduser(proj_path))).resolve()

    # Default fallback: if aops, use current repo root
    if not workspace_dir and (project == "aops" or not project):
        workspace_dir = Path(__file__).resolve().parent.parent.resolve()

    if not workspace_dir or not workspace_dir.exists():
        click.echo(
            "Error: Could not resolve a valid project or workspace path. Please use --repo-dir or set paths in local.yaml",
            err=True,
        )
        sys.exit(1)

    # 3. Setup Session/Log Directory
    session_id = session_name or f"session-{uuid.uuid4().hex[:8]}"
    sessions_base = os.environ.get("AOPS_SESSIONS")
    if sessions_base:
        sessions_base = Path(sessions_base)
    else:
        sessions_base = polecat_home / "sessions"

    session_dir = sessions_base / "crew" / session_id / (project or "workspace")
    session_dir.mkdir(parents=True, exist_ok=True)

    # 4. Resolve PKB URL
    pkb_url = mcp_url or os.environ.get("PKB_MCP_URL")

    # 5. Populate Temp Staging Directory
    staging_base = os.environ.get("POLECAT_STAGING_BASE") or str(polecat_home / "tmp" / "staging")
    Path(staging_base).mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix="staging-", dir=staging_base))
    os.chmod(staging_dir, 0o700)

    try:
        setup_staging(staging_dir, pkb_url)

        # 6. Gather Docker parameters
        image = config.get("docker", {}).get("image", "ghcr.io/nicsuzor/aops-crew")

        # Build environment forwards
        env = get_env_forwards()
        if pkb_url:
            env["PKB_MCP_URL"] = pkb_url

        # Determine internal CLI tool & args
        docker_args = []

        # Determine interactive TTY flag
        is_interactive = (
            agent_cmd in ("shell", "sleep", "sleep infinity")
            or not extra_args
            or "-p" not in extra_args
        )
        if is_interactive:
            docker_args.append("-it")

        # Set container local state directories
        if agent_cmd == "claude":
            container_session_path = "/home/worker/.claude/projects/-workspace"
            inner_cmd = [
                "claude",
                "--permission-mode=auto",
                "--setting-sources=user,project",
            ]
        elif agent_cmd == "agy":
            container_session_path = "/home/worker/.gemini/tmp/workspace"
            inner_cmd = ["agy", "--dangerously-skip-permissions"]
        elif agent_cmd in ("shell", "bash"):
            container_session_path = "/home/worker/.claude/projects/-workspace"
            inner_cmd = ["bash"]
        elif agent_cmd.startswith("sleep"):
            container_session_path = "/home/worker/.claude/projects/-workspace"
            inner_cmd = ["sleep", "infinity"]
        else:
            container_session_path = "/home/worker/.claude/projects/-workspace"
            inner_cmd = [agent_cmd]

        if extra_args:
            inner_cmd.extend(extra_args)

        # Assemble environment flags
        env["AOPS_POLECAT_CONTAINER"] = "1"
        env["POLECAT_CREW_NAME"] = session_id
        env["AOPS_SESSION_STATE_DIR"] = container_session_path
        env["AOPS_HOOK_LOG_PATH"] = f"{container_session_path}/polecat-session-hooks.jsonl"

        # Map exit-reflection check gate MD paths
        for gate in ["exit_reflection", "hydration", "ida"]:
            env[f"AOPS_GATE_FILE_{gate.upper()}"] = (
                f"{container_session_path}/polecat-session-{gate}.md"
            )

        # Construct raw docker run command
        cmd = [
            "docker",
            "run",
            "--rm",
            "-u",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{workspace_dir}:/workspace",
            "-w",
            "/workspace",
            "-v",
            f"{staging_dir}:/tmp/staging:ro",
            "-v",
            f"{session_dir}:{container_session_path}",
            "-v",
            f"{session_dir}/agy-brain:/home/worker/.gemini/antigravity-cli/brain",
            "-v",
            f"{session_dir}/agy-cli.log:/home/worker/.gemini/antigravity-cli/cli.log",
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock",
            "--add-host",
            "host.docker.internal:host-gateway",
        ]

        # Add TTY flags
        cmd.extend(docker_args)

        # Add groups for Docker socket permission
        try:
            docker_gid = Path("/var/run/docker.sock").stat().st_gid
            cmd.extend(["--group-add", str(docker_gid)])
        except Exception:
            pass

        # Add env vars to command line
        for k, v in env.items():
            cmd.extend(["-e", f"{k}={v}"])

        # Add image name and target CLI
        cmd.append(image)
        cmd.extend(inner_cmd)

        click.echo(f"📁 Workspace: {workspace_dir}")
        click.echo(f"📝 Sessions Logs: {session_dir}")
        click.echo(f"🚀 Running: {' '.join(cmd[:15])} ...")

        # Execute the container
        subprocess.run(cmd)

    finally:
        # Clean up staging directory
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)


if __name__ == "__main__":
    main()
