#!/usr/bin/env python3
"""Polecat: run an agent CLI inside an isolated container.

Every path, image reference, endpoint, and credential comes from the
environment or from the operator's config file. Nothing is defaulted here:
a missing required value is a loud failure, never a guess.
"""

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

# The environment forwarded into the container — the OpenTelemetry contract in
# specs/ARCHITECTURE.md plus the rest. One definition, shared with the `docker*`
# Makefile targets; polecat forwards these names and sets none of them.
try:  # imported as part of the installed package
    from .env_contract import CONTAINER_SET_ENV, FORWARDED_ENV
except ImportError:  # run directly as <plugin-root>/polecat/cli.py
    # Put the package's own parent on the path and import through the package,
    # so the module resolves the same way under both entry points.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from polecat.env_contract import CONTAINER_SET_ENV, FORWARDED_ENV


# A trailing flag that means the caller has already asked for headless, so
# polecat must not add its own. Both agent CLIs spell it the same way, and
# neither accepts anything else: `--non-interactive` has never existed.
HEADLESS_FLAGS = {"-p", "--print"}

# The container's own $ACA_DATA (Dockerfile, `ENV ACA_DATA=/data`) — a path
# only the image's own filesystem resolves, not a host value, so it is a
# constant here rather than something forwarded or configured (env_contract.py,
# CONTAINER_SET_ENV docstring, draws the same line). cope's layer 3
# (plugins/cope/hooks/rules.py) reads `$ACA_DATA/.agents/rules/`, so mounting
# a host directory at this path is what makes that layer reach the container.
CONTAINER_ACA_DATA = "/data"


def fail(message):
    """Report and exit non-zero. Nothing proceeds on a missing requirement."""
    click.echo(f"Error: {message}", err=True)
    sys.exit(1)


def load_config():
    """Load operator config from $AOPS_POLECAT_CONFIG, or polecat.yaml under
    $AOPS_SESSIONS. Absent config is legal; every required value can also
    arrive from the environment."""
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
            fail(f"failed to load polecat config from {cfg_path}: {e}")
    return {}


