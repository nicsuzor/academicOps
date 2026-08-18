#!/usr/bin/env python3
"""Polecat: run an agent CLI inside an isolated container.

Every path, image reference, endpoint, and credential comes from the
environment or from the operator's config file. Nothing is defaulted here:
a missing required value is a loud failure, never a guess.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

import click
import yaml

# The environment forwarded into the container — the OpenTelemetry contract in
# specs/ARCHITECTURE.md plus the rest. One definition, shared with the `docker*`
# Makefile targets; polecat forwards these names and sets none of them.
try:  # imported as part of the installed package
    from .env_contract import (
        CONTAINER_SET_ENV,
        FORWARDED_ENV,
        _rehost_loopback_urls,
        docker_env_args,
        format_otel_resource_attributes,
    )
    from .notify import notify_run_complete
except ImportError:  # run directly as <plugin-root>/polecat/cli.py
    # Put the package's own parent on the path and import through the package,
    # so the module resolves the same way under both entry points.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from polecat.env_contract import (
        CONTAINER_SET_ENV,
        FORWARDED_ENV,
        _rehost_loopback_urls,
        docker_env_args,
        format_otel_resource_attributes,
    )
    from polecat.notify import notify_run_complete


# A trailing flag that means the caller has already asked for headless, so
# polecat must not add its own. Both agent CLIs spell it the same way, and
# neither accepts anything else: `--non-interactive` has never existed.
HEADLESS_FLAGS = {"-p", "--print"}

# The container's own $ACA_DATA (Dockerfile, `ENV ACA_DATA=/data`) — a path
# only the image's own filesystem resolves, not a host value, so it is a
# constant here rather than something forwarded or configured (env_contract.py,
# CONTAINER_SET_ENV docstring, draws the same line). cope's layer 3
# (plugins/rbg/hooks/rules.py) reads `$ACA_DATA/.agents/rules/`, so mounting
# a host directory at this path is what makes that layer reach the container.
CONTAINER_ACA_DATA = "/data"


def fail(message: str) -> NoReturn:
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


def resolve_sessions_root():
    """Root of the sessions repository every run's session directory lands under.

    From $AOPS_SESSIONS. No default, and deliberately no config-file key:
    `load_config` finds the config file *at* `$AOPS_SESSIONS/polecat.yaml`, so a
    key inside that file could only be read once the value it defines is already
    known. A key that works only when `$AOPS_POLECAT_CONFIG` also happens to be
    set is a half-working surface, so this value comes from the environment
    alone.

    A fallback is worse than the missing value: a cron or detached-tmux dispatch
    would write a complete transcript into a directory the export pipeline never
    scans, exit zero, and report success with nothing to contradict it.
    """
    raw = os.environ.get("AOPS_SESSIONS")
    if not raw:
        fail(
            "no sessions root configured. Set AOPS_SESSIONS to the sessions "
            "repository this host records into. There is no default: a guessed "
            "path would collect transcripts nothing ever reads."
        )
    return expand(raw)


def resolve_rules_dir(config):
    """Host directory of user-scoped cope/rbg rules to mount read-only into the
    container's layer 3 (`$ACA_DATA/.agents/rules/`, see CONTAINER_ACA_DATA).

    From $POLECAT_RULES_DIR, else config `rules_dir`. Wholly optional: absent
    is a clean, silent no-op — the container simply has no layer 3, exactly
    like a host session with $ACA_DATA unset (plugins/rbg/hooks/rules.py).
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
    misconfigured ambient environment already gets (plugins/rbg/hooks/
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


def resolve_telemetry(config):
    """Resolve OpenTelemetry config from polecat.yaml `telemetry:` block.

    Variables defined here (endpoints, resource attributes) are the only runtime
    telemetry configuration passed to the container. All other standard tracing
    options are built into the Dockerfile itself. No fallback to host environment.
    """
    telemetry = config.get("telemetry") or {}
    env = {}
    if telemetry.get("endpoint"):
        env["BETA_TRACING_ENDPOINT"] = str(telemetry["endpoint"])
        env["OTEL_EXPORTER_OTLP_ENDPOINT"] = str(telemetry["endpoint"])
    if telemetry.get("trace_endpoint"):
        env["GENAI_ENGINE_TRACE_ENDPOINT"] = str(telemetry["trace_endpoint"])
    if telemetry.get("resource_attributes"):
        env["OTEL_RESOURCE_ATTRIBUTES"] = str(telemetry["resource_attributes"])
    return env


def resolve_git_identity(config):
    """Resolve git author/committer identity from polecat config (polecat.yaml).

    Must be defined under `git_identity` (keys: `name` and `email`).
    No fallbacks to host environment (os.environ) or user git config to avoid
    inheriting operator identity. A missing or incomplete identity is a hard failure.
    """
    if config is None or not isinstance(config, dict):
        fail(
            "no git identity configured. Set `git_identity` ({name: ..., email: ...}) "
            "in polecat config (polecat.yaml). There is no default or env fallback."
        )

    raw_identity = config.get("git_identity")
    if not isinstance(raw_identity, dict):
        fail(
            "no git identity configured. Set `git_identity` ({name: ..., email: ...}) "
            "in polecat config (polecat.yaml). There is no default or env fallback."
        )

    identity = dict(raw_identity)
    name = identity.get("name")
    email = identity.get("email")

    if not name or not email:
        fail("git_identity in polecat config must contain both `name` and `email`.")

    return {
        "GIT_AUTHOR_NAME": str(name),
        "GIT_AUTHOR_EMAIL": str(email),
        "GIT_COMMITTER_NAME": str(name),
        "GIT_COMMITTER_EMAIL": str(email),
    }


def get_env_forwards(config=None):
    """Build the environment forwarded into the container."""
    config = config or {}
    env = {}

    # Git identity MUST come strictly from polecat.yaml git_identity block.
    # No fallback to host environment.
    env.update(resolve_git_identity(config))

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

    git_keys = {"GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"}
    for key in FORWARDED_ENV:
        if key in git_keys:
            continue
        if os.environ.get(key):
            env[key] = os.environ[key]

    # The plumbed config path for cope's evaluator: only fills in a name the
    # host environment left unset above, so an ambient export still wins.
    for key, value in resolve_cope_evaluator(config).items():
        env.setdefault(key, value)

    # Telemetry configuration (strictly from config, no host env fallback)
    env.update(resolve_telemetry(config))

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

    return _rehost_loopback_urls(env)


#: Claude Code names each conversation transcript `<session-uuid>.jsonl`. Matched
#: by shape so the session dir's other `.jsonl` files — polecat's own hook log
#: above all — can never be mistaken for the agent's conversation.
_CLAUDE_TRANSCRIPT_NAME = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$"
)


