---
id: polecat-mcp-server
title: "Polecat MCP Server: dispatch as plain MCP tools"
type: spec
status: ready
tier: polecat
depends_on: [polecat-system]
tags: [spec, polecat, mcp, bifrost, wsl]
---

# Polecat MCP Server: dispatch as plain MCP tools

`polecat run`'s dispatch contract ([polecat-system.md](polecat-system.md)),
exposed as three plain MCP tools — `dispatch`, `inspect`, `stop` — instead of
a CLI a caller has to shell out to. The motivating limit: a caller already
inside a container cannot invoke `polecat run` (no Docker socket in the
worker image, by design — see the connections on `obs_9e594b97` in the PKB).
An MCP tool call has no such restriction; a caller inside a polecat container
reaches this server exactly the way a host session does.

## Giving Effect

- [[lib/polecat/server.py]] — the server: three `@mcp.tool()` functions,
  built on `fastmcp.FastMCP`
- [[lib/polecat/cli.py]] — `execute_run()`, `PolecatError`, `RunResult`: the
  plain-function core the server calls in-process. The Click `run` command in
  the same file is now a thin CLI adapter over the same function, so there is
  exactly one implementation of the dispatch contract, not two — the CLI and
  this server are both callers of it.
- [[lib/polecat/Dockerfile.server]] — the server's own image. Distinct from
  the root `Dockerfile` (the aops-crew _worker_ image this server launches):
  this one holds the `docker` CLI and this repo's Python source, not an agent
  CLI.
- `make polecat-server-build` / `make polecat-server-push` (Makefile) — build
  and publish the server image, mirroring `docker-build`/`docker-push` for
  the worker image.

## Why in-process, not a subprocess shelling out to the CLI

`execute_run()` is imported and called directly rather than the server
shelling out to the installed `polecat` console script. Two implementations
of the same dispatch contract is the thing `lib/` injection and this
project's no-duplication rule both exist to prevent, and a subprocess wrapper
would also have made every value `execute_run()` needs (git identity, the PKB
MCP URL, the bot GitHub token, ...) into something that has to cross a second
process boundary for no reason.

The one hazard this creates: `fail()` used to call `sys.exit(1)`. Called
in-process from a long-lived server, that would kill the whole server on the
first resolution failure of any dispatch. `fail()` now raises `PolecatError`
instead (`lib/polecat/cli.py`), left uncaught through `execute_run()`'s whole
call graph. The Click `run` command is the only place it is caught and turned
back into the CLI's stderr-message-plus-exit-1 contract (`_cli_entry`); the
server lets `PolecatError` surface as the MCP tool call's own error.

## Tools

### `dispatch`

Runs `execute_run()` off the event loop thread (`asyncio.to_thread`), so a
long foreground dispatch does not block `inspect`/`stop` calls against other
sessions on the same server — up to saturation. `to_thread` uses the default
executor (`min(32, cpu+4)` threads) and nothing caps concurrent dispatches,
so each `detach=False` dispatch holds a thread for its container's whole
lifetime and everything queues once they are all held. Cap concurrency with a
dedicated sized executor before relying on this under load.

Parameters mirror the CLI's own: `task`,
`project`, `repo_dir`, `agent_cmd` (default `claude`), `prompt`, `base`,
`branch`, `model`, `agent`, `detach`, `with_sessions`. With `task` and no
`prompt`, seeds `/pkb:pull <task>` exactly as `polecat run -t <task>` does.

`detach=False` (the default) blocks until the container exits and the
delivery guard has run — a synchronous dispatch, exactly like a foreground
`polecat run`. `detach=True` returns once the container has started.

Prefer `detach=True` plus `inspect` for anything long. An agent run lasts
minutes to hours, and an HTTP client will usually time out before a
foreground dispatch returns — leaving a container running whose `session_id`
the caller never received, and so cannot `inspect` or `stop`.

Returns the `RunResult` dataclass as a plain dict (`Path` fields stringified,
so the result is JSON-safe): `session_id`, `container_id`, `container_name`,
`session_dir`, `workspace_dir`, `run_record_path`, `seeded_prompt`,
`delivery_ok`, `delivery_err`, `returncode`, `image`, `task_id`.

A resolution failure (unset `$POLECAT_HOME`/`$POLECAT_IMAGE`, an unresolvable
workspace, a missing image, a failed delivery guard, ...) surfaces as an MCP
tool error carrying `PolecatError`'s message, never a silent no-op and never
a crashed server.

Because a failed delivery guard raises, `delivery_ok`/`delivery_err` are only
ever `True`/`None` in a result returned from a non-detached dispatch: on that
path a delivery failure is the raised error, not a field to test. They carry
information only for `detach=True`, where the guard has not run yet.

### `inspect`

