#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT / "aops-core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "aops-core"))

import click
from lib.agent_env import apply_env_mappings
from manager import PolecatManager
from observability import metrics
from validation import TaskIDValidationError, validate_task_id_or_raise

# Max turns for headless Claude runs — must be high enough to accommodate hook
# overhead (hydration gate, custodiet compliance check) plus actual task work.
HEADLESS_CLAUDE_MAX_TURNS = "30"


def _node_version_key(p: Path) -> tuple[int, ...]:
    """Sort key for NVM node version directories using semver comparison.

    Lexicographic sorting gets v9.x.x > v20.x.x wrong because '9' > '2'.
    This extracts numeric components for correct ordering.
    """
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", p.name)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def _make_worker_env(interactive: bool = False) -> dict[str, str]:
    """Create a sanitized environment for polecat/crew worker subprocesses.

    Strips SSH credentials and maps git auth to the bot token, ensuring
    workers can ONLY authenticate via the provided AOPS_BOT_GH_TOKEN.
    This runs agent-env-map.conf mappings eagerly (before subprocess launch)
    rather than relying on the SessionStart hook inside the child process.
    It also ensures 'uv' and other critical binaries are in the PATH.
    It also enables 24-bit color mode if interactive is True.
    """
    env = os.environ.copy()
    apply_env_mappings(env)

    if interactive:
        # Enable 24-bit color (TrueColor) for interactive sessions
        env["COLORTERM"] = "truecolor"
        env["FORCE_COLOR"] = "3"  # 3 = 24-bit color for Node.js chalk and others

    # Ensure uv is in PATH for hooks and agent tools
    current_path = env.get("PATH", "")
    path_segments = [s for s in current_path.split(os.pathsep) if s]

    # Prepend common user-level bin paths if they exist and are not already in PATH.
    # Include nvm-managed node bin (for gemini/claude CLIs installed via npm).
    nvm_dir = os.environ.get("NVM_DIR", str(Path.home() / ".nvm"))
    nvm_bin = os.environ.get("NVM_BIN", "")
    user_bin_paths = [
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / "bin"),
    ]
    # Add NVM bin if set, otherwise scan for nvm node versions
    if nvm_bin:
        user_bin_paths.append(nvm_bin)
    elif os.path.isdir(nvm_dir):
        versions_dir = Path(nvm_dir) / "versions" / "node"
        if versions_dir.is_dir():
            # Use the most recent node version's bin (semver sort, not lexicographic)
            node_versions = sorted(versions_dir.iterdir(), key=_node_version_key, reverse=True)
            if node_versions:
                user_bin_paths.append(str(node_versions[0] / "bin"))
    for p in reversed(user_bin_paths):
        if os.path.isdir(p) and p not in path_segments:
            path_segments.insert(0, p)

    env["PATH"] = os.pathsep.join(path_segments)

    # Prevent gh CLI from launching interactive prompts in non-TTY environments.
    # Workers run headless — any prompt would hang indefinitely.
    env["GH_PROMPT_DISABLED"] = "1"
    return env


def set_terminal_title(title: str) -> None:
    """Set terminal/tmux window title for session identification.

    Uses OSC 0 escape sequence (same as dotfiles set-tab-title function).
    In tmux, also sets the window name via rename-window so it appears
    in set-titles-string (#W) and the window list.
    """
    # OSC 0: Set window title — works in Terminal.app, iTerm2, most terminals
    sys.stdout.write(f"\033]0;{title}\007")
    sys.stdout.flush()

    # If inside tmux, also rename the window for #W in set-titles-string
    if os.environ.get("TMUX"):
        tmux = shutil.which("tmux")
        if tmux:
            subprocess.run([tmux, "rename-window", title], capture_output=True)


def reset_terminal_title() -> None:
    """Reset terminal title to automatic naming after session ends."""
    if os.environ.get("TMUX"):
        tmux = shutil.which("tmux")
        if tmux:
            # Re-enable automatic window renaming
            subprocess.run(
                [tmux, "set-window-option", "automatic-rename", "on"],
                capture_output=True,
            )
    # Clear terminal title (let shell/terminal manage it)
    sys.stdout.write("\033]0;\007")
    sys.stdout.flush()