def _transcript_paths(session_dir):
    """Every conversation transcript this run persisted into `session_dir`.

    The two agent CLIs write to different places, and both are decided here by
    the mounts `_build_docker_argv` makes:

    - `claude`: `session_dir` *is* the container's own project-state directory
      for `cwd=/workspace` (`CLAUDE_SESSION_PATH`, mounted as
      `container_session_path`), so claude's native `<session-uuid>.jsonl` lands
      at the root of `session_dir`. Confirmed against live session dirs under
      `$AOPS_SESSIONS/logs/` for both `entrypoint=cli` (interactive) and
      `entrypoint=sdk-cli` (the `--print` dispatch path), each recording
      `cwd=/workspace`.
    - `agy`: `session_dir/agy-brain` is mounted at the CLI's brain directory, and
      the conversation lands under
      `<uuid>/.system_generated/logs/transcript*.jsonl`.

    A `shell`/`sleep`/other container runs no agent CLI and legitimately
    persists neither.
    """
    session_dir = Path(session_dir)
    paths = []
    if session_dir.is_dir():
        paths.extend(
            sorted(p for p in session_dir.glob("*.jsonl") if _CLAUDE_TRANSCRIPT_NAME.match(p.name))
        )
    brain_dir = session_dir / "agy-brain"
    if brain_dir.is_dir():
        paths.extend(sorted(brain_dir.glob("*/.system_generated/logs/transcript*.jsonl")))
    return paths


def _verify_transcript_created(session_dir: Path) -> dict:
    """Check `.jsonl` transcript existence and count line events (`event_count`).

    Inspects `session_dir` for conversation transcripts persisted by agent CLIs,
    calculates size and line event counts, and returns a dictionary of
    transcript metadata.
    """
    session_dir = Path(session_dir)
    paths = _transcript_paths(session_dir)

    largest = None
    largest_size = -1
    count = 0
    total_event_count = 0

    for path in paths:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        count += 1
        if size > largest_size:
            largest, largest_size = path, size

        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.strip():
                        total_event_count += 1
        except OSError:
            pass

    if largest is None or largest_size <= 0 or total_event_count == 0:
        return {
            "found": False,
            "path": None,
            "bytes": None,
            "count": count,
            "transcript_path": None,
            "transcript_bytes": None,
            "event_count": 0,
        }

    path_str = str(largest)
    return {
        "found": True,
        "path": path_str,
        "bytes": largest_size,
        "count": count,
        "transcript_path": path_str,
        "transcript_bytes": largest_size,
        "event_count": total_event_count,
    }


def transcript_evidence(session_dir):
    """What the run actually persisted, as recorded in run.json.

    `run.json` names the session directory but said nothing about its contents,
    so a run that wrote zero bytes was indistinguishable from one that wrote a
    full conversation: both exited 0 and both recorded `"status": "success"`.
    This is what makes that claim falsifiable — which transcript, how big, and
    how many.

    It does not decide `status`: a `shell` or `sleep` container has no
    conversation to persist, so an absent transcript is a fact to record, not a
    failure to declare. The `degraded[]` entry is what makes an unexpected
    absence legible.
    """
    return _verify_transcript_created(session_dir)


def _seed_confirmed(session_dir, task_id):
    """Best-effort check that the agent actually saw the seeded task.

    A clean exit is not evidence the task was worked: a seed can be dropped
    before delivery while the process still exits zero. The conversation
    transcript is the primary evidence, and it is read the same way whichever
    agent CLI ran the dispatch (`_transcript_paths`); agy's CLI logs are
    diagnostic only and are checked as a fallback.
    """
    candidates = list(_transcript_paths(session_dir))
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