Takes a `session_id`. Combines `docker inspect polecat-<session_id>` (live
state, present only while the container is running) with the persisted
`run.json` (globbed under `$AOPS_SESSIONS/logs/*/<session_id>/*/run.json`,
present once the run has finished) — whichever exists. Both absent means no
session by this id was ever dispatched from this server, or its logs live
under a different `$AOPS_SESSIONS`.

### `stop`

Takes a `session_id`. `docker stop polecat-<session_id>`. A no-op
(`stopped: false, reason: "not running"`) when no such container is
currently running, including one that already finished and was reaped by
`--rm` — never an error for that case. Raises only on an actual `docker stop`
failure against a container that is running.

## Running the server

One container, long-lived, on the WSL host (nicwin) — the same host whose
Docker daemon `polecat run` already dispatches onto
([[mem-f58279e1]]: `/var/run/docker.sock` is this host's own; never SSH to
reach it). Build with `make polecat-server-build`.

`execute_run()` runs the whole staging phase in _this_ process, not in the
worker: it resolves the workspace, `git clone --local`s it, fetches the base
ref and checks out the branch. So every path that phase touches must resolve
inside this container, at its own host path, and `git` must be on its `PATH`
(`Dockerfile.server` installs it). That is what the mount list below is for.

Build the two variable lists first — the repository mounts, and the
environment forwards generated from the contract rather than hand-listed:

```sh
# One -v per `paths` entry in $POLECAT_HOME/local.yaml, each at its own host
# path. Add the same way: $POLECAT_RULES_DIR, the configured scratch_dir, and
# $GEMINI_CONFIG_DIR if any agy dispatch is expected.
repo_mounts=$(uv run python - <<'PY'
import os, pathlib, yaml
home = os.environ["POLECAT_HOME"]
paths = (yaml.safe_load(pathlib.Path(home, "local.yaml").read_text()) or {}).get("paths", {})
seen = sorted({str(pathlib.Path(p).expanduser().resolve()) for p in paths.values()})
print(" ".join(f"-v {p}:{p}" for p in seen))
PY
)

# Every name in the forwarded allowlist, so no worker silently loses one.
env_flags=$(uv run python -c 'from lib.polecat.env_contract import FORWARDED_ENV
print(" ".join(f"-e {n}" for n in FORWARDED_ENV))')
```

```sh
docker run -d --name aops-polecat-server --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --group-add "$(stat -c %g /var/run/docker.sock)" \
  -u "$(id -u):$(id -g)" \
  -v "$POLECAT_HOME:$POLECAT_HOME" \
  -v "$AOPS_SESSIONS:$AOPS_SESSIONS" \
  $repo_mounts \
  -e HOME $env_flags \
  -e POLECAT_MCP_HOST -e POLECAT_MCP_PORT \
  -p "$POLECAT_MCP_PORT:$POLECAT_MCP_PORT" \
  ghcr.io/nicsuzor/aops-polecat-server:latest
```

Every `-e NAME` is valueless, matching
[polecat-system.md](polecat-system.md) step 5's own convention: the value
comes from the invoking shell's environment, never the command line, so it
never appears in `docker inspect`/`ps` output on the host. `--group-add`
plus `-u` gives the server's own process the host UID and docker-socket GID
it needs to both write into the mounted host paths as the right owner and
talk to the socket — the identical pattern `_build_docker_argv`'s
`enable_socket` branch already uses for a polecat worker that legitimately
spawns siblings.

### What must be mounted, and why it is not just `$POLECAT_HOME`

`$POLECAT_HOME` and `$AOPS_SESSIONS` are bind-mounted at their own host
paths (not remapped) because `execute_run()` uses them to build the _next_
`docker run`'s own `-v host_path:container_path` mounts for the worker it
spawns — those bind-mount sources have to resolve on the host's own Docker
daemon, which sees this server's declared mounts and the worker's as
siblings, not as nested paths inside this container's filesystem.

The same reasoning extends to the repositories, and this is the part that is
easy to miss: `_resolve_workspace` reads the source checkout from
`local.yaml`'s `paths` map and then requires it to exist **in this process's
own filesystem**, because the clone is performed here. Those checkouts are
siblings of `$POLECAT_HOME`, not children of it (`resolve_polecat_home`:
polecat home must be on the same filesystem as the repositories it clones),
so mounting `$POLECAT_HOME` does not bring them in. Without a mount per
`paths` entry, every `dispatch(project=…)` fails at workspace resolution;
`dispatch(repo_dir=…)` fails the same way for any path outside the mounts.

Three further paths fail in less obvious ways if they are configured but not
mounted:

- **`$POLECAT_RULES_DIR` / `rules_dir`** — `resolve_rules_dir` fails by
  design on a configured path that does not resolve, so a `rules_dir` in
  `polecat.yaml` breaks _every_ dispatch until it is mounted.
- **`scratch_dir`** — `resolve_scratch_dir` calls `mkdir(parents=True,
  exist_ok=True)`, which _succeeds_ inside this container and then hands that
  path to the worker's `-v` as though it were a host path. Docker
  materialises an empty root-owned directory on the host and nothing errors.
