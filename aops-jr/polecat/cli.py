#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
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
        "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
        "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP",
        "ANTIGRAVITY_ENABLE_TELEMETRY",
        "CLAUDE_CODE_ENABLE_TELEMETRY",
        "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA",
        "ENABLE_BETA_TRACING_DETAILED",
        "BETA_TRACING_ENDPOINT",
        "OTEL_METRICS_EXPORTER",
        "OTEL_LOGS_EXPORTER",
        "OTEL_TRACES_EXPORTER",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
        "OTEL_RESOURCE_ATTRIBUTES",
        "OTEL_LOG_USER_PROMPTS",
        "OTEL_LOG_RAW_API_BODIES",
        "OTEL_LOG_TOOL_DETAILS",
        "OTEL_LOG_ASSISTANT_RESPONSES",
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


def _seed_confirmed(session_dir, task_id):
    """Best-effort check that agy actually saw the seeded task, not just that
    the container exited 0.

    A clean container exit with no trace of the task id anywhere agy actually
    records it saw is exactly the "live container, zero work" failure mode
    this function exists to catch (aops_5e7c6cc0): the seed can be silently
    dropped by a bug upstream of this check (e.g. Go flag-parser swallowing,
    a boot-time trust-dialog race) while the process still exits cleanly.
    This is deliberately conservative (a false "confirmed" is possible if the
    id happens to appear for unrelated reasons) — the goal is to catch the
    total-silence case, not certify correctness.

    Primary evidence: agy's own conversation transcript, written under the
    `agy-brain` mount at `<session-uuid>/.system_generated/logs/
    transcript*.jsonl`. Live-verified (2026-07-20 acceptance run against a
    real PKB task) to contain the seeded prompt verbatim as the first
    USER_INPUT entry — e.g. `"<USER_REQUEST>\\n/pull <task_id>\\n
    </USER_REQUEST>"`. `agy-cli.log`/`agy-logs/cli-*.log` are diagnostic/
    telemetry logs, NOT the conversation — an earlier version of this check
    looked there and produced false negatives (retried and then failed a
    dispatch that had, in fact, fully completed the task) because the task
    id never appears in those files. Kept as a secondary check only.
    """
    brain_dir = Path(session_dir) / "agy-brain"
    candidates = []
    if brain_dir.is_dir():
        candidates.extend(sorted(brain_dir.glob("*/.system_generated/logs/transcript*.jsonl")))
    agy_logs = Path(session_dir) / "agy-logs"
    if agy_logs.is_dir():
        candidates.extend(sorted(agy_logs.glob("cli-*.log")))
    cli_log = Path(session_dir) / "agy-cli.log"
    if cli_log.exists():
        candidates.append(cli_log)
    for path in candidates:
        try:
            content = path.read_text(errors="replace")
        except OSError:
            continue
        if task_id in content:
            return True
    return False