def load_local_overlay(polecat_home):
    """Load per-machine overrides from <polecat_home>/local.yaml."""
    local_path = os.path.join(polecat_home, "local.yaml")
    if os.path.exists(local_path):
        try:
            with open(local_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            fail(f"failed to load overlay from {local_path}: {e}")
    return {}


def expand(value):
    return Path(os.path.expandvars(os.path.expanduser(str(value))))


def resolve_polecat_home(config):
    """Local cache root for isolated clones, staging, and session logs.

    From $POLECAT_HOME, else config `polecat_home`. No default. Must be on the
    same filesystem as the repositories it clones — the clone hardlinks objects.
    """
    raw = os.environ.get("POLECAT_HOME") or config.get("polecat_home")
    if not raw:
        fail(
            "no polecat home configured. Set POLECAT_HOME, or `polecat_home` in "
            "the polecat config file. There is no default."
        )
    return expand(raw)


def resolve_image(config):
    """Container image reference. From $POLECAT_IMAGE, else config `docker.image`.

    No default: an image reference names a registry and an account, which
    belong to the operator's installation, never to this code.
    """
    image = os.environ.get("POLECAT_IMAGE") or config.get("docker", {}).get("image")
    if not image:
        fail(
            "no container image configured. Set POLECAT_IMAGE, or `docker.image` "
            "in the polecat config file. There is no default."
        )
    return image


def resolve_rules_dir(config):
    """Host directory of user-scoped cope/rbg rules to mount read-only into the
    container's layer 3 (`$ACA_DATA/.agents/rules/`, see CONTAINER_ACA_DATA).

    From $POLECAT_RULES_DIR, else config `rules_dir`. Wholly optional: absent
    is a clean, silent no-op — the container simply has no layer 3, exactly
    like a host session with $ACA_DATA unset (plugins/cope/hooks/rules.py).
    Configured but unusable is never silent: a path that does not resolve to a
    readable directory is a hard failure, because setting it is a claim the
    layer exists.
    """
    raw = os.environ.get("POLECAT_RULES_DIR") or config.get("rules_dir")
    if not raw:
        return None
    path = expand(raw)
    if not path.is_dir():
        fail(
            f"rules_dir {raw!r} does not resolve to a readable directory ({path}). "
            "Configuring a user-rules mount is a claim that it exists; a missing "
            "or unreadable directory is a hard failure, not a silent skip."
        )
    return path


def resolve_cope_evaluator(config):
    """cope's evaluator env for the container, from the operator's polecat.yaml
    `cope:` block — a configured, intentional path rather than requiring the
    operator to have exported COPE_EVALUATOR_* in the invoking shell.

    Each variable's host env value, if set, already wins in get_env_forwards()
    via FORWARDED_ENV; this only fills in what the host environment left
    unset. No default: an unconfigured session forwards nothing and cope's
    in-container evaluation stays off, exactly as evaluator.resolve() already
    treats a fully-absent configuration. A value that lands unusable (a bad
    protocol, a partial set) is not this layer's concern to validate — it
    reaches the same fail-loud-once-per-session degradation report that a
    misconfigured ambient environment already gets (plugins/cope/hooks/
    evaluator.py, resolve()); duplicating that check here would be a second
    copy of rules this plugin does not own.
    """
    cope_cfg = config.get("cope") or {}
    mapping = {
        "COPE_EVALUATOR_URL": "evaluator_url",
        "COPE_EVALUATOR_PROTOCOL": "evaluator_protocol",
        "COPE_EVALUATOR_MODEL": "evaluator_model",
        "COPE_EVALUATOR_API_KEY": "evaluator_api_key",
        "COPE_EVALUATOR_TIMEOUT": "evaluator_timeout",
    }
    env = {}
    for env_key, cfg_key in mapping.items():
        value = cope_cfg.get(cfg_key)
        if value not in (None, ""):
            env[env_key] = str(value)
    return env


def get_env_forwards(config=None):
    """Build the environment forwarded into the container."""
    config = config or {}
    env = {}

    oauth = os.environ.get("AOPS_CC_OAUTH_TOKEN") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if oauth:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth

    bot_token = os.environ.get("AOPS_BOT_GH_TOKEN")
    if bot_token:
        env["AOPS_BOT_GH_TOKEN"] = bot_token
        env["GH_TOKEN"] = bot_token
        env["GITHUB_TOKEN"] = bot_token
    else:
        for key in ("GH_TOKEN", "GITHUB_TOKEN"):
            if os.environ.get(key):
                env[key] = os.environ[key]

    for key in FORWARDED_ENV:
        if os.environ.get(key):
            env[key] = os.environ[key]

    # The plumbed config path for cope's evaluator: only fills in a name the
    # host environment left unset above, so an ambient export still wins.
    for key, value in resolve_cope_evaluator(config).items():
        env.setdefault(key, value)

    # Deny every interactive and agent-backed git credential path inside the
    # container: auth resolves from the forwarded token or not at all.
    env["GIT_ASKPASS"] = "true"
    env["SSH_AUTH_SOCK"] = ""
    env["GIT_SSH_COMMAND"] = "false"
    env["GIT_TERMINAL_PROMPT"] = "0"

    # Set, not forwarded: the SessionStart credential hook writes here, and the
    # path must resolve inside the container. A forwarded host path would name a
    # directory the container cannot see, so the hook would no-op and every
    # session would inherit the unscoped environment.
    env.update(CONTAINER_SET_ENV)

    return env


def _seed_confirmed(session_dir, task_id):
    """Best-effort check that the agent actually saw the seeded task.

    A clean exit is not evidence the task was worked: a seed can be dropped
    before delivery while the process still exits zero. The conversation
    transcript under the brain mount is the primary evidence; the CLI logs
    are diagnostic only and are checked as a fallback.
    """
    candidates = []
    brain_dir = Path(session_dir) / "agy-brain"
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


def _get_git_head(repo_path):
    """HEAD commit SHA if `repo_path` is inside a git repo, else None."""
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0 and res.stdout:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def _verify_workspace_delivery(workspace_dir, initial_head=None):
    """Confirm the workspace has no uncommitted changes and no unpushed commits.

    Returns (ok, error_message).
    """
    workspace_path = Path(workspace_dir)
    is_git = subprocess.run(
        ["git", "-C", str(workspace_path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if is_git.returncode != 0:
        return True, None

    status_res = subprocess.run(
        ["git", "-C", str(workspace_path), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    uncommitted = (status_res.stdout or "").strip()
    if uncommitted:
        return False, f"uncommitted changes present in workspace:\n{uncommitted}"

    current_head = _get_git_head(workspace_path)
    if current_head and initial_head and current_head != initial_head:
        ls_remote = subprocess.run(
            ["git", "-C", str(workspace_path), "ls-remote", "origin"],
            capture_output=True,
            text=True,
        )
        if ls_remote.returncode == 0:
            if current_head not in (ls_remote.stdout or ""):
                return False, (
                    f"local commits created (HEAD={current_head[:8]}) "
                    "but no pushed branch found on origin"
                )
        else:
            contains_res = subprocess.run(
                ["git", "-C", str(workspace_path), "branch", "-r", "--contains", "HEAD"],
                capture_output=True,
                text=True,
            )
            if not (contains_res.stdout or "").strip():
                return False, (
                    f"local commits created (HEAD={current_head[:8]}) "
                    "but not present on any remote branch"
                )

    return True, None


def resolve_isolated_workspace(canonical_dir, session_id, polecat_home):
    """Create a per-session standalone clone of `canonical_dir` and return the
    path to mount, so a container never writes to a shared checkout.

    The clone is standalone rather than a linked worktree: a linked worktree's
    `.git` is a pointer to an admin directory on the host that the container
    cannot resolve, so every git operation inside would fail. `--local`
    hardlinks objects, so the clone is cheap. `origin` is repointed at the
    canonical repo's own upstream so a push from inside the container reaches
    the real remote.

    Returns (workspace_path, cleanup_info). `cleanup_info` is None when
    `canonical_dir` is not in a git repository — there is nothing to isolate.
    """
    canonical_dir = Path(canonical_dir).resolve()

    toplevel = subprocess.run(
        ["git", "-C", str(canonical_dir), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if toplevel.returncode != 0:
        click.echo(
            f"Warning: {canonical_dir} is not inside a git repository — mounting "
            "it directly; no per-task isolation is possible.",
            err=True,
        )
        return canonical_dir, None

    repo_root = Path(toplevel.stdout.strip()).resolve()
    try:
        rel = canonical_dir.relative_to(repo_root)
    except ValueError:
        rel = Path(".")

    clones_dir = Path(polecat_home) / "worktrees"
    clones_dir.mkdir(parents=True, exist_ok=True)
    clone_path = clones_dir / session_id
    branch_name = f"polecat/{session_id}"

    # Clone from the commit the canonical repo currently has checked out, not
    # from its default branch.
    head_result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if head_result.returncode != 0:
        fail(f"failed to resolve HEAD in {repo_root}:\n{head_result.stderr}")
    head_sha = head_result.stdout.strip()

    origin_result = subprocess.run(
        ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    origin_url = origin_result.stdout.strip() if origin_result.returncode == 0 else None

    clone_result = subprocess.run(
        ["git", "clone", "--local", "--no-checkout", str(repo_root), str(clone_path)],
        capture_output=True,
        text=True,
    )
    if clone_result.returncode != 0:
        fail(
            f"failed to create isolated clone for session {session_id!r} "
            f"from {repo_root}:\n{clone_result.stderr}"
        )

    checkout_result = subprocess.run(
        ["git", "-C", str(clone_path), "checkout", "-B", branch_name, head_sha],
        capture_output=True,
        text=True,
    )
    if checkout_result.returncode != 0:
        shutil.rmtree(clone_path, ignore_errors=True)
        fail(
            f"failed to check out {head_sha} as {branch_name!r} in "
            f"{clone_path}:\n{checkout_result.stderr}"
        )

    if origin_url:
        subprocess.run(
            ["git", "-C", str(clone_path), "remote", "set-url", "origin", origin_url],
            capture_output=True,
            text=True,
        )

    isolated_path = (clone_path / rel).resolve() if str(rel) != "." else clone_path.resolve()

    if isolated_path in (canonical_dir, repo_root):
        fail(
            f"isolated workspace {isolated_path} resolved to the canonical "
            "checkout — refusing to mount a shared tree."
        )

    return isolated_path, {"path": clone_path}


def cleanup_isolated_workspace(cleanup_info):
    """Tear down the standalone clone. Best effort."""
    if cleanup_info:
        shutil.rmtree(cleanup_info["path"], ignore_errors=True)


def _image_available_locally(image):
    """True if `image` is already in the local image cache."""
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _minimal_agent_settings(host_settings):
    """Derive a secret-free settings file for the container.

    The host file's MCP server block carries live keys and internal URLs, and
    its hooks name host-only paths; neither may reach a container. Only the
    auth-mechanism selector is carried over, because the staged credential is
    otherwise ignored.
    """
    minimal = {}
    auth_type = ((host_settings.get("security") or {}).get("auth") or {}).get("selectedType")
    if auth_type:
        minimal["security"] = {"auth": {"selectedType": auth_type}}
    return minimal


def setup_staging(staging_dir, mcp_url, agent_home):
    """Stage per-session settings and credentials for the container.

    `agent_home` is the host directory holding the agent CLI's own config,
    from $POLECAT_AGENT_HOME. When unset, no credential is staged.
    """
    staging_dir = Path(staging_dir)

    settings = {}
    if mcp_url:
        # `pkb_mcp_url` is declared by the pkb plugin's userConfig, so the value
        # must be staged under that plugin's key. Under any other key the option
        # is silently ignored and the container's PKB MCP server starts with no
        # URL. The key is `<plugin name>@<marketplace name>`, and both halves
        # come from build/marketplace.toml — see build/marketplace.py.
        settings["pluginConfigs"] = {"pkb@academicOps": {"options": {"pkb_mcp_url": mcp_url}}}
    worker_model = os.environ.get("POLECAT_WORKER_MODEL")
    if worker_model:
        settings["model"] = worker_model
    if settings:
        claude_dir = staging_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    if not agent_home:
        return
    gemini_src = Path(agent_home)
    if not gemini_src.is_dir():
        return

    gemini_dst = staging_dir / ".gemini"
    gemini_dst.mkdir(parents=True, exist_ok=True)

    settings_src = gemini_src / "settings.json"
    if settings_src.exists():
        try:
            host_settings = json.loads(settings_src.read_text())
        except (OSError, ValueError):
            host_settings = {}
        (gemini_dst / "settings.json").write_text(
            json.dumps(_minimal_agent_settings(host_settings), indent=2)
        )

    for name in ("google_accounts.json", "oauth_creds.json", "installation_id"):
        src_file = gemini_src / name
        if src_file.exists():
            shutil.copy2(src_file, gemini_dst / name)

    agy_src = gemini_src / "antigravity-cli"
    if agy_src.is_dir():
        agy_dst = gemini_dst / "antigravity-cli"
        agy_dst.mkdir(parents=True, exist_ok=True)
        for name in ("antigravity-oauth-token", "installation_id"):
            src_file = agy_src / name
            if src_file.exists():
                shutil.copy2(src_file, agy_dst / name)

        # The container's only workspace must be pre-trusted, or the trust
        # dialog swallows the seeded prompt. Host project paths and MCP
        # blocks are never copied.
        (agy_dst / "settings.json").write_text(
            json.dumps({"trustedWorkspaces": ["/workspace"]}, indent=2)
        )


def _reject_bad_agent_cmd(agent_cmd, extra_args):
    """Catch the two shapes that would otherwise fail deep inside the container,
    after a clone and an image check, with an error naming neither polecat nor
    the flag's replacement."""
    # Unknown options pass through to the inner CLI, so an option appearing
    # where AGENT_CMD belongs would be silently absorbed as the agent name.
    if agent_cmd.startswith("-"):
        fail(
            f"AGENT_CMD resolved to {agent_cmd!r}, which is an option, not an "
            f"agent name (extra_args={extra_args!r}). AGENT_CMD is a plain "
            "positional: claude, agy, shell, bash, or sleep."
        )

    # Neither agent CLI has a --non-interactive flag; both exit on an unknown one.
    if agent_cmd in ("claude", "agy") and "--non-interactive" in extra_args:
        fail(
            f"{agent_cmd} has no --non-interactive flag and exits immediately when "
            "given one. Headless one-shot mode is --print (-p), which polecat adds "
            "on its own when stdin is not a tty."
        )


def _resolve_workspace(repo_dir, project, polecat_home):
    """The host directory to mount at /workspace. No default: an unresolvable
    workspace is a hard failure, never a guess at the current directory."""
    if repo_dir:
        workspace_dir = repo_dir.resolve()
    elif project:
        proj_path = load_local_overlay(polecat_home).get("paths", {}).get(project)
        workspace_dir = expand(proj_path).resolve() if proj_path else None
    else:
        workspace_dir = None

    if not workspace_dir or not workspace_dir.exists():
        fail(
            "could not resolve a workspace path. Pass --repo-dir, or map the "
            "project under `paths` in <polecat_home>/local.yaml. There is no "
            "default workspace."
        )
    return workspace_dir


def _build_inner_command(agent_cmd, extra_args, is_interactive, explicit_headless, task):
    """The command run inside the container, and the container path that agent
    writes its session state to.

    Returns (inner_cmd, container_session_path, seeded_from_task).
    """
    claude_session_path = "/home/worker/.claude/projects/-workspace"

    if agent_cmd == "claude":
        container_session_path = claude_session_path
        inner_cmd = ["claude", "--permission-mode=auto", "--setting-sources=user,project"]
        if not is_interactive and not explicit_headless:
            # Headless one-shot mode is `--print`, and it is the only one claude
            # has: without it claude opens its interactive UI against a pipe. The
            # prompt is a positional, so it still arrives from extra_args below,
            # or from stdin when there is none.
            inner_cmd.append("--print")
    elif agent_cmd == "agy":
        container_session_path = "/home/worker/.gemini/tmp/workspace"
        inner_cmd = [
            "agy",
            "--dangerously-skip-permissions",
            "--log-file",
            "/home/worker/.gemini/antigravity-cli/cli.log",
        ]
    elif agent_cmd in ("shell", "bash"):
        container_session_path = claude_session_path
        inner_cmd = ["bash"]
    elif agent_cmd.startswith("sleep"):
        container_session_path = claude_session_path
        inner_cmd = ["sleep", "infinity"]
    else:
        container_session_path = claude_session_path
        inner_cmd = [agent_cmd]

    seeded_from_task = bool(task) and not extra_args
    if seeded_from_task:
        extra_args = (f"/pull {task}",)

    if extra_args:
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
            # Autonomous dispatch runs headless so the agent completes its loop
            # and exits; an interactive prompt would leave a live container
            # idling forever. The print timeout must precede --print with
            # nothing between --print and its prompt value: a value-taking flag
            # consumes the next token whatever it is, so an interposed flag
            # becomes the prompt and the real one is silently dropped.
            print_timeout = os.environ.get("POLECAT_PRINT_TIMEOUT")
            if print_timeout:
                inner_cmd.extend(["--print-timeout", print_timeout])
            inner_cmd.extend(["--print", extra_args[0], *extra_args[1:]])
        else:
            inner_cmd.extend(extra_args)

    return inner_cmd, container_session_path, seeded_from_task


def _build_docker_argv(
    *,
    image,
    inner_cmd,
    workspace_dir,
    staging_dir,
    session_dir,
    container_session_path,
    env,
    rules_dir,
    config,
    docker_args,
):
    """The full `docker run` argv. Also pre-creates the bind-mount targets
    under `session_dir` — see below for why that cannot wait until launch."""
    # Pre-create the bind-mount targets as the invoking user. Docker
    # auto-creates a missing bind source as root, which the container's non-root
    # user cannot write, silently losing logs and conversation state.
    (session_dir / "agy-brain").mkdir(parents=True, exist_ok=True)
    (session_dir / "agy-cli.log").touch(exist_ok=True)
    (session_dir / "agy-logs").mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker",
        "run",
        "--rm",
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

    # Layer 3 of cope/rbg's rule set, read-only: absent when the operator
    # configured no rules_dir (resolve_rules_dir already failed loudly if one
    # was configured but unreadable, before any container started).
    if rules_dir:
        cmd.extend(["-v", f"{rules_dir}:{CONTAINER_ACA_DATA}/.agents/rules:ro"])

    # The host docker socket is a container escape. Mount it only where the
    # container legitimately spawns siblings, and document why.
    if config.get("docker", {}).get("enable_socket", False):
        cmd.extend(["-v", "/var/run/docker.sock:/var/run/docker.sock"])
        try:
            cmd.extend(["--group-add", str(Path("/var/run/docker.sock").stat().st_gid)])
        except Exception:
            pass

    cmd.extend(docker_args)
    for key, value in env.items():
        cmd.extend(["-e", f"{key}={value}"])
    cmd.append(image)
    cmd.extend(inner_cmd)
    return cmd


def _execute_with_seed_verification(cmd, *, image, inner_cmd, session_dir, task, verify_seed):
    """Run the container, and for a seeded dispatch confirm the agent actually
    saw the task before letting a clean exit stand as success.

    A clean exit is not evidence the task was worked: the seed can be dropped
    before delivery, which leaves a clean workspace the delivery guard reads as
    a pass. Retry once, then fail rather than report an unverified success.
    """
    max_attempts = 2 if verify_seed else 1
    returncode = 1
    seed_ok = not verify_seed

    for attempt in range(1, max_attempts + 1):
        suffix = f" (attempt {attempt}/{max_attempts})" if max_attempts > 1 else ""
        click.echo(f"Running{suffix}: {image} {' '.join(inner_cmd[:3])} ...")
        returncode = subprocess.run(cmd).returncode

        if not verify_seed:
            break
        seed_ok = returncode == 0 and _seed_confirmed(session_dir, task)
        if seed_ok:
            break
        if attempt < max_attempts:
            click.echo(
                f"Warning: could not confirm the agent processed seeded task "
                f"{task!r} (exit={returncode}). Retrying once.",
                err=True,
            )

    if not seed_ok:
        fail(
            f"seeding task {task!r} could not be confirmed after "
            f"{max_attempts} attempt(s) (last exit={returncode}). The agent's "
            f"transcript shows no trace of the task id, so the seed was "
            f"likely dropped before delivery rather than processed and "
            f"failed. Inspect {session_dir}. Refusing to report success."
        )
    return returncode


@click.group()
def main():
    """Polecat: run an agent CLI inside an isolated container."""


@main.command(context_settings={"ignore_unknown_options": True})
@click.argument("agent_cmd", default="claude")
@click.option("--project", "-p", help="Project name, resolved via local.yaml paths.")
@click.option(
    "--repo-dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Host path to a repository worktree, mounted exactly as given.",
)
@click.option("--session-name", "-s", help="Session id; names the log and clone directories.")
@click.option("--mcp-url", help="Override the knowledge-base MCP URL forwarded into the container.")
@click.option(
    "--task",
    "-t",
    help="Task id to work. With no explicit prompt, seeds '/pull <task-id>'.",
)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def run(agent_cmd, project, repo_dir, session_name, mcp_url, task, extra_args):
    """Run AGENT_CMD (claude, agy, shell, sleep) in a container.

    Anything after AGENT_CMD that is not one of this command's own options is
    forwarded verbatim to the inner invocation.
    """
    _reject_bad_agent_cmd(agent_cmd, extra_args)

    config = load_config()
    polecat_home = resolve_polecat_home(config)
    image = resolve_image(config)
    rules_dir = resolve_rules_dir(config)
    workspace_dir = _resolve_workspace(repo_dir, project, polecat_home)

    session_id = session_name or f"session-{uuid.uuid4().hex[:8]}"
    sessions_base = os.environ.get("AOPS_SESSIONS")
    sessions_base = Path(sessions_base) if sessions_base else polecat_home / "sessions"

    session_date = datetime.now().strftime("%Y%m%d")
    session_dir = sessions_base / "logs" / session_date / session_id / (project or "workspace")
    session_dir.mkdir(parents=True, exist_ok=True)

    # An explicit --repo-dir is the caller's own isolation to own; every other
    # path resolves to a shared checkout and must be cloned first.
    clone_cleanup = None
    if repo_dir is None:
        workspace_dir, clone_cleanup = resolve_isolated_workspace(
            workspace_dir, session_id, polecat_home
        )

    initial_head = _get_git_head(workspace_dir)
    mcp_url = mcp_url or os.environ.get("PKB_MCP_URL")

    staging_base = os.environ.get("POLECAT_STAGING_BASE") or str(polecat_home / "tmp" / "staging")
    Path(staging_base).mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix="staging-", dir=staging_base))
    os.chmod(staging_dir, 0o700)

    try:
        setup_staging(staging_dir, mcp_url, os.environ.get("POLECAT_AGENT_HOME"))

        # The container must run the image built on this machine. --pull=never
        # below blocks a registry fetch; this check turns the resulting "no
        # such image" into an actionable message.
        if not _image_available_locally(image):
            fail(
                f"image {image!r} is not in the local image cache. Polecat never "
                "pulls from a registry — a stale registry image would silently "
                "ship stale plugins. Build it locally, then retry."
            )

        env = get_env_forwards(config)
        if mcp_url:
            env["PKB_MCP_URL"] = mcp_url

        docker_args = []
        explicit_headless = bool(HEADLESS_FLAGS.intersection(extra_args))
        is_interactive = not explicit_headless and sys.stdin.isatty()
        if is_interactive:
            docker_args.append("-it")
        else:
            # Never request a TTY without one: docker run -it hard-fails when
            # stdin is a pipe.
            env["NONINTERACTIVE"] = "1"
            env["CI"] = "1"
            env["CLAUDE_CODE_NON_INTERACTIVE"] = "1"
            env["CLAUDE_NON_INTERACTIVE"] = "1"

        inner_cmd, container_session_path, seeded_from_task = _build_inner_command(
            agent_cmd, extra_args, is_interactive, explicit_headless, task
        )

        env["AOPS_POLECAT_CONTAINER"] = "1"
        env["POLECAT_CREW_NAME"] = session_id
        env["AOPS_SESSION_STATE_DIR"] = container_session_path
        env["AOPS_HOOK_LOG_PATH"] = f"{container_session_path}/polecat-session-hooks.jsonl"

        cmd = _build_docker_argv(
            image=image,
            inner_cmd=inner_cmd,
            workspace_dir=workspace_dir,
            staging_dir=staging_dir,
            session_dir=session_dir,
            container_session_path=container_session_path,
            env=env,
            rules_dir=rules_dir,
            config=config,
            docker_args=docker_args,
        )

        click.echo(f"Workspace: {workspace_dir}")
        click.echo(f"Session logs: {session_dir}")

        returncode = _execute_with_seed_verification(
            cmd,
            image=image,
            inner_cmd=inner_cmd,
            session_dir=session_dir,
            task=task,
            verify_seed=agent_cmd == "agy" and seeded_from_task,
        )
        if returncode != 0:
            sys.exit(returncode)

        delivery_ok, delivery_err = _verify_workspace_delivery(
            workspace_dir, initial_head=initial_head
        )
        if not delivery_ok:
            # Detection ends here; repair belongs to the dispatcher, which owns
            # the graph this task lives in (dispatch/SKILL.md section 6). A
            # launcher carrying its own client for the knowledge base would be a
            # second copy of that plugin's job, so the exit code and this message
            # are the whole of the handoff.
            fail(
                f"delivery guard failed for {task or 'session'!r}:\n{delivery_err}\n"
                "Refusing to report success. If this task is in a terminal status, "
                "the dispatcher must reopen it (via pauli) before filing a fix "
                "subtask or re-dispatching."
            )

    finally:
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        cleanup_isolated_workspace(clone_cleanup)


if __name__ == "__main__":
    main()