- **`$GEMINI_CONFIG_DIR`** — required for `agent_cmd="agy"`, and a hard
  failure when set but absent.

`-e HOME` is required because `expand()` applies `expanduser`: without it,
`~` in `local.yaml` resolves against the image's `/home/worker` rather than
the host user's home, producing a workspace-resolution failure whose message
names a path the operator never configured.

### Forwarding the environment the worker needs

`_build_docker_argv` builds the worker's environment as `{**os.environ,
**env}`, and docker resolves each valueless `-e NAME` against **the invoking
process's** environment — which is now this server container's, not the
host shell's. Any name in `FORWARDED_ENV` that this container does not
itself hold is therefore silently dropped from every worker it dispatches.

That is why `$env_flags` above is generated from
[`lib/polecat/env_contract.py`](../../lib/polecat/env_contract.py)'s
`FORWARDED_ENV` rather than written out here: a hand-list would be a second
copy of that tuple and would drift out of step with it.

The failure this prevents is quiet rather than loud. `PKB_MCP_URL` is easy to
remember and `PKB_MCP_TOKEN` is easy to forget, and a worker that gets the
first without the second reaches an unauthenticated PKB endpoint and reports
no error here. `GEMINI_API_KEY`/`AGY_API_KEY` behave the same way for `agy`
dispatches. Names that `resolve_telemetry`/`resolve_cope_evaluator`
synthesise from `polecat.yaml` (`OTEL_*`, `GENAI_ENGINE_*`,
`COPE_EVALUATOR_*`) do not need forwarding — they have no host counterpart by
design.

`POLECAT_MCP_PORT` has no default (`server._resolve_bind`) — an operator's
port choice, not this code's. `POLECAT_MCP_HOST` defaults to `0.0.0.0`
(every interface) when unset.

## Bifrost registration

Registered as a plain tool server — `tools/list` returns `dispatch`,
`inspect`, `stop` directly, no `executeToolCode` layer, unlike the PKB route
([[kb_bifrost_pkb_code_mode]]: PKB is `is_code_mode_client: true`; this
server is registered without that flag). The registration itself is a
dotfiles change on the host running Bifrost, not a file in this repository —
add an entry alongside the existing `pkb`/`email`/`home`/`phoenix` routes
pointing at `http://<nicwin-tailnet-host>:$POLECAT_MCP_PORT/mcp` (or the
loopback/LAN address Bifrost already uses to reach sibling services on this
host), with `is_code_mode_client` unset or `false`. Match the exact key names
against whichever of those four entries Bifrost's own config already uses —
this repo does not have a copy of that file to diff against.

## Security contract carried over unchanged

[polecat-system.md](polecat-system.md) step 5's contract holds exactly as
written for the worker, because `execute_run()` is the same code path the CLI
uses: valueless `-e NAME` on every `docker run` this server issues, the denied
git credential paths (`GIT_ASKPASS=true`, empty `SSH_AUTH_SOCK`,
`GIT_SSH_COMMAND=false`, `GIT_TERMINAL_PROMPT=0`), and the fixed forwarded
allowlist. Nothing about exposing `dispatch` as an MCP tool changes what a
dispatched worker container can reach.

## The inbound trust boundary

What _does_ change is who can cause a dispatch at all, and that boundary is
new — the CLI had none to state, because invoking it already required a shell
on the host.

This server holds the host Docker socket and `mcp.run(transport="http", …)`
carries no authentication. So reachability of `POLECAT_MCP_PORT` **is** the
authorization boundary: anything that can open that port can create
containers on the host, choose the `agent_cmd` that becomes the container's
argv, and read back whatever `inspect` returns from `run.json`. The port must
therefore be reachable only from the tailnet interface Bifrost uses, never
from a LAN or public interface, and `POLECAT_MCP_HOST` must be set explicitly
to pin that rather than left to bind every interface.

Note what this does and does not reopen. [[obs_9e594b97]]'s resolution — the
worker image does not get the host Docker socket, because handing a
containerised agent that socket is a privilege-escalation decision — is
honoured: the worker image is untouched and the socket reaches only this
server. But a worker that can reach this port obtains container creation
_indirectly_, which is the same capability arriving by a different route. The
narrowing already in the code is deliberate and load-bearing to that
argument: `dispatch` hardcodes `extra_args=()`, `ports=()` and
`scratch_dir=None` rather than exposing them, so a caller cannot set
arbitrary mounts, publish ports, or pass through arbitrary agent flags.

## What this server does not do

It does not migrate any existing caller off `polecat run`, and it does not
delete `lib/polecat/cli.py` — both are
[[aops_polecat_mcp_server_cutover]]. The CLI and the server are both live,
both calling `execute_run()`, until that task retires the CLI's own callers.