def save_worker_transcript(
    task_id: str,
    stdout: str,
    stderr: str,
    exit_code: int,
    agent_type: str,
    home_dir: Path,
) -> Path:
    """Save worker output to transcript file.

    Writes a JSONL entry with metadata and full output to
    $POLECAT_HOME/polecats/<task-id>.jsonl

    Args:
        task_id: The task identifier
        stdout: Captured standard output
        stderr: Captured standard error
        exit_code: Process exit code
        agent_type: "claude" or "gemini"
        home_dir: Polecat home directory (fallback if AOPS_SESSIONS not set)

    Returns:
        Path to the transcript file

    Raises:
        OSError: If transcript directory cannot be created or file cannot be written
    """
    try:
        try:
            from lib.paths import get_polecat_transcripts_dir

            transcript_dir = get_polecat_transcripts_dir()
        except ImportError:
            # Fallback for older installations or missing lib.paths
            transcript_dir = home_dir / "transcripts"

        transcript_dir.mkdir(parents=True, exist_ok=True)

        transcript_file = transcript_dir / f"{task_id}.jsonl"

        entry = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "task_id": task_id,
            "agent": agent_type,
            "session_type": "polecat",
            "exit_code": exit_code,
            "success": exit_code == 0,
            "stdout": stdout or "",
            "stderr": stderr or "",
        }

        with open(transcript_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return transcript_file
    except OSError as e:
        raise OSError(f"Failed to save transcript for task {task_id}: {e}") from e


def _get_sessions_base() -> Path:
    """Return the base directory for session transcript storage.

    Uses ``get_sessions_repo()`` from ``lib.paths`` when available, falling
    back to ``$AOPS_SESSIONS`` or ``$POLECAT_HOME/sessions``.
    """
    try:
        from lib.paths import get_sessions_repo

        return get_sessions_repo()
    except ImportError:
        aops_sessions = os.environ.get("AOPS_SESSIONS")
        if aops_sessions:
            return Path(aops_sessions)
        return Path(os.environ.get("POLECAT_HOME", str(Path.home() / ".polecat"))) / "sessions"


def _detect_system_timezone() -> str:
    """Detect system timezone from /etc/localtime or /etc/timezone. Returns 'UTC' if undetectable."""
    try:
        tz_link = Path("/etc/localtime")
        if tz_link.is_symlink():
            target = str(tz_link.resolve())
            # /etc/localtime -> /usr/share/zoneinfo/Region/City
            marker = "/zoneinfo/"
            idx = target.find(marker)
            if idx != -1:
                return target[idx + len(marker) :]
    except OSError:
        pass
    try:
        tz_file = Path("/etc/timezone")
        if tz_file.exists():
            return tz_file.read_text().strip()
    except OSError:
        pass
    return "UTC"


def _build_docker_cmd(
    cli_tool: str,
    work_dir: Path,
    env: dict,
    agent_cmd: list[str],
    is_interactive: bool,
    tmp_files: list[Path] | None = None,
    session_dir: Path | None = None,
) -> list[str]:
    """Wraps an agent command in a Docker run command with appropriate mounts.

    If tmp_files is provided, any temporary files created (e.g. modified .claude.json)
    are appended to it so callers can clean them up.

    If session_dir is provided and cli_tool is "claude" or "shell", mounts it at
    /home/worker/.claude/projects so Claude session transcripts persist on the host.
    """
    # Use POLECAT_DOCKER_IMAGE if set, otherwise default to the aops-crew image
    # built from the repo root Dockerfile via `make build-docker`.
    image = os.environ.get("POLECAT_DOCKER_IMAGE", "aops-crew")

    cmd = ["docker", "run", "--rm"]

    # TTY allocation
    if is_interactive:
        cmd.append("-it")
    else:
        cmd.append("-i")

    # Run as current user — Claude Code refuses --dangerously-skip-permissions under root
    uid = os.getuid()
    gid = os.getgid()
    cmd.extend(["--user", f"{uid}:{gid}"])
    # Use /home/worker as container home — NOT --tmpfs on $HOME.
    # Docker --tmpfs mounts override bind mounts at the same path, hiding
    # .claude/ and .claude.json and causing Claude to hang on startup.
    container_home = "/home/worker"
    # HOME is set in the image ENV; no need to pass it at runtime

    # Timezone — match host timezone for consistent timestamps in commits/logs
    tz = os.environ.get("TZ") or _detect_system_timezone()
    cmd.extend(["-e", f"TZ={tz}"])

    # Git identity — required for git commit inside the container.
    # Default to aops-bot if not provided in the environment.
    git_name = env.get("GIT_AUTHOR_NAME") or os.environ.get("GIT_AUTHOR_NAME", "aops-bot")
    git_email = env.get("GIT_AUTHOR_EMAIL") or os.environ.get(
        "GIT_AUTHOR_EMAIL", "aops-bot@users.noreply.github.com"
    )
    cmd.extend(["-e", f"GIT_AUTHOR_NAME={git_name}"])
    cmd.extend(["-e", f"GIT_AUTHOR_EMAIL={git_email}"])
    cmd.extend(["-e", f"GIT_COMMITTER_NAME={git_name}"])
    cmd.extend(["-e", f"GIT_COMMITTER_EMAIL={git_email}"])

    # Mount worktree
    cmd.extend(["-v", f"{work_dir.resolve()}:/workspace"])
    cmd.extend(["-w", "/workspace"])

    # Mount authentication and plugin cache for Claude
    # Also mount for "shell" mode so users can run claude interactively
    home = Path.home()
    if cli_tool in ("claude", "shell"):
        claude_json = home / ".claude.json"
        claude_dir = home / ".claude"
        # Create a staging directory under $HOME so Colima/Docker VMs can access it
        # (macOS VMs only share /Users, not /var/folders or /tmp).
        # Use mkdtemp for a unique, non-guessable path; restrict to 0o700 since it holds auth material.
        tmp_root = home / ".aops" / "tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        staging_dir = Path(tempfile.mkdtemp(prefix="staging-", dir=tmp_root))
        os.chmod(staging_dir, 0o700)
        if tmp_files is not None:
            tmp_files.append(staging_dir)
        if claude_json.exists():
            # Claude needs bypassPermissionsModeAccepted=true for --dangerously-skip-permissions
            # to work without an interactive prompt. Create a copy with this flag set
            # rather than modifying the user's actual config.
            with open(claude_json) as f:
                config = json.load(f)
            config["bypassPermissionsModeAccepted"] = True
            staged_claude_json = staging_dir / ".claude.json"
            fd = os.open(staged_claude_json, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(config, f)
        if claude_dir.exists():
            # Copy only the auth files Claude needs at runtime — not the whole directory.
            # The plugin installation is baked into the image (see Dockerfile), so mounting
            # the full ~/.claude dir would override the image's plugin data with the host's
            # (potentially stale or wrong-path) copy.
            staged_claude_dir = staging_dir / ".claude"
            staged_claude_dir.mkdir(exist_ok=True)
            for auth_file in (".credentials.json", ".mcp.json", "settings.json"):
                src = claude_dir / auth_file
                if src.exists():
                    shutil.copy2(src, staged_claude_dir / auth_file)
        cmd.extend(["-v", f"{staging_dir}:/tmp/staging:ro"])

        # Stage Gemini auth files for "shell" mode so users can run gemini interactively.
        # Gemini normally handles its own sandbox, but in shell mode we're managing Docker.
        # (Nested here because staging_dir is only defined when cli_tool in ("claude", "shell"))
        if cli_tool == "shell":
            gemini_dir = home / ".gemini"
            if gemini_dir.exists():
                staged_gemini_dir = staging_dir / ".gemini"
                staged_gemini_dir.mkdir(exist_ok=True)
                for auth_file in (
                    "settings.json",
                    "google_accounts.json",
                    "oauth_creds.json",
                    "installation_id",
                    "trustedFolders.json",
                ):
                    src = gemini_dir / auth_file
                    if src.exists():
                        shutil.copy2(src, staged_gemini_dir / auth_file)
                # Also forward GEMINI_API_KEY if set
                gemini_key = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
                if gemini_key:
                    cmd.extend(["-e", f"GEMINI_API_KEY={gemini_key}"])

    # Mount Docker socket for Docker-outside-of-Docker (build/test inside agents).
    # Pass the socket's gid so the non-root container user can access it — the gid
    # varies by host so we read it from the socket file rather than hardcoding.
    docker_sock = Path("/var/run/docker.sock")
    if docker_sock.exists():
        docker_gid = docker_sock.stat().st_gid
        cmd.extend(["--group-add", str(docker_gid)])
        cmd.extend(["-v", "/var/run/docker.sock:/var/run/docker.sock"])

    # Mount pkb binary for MCP server (plugin config references 'pkb' from PATH)
    pkb_bin = shutil.which("pkb")
    if pkb_bin:
        cmd.extend(["-v", f"{pkb_bin}:/usr/local/bin/pkb:ro"])

    # Mount ACA_DATA for PKB access (read-write — agents may update tasks)
    aca_data = env.get("ACA_DATA") or os.environ.get("ACA_DATA")
    if aca_data and os.path.isdir(aca_data):
        cmd.extend(["-v", f"{aca_data}:{aca_data}"])
        cmd.extend(["-e", f"ACA_DATA={aca_data}"])

    # Add host networking for MCPs running on localhost
    cmd.extend(["--add-host", "host.docker.internal:host-gateway"])

    # Forward specific environment variables to the container
    for key, val in env.items():
        if (
            key.startswith("POLECAT_")
            or key.startswith("AOPS_")
            or key.endswith("_GATE_MODE")
            or key
            in (
                "AOPS_BOT_GH_TOKEN",
                "GH_TOKEN",
                "GITHUB_TOKEN",
                "ANTHROPIC_API_KEY",
                "COLORTERM",
                "FORCE_COLOR",
                "CUSTODIET_TOOL_CALL_THRESHOLD",
            )
        ):
            cmd.extend(["-e", f"{key}={val}"])

    # GitHub authentication — forward tokens to the container.
    # The container entrypoint handles git and gh CLI authentication.
    gh_token = env.get("GH_TOKEN") or os.environ.get("AOPS_BOT_GH_TOKEN")
    if gh_token:
        cmd.extend(
            [
                "-e",
                "GIT_ASKPASS=true",
                "-e",
                f"GH_TOKEN={gh_token}",
                "-e",
                f"AOPS_BOT_GH_TOKEN={gh_token}",
            ]
        )

    # SSH isolation — no SSH auth inside container
    cmd.extend(["-e", "SSH_AUTH_SOCK="])
    cmd.extend(["-e", "GIT_TERMINAL_PROMPT=0"])

    # Mount session directory so Claude transcripts persist on the host.
    # Without this, --rm destroys all session data when the container exits.
    if session_dir and cli_tool in ("claude", "shell"):
        session_dir.mkdir(parents=True, exist_ok=True)
        cmd.extend(["-v", f"{session_dir.resolve()}:{container_home}/.claude/projects"])

    cmd.append(image)
    cmd.extend(agent_cmd)
    return cmd


def _mount_aca_data_sandbox(env: dict) -> None:
    """Mount ACA_DATA read-write into the Gemini sandbox via SANDBOX_MOUNTS.

    Forwarding ACA_DATA as an env var alone (via SANDBOX_FLAGS) is insufficient —
    without the bind mount the PKB server starts with a missing/empty path inside
    the container.  This helper is called from both ``crew -g`` and ``run -g``.
    """
    aca_data = env.get("ACA_DATA") or os.environ.get("ACA_DATA")
    if aca_data and os.path.isdir(aca_data):
        env.setdefault("ACA_DATA", aca_data)
        mounts = env.get("SANDBOX_MOUNTS", "")
        new_mount = f"{aca_data}:{aca_data}:rw"
        env["SANDBOX_MOUNTS"] = f"{mounts},{new_mount}" if mounts else new_mount


def _replicate_gemini_auth(env: dict, work_dir: Path | None = None) -> Path | None:
    """Replicate Gemini authentication files to a directory.

    For headless sessions to authenticate properly in a sandbox, critical files
    from the user's ~/.gemini/ directory must be replicated in the temporary
    GEMINI_CLI_HOME:
    - settings.json
    - google_accounts.json
    - oauth_creds.json
    - installation_id
    - trustedFolders.json

    If work_dir is provided, it is added to the replicated trustedFolders.json
    to avoid trust prompts in the sandbox.

    Returns:
        Path to the directory containing the replicated files,
        or None if authentication replication is disabled or fails.
    """
    if os.environ.get("POLECAT_GEMINI_AUTH_DISABLED") == "1":
        return None

    home = Path.home()
    gemini_dir = home / ".gemini"

    if not gemini_dir.exists():
        return None

    # Check if we have any auth-related files
    auth_files = [
        "settings.json",
        "google_accounts.json",
        "oauth_creds.json",
        "installation_id",
        "trustedFolders.json",
        "projects.json",
        "state.json",
    ]

    existing_files = [f for f in auth_files if (gemini_dir / f).exists()]
    if not existing_files:
        return None

    # Create a temporary directory under $HOME/.aops/tmp so Docker can access it.
    # macOS VMs (Colima/Docker) only share /Users, not /var/folders or /tmp.
    tmp_root = home / ".aops" / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_gemini_home = Path(tempfile.mkdtemp(prefix="polecat-gemini-auth-", dir=tmp_root))
    os.chmod(tmp_gemini_home, 0o700)

    target_dir = tmp_gemini_home / ".gemini"
    target_dir.mkdir(parents=True)

    for f in existing_files:
        if f == "trustedFolders.json" and work_dir:
            try:
                with open(gemini_dir / f) as src_f:
                    trust_data = json.load(src_f)
                # Inject the work directory into trust data
                # We use TRUST_FOLDER which is the most common entry type
                trust_data[str(work_dir.resolve())] = "TRUST_FOLDER"
                with open(target_dir / f, "w") as dest_f:
                    json.dump(trust_data, dest_f, indent=2)
                continue
            except (json.JSONDecodeError, OSError) as e:
                # Fall back to simple copy if processing fails
                print(f"   Warning: could not process {gemini_dir / f}: {e}", file=sys.stderr)

        if f == "settings.json":
            try:
                with open(gemini_dir / f) as src_f:
                    settings_data = json.load(src_f)

                # Force sandbox with network access to prevent OAuth failures
                # The gemini-cli sandbox requires network access to verify the token,
                # otherwise it falls back to interactive auth which fails in CI.
                if "tools" not in settings_data:
                    settings_data["tools"] = {}
                if "sandbox" not in settings_data["tools"] or not isinstance(
                    settings_data["tools"]["sandbox"], dict
                ):
                    settings_data["tools"]["sandbox"] = {}
                settings_data["tools"]["sandbox"]["enabled"] = True
                settings_data["tools"]["sandbox"]["networkAccess"] = True

                with open(target_dir / f, "w") as dst_f:
                    json.dump(settings_data, dst_f, indent=2)
                continue
            except (json.JSONDecodeError, OSError) as e:
                print(f"   Warning: could not process {gemini_dir / f}: {e}", file=sys.stderr)

        # Follow symlinks to copy the actual file content, not the link itself.
        # This is critical for ~/.gemini/settings.json which is often symlinked.
        shutil.copy2(gemini_dir / f, target_dir / f, follow_symlinks=True)

    # If trustedFolders.json didn't exist but we have a work_dir, create it
    if "trustedFolders.json" not in existing_files and work_dir:
        try:
            trust_data = {str(work_dir.resolve()): "TRUST_FOLDER"}
            with open(target_dir / "trustedFolders.json", "w") as f:
                json.dump(trust_data, f, indent=2)
        except OSError as e:
            print(f"   Warning: could not create trustedFolders.json: {e}", file=sys.stderr)

    # Replicate extensions so that extension hooks fire in sandbox sessions.
    # Copy (not symlink) extension dirs because Gemini's sandbox mounts
    # GEMINI_CLI_HOME into a Docker container — symlinks to host paths
    # break since the target paths don't exist inside the container.
    # Create a fresh extension-enablement.json with a wildcard override so the
    # extension is active for any workspace path (the original restricts to
    # /home/<user>/* which won't match test or CI workspaces).
    src_extensions = gemini_dir / "extensions"
    if src_extensions.is_dir():
        dst_extensions = target_dir / "extensions"
        dst_extensions.mkdir(parents=True, exist_ok=True)

        # Copy each extension subdirectory (not symlink — breaks in Docker)
        for child in src_extensions.iterdir():
            if child.is_dir():
                shutil.copytree(child, dst_extensions / child.name, ignore_dangling_symlinks=True)

        # Build a permissive enablement file — allow all paths
        enablement_src = src_extensions / "extension-enablement.json"
        if enablement_src.exists():
            try:
                with open(enablement_src) as f:
                    enablement = json.load(f)
                for ext_name in enablement:
                    enablement[ext_name]["overrides"] = ["*"]
                with open(dst_extensions / "extension-enablement.json", "w") as f:
                    json.dump(enablement, f, indent=2)
            except (json.JSONDecodeError, OSError):
                shutil.copy2(enablement_src, dst_extensions / "extension-enablement.json")

    # Set GEMINI_CLI_HOME to the parent directory — Gemini creates .gemini/
    # inside GEMINI_CLI_HOME (i.e. path.join(GEMINI_CLI_HOME, ".gemini", ...)).
    env["GEMINI_CLI_HOME"] = str(tmp_gemini_home)

    return tmp_gemini_home


def is_interactive() -> bool:
    """Check if we're running in an interactive terminal."""
    return sys.stdin.isatty()


@click.group()
@click.option(
    "--home",
    envvar="POLECAT_HOME",
    type=click.Path(path_type=Path),
    help="Polecat home directory (default: $POLECAT_HOME, or ~/.polecat)",
)
@click.pass_context
def main(ctx, home):
    """Polecat: Ephemeral worker management system."""
    ctx.ensure_object(dict)
    ctx.obj["home"] = home


@main.command()
@click.pass_context
def setup(ctx):
    """Run full framework installation and extension linking.

    This builds extensions and runs scripts/install.py to set up
    cron jobs, symlinks, and link Gemini/Claude extensions.
    Requires uv and should be run from the repository root.
    """
    repo_root = Path(__file__).parent.parent.resolve()
    setup_script = repo_root / "setup.sh"

    if not setup_script.exists():
        print(f"Error: setup.sh not found at {setup_script}", file=sys.stderr)
        sys.exit(1)

    print(f"Running framework setup from {setup_script}...")
    try:
        subprocess.run(["bash", str(setup_script)], check=True)
        print("\n✓ Polecat setup complete")
    except subprocess.CalledProcessError as e:
        print(f"\nError: Setup failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(1)


@main.command()
@click.option("--project", "-p", help="Initialize only this project (default: all)")
@click.pass_context
def init(ctx, project):
    """Initialize bare mirror repos in <home>/polecat/.repos/

    Creates bare clones of all registered projects for isolated worktree spawning.
    Run this once before using polecat, or when adding new projects.

    Examples:
        polecat init              # Initialize all projects
        polecat init -p aops      # Initialize only aops
        polecat --home /custom/path init  # Use custom home directory
    """
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    if project:
        try:
            path = manager.ensure_repo_mirror(project)
            print(f"✓ {project} -> {path}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Failed to initialize {project}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Initializing mirrors in {manager.repos_dir}...")
        results = manager.init_all_mirrors()
        failures = [p for p, path in results.items() if path is None]
        if failures:
            print(f"\n⚠️  Failed: {', '.join(failures)}")
            sys.exit(1)
        print("\n✓ All mirrors ready")


def _clear_stale_git_lock(repo_path: Path) -> bool:
    """Remove stale .git/index.lock if no process holds it.

    Returns True if lock was cleared or didn't exist, False if held by a process.
    """
    lockfile = repo_path / ".git" / "index.lock"
    if not lockfile.exists():
        return True

    # Check if a process holds the lock
    lsof = shutil.which("lsof")
    if lsof:
        result = subprocess.run([lsof, str(lockfile)], capture_output=True, check=False)
        if result.returncode == 0:
            # Process holds the lock
            return False

    # No process holds it — stale lock, remove
    lockfile.unlink(missing_ok=True)
    return True


def _auto_resolve_rebase(repo_path: Path, name: str, ahead_count: int) -> tuple[bool, str]:
    """Auto-resolve conflicts during an in-progress rebase.

    Checks for unmerged files, resolves them (keeping local/--theirs),
    backs up remote versions of non-expendable files, and loops through
    rebase --continue until complete or unresolvable.

    Returns (success, message).
    """
    import fnmatch

    expendable_patterns = [
        "synthesis.json",
        "graph*.json",
        "graph*.dot",
        "graph*.svg",
        "graph*.graphml",
    ]

    def _is_expendable(filepath: str) -> bool:
        basename = Path(filepath).name
        return any(fnmatch.fnmatch(basename, p) for p in expendable_patterns)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    all_conflict_files: list[str] = []
    backup_paths: list[str] = []
    max_rounds = ahead_count + 5

    for _round in range(max_rounds):
        unmerged = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        if not unmerged:
            # No conflicts — try continuing (may be a non-conflict failure)
            cont = subprocess.run(
                ["git", "rebase", "--continue"],
                cwd=repo_path,
                capture_output=True,
                check=False,
                env={**os.environ, "GIT_EDITOR": "true"},
            )
            if cont.returncode == 0:
                break
            # rebase failed for non-conflict reason
            subprocess.run(
                ["git", "rebase", "--abort"],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            return False, f"{name}: rebase failed"

        # Resolve conflicts: keep local (--theirs in rebase), backup remote for non-expendable
        resolved = True
        for cf in unmerged.splitlines():
            all_conflict_files.append(cf)
            if not _is_expendable(cf):
                rc = subprocess.run(
                    ["git", "show", f":2:{cf}"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if rc.returncode == 0 and rc.stdout:
                    bp = Path(repo_path) / f"{cf}.conflict-remote-{timestamp}"
                    bp.parent.mkdir(parents=True, exist_ok=True)
                    bp.write_text(rc.stdout)
                    backup_paths.append(str(bp.relative_to(repo_path)))

            r = subprocess.run(
                ["git", "checkout", "--theirs", "--", cf],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            if r.returncode == 0:
                subprocess.run(
                    ["git", "add", cf],
                    cwd=repo_path,
                    capture_output=True,
                    check=False,
                )
            else:
                resolved = False
                break

        if not resolved:
            subprocess.run(
                ["git", "rebase", "--abort"],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            return False, f"{name}: conflict needs manual resolution"

        # Stage backup files
        for bp in backup_paths:
            subprocess.run(
                ["git", "add", bp],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )

        cont = subprocess.run(
            ["git", "rebase", "--continue"],
            cwd=repo_path,
            capture_output=True,
            check=False,
            env={**os.environ, "GIT_EDITOR": "true"},
        )
        if cont.returncode == 0:
            break
        # If continue failed, loop back to check for new conflicts
    else:
        subprocess.run(
            ["git", "rebase", "--abort"],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )
        return False, f"{name}: rebase exceeded max rounds ({max_rounds})"

    if all_conflict_files:
        conflict_summary = ", ".join(set(all_conflict_files))
        warn = (
            f"⚠ {name}: rebase conflict auto-resolved (kept local) in: {conflict_summary}. "
            f"Remote versions saved to: {', '.join(backup_paths) or 'none'}"
        )
        print(warn, file=sys.stderr)

    return True, f"{name}: auto-resolved {len(set(all_conflict_files))} conflict(s)"


def _sync_working_repo(
    repo_path: Path, *, auto_commit: bool = False, quiet: bool = False
) -> tuple[bool, str]:
    """Sync a working repo: fetch, pull/push, auto-resolve conflicts.

    Returns (success, message).
    """
    name = repo_path.name

    if not (repo_path / ".git").exists():
        return False, f"{name}: not a git repo"

    if not _clear_stale_git_lock(repo_path):
        return False, f"{name}: git lock held by active process"

    # Fetch
    subprocess.run(
        ["git", "fetch", "--quiet"],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )

    # Check status
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    dirty = bool(porcelain)

    # Check ahead/behind
    tracking = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()

    ahead_count = behind_count = 0
    if tracking:
        counts = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if counts:
            parts = counts.split()
            if len(parts) == 2:
                ahead_count, behind_count = int(parts[0]), int(parts[1])

    if dirty:
        if auto_commit:
            # Stage all files (including new untracked) and commit
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=False)
            has_staged = (
                subprocess.run(
                    ["git", "diff", "--cached", "--quiet"],
                    cwd=repo_path,
                    capture_output=True,
                    check=False,
                ).returncode
                != 0
            )

            if has_staged:
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"auto: sync {datetime.now():%Y-%m-%d %H:%M}",
                        "--quiet",
                    ],
                    cwd=repo_path,
                    capture_output=True,
                    check=False,
                )

            # Pull with rebase
            pull = subprocess.run(
                ["git", "pull", "--rebase", "--quiet"],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            if pull.returncode != 0:
                ok, resolve_msg = _auto_resolve_rebase(repo_path, name, ahead_count)
                if not ok:
                    return False, resolve_msg

            # Push
            push = subprocess.run(
                ["git", "push", "--quiet"],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            if push.returncode != 0:
                return False, f"{name}: push failed"
            return True, f"{name}: auto-synced (committed + pushed)"
        else:
            status_parts = ["dirty"]
            if ahead_count:
                status_parts.append(f"{ahead_count} ahead")
            if behind_count:
                status_parts.append(f"{behind_count} behind")
            return False, f"{name}: {', '.join(status_parts)} (skipped — not auto-commit)"

    elif behind_count > 0 and ahead_count == 0:
        pull = subprocess.run(
            ["git", "pull", "--quiet"],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )
        if pull.returncode == 0:
            return True, f"{name}: pulled {behind_count} commit(s)"
        return False, f"{name}: pull failed"

    elif ahead_count > 0:
        # If also behind, rebase local commits on top of remote before pushing
        if behind_count > 0:
            pull = subprocess.run(
                ["git", "pull", "--rebase", "--quiet"],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            if pull.returncode != 0:
                # Attempt to auto-resolve rebase conflicts (same logic as dirty path)
                ok, resolve_msg = _auto_resolve_rebase(repo_path, name, ahead_count)
                if not ok:
                    return False, resolve_msg
        push = subprocess.run(
            ["git", "push", "--quiet"],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )
        if push.returncode == 0:
            return True, f"{name}: pushed {ahead_count} commit(s)"
        return False, f"{name}: push failed"

    else:
        return True, f"{name}: ok"


@main.command()
@click.option("--check", is_flag=True, help="Just show status, don't fix anything")
@click.option("--quiet", "-q", is_flag=True, help="Only show repos needing attention")
@click.option("--mirrors-only", is_flag=True, help="Only sync bare mirrors (skip working repos)")
@click.pass_context
def sync(ctx, check, quiet, mirrors_only):
    """Sync all git repos: working repos and bare mirrors.

    Fetches, pulls, and pushes working repos defined in polecat.yaml.
    Also updates bare mirrors used by polecat workers.

    The brain repo ($ACA_DATA) gets special treatment: dirty files are
    auto-committed and pushed. Other repos are only pulled/pushed if clean.

    Examples:
        polecat sync              # Sync everything
        polecat sync --check      # Just show status
        polecat sync --quiet      # Only show issues
        polecat sync --mirrors-only  # Only sync bare mirrors
    """
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # --- Phase 1: Working repos ---
    if not mirrors_only:
        if not quiet:
            print("Syncing working repos...")

        brain_path = os.environ.get("ACA_DATA", str(Path.home() / "brain"))
        try:
            brain_path = str(Path(brain_path).resolve())
        except OSError:
            brain_path = ""

        needs_attention = []
        for project_name, project_cfg in manager.config.get("projects", {}).items():
            repo_path_str = project_cfg.get("path", "")
            if not repo_path_str:
                continue
            repo_path = Path(os.path.expanduser(repo_path_str))
            if not repo_path.is_dir():
                if not quiet:
                    print(f"  {project_name}: path not found ({repo_path})")
                continue

            # Brain repo gets auto-commit; other repos don't
            is_brain = False
            try:
                is_brain = str(repo_path.resolve()) == brain_path
            except OSError:
                pass

            if is_brain and not check:
                # Run aops lint --fix on brain before syncing
                aops_bin = shutil.which("aops")
                if aops_bin:
                    subprocess.run(
                        [aops_bin, "lint", "--fix"],
                        capture_output=True,
                        check=False,
                    )

            if check:
                # Just report status
                success, msg = _sync_working_repo(repo_path, auto_commit=False, quiet=quiet)
                if not success or not quiet:
                    print(f"  {msg}")
                if not success:
                    needs_attention.append(project_name)
            else:
                success, msg = _sync_working_repo(repo_path, auto_commit=is_brain, quiet=quiet)
                if not success or not quiet:
                    print(f"  {msg}")
                if not success:
                    needs_attention.append(project_name)

        # Also sync AOPS_SESSIONS if defined
        sessions_dir = os.environ.get("AOPS_SESSIONS")
        if sessions_dir:
            sessions_path = Path(os.path.expanduser(sessions_dir))
            if sessions_path.is_dir():
                success, msg = _sync_working_repo(sessions_path, auto_commit=True, quiet=quiet)
                if not success or not quiet:
                    print(f"  {msg}")

        if not quiet:
            if needs_attention:
                print(f"\n⚠ {len(needs_attention)} repo(s) need attention")
            else:
                print()

    # --- Phase 2: Bare mirrors ---
    if not quiet:
        print(f"Syncing mirrors in {manager.repos_dir}...")
    results = manager.sync_all_mirrors()
    successes = sum(1 for v in results.values() if v)
    if not quiet:
        print(f"✓ Synced {successes}/{len(results)} mirrors")


@main.command()
@click.option("--project", "-p", help="Project to claim tasks from")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.pass_context
def start(ctx, project, caller):
    """Claim next ready task and spawn a worktree."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    print(f"Looking for ready tasks{' in project ' + project if project else ''}...")
    task = manager.claim_next_task(caller, project)

    if not task:
        print("No ready tasks found.")
        sys.exit(3)  # Exit 3 = queue empty. Swarm treats non-zero as "stop worker".

    print(f"Claimed task: {task.title} ({task.id})")

    try:
        worktree_path = manager.setup_worktree(task)
        print(f"\nSuccess! Worktree ready at:\n{worktree_path}")
        print(f"\nTo start working:\ncd {worktree_path}")
    except Exception as e:
        print(f"\nError setting up worktree: {e}")
        sys.exit(1)


@main.command()
@click.argument("task_id")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.pass_context
def checkout(ctx, task_id, caller):
    """Checkout a specific task by ID and create its worktree.

    Use with shell integration for automatic cd:
        cd $(polecat checkout TASK_ID)

    Or add to your shell rc:
        pc() { cd "$(polecat checkout "$@")" 2>/dev/null || polecat checkout "$@"; }
    """
    # Validate task ID before any operations
    try:
        validate_task_id_or_raise(task_id)
    except TaskIDValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    task = manager.storage.get_task(task_id)
    if not task:
        print(f"Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    # Claim the task if not already in progress
    try:
        from lib.task_model import TaskStatus

        if task.status == TaskStatus.ACTIVE:
            task.status = TaskStatus.IN_PROGRESS
            task.assignee = caller
            manager.storage.save_task(task)
            print(f"Claimed: {task.title}", file=sys.stderr)
    except ImportError:
        pass

    try:
        worktree_path = manager.setup_worktree(task)
        # Output just the path for shell integration (cd $(polecat checkout ...))
        print(worktree_path)
    except Exception as e:
        print(f"Error setting up worktree: {e}", file=sys.stderr)
        sys.exit(1)


@main.command()
@click.option("--no-push", is_flag=True, help="Skip pushing to remote")
@click.option("--nuke", "do_nuke", is_flag=True, help="Also remove the worktree after finishing")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompts (required in non-interactive mode)",
)
@click.option(
    "--force-done",
    is_flag=True,
    help="Force task status to 'done' even if no git changes detected",
)
@click.pass_context
def finish(ctx, no_push, do_nuke, force, force_done):
    """Mark current task as ready for merge.

    Must be run from within a polecat worktree.
    Pushes branch and sets task status to 'merge_ready'.
    """
    import subprocess

    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    cwd = Path.cwd()

    # Detect if we're in a polecat worktree
    if not cwd.is_relative_to(manager.polecats_dir):
        print(
            f"Error: Not in a polecat worktree. Expected path under {manager.polecats_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Extract task ID from directory name
    task_id = cwd.relative_to(manager.polecats_dir).parts[0]
    task = manager.storage.get_task(task_id)

    if not task:
        print(f"Error: Task {task_id} not found in task database", file=sys.stderr)
        sys.exit(1)

    # --- SAFEGUARD 0: Completion Protection ---
    # If the task is already DONE, or in review/merge phase, do NOT override it.
    # This prevents the "infinite retry loop" where auto-finish resets a manually completed task.
    try:
        from lib.task_model import TaskStatus

        terminal_or_pr_statuses = (
            TaskStatus.DONE,
            TaskStatus.REVIEW,
            TaskStatus.MERGE_READY,
            TaskStatus.MERGING,
            TaskStatus.CANCELLED,
        )

        if task.status in terminal_or_pr_statuses:
            print(
                f"✅ Task {task_id} is in status '{task.status.value}'. Skipping auto-retry reset."
            )
            if do_nuke:
                print("Nuking worktree...")
                os.chdir(Path.home())  # Move out of worktree before nuking
                manager.nuke_worktree(task_id, force=False)
                print("Worktree removed")
            return
    except ImportError:
        pass

    print(f"Finishing task: {task.title} ({task_id})")

    # --- SAFEGUARD 1: Dirty Exit Protection ---
    # Check for uncommitted changes
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  Warning: Uncommitted changes detected.")
        # Automatically commit changes if they are simple
        print("  🧹 Automatically staging and committing changes...")
        try:
            subprocess.run(["git", "add", "-u"], check=True)  # Stage modified/deleted
            subprocess.run(["git", "add", "."], check=True)  # Stage new files (careful!)
            subprocess.run(
                ["git", "commit", "-m", "chore: saving uncommitted agent work"],
                check=True,
            )
            print("  ✅ Changes saved.")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to auto-commit: {e}")
            if not force:
                print(
                    "  🚫 Uncommitted changes could not be saved. Use --force to continue anyway."
                )
                sys.exit(1)

    # --- NO-CHANGES DETECTION ---
    # If the agent made no changes, the task was likely not completed (e.g., stuck in
    # hydration loop, crashed early, or other failure mode). Do NOT mark as done.
    # See: aops-91e4c3f2 - Gemini polecat workers stuck in hydration gate loop
    try:
        # First, fetch to ensure we have latest origin/main
        subprocess.run(
            ["git", "fetch", "origin", "main"],
            capture_output=True,
            check=False,
        )
        # Check if there are any commits on this branch vs origin/main
        diff_check = subprocess.run(
            ["git", "diff", "--quiet", "origin/main", "HEAD"],
            capture_output=True,
            check=False,
        )
        # git diff --quiet returns 0 if no changes, 1 if changes exist
        if diff_check.returncode == 0:
            if force_done:
                print("📭 No changes detected, but --force-done specified.")
                print("✅ Proceeding to mark as DONE (verified complete without changes).")
                try:
                    from lib.task_model import TaskStatus

                    task.status = TaskStatus.DONE
                    manager.storage.save_task(task)
                    print(f"✅ Task {task_id} marked as DONE.")
                except ImportError:
                    print("Warning: Could not update task status (lib.task_model not available)")

                # Optionally nuke
                if do_nuke:
                    print("Nuking worktree...")
                    os.chdir(Path.home())  # Move out of worktree before nuking
                    manager.nuke_worktree(task_id, force=True)
                    print("Worktree removed")
                else:
                    print(f"\nTo clean up later: polecat nuke {task_id}")
                return  # Exit early, task is DONE
            else:
                print("📭 No changes detected. Worker may not have completed the task.")
                print(
                    "⚠️  Marking as 'review' for investigation (use --force-done for legitimate zero-change tasks)."
                )
                # Mark task as REVIEW, NOT active (avoid infinite re-queue for non-code tasks)
                # Zero changes needs human/supervisor judgment — could be failure OR legitimate
                try:
                    from lib.task_model import TaskStatus

                    task.status = TaskStatus.REVIEW
                    task.assignee = None  # Clear assignee for review
                    task.body = (
                        (task.body or "")
                        + "\n\n## ⚠️ Review needed (zero changes detected)\n"
                        + "Worker finished without making changes. Needs investigation:\n"
                        + "- If the task legitimately requires no code changes, re-run with `--force-done`\n"
                        + "- If the worker failed silently, check transcript and retry\n"
                    )
                    manager.storage.save_task(task)
                    print("📋 Task sent to review queue")
                except ImportError:
                    print("Warning: Could not update task status (lib.task_model not available)")

                # Optionally nuke
                if do_nuke:
                    print("Nuking worktree...")
                    os.chdir(Path.home())  # Move out of worktree before nuking
                    manager.nuke_worktree(task_id, force=False)
                    print("Worktree removed")
                else:
                    print(f"\nTo clean up later: polecat nuke {task_id}")
                return  # Exit early, skip rest of finish flow

    except Exception as e:
        print(f"Warning: Could not check for changes against origin/main: {e}")
        # Fallback: try local main ref instead of origin/main
        try:
            diff_local = subprocess.run(
                ["git", "diff", "--quiet", "main", "HEAD"],
                capture_output=True,
                check=False,
            )
            if diff_local.returncode == 0:
                # Zero changes confirmed via local main ref
                if force_done:
                    print(
                        "📭 No changes detected (local main fallback), but --force-done specified."
                    )
                    print("✅ Proceeding to mark as DONE (verified complete without changes).")
                    try:
                        from lib.task_model import TaskStatus

                        task.status = TaskStatus.DONE
                        manager.storage.save_task(task)
                        print(f"✅ Task {task_id} marked as DONE.")
                    except ImportError:
                        print(
                            "Warning: Could not update task status (lib.task_model not available)"
                        )
                    if do_nuke:
                        print("Nuking worktree...")
                        os.chdir(Path.home())
                        manager.nuke_worktree(task_id, force=True)
                        print("Worktree removed")
                    else:
                        print(f"\nTo clean up later: polecat nuke {task_id}")
                    return
                else:
                    print(
                        "📭 No changes detected (local main fallback). Worker may not have completed the task."
                    )
                    print(
                        "⚠️  Marking as 'review' for investigation (use --force-done for legitimate zero-change tasks)."
                    )
                    try:
                        from lib.task_model import TaskStatus

                        task.status = TaskStatus.REVIEW
                        task.assignee = None
                        task.body = (
                            (task.body or "")
                            + "\n\n## ⚠️ Review needed (zero changes detected)\n"
                            + "Worker finished without making changes. Needs investigation:\n"
                            + "- If the task legitimately requires no code changes, re-run with `--force-done`\n"
                            + "- If the worker failed silently, check transcript and retry\n"
                        )
                        manager.storage.save_task(task)
                        print("📋 Task sent to review queue")
                    except ImportError:
                        print(
                            "Warning: Could not update task status (lib.task_model not available)"
                        )
                    if do_nuke:
                        print("Nuking worktree...")
                        os.chdir(Path.home())
                        manager.nuke_worktree(task_id, force=False)
                        print("Worktree removed")
                    else:
                        print(f"\nTo clean up later: polecat nuke {task_id}")
                    return
            # else: diff_local.returncode != 0 means changes exist, fall through to normal flow
        except Exception as e2:
            print(f"Warning: Fallback change detection also failed: {e2}")
            # Both origin/main and local main failed — needs human investigation
            print("⚠️  Cannot verify changes exist. Marking as 'review' (safe default).")
            try:
                from lib.task_model import TaskStatus

                task.status = TaskStatus.REVIEW
                task.assignee = None
                task.body = (
                    (task.body or "")
                    + "\n\n## ⚠️ Review needed (change detection failed)\n"
                    + "Could not compare against main to determine if worker made changes.\n"
                    + "- If the task legitimately requires no code changes, re-run with `--force-done`\n"
                    + "- If the worker failed silently, check transcript and retry\n"
                )
                manager.storage.save_task(task)
                print("📋 Task sent to review queue")
            except ImportError:
                print("Warning: Could not update task status (lib.task_model not available)")
            if do_nuke:
                print("Nuking worktree...")
                os.chdir(Path.home())
                manager.nuke_worktree(task_id, force=False)
                print("Worktree removed")
            else:
                print(f"\nTo clean up later: polecat nuke {task_id}")
            return

    # --- SAFEGUARD 2: Repo-Nuke Protection ---
    # Check if we are unexpectedly rewriting the whole repo
    # This prevents the "orphan branch" issue where an agent commits 1000+ files as new
    try:
        # Get shortstat diff against origin/main to see scale of changes
        diff_res = subprocess.run(
            ["git", "diff", "--shortstat", "origin/main", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Output format: " 10 files changed, 100 insertions(+), 50 deletions(-)"
        if diff_res.returncode == 0 and diff_res.stdout.strip():
            parts = diff_res.stdout.strip().split(",")
            files_changed_str = parts[0].strip().split(" ")[0]
            if files_changed_str.isdigit():
                files_changed = int(files_changed_str)
                if files_changed > 50:
                    print(
                        f"\n🚨 SAFEGUARD ACTIVATE: Large changeset detected ({files_changed} files)."
                    )
                    print("   This looks like a 'repo nuke' or orphan branch issue.")
                    print("   Run 'git reset --soft FETCH_HEAD' to recover if this is accidental.")
                    if not force:
                        print(
                            "   🚫 Large changeset requires confirmation. Use --force to push anyway."
                        )
                        sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not run repo checking safeguards: {e}")

    # Push to origin
    if not no_push:
        branch_name = f"polecat/{task_id}"

        # --- SAFEGUARD 3: Main-Push Blockade ---
        if branch_name == "main" or branch_name == "master":
            print("🚨 SAFEGUARD: Refusing to push 'main' branch via polecat.")
            sys.exit(1)

        # --- REBASE BEFORE PUSH ---
        # Fetch and rebase onto latest main to prevent orphan commits and merge conflicts
        print("🔄 Syncing with latest main before push...")
        try:
            # Fetch latest from origin
            subprocess.run(
                ["git", "fetch", "origin", "main"],
                check=True,
                capture_output=True,
            )

            # Check if we need to rebase (are we behind origin/main?)
            merge_base = subprocess.run(
                ["git", "merge-base", "HEAD", "origin/main"],
                capture_output=True,
                text=True,
                check=True,
            )
            origin_main = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                capture_output=True,
                text=True,
                check=True,
            )

            if merge_base.stdout.strip() != origin_main.stdout.strip():
                # We're behind, need to rebase
                print("  📥 Branch is behind origin/main, rebasing...")
                rebase_result = subprocess.run(
                    ["git", "rebase", "origin/main"],
                    capture_output=True,
                    text=True,
                )
                if rebase_result.returncode != 0:
                    # Rebase failed - abort and report
                    subprocess.run(["git", "rebase", "--abort"], check=False)
                    print("  ❌ Rebase failed due to conflicts.", file=sys.stderr)
                    print(f"  {rebase_result.stderr}", file=sys.stderr)
                    print("  Task will be marked for review.", file=sys.stderr)
                    # Don't exit - let it fall through to mark as review
                    try:
                        from lib.task_model import TaskStatus

                        task.status = TaskStatus.REVIEW
                        task.body += (
                            "\n\n## ⚠️ Rebase Failed\nConflicts detected during rebase onto main.\n"
                        )
                        manager.storage.save_task(task)
                    except ImportError:
                        pass
                    sys.exit(1)
                print("  ✅ Rebase successful")
            else:
                print("  ✅ Already up-to-date with main")

        except subprocess.CalledProcessError as e:
            print(f"  ⚠️ Sync failed: {e}", file=sys.stderr)
            # Continue anyway - the push might still work

        print(f"Pushing {branch_name} to origin...")
        try:
            # Fetch the branch tracking ref so --force-with-lease has current data.
            # Without this, rebase leaves the local tracking ref stale and push
            # is rejected with "(stale info)".
            subprocess.run(
                ["git", "fetch", "origin", branch_name],
                check=False,
                capture_output=True,
            )
            # Use --force for polecat branches (they're ephemeral worker branches)
            # After rebase, --force-with-lease would reject push due to stale tracking ref
            # Force is safe here: polecat branches are single-worker, disposable feature branches
            subprocess.run(
                [
                    "git",
                    "push",
                    "--force",
                    "-u",
                    "origin",
                    f"{branch_name}:{branch_name}",
                ],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error pushing to origin: {e}", file=sys.stderr)
            sys.exit(1)

    # --- GitHub PR Integration ---
    try:
        # Import locally to avoid potential circular dependencies
        try:
            from github import check_gh_installed, generate_pr_body
        except ImportError:
            # Fallback if running as module
            from .github import check_gh_installed, generate_pr_body

        if check_gh_installed():
            print("  🐙 GitHub CLI detected. Updating Pull Request...")
            pr_body = generate_pr_body(task)

            # Create a temp file for the body to handle multiline content safely
            import json
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                f.write(pr_body)
                body_file = f.name

            try:
                # Check if PR exists
                pr_check = subprocess.run(
                    [
                        "gh",
                        "pr",
                        "list",
                        "--head",
                        branch_name,
                        "--json",
                        "number",
                        "--state",
                        "open",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                prs = []
                if pr_check.returncode == 0 and pr_check.stdout.strip():
                    try:
                        prs = json.loads(pr_check.stdout)
                    except json.JSONDecodeError:
                        pass

                if prs:
                    # Update existing PR
                    pr_number = prs[0]["number"]
                    subprocess.run(
                        ["gh", "pr", "edit", str(pr_number), "--body-file", body_file],
                        check=True,
                        capture_output=True,
                    )
                    print(f"  ✅ Updated PR #{pr_number}")
                else:
                    # Create new PR
                    subprocess.run(
                        [
                            "gh",
                            "pr",
                            "create",
                            "--title",
                            task.title,
                            "--body-file",
                            body_file,
                            "--head",
                            branch_name,
                            "--base",
                            "main",
                        ],
                        check=True,
                        capture_output=True,
                    )
                    print("  ✅ Created new PR")

            except subprocess.CalledProcessError as e:
                # Don't fail the whole finish command if PR creation fails
                err_msg = e.stderr.decode().strip() if e.stderr else str(e)
                print(f"  ⚠️  Failed to manage PR: {err_msg}")
            except Exception as e:
                print(f"  ⚠️  Error in PR integration: {e}")
            finally:
                if os.path.exists(body_file):
                    os.unlink(body_file)

    except ImportError:
        print("  ⚠️  Could not import github module for PR integration.")
    except Exception as e:
        print(f"  ⚠️  Unexpected error in PR integration: {e}")

    # Update task status to merge_ready
    try:
        from lib.task_model import TaskStatus

        task.status = TaskStatus.MERGE_READY
        manager.storage.save_task(task)
        print("✅ Task marked as 'merge_ready'")
        print(
            "📋 If a PR was created, the review pipeline will handle merge. See logs above for PR status."
        )

    except ImportError:
        print("Warning: Could not update task status (lib.task_model not available)")

    # Optionally nuke
    if do_nuke:
        print("Nuking worktree...")
        os.chdir(Path.home())  # Move out of worktree before nuking
        # Branch was pushed and PR filed; merge check no longer applies here
        manager.nuke_worktree(task_id, force=True)
        print("Worktree removed")
    else:
        print(f"\nTo clean up later: polecat nuke {task_id}")


@main.command()
@click.argument("target", required=False)
@click.option("--force", "-f", is_flag=True, help="Delete even if work is not merged")
@click.pass_context
def nuke(ctx, target, force):
    """Destroy a polecat or crew worker, or clean up stale branches when run without args."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    if target:
        crew_path = manager.crew_dir / target
        if crew_path.exists():
            try:
                manager.nuke_crew(target, force=force)
                return
            except (ValueError, RuntimeError) as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        # Fallback to worktree logic
        try:
            validate_task_id_or_raise(target)
            manager.nuke_worktree(target, force=force)
            print(f"Nuked polecat {target}")
            return
        except TaskIDValidationError:
            print(
                f"Error: Target '{target}' is not a valid crew worker or task ID.", file=sys.stderr
            )
            sys.exit(1)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Target not provided, run stale cleanup
    print("No target provided. Cleaning up stale branches...")

    # 1. Cleanup stale worktrees
    if manager.polecats_dir.exists():
        exclude = {".repos", "crew"}
        for d in manager.polecats_dir.iterdir():
            if d.is_dir() and not d.name.startswith(".") and d.name not in exclude:
                task_id = d.name
                task = manager.storage.get_task(task_id) if manager.storage else None
                repo_path = manager.get_repo_path(task) if task else Path(".")
                branch_name = f"polecat/{task_id}"

                # Check if branch is merged or deleted
                is_stale = False
                if not manager._branch_exists(repo_path, branch_name):
                    is_stale = True
                elif manager._is_branch_merged(repo_path, branch_name):
                    is_stale = True

                if is_stale:
                    print(f"Nuking stale worktree: {task_id}")
                    try:
                        manager.nuke_worktree(task_id, force=True)
                    except (RuntimeError, ValueError) as e:
                        print(f"Warning: Failed to nuke {task_id}: {e}", file=sys.stderr)

    # 2. Cleanup stale crew clones
    if manager.crew_dir.exists():
        for c in manager.crew_dir.iterdir():
            if c.is_dir():
                crew_name = c.name
                branch_name = f"crew/{crew_name}"
                is_stale = False

                # We need to check if ANY of the project clones in the crew dir are stale
                # A crew is stale if all of its branches are merged or deleted
                projects = [d.name for d in c.iterdir() if d.is_dir()]
                if not projects:
                    continue

                all_stale = True
                for project in projects:
                    repo_path = manager.projects.get(project, {}).get("path")
                    if not repo_path:
                        repo_path = manager.repos_dir / f"{project}.git"

                    if not repo_path.exists():
                        continue

                    if manager._branch_exists(repo_path, branch_name):
                        if not manager._is_branch_merged(repo_path, branch_name):
                            all_stale = False
                            break

                if all_stale:
                    print(f"Nuking stale crew: {crew_name}")
                    try:
                        manager.nuke_crew(crew_name, force=True)
                    except (RuntimeError, ValueError) as e:
                        print(f"Warning: Failed to nuke crew {crew_name}: {e}", file=sys.stderr)


@main.command("list")
@click.pass_context
def list_polecats(ctx):
    """List active polecats."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    if not manager.polecats_dir.exists():
        print("No polecats directory found.")
        return

    # Directories to exclude from listing (system dirs)
    exclude = {".repos", "crew"}

    found = False
    for item in manager.polecats_dir.iterdir():
        if item.is_dir() and not item.name.startswith(".") and item.name not in exclude:
            print(f"{item.name} -> {item}")
            found = True

    if not found:
        print("No active polecats.")


@main.command()
@click.option("--stale-days", default=3, help="Days before flagging a PR as stale (default: 3)")
@click.pass_context
def sweep(ctx, stale_days):
    """Scan 'merge_ready' tasks and update status based on GitHub PR state.

    Checks each task in 'merge_ready' status for its corresponding PR.
    - If merged: sets task to 'done', cleans up worktree/branch.
    - If closed (not merged): sets task back to 'review'.
    - If changes requested: sets task back to 'review' and appends comments.
    - If stale (>N days): flags for attention in task body.
    """
    from datetime import timedelta

    import github

    try:
        from lib.task_model import TaskStatus
    except ImportError:
        print("Error: Task management libraries not found.", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    tasks = manager.storage.list_tasks(status=TaskStatus.MERGE_READY)

    if not tasks:
        print("No tasks in MERGE_READY status.")
        return

    print(f"Sweeping {len(tasks)} tasks in MERGE_READY status...")

    for task in tasks:
        pr_ref = task.pr_url or (str(task.pr) if task.pr else None)

        # If no PR metadata in task fields, try to extract from body
        if not pr_ref:
            # Look for PR URL pattern
            match = re.search(r"https://github\.com/[^/]+/[^/]+/pull/(\d+)", task.body or "")
            if match:
                pr_ref = match.group(0)

        if not pr_ref:
            print(f"  ⚠ Skipping {task.id}: No PR metadata found in task.")
            continue

        print(f"  Checking {task.id} (PR {pr_ref})...")
        pr_status = github.get_pr_status(pr_ref)

        if not pr_status:
            print(f"    ❌ Could not get status for PR {pr_ref}")
            continue

        state = pr_status.get("state")
        merged_at = pr_status.get("mergedAt")
        updated_at_str = pr_status.get("updatedAt")
        reviews = pr_status.get("reviews", [])

        # 1. PR Merged
        if state == "MERGED" or merged_at:
            print("    ✅ PR Merged! Marking task as DONE.")
            task.status = TaskStatus.DONE
            manager.storage.save_task(task)
            # Cleanup worktree
            try:
                manager.nuke_worktree(task.id, force=True)
                print("    🧹 Worktree and branch cleaned up.")
            except Exception as e:
                print(f"    ⚠ Cleanup failed: {e}")
            continue

        # 2. PR Closed (but not merged)
        if state == "CLOSED":
            print("    ❌ PR Closed without merge. Moving to REVIEW.")
            task.status = TaskStatus.REVIEW
            task.body += (
                f"\n\n## 🧹 Sweep Report ({datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')})\n"
            )
            task.body += f"**PR Closed without merge**: {pr_status.get('url')}\n"
            manager.storage.save_task(task)
            continue

        # 3. Changes Requested
        # Check if ANY active reviewer has CHANGES_REQUESTED
        # (GitHub PR view returns all reviews; we care about the latest state)
        latest_reviews = {}
        for r in reviews:
            login = r.get("author", {}).get("login")
            if login:
                latest_reviews[login] = r

        changes_requested = [
            r for r in latest_reviews.values() if r.get("state") == "CHANGES_REQUESTED"
        ]

        if changes_requested:
            print("    ❗ Changes requested. Moving to REVIEW.")
            task.status = TaskStatus.REVIEW
            task.body += (
                f"\n\n## 🧹 Sweep Report ({datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')})\n"
            )
            task.body += f"**Changes requested** on PR {pr_status.get('url') or pr_ref}:\n"
            for review in changes_requested:
                author = review.get("author", {}).get("login", "unknown")
                review_body = review.get("body", "No comment")
                task.body += f"- **{author}**: {review_body}\n"
            manager.storage.save_task(task)
            continue

        # 4. Stale check
        if updated_at_str:
            # fromisoformat handles 'Z' in Python 3.11+, for older we might need a workaround
            # but usually polecat runs on modern python.
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                if datetime.now(UTC) - updated_at > timedelta(days=stale_days):
                    print(f"    ⏳ PR is stale (> {stale_days} days). Flagging.")
                    # We don't change status, just add a note if not already flagged
                    if "PR is stale" not in (task.body or ""):
                        task.body += f"\n\n## ⏳ Stale PR Alert ({datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')})\n"
                        task.body += (
                            f"This PR has been open and inactive for more than {stale_days} days.\n"
                        )
                        manager.storage.save_task(task)
            except Exception as e:
                print(f"    ⚠ Could not parse updatedAt '{updated_at_str}': {e}")


@main.command()
def merge():
    """Scan for tasks in REVIEW status and merge them to main.

    This runs the Refinery: finds all tasks marked 'review',
    squash-merges their polecat branches, runs tests, and
    marks them 'done' on success.
    """
    from engineer import Engineer

    eng = Engineer()
    eng.scan_and_merge()


def _clone_has_changes(repo_path: Path) -> bool:
    """Check if a crew clone has any changes (committed or uncommitted) vs its upstream.

    Returns True if:
    - There are uncommitted changes in the working tree
    - The content of the current branch differs from the upstream default branch
    Returns False if the clone is clean and identical to origin/HEAD.
    """
    try:
        # Check for uncommitted changes (staged or unstaged)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if status.returncode == 0 and status.stdout.strip():
            return True

        # Check for commits beyond the merge base with origin's default branch
        # First, determine the default branch
        head_result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if head_result.returncode == 0:
            default_branch = head_result.stdout.strip()  # e.g., refs/remotes/origin/main
        else:
            default_branch = "origin/main"

        # git diff --quiet returns 0 if no differences, 1 if there are differences
        diff = subprocess.run(
            ["git", "diff", "--quiet", default_branch, "HEAD"],
            cwd=repo_path,
            capture_output=True,
            timeout=10,
        )
        return diff.returncode != 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # If we can't determine, assume there are changes (safe default)
        return True


def _branch_has_open_pr(branch_name: str, repo_path: Path) -> bool:
    """Check if a branch has an open PR on GitHub."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch_name, "--state", "open", "--json", "number"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            prs = json.loads(result.stdout)
            return len(prs) > 0
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return False


@main.command("c", hidden=True)
@click.argument("target", required=False, default=None)
@click.argument("extra", required=False, default=None)
@click.option("--name", "-n", help="Crew name (randomly generated if not specified)")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--interactive", "-i", is_flag=True, help="Drop into an interactive shell (no agent)")
@click.option("--resume", "-r", help="Resume existing crew worker by name")
@click.option("--keep", "-k", is_flag=True, help="Keep worktree even if a PR is open")
@click.pass_context
def crew_alias(ctx, target, extra, name, gemini, interactive, resume, keep):
    """Shorthand for 'crew'. See 'polecat crew --help'."""
    ctx.invoke(
        crew,
        target=target,
        extra=extra,
        name=name,
        gemini=gemini,
        interactive=interactive,
        resume=resume,
        keep=keep,
    )


@main.command()
@click.argument("target", required=False, default=None)
@click.argument("extra", required=False, default=None)
@click.option("--name", "-n", help="Crew name (randomly generated if not specified)")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--interactive", "-i", is_flag=True, help="Drop into an interactive shell (no agent)")
@click.option("--resume", "-r", help="Resume existing crew worker by name")
@click.option("--keep", "-k", is_flag=True, help="Keep worktree even if a PR is open")
@click.pass_context
def crew(ctx, target, extra, name, gemini, interactive, resume, keep):
    """Start an interactive crew session with worker isolation.

    Crew workers are persistent, named agents for interactive collaboration.
    Each crew session creates an isolated local git clone and drops you into it.
    Workers are sandboxed to their clone — no operations outside it.

    TARGET is a project alias (e.g., aops, bm), or 'repo' for arbitrary paths.
    If TARGET is 'repo', EXTRA is the path to the repository.

    \b
    Examples:
        polecat crew aops             # Crew in academicOps repo
        polecat crew bm               # Crew in buttermilk repo
        polecat crew repo /path/to/x  # Crew in arbitrary repo
        polecat crew -r audre         # Resume crew worker "audre"
        polecat crew -i aops          # Interactive shell in crew container
        polecat crew -g aops          # Gemini CLI in sandbox mode
    """
    import subprocess

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # --- Resolve target project(s) ---
    if resume:
        # Resume mode: ignore target, use existing crew
        projects = []  # Will be populated from existing worktrees
        crew_name = resume
        if crew_name not in manager.list_crew():
            print(
                f"Error: No crew worker named '{crew_name}'. Active: {manager.list_crew()}",
                file=sys.stderr,
            )
            sys.exit(1)
    elif target == "repo":
        # Ad-hoc repo mode: pc crew repo /path/to/repo
        if not extra:
            print("Error: 'repo' target requires a path argument.", file=sys.stderr)
            print("Usage: polecat crew repo /path/to/repo", file=sys.stderr)
            sys.exit(1)
        repo_path = Path(extra).expanduser().resolve()
        try:
            slug = manager.register_adhoc_project(repo_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        projects = [slug]
        crew_name = name or manager.generate_crew_name()
    elif target:
        # Named project/alias: pc crew aops, pc crew bm
        try:
            slug = manager.resolve_project_alias(target)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        projects = [slug]
        crew_name = name or manager.generate_crew_name()
    else:
        # No target and not resuming
        print("Error: 'crew' requires a target project or --resume.", file=sys.stderr)
        print("Usage: polecat crew <project>  # e.g., 'polecat crew aops'", file=sys.stderr)
        print("       polecat crew -r <name>  # resume existing crew", file=sys.stderr)
        sys.exit(1)

    print(f"\U0001f9d1\u200d\U0001f91d\u200d\U0001f9d1 Crew worker: {crew_name}")

    # Setup isolated clones for project(s)
    clone_paths = {}
    if resume:
        # Recover clone paths from existing crew directory and sync with upstream
        crew_path = manager.crew_dir / crew_name
        for project_dir in crew_path.iterdir():
            if project_dir.is_dir() and (project_dir / ".git").exists():
                clone_paths[project_dir.name] = project_dir
                print(f"\U0001f4c1 {project_dir.name}: {project_dir}")
                # Sync with upstream so we don't resume on stale code
                print(f"   Syncing {project_dir.name} with origin...")
                fetch_result = subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=project_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if fetch_result.returncode != 0:
                    print(f"   \u26a0 git fetch failed: {fetch_result.stderr.strip()}")
                    continue
                # Detect default branch from remote HEAD, fall back to project config
                head_result = subprocess.run(
                    ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                    cwd=project_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if head_result.returncode == 0:
                    # refs/remotes/origin/HEAD -> refs/remotes/origin/main
                    default_branch = head_result.stdout.strip().split("/")[-1]
                else:
                    default_branch = manager.projects.get(project_dir.name, {}).get(
                        "default_branch", "main"
                    )
                merge_result = subprocess.run(
                    ["git", "merge", "--ff-only", f"origin/{default_branch}"],
                    cwd=project_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if merge_result.returncode == 0:
                    print(f"   \u2705 Up to date with origin/{default_branch}")
                else:
                    print(
                        f"   \u26a0 Could not fast-forward to origin/{default_branch} "
                        f"(local changes?). Manual merge may be needed."
                    )
                    if merge_result.stderr:
                        print(f"      Git error: {merge_result.stderr.strip()}")
        projects = list(clone_paths.keys())
    else:
        try:
            for proj in projects:
                clone_path = manager.setup_crew_worktree(crew_name, proj)
                clone_paths[proj] = clone_path
                print(f"\U0001f4c1 {proj}: {clone_path}")
        except FileExistsError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error setting up crew clone: {e}", file=sys.stderr)
            sys.exit(1)

    if not clone_paths:
        print("Error: No clones available.", file=sys.stderr)
        sys.exit(1)

    # Determine working directory:
    # Single project -> drop directly into the project clone
    # Multiple projects -> use crew root (parent of all project clones)
    if len(clone_paths) == 1:
        work_dir = next(iter(clone_paths.values()))
    else:
        work_dir = manager.crew_dir / crew_name

    # Build agent command with isolation
    if interactive:
        cli_tool = "shell"
    elif gemini:
        cli_tool = "gemini"
    else:
        cli_tool = "claude"
    print(f"\n\U0001f91d Starting {cli_tool} crew session...")
    print(f"   Crew: {crew_name}")
    print(f"   Projects: {', '.join(projects)}")
    print(f"   Working dir: {work_dir}")
    print("-" * 50)

    if interactive:
        # Interactive shell: drop into bash inside the Docker container.
        # Both claude and gemini CLIs are pre-installed in the image along
        # with their aops plugins, so the user can run either manually.
        cmd = ["bash"]
    elif gemini:
        # Gemini: sandbox is enabled via the replicated settings.json to avoid
        # CLI bugs where --sandbox forces an internal network without internet access.
        # The image is built from Dockerfile via `make build-docker`.
        cmd = [
            "gemini",
        ]
    else:
        # Claude Code: sandbox via project settings.json + setting-sources
        cmd = [
            "claude",
            "--permission-mode=plan",
            "--dangerously-skip-permissions",
            "--setting-sources=user,project",
        ]

    # Set session type environment variable for hooks to detect
    # Use sanitized env: SSH stripped, git auth set to bot token only
    env = _make_worker_env(interactive=True)
    env["POLECAT_SESSION_TYPE"] = "crew"
    env["POLECAT_CREW_NAME"] = crew_name
    env["POLECAT_WORKTREE"] = str(work_dir)

    # Compute session directory for Claude transcript persistence.
    project_slug = target or projects[0]
    session_dir = _get_sessions_base() / "crew" / crew_name / project_slug

    tmp_gemini_home = None
    tmp_files: list[Path] = []
    if gemini and not interactive:
        # Replicate Gemini authentication if available.
        tmp_gemini_home = _replicate_gemini_auth(env, work_dir=work_dir)
        if tmp_gemini_home:
            print(f"   Auth: Replicated to {env['GEMINI_CLI_HOME']}")

        # Gemini --sandbox re-execs itself inside the container, so the image
        # needs the Gemini CLI installed. Use aops-crew (full image with AI CLIs).
        env.setdefault("GEMINI_SANDBOX_IMAGE", "aops-crew")

        # Set the hook state directory to Gemini's natural log path inside the container
        if tmp_gemini_home:
            container_sessions_dir = str(tmp_gemini_home / ".gemini" / "tmp" / project_slug)
        else:
            container_sessions_dir = str(Path.home() / ".gemini" / "tmp" / project_slug)

        env["AOPS_SESSION_STATE_DIR"] = container_sessions_dir

        # Mount the clean host session directory directly to Gemini's log path
        session_dir.mkdir(parents=True, exist_ok=True)
        mounts = env.get("SANDBOX_MOUNTS", "")
        new_mount = f"{session_dir.resolve()}:{container_sessions_dir}:rw"
        env["SANDBOX_MOUNTS"] = f"{mounts},{new_mount}" if mounts else new_mount

        # Provide a stable Gemini session ID based on the crew/task ID
        env["GEMINI_SESSION_ID"] = f"gemini-{crew_name}"

        _mount_aca_data_sandbox(env)

        # Gemini sandbox only forwards a hardcoded allowlist of env vars into
        # its Docker container. Use SANDBOX_FLAGS for simple -e flags and
        # SANDBOX_MOUNTS for volumes. Git credentials use a mounted .gitconfig
        # because shell-quote mangles the credential helper shell function.
        extra_flags = []
        for key, val in env.items():
            if key.endswith("_GATE_MODE") or key in (
                "ACA_DATA",
                "GH_TOKEN",
                "GEMINI_SANDBOX_IMAGE",
                "GEMINI_SESSION_ID",
                "AOPS_SESSION_STATE_DIR",
            ):
                extra_flags.extend(["-e", f"{key}={val}"])

        # Git credential helper — write a .gitconfig and mount it read-only.
        # SANDBOX_FLAGS can't carry the credential helper because shell-quote
        # interprets { } ; ( ) as operators, mangling the shell function.
        #
        # File-based credentials are preferred over SANDBOX_FLAGS -e for two reasons:
        # 1. Security: env vars are visible in /proc/<pid>/environ and `ps auxe`;
        #    mounted files are not leaked through process listings.
        # 2. Reliability: Gemini sandbox only forwards a hardcoded allowlist of env
        #    vars into the container. SANDBOX_FLAGS -e is kept as belt-and-suspenders
        #    but cannot be the primary mechanism.
        #
        # The token is embedded directly in the gitconfig so git does not need
        # $GH_TOKEN to be present in the container environment at push time.
        gh_token = env.get("GH_TOKEN") or os.environ.get("AOPS_BOT_GH_TOKEN")
        if gh_token:
            extra_flags.extend(["-e", "GIT_ASKPASS=true"])
            extra_flags.extend(["-e", f"GH_TOKEN={gh_token}"])
            extra_flags.extend(["-e", f"GITHUB_TOKEN={gh_token}"])
            extra_flags.extend(["-e", "SSH_AUTH_SOCK="])
            extra_flags.extend(["-e", "GIT_TERMINAL_PROMPT=0"])
            gitconfig = tempfile.NamedTemporaryFile(
                suffix=".gitconfig", delete=False, mode="w", prefix="polecat-"
            )
            # Embed token value directly — does not rely on $GH_TOKEN being in
            # the container environment (SANDBOX_FLAGS -e forwarding is unreliable).
            gitconfig.write(
                "[credential]\n"
                f'\thelper = !f() {{ echo username=x-access-token; echo "password={gh_token}"; }}; f\n'
                '[credential "https://github.com"]\n'
                f'\thelper = !f() {{ echo username=x-access-token; echo "password={gh_token}"; }}; f\n'
                '[url "https://github.com/"]\n'
                "\tinsteadOf = git@github.com:\n"
            )
            gitconfig.close()
            if tmp_files is not None:
                tmp_files.append(Path(gitconfig.name))
            # Mount via SANDBOX_MOUNTS (colon-separated from:to:opts).
            # Gemini sandbox maps homedir() to the same path in the container,
            # so mount .gitconfig at the host user's home path.
            container_gitconfig = str(Path.home() / ".gitconfig")
            mounts = env.get("SANDBOX_MOUNTS", "")
            new_mount = f"{gitconfig.name}:{container_gitconfig}:ro"
            env["SANDBOX_MOUNTS"] = f"{mounts},{new_mount}" if mounts else new_mount

            # gh CLI hosts.yml — mount token so `gh pr create` works without
            # needing GH_TOKEN in the container env (file-based auth fallback).
            gh_hosts = tempfile.NamedTemporaryFile(
                suffix=".yml", delete=False, mode="w", prefix="polecat-gh-hosts-"
            )
            gh_hosts.write(f"github.com:\n    oauth_token: {gh_token}\n    git_protocol: https\n")
            gh_hosts.close()
            if tmp_files is not None:
                tmp_files.append(Path(gh_hosts.name))
            container_gh_hosts = str(Path.home() / ".config" / "gh" / "hosts.yml")
            mounts = env.get("SANDBOX_MOUNTS", "")
            new_mount = f"{gh_hosts.name}:{container_gh_hosts}:ro"
            env["SANDBOX_MOUNTS"] = f"{mounts},{new_mount}" if mounts else new_mount

        if extra_flags:
            existing = env.get("SANDBOX_FLAGS", "")
            new_flags = " ".join(extra_flags)
            env["SANDBOX_FLAGS"] = f"{existing} {new_flags}".strip() if existing else new_flags

        final_cmd = cmd
    elif interactive:
        # Interactive shell: wrap in Docker container (same as Claude path)
        final_cmd = _build_docker_cmd(
            "shell",
            work_dir,
            env,
            cmd,
            is_interactive=True,
            tmp_files=tmp_files,
            session_dir=session_dir,
        )
    else:
        # Claude Code: manually wrap in docker container
        final_cmd = _build_docker_cmd(
            cli_tool,
            work_dir,
            env,
            cmd,
            is_interactive=True,
            tmp_files=tmp_files,
            session_dir=session_dir,
        )
    print(f"   Sessions: {session_dir}")

    # Resolve CLI binary to absolute path so subprocess doesn't depend on PATH lookup
    resolved = shutil.which(final_cmd[0], path=env.get("PATH"))
    if resolved:
        final_cmd[0] = resolved

    set_terminal_title(f"crew:{crew_name}")
    try:
        subprocess.run(final_cmd, cwd=work_dir, env=env)
    except FileNotFoundError:
        print(f"Error: '{cli_tool}' command not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n\u26a0\ufe0f  Session interrupted")
    finally:
        reset_terminal_title()
        # Clean up temporary Gemini home
        if tmp_gemini_home and tmp_gemini_home.exists():
            shutil.rmtree(tmp_gemini_home)
        # Clean up temporary files created by _build_docker_cmd
        for tmp_file in tmp_files:
            if tmp_file.is_dir():
                shutil.rmtree(tmp_file, ignore_errors=True)
            else:
                tmp_file.unlink(missing_ok=True)

    print("-" * 50)
    print(f"\n\U0001f4cb Crew '{crew_name}' session ended.")

    # Auto-cleanup: nuke clone if no changes were made or a PR is open
    branch_name = f"crew/{crew_name}"
    auto_nuke = False
    nuke_reason = ""
    if not keep:
        if not _clone_has_changes(work_dir):
            auto_nuke = True
            nuke_reason = "no changes made"
        elif _branch_has_open_pr(branch_name, work_dir):
            auto_nuke = True
            nuke_reason = f"PR open for {branch_name}"

    if auto_nuke:
        print(f"   {nuke_reason} — cleaning up clone.")
        try:
            manager.nuke_crew(crew_name, force=True)
            print("   Clone removed.")
        except (ValueError, RuntimeError) as e:
            print(f"   Cleanup failed: {e}", file=sys.stderr)
            print(f"   Manual cleanup: polecat nuke-crew {crew_name}")
    else:
        print(f"   Clone preserved at: {manager.crew_dir / crew_name}")
        print(f"   To resume: polecat crew -r {crew_name}")
        print(f"   To nuke:   polecat nuke-crew {crew_name}")


@main.command("list-crew")
@click.pass_context
def list_crew(ctx):
    """List active crew workers."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    crew = manager.list_crew()
    if not crew:
        print("No active crew workers.")
        return
    print("Active crew workers:")
    for name in crew:
        crew_path = manager.crew_dir / name
        projects = [d.name for d in crew_path.iterdir() if d.is_dir()]
        print(f"  {name}: {', '.join(projects)}")


def _fetch_github_issue(issue_ref: str, project: str | None) -> dict:
    """Fetch a GitHub issue and return a dict with task-like fields.

    Args:
        issue_ref: GitHub issue reference. Accepted formats:
            - "owner/repo#123"
            - "https://github.com/owner/repo/issues/123"
            - "#123" or "123" (requires --project to resolve the repo)
        project: Polecat project slug, used to resolve bare issue numbers.

    Returns:
        Dict with keys: id, title, body, project, repo, number, url
    """
    import json
    import re
    import subprocess

    repo = None
    number = None

    # Full URL: https://github.com/owner/repo/issues/123
    url_match = re.match(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)", issue_ref)
    if url_match:
        repo = url_match.group(1)
        number = url_match.group(2)

    # owner/repo#123
    if not repo:
        ref_match = re.match(r"([^/]+/[^#]+)#(\d+)", issue_ref)
        if ref_match:
            repo = ref_match.group(1)
            number = ref_match.group(2)

    # Bare #123 or 123
    if not repo:
        bare_match = re.match(r"#?(\d+)$", issue_ref)
        if bare_match:
            number = bare_match.group(1)
            if not project:
                print(
                    f"Error: Bare issue number '{issue_ref}' requires --project to resolve the repo.",
                    file=sys.stderr,
                )
                sys.exit(1)

    if number is None:
        print(f"Error: Could not parse issue reference: {issue_ref}", file=sys.stderr)
        sys.exit(1)

    gh_args = ["gh", "issue", "view", number, "--json", "title,body,number,url"]
    if repo:
        gh_args.extend(["--repo", repo])

    try:
        result = subprocess.run(gh_args, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        print("Error: 'gh' CLI not found. Install: https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching issue: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)

    # Synthesize a safe task ID for worktree/branch naming
    repo_slug = repo.replace("/", "-") if repo else (project or "gh")
    task_id = f"gh-{repo_slug}-{number}"

    return {
        "id": task_id,
        "title": data.get("title", f"Issue #{number}"),
        "body": data.get("body", ""),
        "project": project,
        "number": int(number),
        "url": data.get("url", ""),
        "repo": repo,
    }


class _IssueTask:
    """Lightweight task-like object for GitHub issues.

    Duck-types the attributes that setup_worktree and prompt_template need.
    """

    def __init__(self, issue_data: dict):
        self.id = issue_data["id"]
        self.title = issue_data["title"]
        self.body = issue_data["body"]
        self.project = issue_data["project"]
        self.type = "task"
        self.status = None
        self.parent = None
        self.priority = None
        self.tags = []
        self.soft_depends_on = []
        self.assignee = None
        self.issue_url = issue_data.get("url", "")
        self.issue_number = issue_data.get("number")
        self.issue_repo = issue_data.get("repo")


@main.command()
@click.option("--project", "-p", help="Project to claim tasks from")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.option("--task-id", "-t", help="Specific task ID to run (skips claim)")
@click.option("--issue", help="GitHub issue to run (owner/repo#N, URL, or #N with --project)")
@click.option("--no-finish", is_flag=True, hidden=True, help="(Deprecated, no-op)")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--interactive", "-i", is_flag=True, help="Run in interactive mode (not headless)")
@click.option(
    "--no-auto-finish",
    is_flag=True,
    help="Skip automatic 'polecat finish' on successful completion",
)
@click.pass_context
def run(ctx, project, caller, task_id, issue, no_finish, gemini, interactive, no_auto_finish):
    """Run a polecat cycle: claim → setup → work → finish.

    Claims a task, spawns a worktree, and runs claude with the task context.
    On successful completion (exit code 0), automatically runs `polecat finish`.

    Examples:
        polecat run -p aops              # Run next ready task from aops project
        polecat run -t task-123          # Run specific task
        polecat run --issue owner/repo#42  # Run a GitHub issue
        polecat run --issue 42 -p writing  # Run issue #42 from writing project repo
        polecat run -p aops --no-auto-finish  # Skip auto-finish on success
    """
    import subprocess

    if issue and task_id:
        print("Error: --issue and --task-id are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Step 1: Get/claim task (or fetch GitHub issue)
    is_issue = False
    if issue:
        # GitHub issue path — fetch metadata, create lightweight task object
        print(f"Fetching GitHub issue: {issue}...")
        issue_data = _fetch_github_issue(issue, project)
        task = _IssueTask(issue_data)
        is_issue = True
    elif task_id:
        # Validate task ID before any operations
        try:
            validate_task_id_or_raise(task_id)
        except TaskIDValidationError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        task = manager.storage.get_task(task_id)
        if not task:
            print(f"Task not found: {task_id}", file=sys.stderr)
            sys.exit(1)

        # Claim if not already in progress
        try:
            from lib.task_model import TaskStatus

            if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
                print(f"✅ Task {task_id} is already '{task.status.value}'.")
                sys.exit(0)

            # Refuse to re-dispatch tasks locked by an open PR (not yet merged).
            # MERGE_READY/REVIEW/MERGING all mean a PR was filed and is pending.
            # Even if status somehow reverted to ACTIVE, a pr_url/pr field signals prior work.
            _LOCKED_STATUSES = (TaskStatus.MERGE_READY, TaskStatus.REVIEW, TaskStatus.MERGING)
            pr_ref = task.pr_url or (f"#{task.pr}" if task.pr else None)
            if task.status in _LOCKED_STATUSES or pr_ref:
                print(
                    f"🔒 Task {task_id} is locked "
                    f"(status: {task.status.value}"
                    + (f", PR: {pr_ref}" if pr_ref else "")
                    + "). A PR already exists for this task — refusing to re-dispatch.",
                    file=sys.stderr,
                )
                sys.exit(2)  # Exit 2 = locked; distinct from exit 1 (error) / exit 3 (empty queue)

            if task.status == TaskStatus.ACTIVE:
                task.status = TaskStatus.IN_PROGRESS
                task.assignee = caller
                manager.storage.save_task(task)
        except ImportError:
            pass
    else:
        print(f"Looking for ready tasks{' in project ' + project if project else ''}...")
        task = manager.claim_next_task(caller, project)
        if not task:
            print("No ready tasks found.")
            sys.exit(3)  # Exit 3 = queue empty. Swarm treats non-zero as "stop worker".

    if is_issue:
        print(f"🎯 Issue: {task.title} ({getattr(task, 'issue_url', '') or task.id})")
    else:
        print(f"🎯 Task: {task.title} ({task.id})")

    # Step 2: Setup worktree
    try:
        worktree_path = manager.setup_worktree(task)
        print(f"📁 Worktree: {worktree_path}")
    except Exception as e:
        print(f"Error setting up worktree: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 3: Build prompt from task context (self-contained, no /pull needed)
    from polecat.prompt_template import build_polecat_prompt

    # Build task body — for issues, prepend the issue URL for reference
    task_body = task.body or ""
    issue_url = getattr(task, "issue_url", "")
    if is_issue and issue_url:
        task_body = f"**GitHub Issue**: {issue_url}\n\n{task_body}"

    # Resolve soft dependencies for context injection (local tasks only)
    soft_deps = None
    if not is_issue and task.soft_depends_on:
        soft_deps = []
        for dep_id in task.soft_depends_on:
            dep_task = manager.storage.get_task(dep_id)
            if dep_task:
                soft_deps.append(
                    {
                        "id": dep_task.id,
                        "title": dep_task.title,
                        "status": dep_task.status.value
                        if hasattr(dep_task.status, "value")
                        else str(dep_task.status),
                        "body": dep_task.body or "",
                    }
                )

    prompt = build_polecat_prompt(
        task_id=task.id,
        task_title=task.title,
        task_type=task.type.value if hasattr(task.type, "value") else str(task.type),  # type: ignore[reportAttributeAccessIssue]
        task_project=task.project or "",
        task_body=task_body,
        task_meta={
            "parent": task.parent,
            "priority": task.priority,
            "tags": task.tags,
            "status": (task.status.value if hasattr(task.status, "value") else str(task.status))
            if task.status is not None
            else None,
            "pr_url": getattr(task, "pr_url", None),
            "pr": getattr(task, "pr", None),
        },
        soft_deps=soft_deps,
        is_issue=is_issue,
    )

    # Step 4: Run agent in the worktree
    # Choose CLI tool based on --gemini flag
    cli_tool = "gemini" if gemini else "claude"
    mode = "interactive" if interactive else "headless"
    print(f"\n🤖 Starting {cli_tool} agent ({mode})...")
    print("-" * 50)

    # Build command - gemini and claude have different CLI interfaces
    if gemini:
        # Gemini CLI
        cmd = [
            "gemini",
            "--sandbox",
            "--approval-mode",
            "yolo",
        ]
        # Note: Gemini CLI doesn't support --session-id; it uses --resume for session management
        # For now, each polecat run starts a fresh session

        if interactive:
            # -i starts interactive mode with initial prompt
            cmd.extend(["-i", prompt])
        else:
            # Headless mode with auto-approve
            cmd.extend(["-p", prompt])
    else:
        # Claude CLI
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--setting-sources=user,project",
        ]

        if interactive:
            # Interactive: just append the prompt as positional arg
            cmd.append(prompt)
        else:
            # Headless: use -p for print mode
            cmd.extend(["-p", prompt, "--max-turns", HEADLESS_CLAUDE_MAX_TURNS])

    # Set session type environment variable for hooks to detect
    # Use sanitized env: SSH stripped, git auth set to bot token only
    env = _make_worker_env(interactive=interactive)
    env["POLECAT_SESSION_TYPE"] = "polecat"

    tmp_gemini_home = None
    tmp_files: list[Path] = []
    # Compute session directory for transcript persistence.
    project_slug = task.project or project or worktree_path.name
    run_session_dir = _get_sessions_base() / "polecats" / task.id / project_slug

    if gemini:
        # Replicate Gemini authentication if available.
        tmp_gemini_home = _replicate_gemini_auth(env, work_dir=worktree_path)
        if tmp_gemini_home:
            print(f"   Auth: Replicated to {env['GEMINI_CLI_HOME']}")

        # Gemini --sandbox re-execs itself inside the container, so the image
        # needs the Gemini CLI installed. Use aops-crew (full image with AI CLIs).
        env.setdefault("GEMINI_SANDBOX_IMAGE", "aops-crew")

        # Set the hook state directory to Gemini's natural log path inside the container
        if tmp_gemini_home:
            container_sessions_dir = str(tmp_gemini_home / ".gemini" / "tmp" / project_slug)
        else:
            container_sessions_dir = str(Path.home() / ".gemini" / "tmp" / project_slug)

        env["AOPS_SESSION_STATE_DIR"] = container_sessions_dir

        # Mount the clean host session directory directly to Gemini's log path
        run_session_dir.mkdir(parents=True, exist_ok=True)
        mounts = env.get("SANDBOX_MOUNTS", "")
        new_mount = f"{run_session_dir.resolve()}:{container_sessions_dir}:rw"
        env["SANDBOX_MOUNTS"] = f"{mounts},{new_mount}" if mounts else new_mount

        # Provide a stable Gemini session ID based on the task ID
        env["GEMINI_SESSION_ID"] = f"gemini-{task.id}"

        _mount_aca_data_sandbox(env)

        # Gemini sandbox only forwards a hardcoded allowlist of env vars into
        # its Docker container. Use SANDBOX_FLAGS for simple -e flags.
        extra_flags = []
        for key, val in env.items():
            if key.endswith("_GATE_MODE") or key in (
                "ACA_DATA",
                "GH_TOKEN",
                "GEMINI_SANDBOX_IMAGE",
                "GEMINI_SESSION_ID",
                "AOPS_SESSION_STATE_DIR",
            ):
                extra_flags.extend(["-e", f"{key}={val}"])

        if extra_flags:
            existing = env.get("SANDBOX_FLAGS", "")
            new_flags = " ".join(extra_flags)
            env["SANDBOX_FLAGS"] = f"{existing} {new_flags}".strip() if existing else new_flags

        final_cmd = cmd
    else:
        # Claude Code: manually wrap in docker container
        final_cmd = _build_docker_cmd(
            cli_tool,
            worktree_path,
            env,
            cmd,
            is_interactive=interactive,
            tmp_files=tmp_files,
            session_dir=run_session_dir,
        )
        print(f"   Sessions: {run_session_dir}")

    # Resolve CLI binary to absolute path so subprocess doesn't depend on PATH lookup
    resolved = shutil.which(final_cmd[0], path=env.get("PATH"))
    if resolved:
        final_cmd[0] = resolved

    if interactive:
        set_terminal_title(f"polecat:{task.id}")
    try:
        if interactive:
            # In interactive mode, we MUST NOT capture output or it will hang
            # and we want the user to see/interact with the CLI
            result = subprocess.run(
                final_cmd,
                cwd=worktree_path,
                env=env,
            )
            exit_code = result.returncode
            # No transcript to analyze in interactive mode (currently)
        else:
            result = subprocess.run(
                final_cmd,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                env=env,
            )
            exit_code = result.returncode
            # Display agent output after run
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            # Save transcript to $POLECAT_HOME/polecats/<task-id>.jsonl
            try:
                transcript_path = save_worker_transcript(
                    task_id=task.id,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=exit_code,
                    agent_type=cli_tool,
                    home_dir=manager.home_dir,
                )
                print(f"📝 Transcript saved: {transcript_path}")
            except OSError as e:
                print(f"⚠️  Warning: Failed to save transcript: {e}", file=sys.stderr)

            # Analyze the transcript for failures
            analyze_func = getattr(manager, "analyze_transcript", None)
            if analyze_func:
                analyze_func(task, result.stdout, result.stderr)

    except FileNotFoundError:
        print(f"Error: '{cli_tool}' command not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Agent interrupted by user")
        exit_code = 130
    finally:
        if interactive:
            reset_terminal_title()
        # Clean up temporary Gemini home
        if tmp_gemini_home and tmp_gemini_home.exists():
            shutil.rmtree(tmp_gemini_home)
        # Clean up temporary files created by _build_docker_cmd
        for tmp_file in tmp_files:
            if tmp_file.is_dir():
                shutil.rmtree(tmp_file, ignore_errors=True)
            else:
                tmp_file.unlink(missing_ok=True)

    print("-" * 50)

    # Step 5: Auto-finish on success (unless disabled)
    if exit_code == 0:
        print("\n✅ Agent completed successfully.")

        # Check for completion signals in stdout/stderr (e.g. fix already deployed)
        # This allows us to auto-finish even if no git changes were detected.
        auto_force_done = False
        completion_signals = [
            "verified complete",
            "fix already deployed",
            "no changes needed",
            "work already done",
            "verified the change is present",
            "verified the fix is already there",
            "task already completed",
            "already been completed",
        ]

        # Use result.stdout if it exists (not captured in interactive mode)
        agent_output = ""
        try:
            if not interactive and result.stdout:
                stdout = (
                    result.stdout
                    if isinstance(result.stdout, str)
                    else result.stdout.decode("utf-8", errors="replace")
                )
                agent_output += stdout
            if not interactive and result.stderr:
                stderr = (
                    result.stderr
                    if isinstance(result.stderr, str)
                    else result.stderr.decode("utf-8", errors="replace")
                )
                agent_output += stderr
        except (AttributeError, NameError):
            pass

        if agent_output:
            for signal in completion_signals:
                if signal.lower() in agent_output.lower():
                    print(f"✨ Found completion signal: '{signal}'")
                    auto_force_done = True
                    break

        if not no_auto_finish:
            print("🔄 Running auto-finish...")
            # Change to worktree directory and invoke finish directly
            original_cwd = os.getcwd()
            try:
                os.chdir(worktree_path)
                # Pass force_done if we detected a completion signal
                ctx.invoke(finish, no_push=False, do_nuke=True, force_done=auto_force_done)
                print("✅ Auto-finish completed.")
            except SystemExit as e:
                if e.code != 0:
                    print("⚠️  Auto-finish failed.")
                    print(f"   You can retry manually: cd {worktree_path} && polecat finish")
            except Exception as e:
                print(f"⚠️  Auto-finish failed: {e}")
                print(f"   You can retry manually: cd {worktree_path} && polecat finish")
            finally:
                os.chdir(original_cwd)
        else:
            print("📝 Auto-finish disabled. Run `polecat finish` when ready.")
            print(f"   Worktree: {worktree_path}")
    else:
        print(f"\n⚠️  Agent exited with code {exit_code}. Skipping auto-finish.")
        print(f"   Worktree: {worktree_path}")
        print(f"   To finish manually: cd {worktree_path} && polecat finish")


@main.command()
@click.argument("task_id")
@click.option("--transcript-lines", "-n", default=20, help="Number of transcript lines to show")
@click.pass_context
def analyze(ctx, task_id, transcript_lines):
    """Diagnose a stalled or failed task.

    Shows task metadata, worktree status, transcript tail, and suggested
    remediation actions for tasks that are stuck in_progress.

    Examples:
        polecat analyze aops-abc12345     # Full diagnostic
        polecat analyze aops-abc12345 -n 50  # Show more transcript
    """
    from datetime import datetime

    # Validate task ID
    try:
        validate_task_id_or_raise(task_id)
    except TaskIDValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Load task
    task = manager.storage.get_task(task_id)
    if not task:
        print(f"❌ Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Analyzing task: {task_id}")
    print("=" * 60)

    # --- Section 1: Task Metadata ---
    print("\n📋 TASK METADATA")
    print(f"   Title:    {task.title}")
    print(f"   Status:   {task.status.value if hasattr(task.status, 'value') else task.status}")
    print(f"   Assignee: {task.assignee or '(none)'}")
    print(f"   Project:  {task.project or 'aops'}")
    print(f"   Priority: P{task.priority}")

    # Calculate staleness
    if task.modified:
        now = datetime.now().astimezone()
        modified = task.modified
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=UTC)
        age = now - modified
        hours = age.total_seconds() / 3600
        print(f"   Modified: {modified.isoformat()} ({hours:.1f}h ago)")

        # Flag staleness
        if hours > 4:
            print(f"   ⚠️  STALE: No activity for {hours:.1f} hours")

    # --- Section 2: Worktree Status ---
    print("\n📁 WORKTREE STATUS")
    worktree_path = manager.polecats_dir / task_id

    if not worktree_path.exists():
        print(f"   ❌ Worktree not found at {worktree_path}")
        print("   💡 Suggestion: Task may not have been started, or worktree was nuked")
    else:
        print(f"   ✓ Worktree exists at {worktree_path}")

        # Check git status
        import subprocess

        git_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if git_status.returncode == 0:
            if git_status.stdout.strip():
                changes = git_status.stdout.strip().split("\n")
                print(f"   ⚠️  Uncommitted changes ({len(changes)} files):")
                for line in changes[:5]:
                    print(f"      {line}")
                if len(changes) > 5:
                    print(f"      ... and {len(changes) - 5} more")
            else:
                print("   ✓ Working tree clean")
        else:
            print(f"   ❌ Git status failed: {git_status.stderr.strip()}")

        # Check branch and commits
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if branch_result.returncode == 0:
            branch = branch_result.stdout.strip()
            print(f"   Branch: {branch}")

            # Check commits ahead of main
            commits_result = subprocess.run(
                ["git", "log", "--oneline", "origin/main..HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if commits_result.returncode == 0 and commits_result.stdout.strip():
                commits = commits_result.stdout.strip().split("\n")
                print(f"   Commits ahead of main ({len(commits)}):")
                for commit in commits[:3]:
                    print(f"      {commit}")
                if len(commits) > 3:
                    print(f"      ... and {len(commits) - 3} more")
            else:
                print("   No commits ahead of main")

    # --- Section 3: Transcript (if available) ---
    print("\n📜 TRANSCRIPT")
    try:
        from lib.paths import find_polecat_transcript

        transcript_path = find_polecat_transcript(task_id)
    except ImportError:
        transcript_path = manager.home_dir / "transcripts" / f"{task_id}.jsonl"

    if not transcript_path.exists():
        print(f"   (No transcript found at {transcript_path})")
        print("   💡 Transcript capture may not be enabled yet")
    else:
        import json

        try:
            # Read last N lines
            with open(transcript_path) as f:
                lines = f.readlines()

            if not lines:
                print("   (Transcript file is empty)")
            else:
                print(
                    f"   Showing last {min(transcript_lines, len(lines))} of {len(lines)} entries:"
                )
                print()
                for line in lines[-transcript_lines:]:
                    try:
                        entry = json.loads(line)
                        # Format depends on transcript structure
                        if "type" in entry:
                            print(
                                f"   [{entry.get('type', '?')}] {entry.get('message', entry.get('content', str(entry)[:80]))}"
                            )
                        else:
                            print(f"   {str(entry)[:100]}")
                    except json.JSONDecodeError:
                        print(f"   {line.strip()[:100]}")
        except Exception as e:
            print(f"   ❌ Failed to read transcript: {e}")

    # --- Section 4: Suggested Remediation ---
    print("\n💡 SUGGESTED ACTIONS")

    status_str = task.status.value if hasattr(task.status, "value") else str(task.status)

    if status_str == "in_progress":
        if not worktree_path.exists():
            print("   1. Task claimed but no worktree - may have crashed during setup")
            print(
                f"      → Reset: polecat reset-stalled --hours 0 --project {task.project or 'aops'}"
            )
            print("      → Or retry: polecat run -t {task_id}")
        elif hours > 4:
            print("   1. Task appears stalled (no activity > 4h)")
            print("      → Check if agent is still running")
            print("      → Reset if abandoned: polecat reset-stalled")
            print(f"      → Or manually finish: cd {worktree_path} && polecat finish")
        else:
            print("   1. Task is in progress and appears active")
            print("      → Wait for agent to complete, or check logs")
    elif status_str == "merge_ready":
        print("   1. Task ready to merge")
        print("      → Run: polecat merge")
    elif status_str == "review":
        print("   1. Task needs human review before merging")
        print(f"      → Review changes: cd {worktree_path}")
        print("      → Then set status to merge_ready or fix issues")
    elif status_str == "blocked":
        print("   1. Task is blocked")
        print("      → Check task body for blocker details")
        if task.depends_on:
            print(f"      → Depends on: {', '.join(task.depends_on)}")
    elif status_str == "done":
        print("   1. Task is already complete ✓")
        if worktree_path.exists():
            print(f"      → Consider cleanup: polecat nuke {task_id}")
    else:
        print(f"   Status is '{status_str}' - no specific suggestions")

    print()


@main.command("reset-stalled")
@click.option("--project", "-p", help="Filter by project")
@click.option("--hours", default=4.0, help="Hours since last modification (default: 4)")
@click.option("--dry-run", is_flag=True, help="Show what would be reset without changing")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt (required in non-interactive mode)",
)
@click.pass_context
def reset_stalled(ctx, project, hours, dry_run, force):
    """Reset stalled in_progress tasks back to active.

    Finds tasks that have been in_progress for > N hours and resets them.
    Useful for cleaning up after crashed/abandoned agents.
    """
    from datetime import datetime, timedelta

    try:
        from lib.task_index import TaskIndex
        from lib.task_model import TaskStatus
    except ImportError:
        print(
            "Error: Could not import task libraries. Ensure aops-core is available.",
            file=sys.stderr,
        )
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Calculate cutoff time
    cutoff = datetime.now().astimezone() - timedelta(hours=hours)

    print(f"Checking for tasks stalled since {cutoff.isoformat()}...")

    # List tasks
    candidates = manager.storage.list_tasks(status=TaskStatus.IN_PROGRESS, project=project)

    stalled = []
    pr_locked = []
    for task in candidates:
        # Ensure timezone awareness
        task_mod = task.modified
        if task_mod.tzinfo is None:
            task_mod = task_mod.replace(tzinfo=UTC)

        if task_mod < cutoff:
            # Never reset tasks that have an open PR — they are locked by prior work.
            if task.pr_url or task.pr:
                pr_locked.append(task)
            else:
                stalled.append(task)

    if pr_locked:
        print(f"Skipping {len(pr_locked)} PR-locked tasks (have open PR — will not reset):")
        for t in pr_locked:
            pr_ref = t.pr_url or f"#{t.pr}"
            print(f"  [{t.id}] {t.title} (PR: {pr_ref})")

    if not stalled:
        print("No stalled tasks found.")
        return

    print(f"Found {len(stalled)} stalled tasks (modified > {hours}h ago):")
    for t in stalled:
        print(f"  [{t.id}] {t.title} (modified: {t.modified.isoformat()})")

    if dry_run:
        print("\nDry run: no changes made.")
        return

    if not force:
        print(f"\nError: This will reset {len(stalled)} tasks. Use --force to confirm.")
        sys.exit(1)

    reset_count = 0
    for task in stalled:
        try:
            task.status = TaskStatus.ACTIVE
            task.assignee = None
            manager.storage.save_task(task)
            reset_count += 1
        except Exception as e:
            print(f"Failed to reset {task.id}: {e}", file=sys.stderr)

    # Rebuild index
    if reset_count > 0:
        try:
            # Try to get data root from storage or use default
            data_root = manager.storage.data_root
            index = TaskIndex(data_root)
            index.rebuild_fast()
            print("Index rebuilt.")
        except Exception as e:
            print(f"Warning: Failed to rebuild index: {e}", file=sys.stderr)

    print(f"\n✅ Reset {reset_count} tasks.")


def _send_notification(title: str, message: str, urgency: str = "normal"):
    """Send a desktop notification via notify-send if available.

    Args:
        title: Notification title
        message: Notification body
        urgency: low, normal, or critical
    """
    import shutil

    print(f"[{urgency.upper()}] {title}: {message}")

    if shutil.which("notify-send"):
        try:
            import subprocess

            subprocess.run(
                ["notify-send", "-u", urgency, title, message],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass


@main.command()
@click.option(
    "--interval",
    "-i",
    default=300,
    help="Polling interval in seconds (default: 300 = 5 min)",
)
@click.option(
    "--stall-threshold",
    "-s",
    default=30,
    help="Minutes without progress before stall alert (default: 30)",
)
@click.option("--project", "-p", help="Project to monitor (default: all)")
@click.pass_context
def watch(ctx, interval, stall_threshold, project):
    """Monitor swarm activity and send desktop notifications.

    Runs as a background process that:
    - Polls for new PRs and merge_ready tasks
    - Sends notification when a new PR is filed
    - Alerts if swarm stalls (no progress in threshold minutes)

    Examples:
        polecat watch              # Default: poll every 5min, stall at 30min
        polecat watch -i 60        # Poll every 60 seconds
        polecat watch -s 60        # Alert after 60min of no progress
        polecat watch &            # Run in background
    """
    import signal
    import time
    from datetime import datetime, timedelta

    try:
        from lib.task_model import TaskStatus
    except ImportError:
        print("Error: Could not import task libraries.", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Track seen PRs and last activity time
    seen_merge_ready = set()
    seen_review = set()
    last_activity = datetime.now().astimezone()

    # Graceful shutdown
    stop_requested = False

    def handle_signal(signum, frame):
        nonlocal stop_requested
        print("\nShutting down watch...")
        stop_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print("Starting polecat watch...")
    print(f"  Polling interval: {interval}s")
    print(f"  Stall threshold: {stall_threshold}min")
    print(f"  Project filter: {project or 'all'}")
    print("  Press Ctrl+C to stop.\n")

    # Initial scan to populate seen sets (don't alert on startup)
    try:
        merge_ready_tasks = manager.storage.list_tasks(
            status=TaskStatus.MERGE_READY, project=project
        )
        for task in merge_ready_tasks:
            seen_merge_ready.add(task.id)

        review_tasks = manager.storage.list_tasks(status=TaskStatus.REVIEW, project=project)
        for task in review_tasks:
            seen_review.add(task.id)

        print(f"Initial state: {len(seen_merge_ready)} merge_ready, {len(seen_review)} review")
    except Exception as e:
        print(f"Warning: Initial scan failed: {e}")

    while not stop_requested:
        try:
            now = datetime.now().astimezone()

            # Check for new merge_ready tasks (new PRs filed)
            merge_ready_tasks = manager.storage.list_tasks(
                status=TaskStatus.MERGE_READY, project=project
            )
            for task in merge_ready_tasks:
                if task.id not in seen_merge_ready:
                    seen_merge_ready.add(task.id)
                    last_activity = now
                    _send_notification(
                        "PR Filed",
                        f"{task.id}: {task.title}",
                        urgency="normal",
                    )

            # Check for new review tasks (merge failures)
            review_tasks = manager.storage.list_tasks(status=TaskStatus.REVIEW, project=project)
            for task in review_tasks:
                if task.id not in seen_review:
                    seen_review.add(task.id)
                    last_activity = now
                    _send_notification(
                        "Review Needed",
                        f"{task.id}: {task.title}",
                        urgency="critical",
                    )

            # Check for completed tasks (mark as activity)
            manager.storage.list_tasks(status=TaskStatus.DONE, project=project)
            # We don't track done tasks, but finding new ones means progress
            # This is a simplification - in production you'd track these too

            # Check for in_progress tasks (active work)
            in_progress = manager.storage.list_tasks(status=TaskStatus.IN_PROGRESS, project=project)
            if in_progress:
                # Check if any were modified recently
                for task in in_progress:
                    task_mod = task.modified
                    if task_mod.tzinfo is None:
                        task_mod = task_mod.replace(tzinfo=UTC)
                    if task_mod > last_activity:
                        last_activity = task_mod

            # Get leaf-ready tasks (actually pullable work)
            leaf_ready = manager.storage.get_ready_tasks(project=project)

            # Check for stall
            stall_cutoff = now - timedelta(minutes=stall_threshold)
            if last_activity < stall_cutoff:
                minutes_stalled = int((now - last_activity).total_seconds() / 60)
                _send_notification(
                    "Swarm Stalled",
                    f"No progress in {minutes_stalled} minutes",
                    urgency="critical",
                )
                # Reset to avoid spamming alerts
                last_activity = now

            # Status line (leaf-ready is the primary queue metric)
            ready_count = len(leaf_ready)
            active_count = len(in_progress)
            merge_ready_count = len(merge_ready_tasks)
            review_count = len(review_tasks)
            timestamp = now.strftime("%H:%M:%S")
            print(
                f"[{timestamp}] ready={ready_count} active={active_count} merge_ready={merge_ready_count} review={review_count}"
            )

            # Record periodic metrics for dashboard
            metrics.record_queue_depth("ready", count=ready_count, project=project)
            metrics.record_queue_depth("active", count=active_count, project=project)
            metrics.record_queue_depth("merge_ready", count=merge_ready_count, project=project)
            metrics.record_queue_depth("review", count=review_count, project=project)

        except Exception as e:
            print(f"Error during poll: {e}")

        # Sleep in small chunks to allow interrupt
        for _ in range(interval):
            if stop_requested:
                break
            time.sleep(1)

    print("Watch stopped.")


@main.command()
@click.option("--claude", "-c", default=0, help="Number of Claude workers")
@click.option("--gemini", "-g", default=0, help="Number of Gemini workers")
@click.option("--project", "-p", help="Project to focus on (default: all)")
@click.option("--caller", default="polecat", help="Identity claiming the tasks (default: bot)")
@click.option("--dry-run", is_flag=True, help="Simulate execution")
@click.pass_context
def swarm(ctx, claude, gemini, project, caller, dry_run):
    """Run a swarm of parallel Polecat workers.

    Spawns N claude and M gemini workers, managing CPU affinity.
    Restarting workers on success, stopping on failure.
    """
    try:
        from swarm import run_swarm
    except ImportError:
        # Fallback for when running as script in same dir
        try:
            from .swarm import run_swarm
        except ImportError:
            # Last ditch for direct execution
            try:
                import swarm as swarm_module

                run_swarm = swarm_module.run_swarm
            except ImportError:
                print("Error: Could not import swarm module.", file=sys.stderr)
                sys.exit(1)

    home = ctx.obj.get("home")
    run_swarm(claude, gemini, project, caller, dry_run, str(home) if home else None)


@main.command()
@click.option("--project", "-p", required=True, help="Project to pull tasks from")
@click.option(
    "--max-pairs", "-n", default=3, help="Max (task, runner) pairs per round (default: 3)"
)
@click.option("--max-rounds", default=10, help="Max supervisor loop iterations (default: 10)")
@click.option(
    "--supervisor",
    type=click.Choice(["claude", "gemini"]),
    default="claude",
    help="Which LLM to use as supervisor (default: claude)",
)
@click.option("--model", default=None, help="Model override for supervisor LLM")
@click.option("--dry-run", is_flag=True, help="Show what would be dispatched without running")
def supervise(project, max_pairs, max_rounds, supervisor, model, dry_run):
    """LLM-driven supervisor loop: plan, dispatch, verify, repeat.

    Each round: an LLM reviews the task queue, selects tasks to dispatch,
    workers run in parallel, then the LLM verifies results before continuing.
    """
    try:
        from supervisor_loop import supervisor_loop
    except ImportError:
        try:
            from .supervisor_loop import supervisor_loop
        except ImportError:
            print("Error: Could not import supervisor_loop module.", file=sys.stderr)
            sys.exit(1)

    supervisor_loop(
        project=project,
        max_pairs=max_pairs,
        max_rounds=max_rounds,
        supervisor=supervisor,
        model=model,
        dry_run=dry_run,
    )


def parse_duration(duration_str: str) -> int:
    """Parse a duration string like '8h', '1d', '30m' into seconds.

    Args:
        duration_str: Duration string with suffix h (hours), d (days), or m (minutes)

    Returns:
        Duration in seconds

    Raises:
        ValueError: If format is invalid
    """
    if not duration_str:
        raise ValueError("Duration string cannot be empty")

    duration_str = duration_str.strip().lower()

    # Handle numeric-only input (default to hours)
    if duration_str.isdigit():
        return int(duration_str) * 3600

    if len(duration_str) < 2:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value_str = duration_str[:-1]
    unit = duration_str[-1]

    try:
        value = float(value_str)
    except ValueError as e:
        raise ValueError(f"Invalid duration value: {value_str}") from e

    multipliers = {
        "m": 60,  # minutes
        "h": 3600,  # hours
        "d": 86400,  # days
    }

    if unit not in multipliers:
        raise ValueError(f"Unknown duration unit: {unit}. Use m, h, or d")

    return int(value * multipliers[unit])


@main.command()
@click.option(
    "--since",
    "-s",
    default="8h",
    help="Time period to summarize (e.g., 8h, 1d, 30m). Default: 8h",
)
@click.option("--project", "-p", help="Filter by project (default: all)")
@click.pass_context
def summary(ctx, since, project):
    """Generate a summary of polecat swarm work.

    Shows merged PRs, completed tasks, and queue changes for the specified
    time period. Output is markdown suitable for daily notes.

    Examples:
        polecat summary                # Last 8 hours
        polecat summary --since 1d     # Last day
        polecat summary -s 4h -p aops  # Last 4 hours, aops only
    """
    import json
    import subprocess
    from datetime import datetime, timedelta

    try:
        from lib.task_model import TaskStatus
    except ImportError:
        print(
            "Error: Could not import task libraries. Ensure aops-core is available.",
            file=sys.stderr,
        )
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Parse the duration
    try:
        seconds = parse_duration(since)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    cutoff = datetime.now().astimezone() - timedelta(seconds=seconds)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    # Format duration for display
    if seconds >= 86400:
        duration_display = f"{seconds // 86400} day(s)"
    elif seconds >= 3600:
        duration_display = f"{seconds // 3600} hour(s)"
    else:
        duration_display = f"{seconds // 60} minute(s)"

    print(f"## Polecat Swarm Summary (last {duration_display})")
    print()

    # --- Merged PRs ---
    print("### PRs Merged")
    print()

    merged_prs = []
    try:
        # Query GitHub for merged PRs
        # gh pr list --state merged returns PRs merged, filtered by date
        gh_cmd = [
            "gh",
            "pr",
            "list",
            "--state",
            "merged",
            "--search",
            f"merged:>{cutoff_iso[:10]}",  # Date only for search
            "--json",
            "number,title,mergedAt,headRefName",
            "--limit",
            "100",
        ]

        result = subprocess.run(gh_cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0 and result.stdout.strip():
            all_prs = json.loads(result.stdout)

            # Filter by actual merged time (gh search is date-only)
            for pr in all_prs:
                merged_at = pr.get("mergedAt", "")
                if merged_at:
                    # Parse ISO timestamp
                    try:
                        merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
                        if merged_dt >= cutoff:
                            # Filter by project if specified
                            if project:
                                # Check if branch matches project pattern
                                branch = pr.get("headRefName", "")
                                if not branch.startswith("polecat/"):
                                    continue
                            merged_prs.append(pr)
                    except (ValueError, TypeError):
                        pass

            if merged_prs:
                print(f"**{len(merged_prs)} PRs merged**")
                print()
                for pr in merged_prs[:20]:  # Limit display
                    print(f"- #{pr['number']}: {pr['title']}")
                if len(merged_prs) > 20:
                    print(f"- ... and {len(merged_prs) - 20} more")
            else:
                print("No PRs merged in this period.")
        else:
            print("(Could not query GitHub - gh CLI not available or not authenticated)")

    except FileNotFoundError:
        print("(GitHub CLI not installed)")
    except Exception as e:
        print(f"(GitHub query failed: {e})")

    print()

    # --- Completed Tasks ---
    print("### Tasks Completed")
    print()

    completed_tasks = []
    try:
        # Get all done tasks and filter by modified time
        all_done = manager.storage.list_tasks(status=TaskStatus.DONE, project=project)

        for task in all_done:
            task_mod = task.modified
            # Handle both date and datetime objects
            if hasattr(task_mod, "tzinfo"):
                # It's a datetime
                if task_mod.tzinfo is None:
                    task_mod = task_mod.replace(tzinfo=UTC)
            else:
                # It's a date - convert to datetime at midnight UTC
                task_mod = datetime.combine(task_mod, datetime.min.time(), tzinfo=UTC)

            if task_mod >= cutoff:
                completed_tasks.append(task)

        if completed_tasks:
            print(f"**{len(completed_tasks)} tasks completed**")
            print()
            for task in completed_tasks[:20]:
                print(f"- [{task.id}] {task.title}")
            if len(completed_tasks) > 20:
                print(f"- ... and {len(completed_tasks) - 20} more")
        else:
            print("No tasks completed in this period.")

    except Exception as e:
        print(f"(Task query failed: {e})")

    print()

    # --- Queue Status ---
    print("### Queue Status")
    print()

    try:
        # Count tasks by status
        ready_tasks = manager.storage.get_ready_tasks(project=project)
        in_progress = manager.storage.list_tasks(status=TaskStatus.IN_PROGRESS, project=project)
        blocked = manager.storage.list_tasks(status=TaskStatus.BLOCKED, project=project)
        review = manager.storage.list_tasks(status=TaskStatus.REVIEW, project=project)
        merge_ready = manager.storage.list_tasks(status=TaskStatus.MERGE_READY, project=project)

        print(f"- **Ready**: {len(ready_tasks)} tasks")
        print(f"- **In Progress**: {len(in_progress)} tasks")
        print(f"- **Blocked**: {len(blocked)} tasks")
        print(f"- **Review**: {len(review)} tasks")
        print(f"- **Merge Ready**: {len(merge_ready)} tasks")
        print(f"- **Completed** (this period): {len(completed_tasks)} tasks")

    except Exception as e:
        print(f"(Queue status query failed: {e})")

    print()

    # --- Active Workers ---
    print("### Active Workers")
    print()

    try:
        # Count active polecats (worktrees)
        exclude = {".repos", "crew", ".git"}
        active_polecats = [
            d.name
            for d in manager.polecats_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in exclude
        ]

        # Count crew workers
        crew_workers = manager.list_crew()

        if active_polecats:
            print(f"- **Polecats**: {len(active_polecats)} active worktrees")
        else:
            print("- **Polecats**: None active")

        if crew_workers:
            print(f"- **Crew**: {len(crew_workers)} workers ({', '.join(crew_workers)})")
        else:
            print("- **Crew**: None active")

    except Exception as e:
        print(f"(Worker status query failed: {e})")

    print()


if __name__ == "__main__":
    main()