def _image_available_locally(image):
    """Return True if `image` already exists in the local Docker image cache.

    Used to gate `docker run` on a preflight check instead of letting Docker's
    own default pull-if-missing behaviour silently reach out to the registry.
    """
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _minimal_gemini_settings(host_settings):
    """Derive a secret-free ~/.gemini/settings.json for the container.

    The host file's `mcpServers` (live API keys, internal Tailscale-only
    URLs) and `hooks` (host-filesystem-only command paths) must never reach
    a container — every polecat worker got a byte-identical copy of the
    launching user's live credentials and internal network map (aops_624a462e).
    aops/aops-tools MCP tooling is installed into the image as agy plugins
    (see Dockerfile `agy plugin install`), not through this file's
    `mcpServers` key, so dropping it costs the container nothing. The only
    value carried over is the auth mechanism selector, needed for the
    staged oauth_creds.json / GEMINI_API_KEY credential to actually be
    honoured.
    """
    minimal = {}
    auth_type = ((host_settings.get("security") or {}).get("auth") or {}).get("selectedType")
    if auth_type:
        minimal["security"] = {"auth": {"selectedType": auth_type}}
    return minimal


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

        # settings.json is regenerated minimal, never copied verbatim — see
        # _minimal_gemini_settings (aops_624a462e).
        settings_src = gemini_src / "settings.json"
        if settings_src.exists():
            try:
                host_settings = json.loads(settings_src.read_text())
            except (OSError, ValueError):
                host_settings = {}
            (gemini_dst / "settings.json").write_text(
                json.dumps(_minimal_gemini_settings(host_settings), indent=2)
            )

        for f in ["google_accounts.json", "oauth_creds.json", "installation_id"]:
            src_file = gemini_src / f
            if src_file.exists():
                shutil.copy2(src_file, gemini_dst / f)

        # Replicate Antigravity CLI configs
        agy_src = gemini_src / "antigravity-cli"
        if agy_src.is_dir():
            agy_dst = gemini_dst / "antigravity-cli"
            agy_dst.mkdir(parents=True, exist_ok=True)
            for f in ["antigravity-oauth-token", "installation_id"]:
                src_file = agy_src / f
                if src_file.exists():
                    shutil.copy2(src_file, agy_dst / f)

            # agy 1.1.3's authoritative folder-trust store is this file's
            # `trustedWorkspaces` array — NOT the top-level
            # ~/.gemini/trustedFolders.json, which is the legacy gemini-cli
            # mechanism that agy 1.1.3 ignores. Regenerated minimal, never
            # copied: the host file's `mcpServers` key can carry API keys
            # the same way the top-level settings.json's does, and its
            # `trustedWorkspaces` lists host project paths the container
            # has no use for — it only ever needs /workspace trusted so
            # agy skips the "Do you trust the contents of this project?"
            # dialog (which would otherwise swallow any seeded prompt —
            # aops_428fe64b) (aops_624a462e).
            (agy_dst / "settings.json").write_text(
                json.dumps({"trustedWorkspaces": ["/workspace"]}, indent=2)
            )


@click.group()
def main():
    """Polecat-Lite: Lightweight containerized agent wrapper."""
    pass