def resolve_isolated_workspace(
    canonical_dir, session_id, polecat_home, base=None, config=None, branch=None, quiet=False
):
    """Create a per-session standalone clone of `canonical_dir` and return the
    path to mount, so a container never writes to a shared checkout.

    The clone is created from the commit specified in `base` if provided,
    otherwise falling back to `branch`, then the `branch` key in `config`
    (polecat.yaml), and defaulting to HEAD if none is set.

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
        if not quiet:
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
    branch_name = branch or f"polecat/{session_id}"

    config = config or {}
    base_ref = base or branch or config.get("branch") or "HEAD"

    # Resolve the base commit SHA from base_ref (base option, branch option, polecat.yaml branch, or HEAD)
    base_sha = None
    last_err = ""
    refs_to_try = [base_ref]
    if not base_ref.startswith("origin/"):
        refs_to_try.append(f"origin/{base_ref}")

    for ref_to_try in refs_to_try:
        base_result = subprocess.run(
            ["git", "-C", str(canonical_dir), "rev-parse", f"{ref_to_try}^{{commit}}"],
            capture_output=True,
            text=True,
        )
        if base_result.returncode != 0:
            base_result = subprocess.run(
                ["git", "-C", str(canonical_dir), "rev-parse", ref_to_try],
                capture_output=True,
                text=True,
            )
        if base_result.returncode == 0:
            base_sha = base_result.stdout.strip()
            break
        last_err = base_result.stderr

    if not base_sha:
        fail(f"failed to resolve base ref {base_ref!r} in {canonical_dir}:\n{last_err}")

    origin_result = subprocess.run(
        ["git", "-C", str(canonical_dir), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    origin_url = origin_result.stdout.strip() if origin_result.returncode == 0 else None

    clone_result = subprocess.run(
        [
            "git",
            "clone",
            "--local",
            "--no-checkout",
            "-c",
            "push.autoSetupRemote=true",
            str(repo_root),
            str(clone_path),
        ],
        capture_output=True,
        text=True,
    )
    if clone_result.returncode != 0:
        fail(
            f"failed to create isolated clone for session {session_id!r} "
            f"from {repo_root}:\n{clone_result.stderr}"
        )

    checkout_result = subprocess.run(
        ["git", "-C", str(clone_path), "checkout", "-B", branch_name, base_sha],
        capture_output=True,
        text=True,
    )
    if checkout_result.returncode != 0:
        shutil.rmtree(clone_path, ignore_errors=True)
        fail(
            f"failed to check out {base_sha} (from base {base_ref!r}) as {branch_name!r} in "
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


def _minimal_agent_settings(host_settings, mcp_url=None):
    """Derive a secret-free settings file for the container.

    The host file's MCP server block carries live keys and internal URLs, and
    its hooks name host-only paths; neither may reach a container. Only the
    auth-mechanism selector is carried over, because the staged credential is
    otherwise ignored.

    `mcp_url` re-adds exactly one server, from the environment, declared as
    `httpUrl` so agy connects directly rather than spawning a proxy that has to
    win a startup race.

    Measured 2026-08-09, agy 1.1.11, headless `agy -p` in the container: it is
    the *plugin-level* `mcp_config.json` that registers agy's MCP execution
    primitive (`call_mcp_tool`). Emptying it removed `call_mcp_tool`,
    `list_resources` and `read_resource` from the declared tool set even though
    this user-level block was present and correct. Keep both — do not "simplify"
    by dropping the plugin declaration.

    Not measured for other agy versions or for the interactive TUI. The TUI
    declares no MCP tools at all (it defers them as "lazy" and registers no
    primitive), which is a client limitation, not a consequence of this file.
    """
    minimal = {}
    auth_type = ((host_settings.get("security") or {}).get("auth") or {}).get("selectedType")
    if auth_type:
        minimal["security"] = {"auth": {"selectedType": auth_type}}
    if mcp_url:
        minimal["mcpServers"] = {"services": {"httpUrl": mcp_url}}
    return minimal


def setup_staging(staging_dir, mcp_url, agent_home, agent_cmd=None):
    """Stage per-session settings and credentials for the container.

    `agent_home` is the host directory holding the agent CLI's own config,
    from $GEMINI_CONFIG_DIR. `agy` dispatch stages its Antigravity OAuth
    credentials from here; without them agy falls back to an interactive
    Google login prompt that a headless container can never answer, so for
    `agent_cmd == "agy"` a missing/incomplete agent_home is a hard failure
    rather than a silent no-op. Other agents (claude) authenticate a
    different way (CLAUDE_CODE_OAUTH_TOKEN, forwarded separately) and do not
    need this — for them an unset agent_home stays a legal no-op.
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
        if agent_cmd == "agy":
            fail(
                "agy dispatch requires $GEMINI_CONFIG_DIR (the host directory "
                "holding your Antigravity CLI config, normally ~/.gemini) to "
                "stage OAuth credentials into the container. Unset, agy falls "
                "back to an interactive Google login prompt a headless "
                "container can never answer. Export GEMINI_CONFIG_DIR and retry."
            )
        return
    gemini_src = Path(agent_home)
    if not gemini_src.is_dir():
        if agent_cmd == "agy":
            fail(f"$GEMINI_CONFIG_DIR={agent_home!r} is not a directory.")
        return

    gemini_dst = staging_dir / ".gemini"
    gemini_dst.mkdir(parents=True, exist_ok=True)

    settings_src = gemini_src / "settings.json"
    host_settings = {}
    if settings_src.exists():
        try:
            host_settings = json.loads(settings_src.read_text())
        except (OSError, ValueError):
            host_settings = {}
    # Written whenever there is anything to say — a host with no settings file
    # of its own still needs the MCP server declared, or the container reaches
    # nothing.
    staged = _minimal_agent_settings(host_settings, mcp_url)
    if staged:
        (gemini_dst / "settings.json").write_text(json.dumps(staged, indent=2))

    for name in ("google_accounts.json", "oauth_creds.json", "installation_id"):
        src_file = gemini_src / name
        if src_file.exists():
            shutil.copy2(src_file, gemini_dst / name)

    agy_src = gemini_src / "antigravity-cli"
    if agy_src.is_dir():
        agy_dst = gemini_dst / "antigravity-cli"
        agy_dst.mkdir(parents=True, exist_ok=True)
        token_staged = False
        for name in ("antigravity-oauth-token", "installation_id"):
            src_file = agy_src / name
            if src_file.exists():
                shutil.copy2(src_file, agy_dst / name)
                if name == "antigravity-oauth-token":
                    token_staged = True
        if agent_cmd == "agy" and not token_staged:
            fail(
                f"{agy_src / 'antigravity-oauth-token'} does not exist, so no "
                "Antigravity OAuth token can be staged for agy. Run agy "
                "interactively on this host at least once to create it."
            )

    elif agent_cmd == "agy":
        fail(
            f"{agy_src} does not exist, so no Antigravity OAuth token can be "
            "staged for agy. Run agy interactively on this host at least once "
            "to create it."
        )


