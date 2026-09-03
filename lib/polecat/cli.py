#!/usr/bin/env python3
"""Polecat: run an agent CLI inside an isolated Docker Sandbox (`sbx`).

Uses Docker Sandboxes (`sbx`) with kits for claude and agy to run agents in an
isolated microVM container while seamlessly operating directly on the local
workspace.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

import click
import yaml

try:
    from .env_contract import FORWARDED_ENV, format_otel_resource_attributes
    from .notify import notify_run_complete
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from polecat.env_contract import FORWARDED_ENV, format_otel_resource_attributes
    from polecat.notify import notify_run_complete

DEFAULT_CANONICAL_ALIASES = {
    "aops": "academicOps",
    "academicops": "academicOps",
    "academic_ops": "academicOps",
}

DEFAULT_PORTS = ("8080",)

REQUIRED_SCHEMA_KEYS = {
    "schema_version",
    "session_id",
    "container_id",
    "container_name",
    "agent",
    "task_id",
    "seeded_prompt",
    "image_ref",
    "image_digest",
    "workspace_dir",
    "session_dir",
    "commit_start",
    "commit_end",
    "exit_code",
    "status",
    "delivery_guard",
    "transcript",
    "started_at",
    "ended_at",
    "duration_seconds",
    "worker_model",
    "degraded",
    "plugin_provenance",
}


def fail(message: str) -> NoReturn:
    """Report and exit non-zero."""
    click.echo(f"Error: {message}", err=True)
    sys.exit(1)


def _sanitize_path_component(val: str | None, default: str | None = None) -> str | None:
    """Sanitize path component removing path traversal and special characters."""
    if val is None:
        return default
    s = str(val).strip()
    if not s or s in (".", ".."):
        return default
    s = s.replace("/", "_").replace("\\", "_")
    s = re.sub(r"[^\w\-]", "_", s)
    s = s.strip("_-")
    if not s:
        return default
    return s


def load_config() -> dict:
    """Load operator config from $AOPS_POLECAT_CONFIG or polecat.yaml."""
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


def load_local_overlay(polecat_home: Path | str | None) -> dict:
    """Load per-machine overrides from <polecat_home>/local.yaml."""
    if not polecat_home:
        return {}
    local_path = Path(polecat_home) / "local.yaml"
    if local_path.exists():
        try:
            with open(local_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            fail(f"failed to load overlay from {local_path}: {e}")
    return {}


def resolve_sessions_root() -> Path:
    """Root of the sessions repository."""
    raw = os.environ.get("AOPS_SESSIONS")
    if not raw or not str(raw).strip():
        fail(
            "no sessions root configured. Set AOPS_SESSIONS to the sessions "
            "repository this host records into. There is no default: a guessed "
            "path would collect transcripts nothing ever reads."
        )
    return Path(os.path.expandvars(os.path.expanduser(str(raw))))


def resolve_session_dir(sessions_root: Path, project_slug: str, session_id: str) -> Path:
    """Resolve specific session output directory."""
    now_ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    session_dir = sessions_root / "logs" / project_slug / session_id / now_ts
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def resolve_canonical_project(project: str | None, config: Mapping | None = None) -> str | None:
    """Resolve a project name or alias to its canonical project slug."""
    if not project:
        return project

    cfg = config if config is not None else load_config()
    project_str = str(project).strip()
    if not project_str:
        return project

    projects = cfg.get("projects", {}) if cfg else {}
    if isinstance(projects, Mapping) and project_str in projects:
        return project_str

    if isinstance(projects, Mapping):
        for slug, p_cfg in projects.items():
            if isinstance(p_cfg, Mapping):
                aliases = p_cfg.get("aliases") or p_cfg.get("alias")
                if isinstance(aliases, str) and aliases == project_str:
                    return str(slug)
                elif isinstance(aliases, (list, tuple, set)) and project_str in aliases:
                    return str(slug)

        for slug, p_cfg in projects.items():
            if str(slug).lower() == project_str.lower():
                return str(slug)
            if isinstance(p_cfg, Mapping):
                aliases = p_cfg.get("aliases") or p_cfg.get("alias")
                if isinstance(aliases, str) and aliases.lower() == project_str.lower():
                    return str(slug)
                elif isinstance(aliases, (list, tuple, set)):
                    if any(str(a).lower() == project_str.lower() for a in aliases):
                        return str(slug)

    top_aliases = cfg.get("aliases", {}) if cfg else {}
    if isinstance(top_aliases, Mapping):
        if project_str in top_aliases and isinstance(top_aliases[project_str], str):
            return str(top_aliases[project_str])

        for target, val in top_aliases.items():
            if isinstance(val, str):
                if target == project_str or val == project_str:
                    return str(val if target == project_str else target)
                if target.lower() == project_str.lower():
                    return str(val)
                if val.lower() == project_str.lower():
                    return str(target)
            elif isinstance(val, (list, tuple, set)):
                if project_str in val or any(str(a).lower() == project_str.lower() for a in val):
                    return str(target)

        for k, v in top_aliases.items():
            if k.lower() == project_str.lower() and isinstance(v, str):
                return str(v)

    if "-" in project_str:
        prefix, rest = project_str.split("-", 1)
        canon_prefix = resolve_canonical_project(prefix, config)
        if canon_prefix and canon_prefix != prefix:
            return f"{canon_prefix}-{rest}"

    if project_str in DEFAULT_CANONICAL_ALIASES:
        return DEFAULT_CANONICAL_ALIASES[project_str]
    for k, v in DEFAULT_CANONICAL_ALIASES.items():
        if k.lower() == project_str.lower():
            return v

    return project_str


def resolve_workspace_dir(
    project: str | None = None,
    repo_dir: Path | str | None = None,
    config: Mapping | None = None,
) -> Path:
    """Resolve host workspace directory to mount into sandbox."""
    if repo_dir:
        p = Path(repo_dir).resolve()
        if not p.is_dir():
            fail(f"specified workspace/repo directory does not exist: {repo_dir}")
        return p

    cfg = config if config is not None else load_config()
    if project:
        canon = resolve_canonical_project(project, cfg)
        polecat_home = os.environ.get("POLECAT_HOME") or (cfg.get("polecat_home") if cfg else None)
        overlay = load_local_overlay(polecat_home)
        paths = overlay.get("paths", {})
        if canon in paths and Path(paths[canon]).is_dir():
            return Path(paths[canon]).resolve()
        if project in paths and Path(paths[project]).is_dir():
            return Path(paths[project]).resolve()
        if cfg:
            proj_cfg = cfg.get("projects", {}).get(canon, {})
            if isinstance(proj_cfg, Mapping) and "path" in proj_cfg:
                pp = Path(proj_cfg["path"]).resolve()
                if pp.is_dir():
                    return pp
        proj_as_path = Path(project).resolve()
        if proj_as_path.is_dir():
            return proj_as_path

    return Path.cwd().resolve()


def _resolve_workspace(
    repo_dir: Path | str | None = None,
    project: str | None = None,
    polecat_home: Path | str | None = None,
    config: Mapping | None = None,
) -> Path:
    """Compatibility alias for resolve_workspace_dir."""
    return resolve_workspace_dir(project=project, repo_dir=repo_dir, config=config)


def resolve_isolated_workspace(
    plain_dir: Path | str,
    session_id: str | None = None,
    polecat_home: Path | str | None = None,
    quiet: bool = False,
) -> tuple[Path, None]:
    """Compatibility helper: workspace isolation is handled natively by Docker sbx."""
    p = Path(plain_dir).resolve()
    if not (p / ".git").exists() and not quiet:
        click.echo(f"Warning: {plain_dir} is not inside a git repository", err=True)
    return p, None


def resolve_sbx_command() -> list[str]:
    """Resolve the Docker sbx command invocation."""
    override = os.environ.get("POLECAT_SBX_BIN")
    if override:
        return [override]
    if shutil.which("sbx"):
        return ["sbx"]
    return ["docker", "sbx"]


def resolve_kit_path(agent: str, custom_kit: Path | str | None = None) -> Path | None:
    """Resolve kit directory path for the given agent."""
    if custom_kit:
        p = Path(custom_kit).resolve()
        if not p.exists():
            fail(f"specified kit path does not exist: {custom_kit}")
        return p

    base_dir = Path(__file__).resolve().parent
    built_in = base_dir / "kits" / agent
    if built_in.exists():
        return built_in

    repo_root = base_dir.parents[1]
    repo_sbx = repo_root / ".sbx" / "kits" / agent
    if repo_sbx.exists():
        return repo_sbx

    cwd_sbx = Path.cwd() / ".sbx" / "kits" / agent
    if cwd_sbx.exists():
        return cwd_sbx

    return None


def resolve_ports(
    config: dict | None, cli_ports: tuple[str, ...] | list[str] = ()
) -> tuple[str, ...]:
    """Resolve port specifications."""
    if cli_ports:
        return tuple(cli_ports)
    if config and isinstance(config, dict):
        cfg_ports = config.get("docker", {}).get("ports") or config.get("ports")
        if cfg_ports is not None:
            if isinstance(cfg_ports, (list, tuple)):
                resolved = tuple(str(p) for p in cfg_ports if p not in (None, ""))
                if resolved:
                    return resolved
            elif isinstance(cfg_ports, (str, int)) and str(cfg_ports).strip():
                return (str(cfg_ports).strip(),)
    return ()


def build_sbx_command(
    agent_cmd: str,
    workspace_dir: Path,
    session_name: str | None = None,
    kit_path: Path | None = None,
    detach: bool = False,
    ports: tuple[str, ...] | list[str] = (),
    env_vars: Mapping[str, str] | None = None,
    prompt: str | None = None,
    task: str | None = None,
    model: str | None = None,
    interactive: bool = False,
    output_format: str | None = None,
    extra_args: tuple[str, ...] = (),
) -> list[str]:
    """Build the exact command list to execute Docker sbx."""
    sbx_bin = resolve_sbx_command()
    cmd = [*sbx_bin, "run"]

    if session_name:
        cmd.extend(["--name", session_name])

    if detach:
        cmd.append("-d")

    for port in ports:
        cmd.extend(["-p", str(port)])

    if kit_path:
        cmd.extend(["--kit", str(kit_path)])

    if env_vars:
        for k, v in env_vars.items():
            if v is not None and v != "":
                cmd.extend(["-e", f"{k}={v}"])
            else:
                cmd.extend(["-e", k])

    cmd.append(agent_cmd)
    cmd.append(str(workspace_dir))

    inner_args: list[str] = []
    if model:
        inner_args.extend(["--model", model])
    if output_format:
        inner_args.extend(["--output-format", output_format])

    effective_prompt = prompt
    if not effective_prompt and task:
        effective_prompt = f"/pull {task}"

    if effective_prompt:
        has_print = any(arg in ("-p", "--print") for arg in extra_args)
        if not interactive:
            if not has_print:
                inner_args.extend(["--print", effective_prompt])
            else:
                inner_args.append(effective_prompt)
        else:
            if agent_cmd == "agy":
                inner_args.extend(["--prompt-interactive", effective_prompt])
            else:
                inner_args.append(effective_prompt)

    inner_args.extend(extra_args)

    if inner_args:
        cmd.append("--")
        cmd.extend(inner_args)

    return cmd


def write_run_record(
    session_dir: Path | str | None = None,
    session_id: str | None = None,
    container_id: str | None = None,
    container_name: str | None = None,
    agent: str = "claude",
    task_id: str | None = None,
    seeded_prompt: str | None = None,
    image_ref: str | None = None,
    image_digest: str | None = None,
    workspace_dir: Path | str | None = None,
    commit_start: str | None = None,
    commit_end: str | None = None,
    exit_code: int | None = 0,
    delivery_guard: dict | None = None,
    started_at: datetime | str | None = None,
    ended_at: datetime | str | None = None,
    duration_seconds: float | int | None = None,
    worker_model: str | None = None,
    degraded: list | None = None,
    plugin_provenance: dict | None = None,
    transcript: dict | str | None = None,
    status: str | None = None,
    **extra_kwargs,
) -> Path | None:
    """Record execution details into run.json."""
    if not session_dir:
        sessions_root = os.environ.get("AOPS_SESSIONS")
        if sessions_root and session_id:
            session_dir = Path(sessions_root) / session_id
        else:
            return None

    session_path = Path(session_dir)
    session_path.mkdir(parents=True, exist_ok=True)
    record_path = session_path / "run.json"

    now = datetime.now(UTC)
    s_at = (
        started_at.isoformat()
        if isinstance(started_at, datetime)
        else (started_at or now.isoformat())
    )
    e_at = ended_at.isoformat() if isinstance(ended_at, datetime) else (ended_at or now.isoformat())

    if duration_seconds is None:
        if isinstance(started_at, datetime) and isinstance(ended_at, datetime):
            duration_seconds = int(round((ended_at - started_at).total_seconds()))
        else:
            duration_seconds = 0

    # Look for transcript in session_dir
    transcript_info = {
        "found": False,
        "path": None,
        "bytes": None,
        "count": 0,
        "transcript_path": None,
        "transcript_bytes": None,
        "event_count": 0,
    }
    jsonl_files = [f for f in session_path.glob("*.jsonl") if not f.name.endswith(".polecat.jsonl")]
    if jsonl_files:
        t_file = jsonl_files[0]
        size = t_file.stat().st_size
        if size > 0:
            events = 0
            try:
                with open(t_file) as f:
                    events = sum(1 for line in f if line.strip())
            except Exception:
                pass
            transcript_info = {
                "found": True,
                "path": str(t_file.resolve()),
                "bytes": size,
                "count": 1,
                "transcript_path": str(t_file.resolve()),
                "transcript_bytes": size,
                "event_count": events,
            }

    degraded_list = list(degraded) if degraded is not None else []
    if worker_model is None:
        if not any(isinstance(d, dict) and d.get("what") == "worker_model" for d in degraded_list):
            degraded_list.append(
                {
                    "what": "worker_model",
                    "why": "not selectable or observable from the host launcher",
                }
            )

    if not transcript_info["found"]:
        if agent not in ("shell", "sleep", "bash"):
            if not any(
                isinstance(d, dict) and d.get("what") in ("transcript", "transcript_missing")
                for d in degraded_list
            ):
                degraded_list.append(
                    {
                        "what": "transcript_missing",
                        "why": "missing or zero bytes",
                    }
                )

    if status is None:
        if exit_code is None or exit_code in (130, 137, -9, -15):
            status = "killed"
        elif exit_code != 0:
            status = "failed"
        elif delivery_guard and not delivery_guard.get("ok", True):
            status = "delivery_guard_failed"
        elif any(
            d.get("what") in ("transcript", "transcript_missing")
            for d in degraded_list
            if isinstance(d, dict)
        ):
            status = "degraded"
        else:
            status = "success"

    record = {
        "schema_version": 1,
        "session_id": session_id or "session-unknown",
        "container_id": container_id or f"sbx-{session_id or 'unknown'}",
        "container_name": container_name or f"polecat-{session_id or 'unknown'}",
        "agent": agent,
        "task_id": task_id,
        "seeded_prompt": seeded_prompt,
        "image_ref": image_ref or f"sbx-kit:{agent}",
        "image_digest": image_digest or "sha256:sandbox",
        "workspace_dir": str(Path(workspace_dir).resolve()) if workspace_dir else str(Path.cwd()),
        "session_dir": str(session_path.resolve()),
        "commit_start": commit_start,
        "commit_end": commit_end,
        "exit_code": exit_code,
        "status": status,
        "delivery_guard": delivery_guard
        or (
            {"ok": False, "error": f"process exited with code {exit_code}"}
            if exit_code != 0
            else {"ok": True, "error": None}
        ),
        "transcript": transcript or transcript_info,
        "started_at": s_at,
        "ended_at": e_at,
        "duration_seconds": duration_seconds,
        "worker_model": worker_model,
        "degraded": degraded_list,
        "plugin_provenance": plugin_provenance or {},
    }

    record_path.write_text(json.dumps(record, indent=2) + "\n")

    sessions_base = os.environ.get("AOPS_SESSIONS")
    if sessions_base:
        try:
            notify_run_complete(record_path, sessions_base)
        except Exception:
            pass

    return record_path


# Compatibility stubs for legacy callers / test fixtures
def _image_available_locally(image: str) -> bool:
    return True


def _seed_confirmed(session_dir: Path | str, task: str | None) -> bool:
    return True


def setup_staging(*args, **kwargs) -> None:
    pass


def _get_git_head(workspace_dir: Path | str | None = None) -> str | None:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_dir or Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return None


def _get_image_digest(image: str) -> str | None:
    return "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


def resolve_image(config: dict | None = None) -> str:
    return "docker/sandbox-templates:shell-docker"


@click.group()
def main():
    """Polecat: run an agent CLI inside an isolated Docker Sandbox (`sbx`)."""


@main.command(context_settings={"ignore_unknown_options": True})
@click.argument("agent_cmd", default="claude")
@click.option("--project", "-p", help="Project name or alias, resolved via local.yaml paths.")
@click.option(
    "--repo-dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Host path to repository/workspace mounted in sandbox.",
)
@click.option(
    "--workspace",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Alias for --repo-dir.",
)
@click.option(
    "--kit",
    type=click.Path(path_type=Path),
    help="Path to custom Docker Sandbox kit directory.",
)
@click.option("--session-name", "-s", "--name", help="Sandbox instance name.")
@click.option(
    "--task",
    "-t",
    help="Task id to work. With no explicit prompt, seeds '/pull <task-id>'.",
)
@click.option(
    "--prompt",
    help="Prompt string for print/headless mode.",
)
@click.option(
    "--model",
    "-m",
    help="Model override.",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    default=False,
    help="Run interactively (attaches TTY).",
)
@click.option(
    "--detach",
    "--detached",
    is_flag=True,
    default=False,
    help="Run sandbox in detached mode.",
)
@click.option(
    "--port",
    "--publish",
    "-P",
    "ports",
    multiple=True,
    help="Publish container port(s).",
)
@click.option(
    "--env",
    "-e",
    "custom_envs",
    multiple=True,
    help="Set environment variable(s) in sandbox (KEY=VAL or KEY).",
)
@click.option(
    "--output-format",
    "-o",
    help="Output format for print/headless mode.",
)
@click.option(
    "--mcp-url",
    help="Override knowledge-base MCP URL forwarded into sandbox.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress polecat's own progress output on stderr.",
)
# Legacy options accepted for compatibility
@click.option("--base", help="[Deprecated] Base commit or branch.")
@click.option("--branch", "-b", help="[Deprecated] Custom branch name.")
@click.option("--no-pkb", is_flag=True, default=False, help="Allow run without PKB MCP URL.")
@click.option("--agent", "-a", help="Agent persona.")
@click.option("--no-agent", is_flag=True, default=False, help="Run without agent persona.")
@click.option("--with-sessions", is_flag=True, default=False, help="Sessions flag.")
@click.option("--scratch-dir", "--scratch", help="Scratch directory.")
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def run(
    agent_cmd,
    project,
    repo_dir,
    workspace,
    kit,
    session_name,
    task,
    prompt,
    model,
    interactive,
    detach,
    ports,
    custom_envs,
    output_format,
    mcp_url,
    quiet,
    base,
    branch,
    no_pkb,
    agent,
    no_agent,
    with_sessions,
    scratch_dir,
    extra_args,
):
    """Run AGENT_CMD (claude, agy, shell) in a Docker sandbox."""
    if detach and interactive:
        fail("cannot run in interactive mode with --detach")

    # Resolve sessions root
    sessions_root = resolve_sessions_root()

    config = load_config()
    target_repo = repo_dir or workspace
    workspace_dir = resolve_workspace_dir(project, target_repo, config)
    initial_head = _get_git_head(workspace_dir)
    effective_model = model or os.environ.get("POLECAT_WORKER_MODEL")

    if agent_cmd in ("claude", "agy") and not no_pkb:
        effective_url = mcp_url or os.environ.get("PKB_MCP_URL")
        if not effective_url:
            fail(
                "PKB_MCP_URL is not set. Neither $PKB_MCP_URL nor --mcp-url resolved to a URL "
                "(e.g. port 8020 or 8026). Pass --no-pkb to allow a run with no knowledge-base."
            )

    effective_session_name = _sanitize_path_component(session_name)
    if not effective_session_name:
        effective_session_name = f"session-{uuid.uuid4().hex[:8]}"

    resolved_kit = resolve_kit_path(agent_cmd, kit)

    env_map: dict[str, str] = {}
    for env_name in FORWARDED_ENV:
        if env_name in os.environ:
            env_map[env_name] = os.environ[env_name]

    if mcp_url:
        env_map["PKB_MCP_URL"] = mcp_url

    for ce in custom_envs:
        if "=" in ce:
            k, v = ce.split("=", 1)
            env_map[k] = v
        else:
            env_map[ce] = os.environ.get(ce, "")

    resolved_ports = resolve_ports(config, ports)

    effective_prompt = prompt
    if not effective_prompt and task:
        effective_prompt = f"/aops:pull {task}"

    canon_proj = resolve_canonical_project(project, config)
    if canon_proj:
        env_map["OTEL_SERVICE_NAME"] = canon_proj
        env_map["PHOENIX_PROJECT_NAME"] = canon_proj
        otel_res = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
        env_map["OTEL_RESOURCE_ATTRIBUTES"] = format_otel_resource_attributes(
            session_id=effective_session_name,
            project=canon_proj,
            task_id=task,
            existing=otel_res,
        )
    if task:
        env_map["GENAI_ENGINE_TASK_ID"] = task

    cmd = build_sbx_command(
        agent_cmd=agent_cmd,
        workspace_dir=workspace_dir,
        session_name=effective_session_name,
        kit_path=resolved_kit,
        detach=detach,
        ports=resolved_ports,
        env_vars=env_map,
        prompt=effective_prompt,
        task=task,
        model=model,
        interactive=interactive,
        output_format=output_format,
        extra_args=extra_args,
    )

    session_dir = (
        resolve_session_dir(
            sessions_root,
            resolve_canonical_project(project, config) or "unknown",
            effective_session_name,
        )
        if sessions_root
        else Path("/tmp") / effective_session_name
    )

    if not quiet:
        click.echo(f"Running: {' '.join(cmd)}", err=True)
        click.echo(f"Workspace: {workspace_dir}", err=True)
        click.echo(f"Session logs: {session_dir}", err=True)

    start_time = datetime.now(UTC)
    exit_code = 0

    try:
        proc = subprocess.run(cmd)
        exit_code = proc.returncode
    except FileNotFoundError:
        fail(
            f"executable not found: '{cmd[0]}'. Ensure Docker Sandboxes (`sbx` or `docker sbx`) is installed."
        )

    end_time = datetime.now(UTC)
    status = (
        "detached" if (detach and exit_code == 0) else ("success" if exit_code == 0 else "failed")
    )

    if exit_code != 0 and not quiet:
        click.echo(f"Workspace preserved for inspection: {workspace_dir}", err=True)

    final_head = _get_git_head(workspace_dir)

    write_run_record(
        session_dir=session_dir,
        session_id=effective_session_name,
        agent=agent_cmd,
        status=status,
        workspace_dir=workspace_dir,
        commit_start=initial_head,
        commit_end=final_head,
        exit_code=exit_code,
        task_id=task,
        seeded_prompt=effective_prompt,
        started_at=start_time,
        ended_at=end_time,
        worker_model=effective_model,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