@main.command(context_settings={"ignore_unknown_options": True})
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
@click.option(
    "--task",
    "-t",
    help="Task ID to work. When set and no explicit prompt/extra args are given, "
    "defaults the initial prompt to '/pull <task_id>'.",
)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def run(agent_cmd, project, repo_dir, session_name, mcp_url, task, extra_args):
    """Spin up the polecat container and run CLIs (claude, agy, shell, sleep).

    Anything after AGENT_CMD that isn't one of this command's own options is
    forwarded verbatim to the inner agent invocation — e.g.
    `polecat run claude --model opus "/pull task-abc123"` passes `--model opus`
    to `claude` and seeds `/pull task-abc123` as its initial prompt.
    """
    # Defensive guard: this command sets `ignore_unknown_options=True` so
    # flags meant for the inner agent CLI (e.g. `claude --model opus`) pass
    # through without click erroring on them. The side effect: if AGENT_CMD
    # is omitted and the first token is instead an unrecognized flag (e.g.
    # a stale `polecat run --model antigravity --force`, or any typo'd
    # option), click does NOT error — it silently assigns that flag to the
    # AGENT_CMD positional (e.g. agent_cmd='--model',
    # extra_args=('antigravity', '--force')). That garbage then flows
    # through inner_cmd all the way into the container's `exec "$@"`, which
    # dies deep inside Docker with a cryptic
    # "entrypoint.sh: line 88: exec: --: invalid option" instead of a clear
    # top-level error. Fail fast here with an actionable message instead
    # (bug: polecat container entrypoint.sh exec '--' invalid option breaks
    # all dispatch).
    if agent_cmd.startswith("-"):
        click.echo(
            f"Error: AGENT_CMD resolved to {agent_cmd!r}, which looks like "
            "an option, not an agent name.\n"
            "AGENT_CMD is a plain positional (e.g. `polecat run agy -t "
            "<task-id>`) — an unrecognized flag placed before it gets "
            "silently absorbed here instead of being rejected, corrupting "
            "the container invocation.\n"
            f"Parsed: agent_cmd={agent_cmd!r} extra_args={extra_args!r}\n"
            "Valid AGENT_CMD values: claude, agy, shell, bash, sleep[...]. "
            "See the aops-jr dispatch skill for canonical usage.",
            err=True,
        )
        sys.exit(1)

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

    # Default fallback: if aops, use current repo root. $AOPS (when set) is
    # the canonical monorepo root and is correct even when this file is
    # running from an installed plugin location — Path(__file__).parent.parent
    # would resolve to the plugin cache dir there, not a monorepo checkout.
    # Fall back to the historical __file__-relative heuristic only for
    # in-repo dev invocations that don't export $AOPS.
    if not workspace_dir and (project == "aops" or not project):
        aops_root = os.environ.get("AOPS")
        if aops_root:
            workspace_dir = Path(os.path.expandvars(os.path.expanduser(aops_root))).resolve()
        else:
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

    session_date = datetime.now().strftime("%Y%m%d")
    session_dir = sessions_base / "logs" / session_date / session_id / (project or "workspace")
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

        # Local dispatch must always run the image `make build-docker` just built
        # from THIS branch's dist/ — never a stale or registry copy (Nic ruling,
        # 2026-07-15: "local polecats must run on the image built by make
        # build-docker"). `--pull=never` below stops `docker run` from ever
        # reaching out to the registry itself; this preflight check turns the
        # resulting "no such image" failure into a clear, actionable message
        # instead of a bare Docker error.
        if not _image_available_locally(image):
            click.echo(
                f"Error: image '{image}' not found in the local Docker cache.\n"
                "Polecat only runs images built on this machine — it never pulls "
                "from a registry (a stale/registry image would silently ship stale "
                "plugins/MCP config).\n"
                "Run `make build-docker` (or `make build-docker-dev` for the ':dev' "
                "tag) to build it from your current branch, then retry.",
                err=True,
            )
            sys.exit(1)

        # Build environment forwards
        env = get_env_forwards()
        if pkb_url:
            env["PKB_MCP_URL"] = pkb_url

        # Determine internal CLI tool & args
        docker_args = []

        # Determine interactive TTY flag.
        # Bug (found 2026-07-14 dispatching a demo container over a non-tty SSH
        # pipe): the old check forced -it for agent_cmd in (shell, sleep, ...)
        # regardless of whether a TTY was actually available, so `docker run -it`
        # hard-failed with "the input device is not a TTY" instead of degrading
        # gracefully. This is the same bug class fixed once already in the
        # now-removed polecat/cli.py (task-academicops-a39821f4, PR #1340) for
        # the `crew -- -p "..."` headless path; cli_lite.py reintroduced it in a
        # sibling implementation that fix never touched.
        # Fix: never request -it without a real TTY on our side, and still honour
        # an explicit `-p` (headless prompt) flag as an unconditional override.
        explicit_headless = "-p" in extra_args
        is_interactive = not explicit_headless and sys.stdin.isatty()
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
            inner_cmd = [
                "agy",
                "--dangerously-skip-permissions",
                "--log-file",
                "/home/worker/.gemini/antigravity-cli/cli.log",
            ]
        elif agent_cmd in ("shell", "bash"):
            container_session_path = "/home/worker/.claude/projects/-workspace"
            inner_cmd = ["bash"]
        elif agent_cmd.startswith("sleep"):
            container_session_path = "/home/worker/.claude/projects/-workspace"
            inner_cmd = ["sleep", "infinity"]
        else:
            container_session_path = "/home/worker/.claude/projects/-workspace"
            inner_cmd = [agent_cmd]

        seeded_from_task = bool(task) and not extra_args

        if not extra_args and task:
            extra_args = (f"/pull {task}",)

        if extra_args:
            # agy has no bare-positional-prompt convention (unlike claude) — a
            # prompt must go via -i/--prompt-interactive (session continues) or
            # -p/--print (headless, exits after). A bare string like the
            # seeded "/pull <task>" is silently dropped, leaving agy idling at
            # a ready prompt forever (root cause, aops_cbeb71dc — verified
            # live 2026-07-16, since lost from the tree). Only wrap when the
            # caller hasn't already picked an explicit agy prompt/session flag.
            agy_prompt_flags = {
                "-p",
                "--print",
                "--prompt",
                "-i",
                "--prompt-interactive",
                "-c",
                "--continue",
                "--conversation",
            }
            if agent_cmd == "agy" and not agy_prompt_flags.intersection(extra_args):
                # Autonomous dispatch (seeded `/pull <task>` via -t, or any
                # one-shot prompt): run headless with `--print` so agy runs the
                # full agentic loop and then EXITS — the --rm container tears
                # down and the tmux session ends. The previous default,
                # `--prompt-interactive`, ran the loop but then sat idle at a
                # ready prompt forever, leaking a live container that looks like
                # progress (aops_5e7c6cc0 — the P2 dispatch reproduced it after
                # completing all its work + opening a PR, 2026-07-18).
                #
                # agy's `--print-timeout` defaults to 5m, which guillotines any
                # real agentic task; raise it to a generous, env-tunable ceiling
                # (POLECAT_AGY_PRINT_TIMEOUT) so long tasks complete but a wedged
                # session still cannot idle unbounded. Callers who genuinely want
                # an interactive/supervised session pass `-i`/`--prompt-interactive`
                # explicitly (honoured by the flag-intersection check above).
                # agy's flag parser is Go stdlib `flag`-based: a value-taking
                # flag unconditionally consumes the very next argv token as its
                # value, even if that token itself looks like another flag (it
                # never checks for a leading `-`). `--print`/`-p` is such a
                # value-taking flag — its value IS the prompt (confirmed via
                # `agy changelog` 1.1.2: "...when a prompt is provided via a
                # flag"). Putting `--print-timeout <dur>` directly after
                # `--print` therefore made `--print-timeout` (the literal
                # string) BECOME the prompt, silently dropping the real one —
                # the worker then dutifully investigated its own "prompt"
                # (aops_87e6964a: agy ran `--help`, read the antigravity-guide
                # skill, and wrote a print_timeout_guide.md instead of ever
                # touching `/pull <task>`). Fix: keep `--print-timeout <dur>`
                # BEFORE `--print`, and nothing else between `--print` and its
                # prompt value.
                agy_print_timeout = os.environ.get("POLECAT_AGY_PRINT_TIMEOUT", "60m")
                inner_cmd.extend(
                    [
                        "--print-timeout",
                        agy_print_timeout,
                        "--print",
                        extra_args[0],
                        *extra_args[1:],
                    ]
                )
            else:
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

        # Pre-create agy's bind-mount targets under the invoking host user
        # before docker run touches them. Without this, dockerd (running as
        # root) auto-vivifies missing bind sources as root-owned/0755 —
        # unwritable by the container's non-root `-u {uid}:{gid}` user, which
        # silently breaks agy's conversation persistence and log capture
        # (aops_cbeb71dc). agy's real active log always lives under
        # antigravity-cli/log/ via a cli.log.tmp symlink regardless of
        # --log-file, so that directory needs its own mount too.
        (session_dir / "agy-brain").mkdir(parents=True, exist_ok=True)
        (session_dir / "agy-cli.log").touch(exist_ok=True)
        (session_dir / "agy-logs").mkdir(parents=True, exist_ok=True)

        # Construct raw docker run command
        cmd = [
            "docker",
            "run",
            "--rm",
            # Never let docker fall back to pulling from the registry — local
            # dispatch must consume the image `make build-docker` just built from
            # this branch, not a stale/registry copy. The preflight check above
            # already confirmed the image exists locally; this is defense in
            # depth against a race (e.g. the image being pruned between check and
            # run) surfacing as a silent registry pull instead of a clear error.
            "--pull=never",
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
            f"{session_dir}/agy-logs:/home/worker/.gemini/antigravity-cli/log",
            "--add-host",
            "host.docker.internal:host-gateway",
        ]

        # Docker socket access: sandbox escape protection (aops_e3b194fb)
        # By default, containers do NOT have access to the host Docker socket
        # (which would allow privilege escalation / escape from the container).
        # Set docker.enable_socket: true in polecat.yaml ONLY if the container
        # legitimately needs to spawn other containers or access host Docker.
        # This is a scoped need and must be documented with its justification.
        if config.get("docker", {}).get("enable_socket", False):
            cmd.extend([
                "-v",
                "/var/run/docker.sock:/var/run/docker.sock",
            ])
            # Add groups for Docker socket permission
            try:
                docker_gid = Path("/var/run/docker.sock").stat().st_gid
                cmd.extend(["--group-add", str(docker_gid)])
            except Exception:
                pass

        # Add TTY flags
        cmd.extend(docker_args)

        # Add env vars to command line
        for k, v in env.items():
            cmd.extend(["-e", f"{k}={v}"])

        # Add image name and target CLI
        cmd.append(image)
        cmd.extend(inner_cmd)

        click.echo(f"📁 Workspace: {workspace_dir}")
        click.echo(f"📝 Sessions Logs: {session_dir}")

        # Execute the container. For an autonomous agy dispatch seeded via
        # `-t <task_id>` (the exact path repeatedly reproduced as a silent
        # no-op — aops_5e7c6cc0/aops_c40125ba), a clean process exit is not
        # by itself evidence the task was ever worked: the seed can be
        # dropped upstream (flag-parser swallowing, boot-time trust-dialog
        # race) while the container still exits 0. Verify agy's own log
        # actually references the task id; retry once on failure; fail fast
        # (non-zero exit, clear message) rather than silently reporting
        # success when seeding cannot be confirmed. Every other invocation
        # shape (claude, explicit prompts, interactive `-i`) is unaffected —
        # only propagating the real exit code instead of masking it.
        verify_seed = agent_cmd == "agy" and seeded_from_task
        max_attempts = 2 if verify_seed else 1
        returncode = 1
        seed_ok = not verify_seed  # non-seeded runs don't need this signal
        for attempt in range(1, max_attempts + 1):
            suffix = f" (attempt {attempt}/{max_attempts})" if max_attempts > 1 else ""
            click.echo(f"🚀 Running{suffix}: {' '.join(cmd[:15])} ...")
            returncode = subprocess.run(cmd).returncode

            if not verify_seed:
                break
            seed_ok = returncode == 0 and _seed_confirmed(session_dir, task)
            if seed_ok:
                break
            if attempt < max_attempts:
                click.echo(
                    f"⚠️  Could not confirm agy processed seeded task {task!r} "
                    f"(exit={returncode}, no trace of the task id in "
                    f"{session_dir}/agy-logs). Retrying once.",
                    err=True,
                )

        if not seed_ok:
            click.echo(
                f"Error: seeding task {task!r} into agy could not be "
                f"confirmed after {max_attempts} attempt(s) (last exit="
                f"{returncode}). agy's log shows no trace of the task id — "
                "the seed was likely dropped before delivery rather than "
                "processed and failed. Inspect "
                f"{session_dir}/agy-logs and {session_dir}/agy-cli.log. "
                "Refusing to report success.",
                err=True,
            )
            sys.exit(returncode if returncode else 1)
        if returncode != 0:
            sys.exit(returncode)

    finally:
        # Clean up staging directory
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)


if __name__ == "__main__":
    main()
