"""The aops MCP server: `polecat run`'s dispatch contract, exposed as plain
MCP tools instead of a CLI a caller has to shell out to.

Runs as its own container on the WSL host, with the host Docker socket and
every host path `polecat run` already needs mounted in at its own host path:
`$POLECAT_HOME`, `$AOPS_SESSIONS`, **each repository checkout in
`local.yaml`'s `paths` map** (the clone happens in this process, so the source
has to resolve here), and an optional rules dir, scratch dir, and
`$GEMINI_CONFIG_DIR` — see specs/polecat/polecat-mcp-server.md for the full
invocation and for why the mount list is not just `$POLECAT_HOME`.
Registered on Bifrost as a plain tool server (`tools/list` shows `dispatch` /
`inspect` / `stop` directly), not code mode: unlike the PKB proxy, there is no
`executeToolCode` layer here.

This module imports `execute_run` from `cli.py` and calls it in-process
rather than shelling out to the `polecat` console script: one implementation
of the dispatch contract in [[polecat-system]], not two. `fail()` (used
throughout `execute_run`'s call graph) raises `PolecatError` instead of
exiting the process, which is what makes that safe to call from inside this
long-lived server — see `cli.PolecatError`'s docstring.
"""

import asyncio
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

from fastmcp import FastMCP

from .cli import PolecatError, RunResult, execute_run, resolve_sessions_root

mcp = FastMCP("polecat")


def _container_name(session_id: str) -> str:
    """Match `cli._build_docker_argv`'s own `--name polecat-<session_id>`."""
    return f"polecat-{session_id}"


def _run_result_to_dict(result: RunResult) -> dict:
    return {
        "detached": result.detached,
        "returncode": result.returncode,
        "session_id": result.session_id,
        "session_dir": str(result.session_dir),
        "workspace_dir": str(result.workspace_dir),
        "container_id": result.container_id,
        "container_name": result.container_name,
        "run_record_path": str(result.run_record_path),
        "seeded_prompt": result.seeded_prompt,
        "delivery_ok": result.delivery_ok,
        "delivery_err": result.delivery_err,
        "image": result.image,
        "task_id": result.task_id,
    }


@mcp.tool()
async def dispatch(
    task: str | None = None,
    project: str | None = None,
    repo_dir: str | None = None,
    agent_cmd: str = "claude",
    prompt: str | None = None,
    base: str | None = None,
    branch: str | None = None,
    model: str | None = None,
    agent: str | None = None,
    detach: bool = False,
    with_sessions: bool = False,
) -> dict:
    """Dispatch an agent CLI into an isolated polecat container.

    Mirrors `polecat run`'s own contract (specs/polecat/polecat-system.md):
    an isolated clone, the credential/environment/mount contract from that
    spec's step 5, and the same post-run delivery guard. With `task` and no
    `prompt`, seeds `/pkb:pull <task>` exactly as the CLI does.

    `detach=True` returns as soon as the container starts, without waiting
    for it to finish or verifying delivery — use `inspect`/`stop` afterward.
    `detach=False` (the default) blocks until the container exits and the
    delivery guard has run, exactly like a foreground `polecat run`.

    Raises an MCP tool error (surfacing `PolecatError`'s message) on any
    resolution failure — an unset `$POLECAT_HOME`/`$POLECAT_IMAGE`/
    `$AOPS_SESSIONS`, an unresolvable workspace, a missing image — never a
    silent no-op.
    """
    # execute_run() is synchronous (subprocess.run under the hood, blocking
    # for the life of the container on a foreground dispatch) — run it off
    # the event loop thread so a slow dispatch does not stall `inspect` /
    # `stop` calls against other sessions on this same server.
    result = await asyncio.to_thread(
        execute_run,
        agent_cmd=agent_cmd,
        project=project,
        repo_dir=Path(repo_dir) if repo_dir else None,
        session_name=None,
        mcp_url=None,
        no_pkb=False,
        task=task,
        base=base,
        branch=branch,
        with_sessions=with_sessions,
        model=model,
        agent=agent,
        no_agent=False,
        output_format=None,
        prompt=prompt,
        interactive=False,
        detach=detach,
        quiet=True,
        ports=(),
        scratch_dir=None,
        extra_args=(),
    )
    return _run_result_to_dict(result)


#: `docker inspect`/`docker stop` against a name that does not exist. Anything
#: else on stderr is a daemon or permission fault, which must not be reported
#: as an absent container.
_NO_SUCH_CONTAINER = ("no such object", "no such container")

#: Bound on every docker CLI call. A wedged daemon must not hold a thread-pool
#: slot forever (lib/axioms/bounded-execution.md). `docker stop` gets room for
#: the default 10s SIGTERM grace period plus overhead.
_INSPECT_TIMEOUT = 30
_STOP_TIMEOUT = 60