def _reject_bad_agent_cmd(agent_cmd, extra_args, agent=None):
    """Catch the shapes that would otherwise fail deep inside the container,
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

    if agent_cmd == "ida" or agent == "ida":
        fail(
            "ida is the interactive face plugin and is not installed in polecat containers. "
            "Polecat containers run autonomous worker agents (e.g. james, pauli, rbg) via "
            "claude or agy."
        )

    for idx, arg in enumerate(extra_args):
        if arg == "--agent=ida" or (
            arg == "--agent" and idx + 1 < len(extra_args) and extra_args[idx + 1] == "ida"
        ):
            fail(
                "ida is the interactive face plugin and is not installed in polecat containers. "
                "Polecat containers run autonomous worker agents (e.g. james, pauli, rbg)."
            )

    # Neither agent CLI has a --non-interactive flag; both exit on an unknown one.
    if agent_cmd in ("claude", "agy") and "--non-interactive" in extra_args:
        fail(
            f"{agent_cmd} has no --non-interactive flag and exits immediately when "
            "given one. Headless one-shot mode is --print (-p), which polecat adds "
            "on its own when stdin is not a tty."
        )


def _sanitize_path_component(val: str | None, default: str | None = None) -> str | None:
    """Sanitize a path component (e.g. project or session_name) to prevent
    directory hierarchy corruption, path traversal ('..', '/', '\\'), or
    invalid container name characters.
    """
    if not val:
        return default
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(val))
    cleaned = cleaned.strip("._-")
    if not cleaned:
        return default
    return cleaned


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
            f"project under `paths` in {polecat_home}/local.yaml. There is no "
            "default workspace."
        )
    return workspace_dir


#: Where each client writes its session state inside the container. Module-level
#: so tests mount and probe the same paths the run uses, with no second copy.
CLAUDE_SESSION_PATH = "/home/worker/.claude/projects/-workspace"
AGY_SESSION_PATH = "/home/worker/.gemini/tmp/workspace"

#: Default agent persona per client. Used when neither --agent nor --no-agent is given.
DEFAULT_AGENTS: dict[str, str] = {
    "claude": "james",
    "agy": "james",
}


def _agent_args(extra_args, agent=None):
    """`--agent <agent_name>`, or nothing when no agent was specified."""
    if not agent:
        return []
    caller_chose_agent = any(arg == "--agent" or arg.startswith("--agent=") for arg in extra_args)
    if caller_chose_agent:
        return []
    return ["--agent", agent]


def _build_inner_command(
    agent_cmd,
    extra_args,
    is_interactive,
    explicit_headless,
    task,
    agent=None,
    output_format=None,
    prompt=None,
):
    """The command run inside the container, and the container path that agent
    writes its session state to.

    Returns (inner_cmd, container_session_path, seeded_from_task, seeded_prompt).
    """
    claude_session_path = CLAUDE_SESSION_PATH

    if agent_cmd == "claude":
        container_session_path = claude_session_path
        inner_cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--setting-sources=user,project",
            *_agent_args(extra_args, agent),
        ]
        if output_format:
            inner_cmd.extend(["--output-format", output_format])
        if not is_interactive and not explicit_headless:
            # Headless one-shot mode is `--print`, and it is the only one claude
            # has: without it claude opens its interactive UI against a pipe. The
            # prompt is a positional, so it still arrives from extra_args below,
            # or from stdin when there is none.
            inner_cmd.append("--print")
    elif agent_cmd == "agy":
        container_session_path = AGY_SESSION_PATH
        inner_cmd = [
            "agy",
            "--dangerously-skip-permissions",
            "--log-file",
            "/home/worker/.gemini/antigravity-cli/cli.log",
            *_agent_args(extra_args, agent),
        ]
        if output_format:
            inner_cmd.extend(["--output-format", output_format])
    elif agent_cmd in ("shell", "bash"):
        container_session_path = claude_session_path
        inner_cmd = ["bash"]
    elif agent_cmd.startswith("sleep"):
        container_session_path = claude_session_path
        inner_cmd = ["sleep", "infinity"]
    else:
        container_session_path = claude_session_path
        inner_cmd = [agent_cmd]

    seeded_from_task = bool(task) and not extra_args and not prompt
    if prompt:
        seeded_prompt = prompt
        if agent_cmd == "agy":
            inner_cmd.extend(["--prompt", prompt])
        elif agent_cmd == "claude":
            inner_cmd.append(prompt)
        elif extra_args:
            inner_cmd.extend(extra_args)
    elif seeded_from_task:
        seeded_prompt = f"/pull {task}"
        if agent_cmd == "agy":
            inner_cmd.extend(["--print", f"/pull {task}"])
        else:
            inner_cmd.append(f"/pull {task}")
    elif extra_args:
        seeded_prompt = " ".join(extra_args)
        if agent_cmd == "agy":
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
            if not agy_prompt_flags.intersection(extra_args):
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
        else:
            inner_cmd.extend(extra_args)
    else:
        seeded_prompt = None

    return inner_cmd, container_session_path, seeded_from_task, seeded_prompt


def _drain_cidfile(session_dir):
    """Remove the `--cidfile` docker writes, returning the id it held.

    Docker will not start a container when the cidfile path already exists, so
    the file has to be gone before *every* invocation that uses it. Returning
    the contents first keeps the id of an already-finished container
    recoverable, since `--rm` has by then reaped the container itself."""
    cidfile = Path(session_dir) / "container.cid"
    cid = None
    try:
        cid = cidfile.read_text().strip() or None
    except OSError:
        pass
    try:
        cidfile.unlink()
    except OSError:
        pass
    return cid


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
    session_id=None,
    with_sessions=False,
    sessions_base=None,
):
    """The full `docker run` argv, and the environment to launch it with.

    Returns `(argv, run_env)`. The argv carries **no** variable values: every
    name in `env` is passed as a valueless `-e NAME` flag and its value is
    handed to the `docker` process itself through `run_env`, which the caller
    must pass to `subprocess.run(..., env=run_env)`. Values on argv are
    world-readable in the host process table (`ps`, `/proc/<pid>/cmdline`) for
    the whole life of the container, which put live GitHub and agent-API
    tokens in front of every local process. `-e NAME` reads the value out of
    docker's own environment instead, so nothing lands on the command line.

    `CONTAINER_SET_ENV` names are the one exception and keep their value on
    argv — they are container-internal paths and flags, never credentials —
    which is exactly the split `env_contract.docker_env_args()` already makes.

    Also pre-creates the bind-mount targets under `session_dir` — see below
    for why that cannot wait until launch."""
    # Pre-create the bind-mount targets as the invoking user. Docker
    # auto-creates a missing bind source as root, which the container's non-root
    # user cannot write, silently losing logs and conversation state.
    (session_dir / "agy-brain").mkdir(parents=True, exist_ok=True)
    (session_dir / "agy-cli.log").touch(exist_ok=True)
    (session_dir / "agy-logs").mkdir(parents=True, exist_ok=True)

    cidfile = session_dir / "container.cid"
    _drain_cidfile(session_dir)

    # We use --cidfile to capture the container ID because docker writes the container ID
    # to the cidfile immediately upon creation, ensuring it is preserved even when --rm
    # reaps the container on exit or if the container fails. We also set --name derived
    # from session_id so the container is easily identifiable in `docker ps` while live.
    cmd = [
        "docker",
        "run",
        "--rm",
        "--cidfile",
        str(cidfile),
    ]
    if session_id:
        cmd.extend(["--name", f"polecat-{session_id}"])

    cmd.extend(
        [
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
    )

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

    if with_sessions and sessions_base:
        transcripts_path = (sessions_base / "transcripts").resolve()
        transcripts_path.mkdir(parents=True, exist_ok=True)
        cmd.extend(["-v", f"{transcripts_path}:/sessions/transcripts:ro"])
        env["AOPS_SESSIONS"] = "/sessions"

    cmd.extend(docker_args)
    # Valueless `-e NAME` flags: the values travel in `run_env`, not on argv.
    cmd.extend(docker_env_args(tuple(env)))
    cmd.append(image)
    cmd.extend(inner_cmd)

    # docker resolves each valueless `-e NAME` against its *own* environment,
    # so every name flagged above has to be set here or the container silently
    # loses it. Several are synthesised by get_env_forwards() and have no host
    # counterpart at all (the AOPS_BOT_GH_TOKEN -> GH_TOKEN/GITHUB_TOKEN
    # fan-out, resolve_cope_evaluator, resolve_telemetry, CONTAINER_SET_ENV),
    # and where a name does exist on the host the polecat-side value must win.
    # Hence os.environ first, `env` last.
    run_env = {**os.environ, **{k: str(v) for k, v in env.items()}}
    return cmd, run_env


def _get_image_digest(image: str) -> str | None:
    """Retrieve sha256 digest for local or repo docker image.

    Tries repo digest first, falling back to image ID (.Id) for local builds.
    """
    try:
        res = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", image],
            capture_output=True,
            text=True,
        )
        digest = res.stdout.strip() if res.returncode == 0 else ""
        if digest and digest.startswith("sha256:"):
            return digest

        res = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            capture_output=True,
            text=True,
        )
        digest = res.stdout.strip() if res.returncode == 0 else ""
        if digest and digest.startswith("sha256:"):
            return digest
    except Exception:
        pass
    return None


def write_run_record(
    *,
    session_dir: Path,
    session_id: str,
    container_id: str | None,
    container_name: str,
    agent: str,
    task_id: str | None,
    seeded_prompt: str | None,
    image_ref: str,
    image_digest: str | None,
    workspace_dir: Path,
    commit_start: str | None,
    commit_end: str | None,
    exit_code: int | None,
    delivery_guard: dict,
    started_at: datetime,
    ended_at: datetime,
    worker_model: str | None = None,
    degraded: list | None = None,
) -> Path:
    """Persist run.json at the root of session_dir.

    All schema keys are always present; unobtainable values are recorded as null.
    `status` is derived from exit_code and delivery_guard.
    `degraded[]` is always present and records missing observable state.
    `transcript` is read off the session directory here rather than passed in,
    so no call path can write a record that says nothing about whether the run
    persisted a conversation.
    """
    duration_seconds = int(round((ended_at - started_at).total_seconds()))

    degraded_list = list(degraded) if degraded is not None else []

    transcript = _verify_transcript_created(session_dir)
    is_agent_cmd = agent and agent.lower() in ("claude", "agy")
    transcript_missing = (
        not transcript["found"]
        or not transcript.get("transcript_bytes")
        or not transcript.get("event_count")
    )

    if is_agent_cmd and transcript_missing:
        if not any(
            isinstance(d, dict) and d.get("what") in ("transcript", "transcript_missing")
            for d in degraded_list
        ):
            degraded_list.append(
                {
                    "what": "transcript_missing",
                    "why": (
                        "no non-empty agent conversation transcript was persisted under the session directory"
                    ),
                }
            )
    # If worker_model is unobtainable from host launcher, record it as null and flag in degraded[] per Criterion 8
    if worker_model is None:
        if not any(isinstance(d, dict) and d.get("what") == "worker_model" for d in degraded_list):
            degraded_list.append(
                {
                    "what": "worker_model",
                    "why": "not selectable or observable from the host launcher",
                }
            )

    if exit_code is None or exit_code in (130, 137, -9, -15):
        status = "killed"
    elif exit_code != 0:
        status = "failed"
    elif not delivery_guard.get("ok", True):
        status = "delivery_guard_failed"
    elif is_agent_cmd and transcript_missing:
        status = "degraded"
    else:
        status = "success"

    record = {
        "schema_version": 1,
        "session_id": session_id,
        "container_id": container_id,
        "container_name": container_name,
        "agent": agent,
        "task_id": task_id,
        "seeded_prompt": seeded_prompt,
        "image_ref": image_ref,
        "image_digest": image_digest,
        "workspace_dir": str(Path(workspace_dir).resolve()),
        "session_dir": str(Path(session_dir).resolve()),
        "commit_start": commit_start,
        "commit_end": commit_end,
        "exit_code": exit_code,
        "status": status,
        "delivery_guard": delivery_guard,
        "transcript": transcript,
        "started_at": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ended_at": ended_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": duration_seconds,
        "worker_model": worker_model,
        "degraded": degraded_list,
    }

    out_path = Path(session_dir) / "run.json"
    out_path.write_text(json.dumps(record, indent=2) + "\n")
    return out_path


def _execute_with_seed_verification(
    cmd, *, image, inner_cmd, session_dir, task, verify_seed, run_env, quiet=False
):
    """Run the container, and for a seeded dispatch confirm the agent actually
    saw the task before letting a clean exit stand as success.

    A clean exit is not evidence the task was worked: the seed can be dropped
    before delivery, which leaves a clean workspace the delivery guard reads as
    a pass. Retry once, then fail rather than report an unverified success.

    `run_env` carries the values behind the valueless `-e NAME` flags in `cmd`,
    and is required rather than defaulted. Defaulting it to None would make
    `subprocess.run(cmd, env=None)` inherit os.environ, under which host-set
    names still arrive but every synthesised one — the AOPS_BOT_GH_TOKEN
    fan-out, resolve_telemetry, AOPS_SESSIONS, AOPS_POLECAT_BRANCH — vanishes
    silently at exit 0. That is the failure this whole path exists to prevent,
    so it must not be reachable by forgetting an argument.
    """
    max_attempts = 2 if verify_seed else 1
    returncode = 1
    seed_ok = not verify_seed

    last_cid = None

    for attempt in range(1, max_attempts + 1):
        suffix = f" (attempt {attempt}/{max_attempts})" if max_attempts > 1 else ""
        if not quiet:
            click.echo(f"Running{suffix}: {image} {' '.join(inner_cmd)}", err=True)
        # `cmd` is prebuilt once and reused, so the same --cidfile path is
        # passed on every attempt. Docker refuses to start when that file
        # already exists ("container ID file found", exit 125), which would
        # make the retry unable to ever succeed after a first-attempt
        # container failure. Drain it before each attempt, keeping whatever
        # id it held so a failed attempt's container is still reportable.
        last_cid = _drain_cidfile(session_dir) or last_cid
        returncode = subprocess.run(cmd, env=run_env).returncode

        if not verify_seed:
            break
        seed_ok = returncode == 0 and _seed_confirmed(session_dir, task)
        if seed_ok:
            break
        if attempt < max_attempts and not quiet:
            click.echo(
                f"Warning: could not confirm the agent processed seeded task "
                f"{task!r} (exit={returncode}). Retrying once.",
                err=True,
            )

    # The caller reads container.cid after this returns. If the last attempt
    # never got far enough for docker to write one, restore the most recent id
    # seen so run.json still reports a container instead of silently dropping
    # the evidence a draining retry collected.
    cidfile = Path(session_dir) / "container.cid"
    if last_cid and not cidfile.exists():
        try:
            cidfile.write_text(last_cid + "\n")
        except OSError:
            pass

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
@click.option(
    "--base",
    help="Base commit or branch to create private branch from (default: branch in polecat.yaml).",
)
@click.option(
    "--branch",
    "-b",
    help="Custom branch name to check out in isolated clone (default: polecat/<session-id>).",
)
@click.option(
    "--with-sessions",
    is_flag=True,
    help="Mount read-only sessions transcripts directory and set $AOPS_SESSIONS.",
)
@click.option(
    "--agent",
    "-a",
    default=None,
    help="Agent persona to run inside container (defaults to 'james' for claude and agy).",
)
@click.option(
    "--no-agent",
    is_flag=True,
    default=False,
    help="Run without an agent persona, disabling the default agent.",
)
@click.option(
    "--output-format",
    "-o",
    help="Output format for print/headless mode (e.g. text, json, stream-json).",
)
@click.option(
    "--prompt",
    help="Prompt string for print/headless mode.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress polecat's own progress output on stderr. This also hides the "
    "'Workspace:' and 'Session logs:' lines, so it is not recommended when "
    "debugging interactively. Errors are always reported.",
)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def run(
    agent_cmd,
    project,
    repo_dir,
    session_name,
    mcp_url,
    task,
    base,
    branch,
    with_sessions,
    agent,
    no_agent,
    output_format,
    prompt,
    quiet,
    extra_args,
):
    """Run AGENT_CMD (claude, agy, shell, sleep) in a container.

    Anything after AGENT_CMD that is not one of this command's own options is
    forwarded verbatim to the inner invocation.
    """
    if no_agent:
        effective_agent = None
    elif agent is not None:
        effective_agent = agent
    else:
        effective_agent = DEFAULT_AGENTS.get(agent_cmd)

    _reject_bad_agent_cmd(agent_cmd, extra_args, agent=effective_agent)

    if project:
        project = _sanitize_path_component(project)
    if session_name:
        session_name = _sanitize_path_component(session_name)

    config = load_config()
    polecat_home = resolve_polecat_home(config)
    image = resolve_image(config)
    sessions_base = resolve_sessions_root()
    rules_dir = resolve_rules_dir(config)
    workspace_dir = _resolve_workspace(repo_dir, project, polecat_home)

    session_id = session_name or f"session-{uuid.uuid4().hex[:8]}"

    session_date = datetime.now().strftime("%Y%m%d")
    session_dir = sessions_base / "logs" / session_date / session_id / (project or "workspace")
    session_dir.mkdir(parents=True, exist_ok=True)

    # An explicit --repo-dir is the caller's own isolation to own; every other
    # path resolves to a shared checkout and must be cloned first.
    clone_cleanup = None
    if repo_dir is None:
        workspace_dir, clone_cleanup = resolve_isolated_workspace(
            workspace_dir,
            session_id,
            polecat_home,
            base=base,
            config=config,
            branch=branch,
            quiet=quiet,
        )

    initial_head = _get_git_head(workspace_dir)
    mcp_url = mcp_url or os.environ.get("PKB_MCP_URL")

    staging_base = os.environ.get("POLECAT_STAGING_BASE") or str(polecat_home / "tmp" / "staging")
    Path(staging_base).mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix="staging-", dir=staging_base))
    os.chmod(staging_dir, 0o700)

    preserve_workspace = False
    started_at = datetime.now(UTC)
    returncode = None
    delivery_ok = True
    delivery_err = None
    container_id = None
    container_name = f"polecat-{session_id}"
    seeded_prompt = None
    worker_model = os.environ.get("POLECAT_WORKER_MODEL")
    degraded = []

    try:
        setup_staging(staging_dir, mcp_url, os.environ.get("GEMINI_CONFIG_DIR"), agent_cmd)

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

        if branch:
            env["AOPS_POLECAT_BRANCH"] = branch

        has_sessions_access = False
        if with_sessions:
            has_sessions_access = True
        elif config.get("sessions_access"):
            has_sessions_access = True
        elif project and config.get("projects", {}).get(project, {}).get("sessions_access"):
            has_sessions_access = True

        docker_args = []
        explicit_headless = (
            bool(HEADLESS_FLAGS.intersection(extra_args)) or bool(output_format) or bool(prompt)
        )
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

        inner_cmd, container_session_path, seeded_from_task, seeded_prompt = _build_inner_command(
            agent_cmd,
            extra_args,
            is_interactive,
            explicit_headless,
            task,
            agent=effective_agent,
            output_format=output_format,
            prompt=prompt,
        )

        env["AOPS_POLECAT_CONTAINER"] = "1"
        env["POLECAT_CREW_NAME"] = session_id
        env["AOPS_SESSION_STATE_DIR"] = container_session_path
        env["AOPS_HOOK_LOG_PATH"] = f"{container_session_path}/polecat-session-hooks.jsonl"
        env["OTEL_RESOURCE_ATTRIBUTES"] = format_otel_resource_attributes(
            existing=env.get("OTEL_RESOURCE_ATTRIBUTES"),
            session_id=session_id,
            project=project,
            task_id=task,
        )

        task_identifier = None
        if project and task:
            task_identifier = f"{project}-{task}"
        elif task:
            task_identifier = task
        elif project:
            task_identifier = project

        if task_identifier is not None:
            env["GENAI_ENGINE_TASK_ID"] = task_identifier
            env["OTEL_SERVICE_NAME"] = task_identifier

        cmd, run_env = _build_docker_argv(
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
            session_id=session_id,
            with_sessions=has_sessions_access,
            sessions_base=sessions_base,
        )

        if not quiet:
            click.echo(f"Workspace: {workspace_dir}", err=True)
            click.echo(f"Session logs: {session_dir}", err=True)

        returncode = _execute_with_seed_verification(
            cmd,
            image=image,
            inner_cmd=inner_cmd,
            session_dir=session_dir,
            task=task,
            # Both agent CLIs persist a conversation transcript into the session
            # dir (`_transcript_paths`), so a seeded dispatch is verified the
            # same way whichever one ran it. `shell`/`sleep`/other run no agent
            # CLI and have no conversation to check.
            verify_seed=agent_cmd in ("claude", "agy") and seeded_from_task,
            run_env=run_env,
            quiet=quiet,
        )
        cidfile = session_dir / "container.cid"
        if cidfile.exists():
            try:
                cid_content = cidfile.read_text().strip()
                if cid_content:
                    container_id = cid_content
            except OSError:
                pass

        if returncode != 0:
            preserve_workspace = True
            if not quiet:
                click.echo(f"Workspace preserved for inspection: {workspace_dir}", err=True)

        if returncode == 0:
            delivery_ok, delivery_err = _verify_workspace_delivery(
                workspace_dir, initial_head=initial_head
            )
            if not delivery_ok:
                preserve_workspace = True

    finally:
        cidfile = session_dir / "container.cid"
        if cidfile.exists() and not container_id:
            try:
                cid_content = cidfile.read_text().strip()
                if cid_content:
                    container_id = cid_content
            except OSError:
                pass

        ended_at = datetime.now(UTC)
        commit_end = _get_git_head(workspace_dir)
        image_digest = _get_image_digest(image)

        delivery_guard = {"ok": delivery_ok, "error": delivery_err}
        if returncode != 0 and delivery_ok and delivery_err is None:
            delivery_guard = {
                "ok": False,
                "error": f"container exited with code {returncode}"
                if returncode is not None
                else "container execution failed",
            }

        run_record_path = write_run_record(
            session_dir=session_dir,
            session_id=session_id,
            container_id=container_id,
            container_name=container_name,
            agent=agent_cmd,
            task_id=task if task else None,
            seeded_prompt=seeded_prompt,
            image_ref=image,
            image_digest=image_digest,
            workspace_dir=workspace_dir,
            commit_start=initial_head,
            commit_end=commit_end,
            exit_code=returncode,
            delivery_guard=delivery_guard,
            started_at=started_at,
            ended_at=ended_at,
            worker_model=worker_model,
            degraded=degraded,
        )

        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        if not preserve_workspace:
            cleanup_isolated_workspace(clone_cleanup)

        # Last, so a slow or interrupted POST cannot delay or skip the cleanup
        # above: a Ctrl-C during the request raises out of this `finally:`.
        try:
            notify_run_complete(run_record_path, sessions_base)
        except Exception:
            pass

    if returncode != 0:
        sys.exit(returncode)

    if not delivery_ok:
        # Detection ends here; repair belongs to the dispatcher, which owns
        # the graph this task lives in (dispatch/SKILL.md section 6). A
        # launcher carrying its own client for the knowledge base would be a
        # second copy of that plugin's job, so the exit code and this message
        # are the whole of the handoff. The workspace is the only copy of
        # whatever the failed run left uncommitted, so it outlives the exit.
        fail(
            f"delivery guard failed for {task or 'session'!r}:\n{delivery_err}\n"
            "Refusing to report success. If this task is in a terminal status, "
            "the dispatcher must reopen it (via pauli) before filing a fix "
            "subtask or re-dispatching.\n"
            f"Workspace preserved for inspection: {workspace_dir}"
        )


if __name__ == "__main__":
    main()