def _is_absent(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(marker in lowered for marker in _NO_SUCH_CONTAINER)


def _docker_inspect(name: str) -> dict | None:
    """`docker inspect <name>`'s first element, or None if no such container.

    A non-zero exit that is *not* "no such object" — an unreachable daemon, a
    socket permission denial — raises rather than returning None: reporting
    "not running" for a container this server simply cannot see would let a
    caller conclude a live session had finished.
    """
    try:
        res = subprocess.run(
            ["docker", "inspect", name],
            capture_output=True,
            text=True,
            timeout=_INSPECT_TIMEOUT,
        )
    except subprocess.TimeoutExpired as e:
        raise PolecatError(
            f"docker inspect {name} did not return within {_INSPECT_TIMEOUT}s. "
            "The Docker daemon is unreachable or wedged."
        ) from e
    if res.returncode != 0:
        if _is_absent(res.stderr):
            return None
        raise PolecatError(f"docker inspect {name} failed: {res.stderr.strip()}")
    parsed = json.loads(res.stdout)
    return parsed[0] if parsed else None


def _find_run_record(session_id: str) -> dict | None:
    """The most recently written run.json for this session id, if the run has
    finished and recorded one. Session directories are dated
    (`logs/<date>/<session_id>/<project>/run.json`), and neither the date nor
    the project is known from `session_id` alone, so this globs for it rather
    than reconstructing the path."""
    sessions_base = resolve_sessions_root()
    matches = sorted(
        glob.glob(str(sessions_base / "logs" / "*" / session_id / "*" / "run.json")),
        key=lambda p: Path(p).stat().st_mtime,
        reverse=True,
    )
    if not matches:
        return None
    return json.loads(Path(matches[0]).read_text())


@mcp.tool()
async def inspect(session_id: str) -> dict:
    """Report what a dispatched session is doing now.

    Combines live container state (`docker inspect polecat-<session_id>`,
    present only while the container is running) with the persisted run
    record (`run.json`, written once the run finishes) — whichever of the two
    exists. Both absent means no session by this id was ever dispatched from
    this server, or its logs are not under this server's `$AOPS_SESSIONS`.
    """
    name = _container_name(session_id)
    container = await asyncio.to_thread(_docker_inspect, name)
    run_record = await asyncio.to_thread(_find_run_record, session_id)

    if container is None and run_record is None:
        return {
            "session_id": session_id,
            "container_name": name,
            "found": False,
            "container": None,
            "run_record": None,
        }

    return {
        "session_id": session_id,
        "container_name": name,
        "found": True,
        "running": bool(container and container.get("State", {}).get("Running")),
        "container": {
            "id": container.get("Id"),
            "state": container.get("State"),
        }
        if container
        else None,
        "run_record": run_record,
    }


@mcp.tool()
async def stop(session_id: str) -> dict:
    """Stop a running polecat container by session id.

    A no-op (`stopped: False, reason: "not running"`) when no container by
    this name is currently running — including a session that already
    finished, which `--rm` has already reaped. Never raises for that case;
    only a `docker stop` failure against a container that *is* running does.
    """
    name = _container_name(session_id)
    container = await asyncio.to_thread(_docker_inspect, name)
    if container is None or not container.get("State", {}).get("Running"):
        return {
            "session_id": session_id,
            "container_name": name,
            "stopped": False,
            "reason": "not running",
        }

    def _stop() -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker", "stop", name],
            capture_output=True,
            text=True,
            timeout=_STOP_TIMEOUT,
        )

    try:
        res = await asyncio.to_thread(_stop)
    except subprocess.TimeoutExpired as e:
        raise PolecatError(f"docker stop {name} did not return within {_STOP_TIMEOUT}s.") from e
    if res.returncode != 0:
        # Containers run `--rm`, so one that exits between the inspect above
        # and this call is already reaped. That is the documented no-op, not a
        # failure — it is the normal race for a run that is finishing.
        if _is_absent(res.stderr):
            return {
                "session_id": session_id,
                "container_name": name,
                "stopped": False,
                "reason": "not running",
            }
        raise PolecatError(f"docker stop {name} failed: {res.stderr.strip()}")
    return {"session_id": session_id, "container_name": name, "stopped": True, "reason": None}


def _resolve_bind() -> tuple[str, int]:
    """Host/port this server listens on. Port has no default: an operator's
    choice, not this code's. Host defaults to every interface (`0.0.0.0`) —
    a bind-all convention, not an installation identity, so it is the one
    exception to "no defaults" here."""
    host = os.environ.get("POLECAT_MCP_HOST", "0.0.0.0")
    port_raw = os.environ.get("POLECAT_MCP_PORT")
    if not port_raw:
        raise PolecatError(
            "no POLECAT_MCP_PORT set. The server needs a port to listen on; "
            "there is no default. Export POLECAT_MCP_PORT and retry."
        )
    try:
        port = int(port_raw)
    except ValueError as e:
        raise PolecatError(f"POLECAT_MCP_PORT={port_raw!r} is not an integer.") from e
    return host, port


def main() -> None:
    """Entry point for the console script and the image ENTRYPOINT.

    A `PolecatError` here is an operator misconfiguration, not a bug: report it
    the way the CLI does and exit non-zero, so a restarting container logs one
    actionable line rather than the same traceback on every loop.
    """
    try:
        host, port = _resolve_bind()
    except PolecatError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from e
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
