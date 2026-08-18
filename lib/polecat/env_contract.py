#!/usr/bin/env python3
"""The environment contract for containerised agent sessions.

One definition, consumed by every surface that starts a container: the
`docker*` Makefile targets emit `-e KEY` flags from it via `--docker-args`,
and `cli.py` calls `docker_env_args()` directly for the same flags. Neither
puts a value on the command line, because argv is world-readable in the host
process table for as long as the container runs.

Names in `FORWARDED_ENV` and `CONTAINER_AUTH_ENV` are forwarded, never set.
`docker run -e KEY` (no value) propagates the host's value only when there is
one, so a variable unset on the host stays unset in the container. Nothing in
this file is a default.

`CONTAINER_SET_ENV` is the one exception, and holds container-internal paths
rather than host values: a path only the container's own filesystem can
resolve has no host value to forward.

Telemetry names are the OpenTelemetry contract in specs/ARCHITECTURE.md.
"""

import argparse
from urllib.parse import urlsplit, urlunsplit

# Claude Code's native OpenTelemetry export. Session-scoped: enabling it once
# covers every plugin.
TELEMETRY_ENV = (
    "CLAUDE_CODE_ENABLE_TELEMETRY",
    "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA",
    "ANTIGRAVITY_ENABLE_TELEMETRY",
    "OTEL_METRICS_EXPORTER",
    "OTEL_LOGS_EXPORTER",
    "OTEL_TRACES_EXPORTER",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
    "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
    "OTEL_RESOURCE_ATTRIBUTES",
    "OTEL_LOG_USER_PROMPTS",
    "OTEL_LOG_RAW_API_BODIES",
    "OTEL_LOG_TOOL_DETAILS",
    "OTEL_LOG_ASSISTANT_RESPONSES",
    "OTEL_METRIC_EXPORT_INTERVAL",
    "OTEL_LOGS_EXPORT_INTERVAL",
    "OTEL_TRACES_EXPORT_INTERVAL",
    "GENAI_ENGINE_TRACE_ENDPOINT",
    "GENAI_ENGINE_API_KEY",
    "GENAI_ENGINE_TASK_ID",
)

# Everything else forwarded verbatim when set on the host.
FORWARDED_ENV = (
    "GEMINI_API_KEY",
    "AGY_API_KEY",
    "PKB_MCP_URL",
    "PKB_MCP_TOKEN",
    "PKB_MCP_TOOL_PREFIX",
    "COPE_EVALUATOR_URL",
    "COPE_EVALUATOR_PROTOCOL",
    "COPE_EVALUATOR_MODEL",
    "COPE_EVALUATOR_API_KEY",
    "COPE_EVALUATOR_TIMEOUT",
    "GENAI_ENGINE_TRACE_ENDPOINT",
    "GENAI_ENGINE_API_KEY",
    "GENAI_ENGINE_TASK_ID",
    "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "COLORTERM",
    "FORCE_COLOR",
    "NO_COLOR",
    "CI",
    "NONINTERACTIVE",
    "TZ",
    "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP",
)

# Credentials the container's entrypoint requires to reach GitHub and the agent
# API. `cli.py` derives these from its own operator-scoped names; a plain
# `docker run` has only the host's, so they are forwarded by name.
CONTAINER_AUTH_ENV = (
    "AOPS_BOT_GH_TOKEN",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
)

# Container-internal paths and default flags, given a value rather than forwarded.
#
# CLAUDE_ENV_FILE is where the SessionStart credential hook appends git/gh auth
# config; the hook does nothing at all when the name is unset. Claude Code
# creates its own per-session file and overrides this value, so this path is
# the one used by clients that supply none. It sits outside every bind mount,
# so what it holds dies with the container instead of persisting on the host.
CONTAINER_SET_ENV = {
    "CLAUDE_ENV_FILE": "/tmp/aops-session.env",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_CODE_ENABLE_TODO_TOOLS": "1",
}

#: Host tokens that mean "this machine" on the host and "this container" inside
#: one. Forwarded verbatim they resolve to the container's own empty loopback.
#: Bare hosts, never endpoints: no scheme, no port, nothing dialable. They exist
#: to be *detected and replaced*, which is the opposite of a compiled-in default.
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"})

#: The gateway alias back to the host. `_build_docker_argv` always passes
#: `--add-host host.docker.internal:host-gateway`, so this resolves on plain
#: Linux Docker too, not only where Docker Desktop provides it natively.
_CONTAINER_HOST_ALIAS = "host.docker.internal"


def _rehost_loopback_urls(env):
    """Point loopback URLs and endpoints at the host, not at the container's own loopback.

    A URL whose host is a loopback token names a service on the operator's own
    machine. Forwarded unchanged it names that port *inside the container*,
    where nothing listens — so the dependent feature degrades instead of
    working, while the operator sees a service they can curl by hand.

    Rewrites loopback URLs and endpoints (e.g. COPE_EVALUATOR_URL,
    GENAI_ENGINE_TRACE_ENDPOINT, OTEL_EXPORTER_OTLP_ENDPOINT, BETA_TRACING_ENDPOINT)
    with or without scheme from loopback hosts to host.docker.internal.
    """
    rehosted = {}
    for key, value in env.items():
        if not isinstance(value, str):
            continue
        if "://" in value:
            parsed = urlsplit(value)
            if parsed.hostname is None or parsed.hostname.lower() not in _LOOPBACK_HOSTS:
                continue
            netloc = _CONTAINER_HOST_ALIAS
            if parsed.port is not None:
                netloc = f"{netloc}:{parsed.port}"
            if parsed.username:
                credentials = parsed.username
                if parsed.password:
                    credentials = f"{credentials}:{parsed.password}"
                netloc = f"{credentials}@{netloc}"
            rehosted[key] = urlunsplit(parsed._replace(netloc=netloc))
        elif key.endswith(("_ENDPOINT", "_URL")) or key in (
            "GENAI_ENGINE_TRACE_ENDPOINT",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "BETA_TRACING_ENDPOINT",
            "COPE_EVALUATOR_URL",
            "PKB_MCP_URL",
        ):
            parsed = urlsplit("//" + value)
            if parsed.hostname is None or parsed.hostname.lower() not in _LOOPBACK_HOSTS:
                continue
            netloc = _CONTAINER_HOST_ALIAS
            if parsed.port is not None:
                netloc = f"{netloc}:{parsed.port}"
            if parsed.username:
                credentials = parsed.username
                if parsed.password:
                    credentials = f"{credentials}:{parsed.password}"
                netloc = f"{credentials}@{netloc}"
            rehosted_val = netloc
            if parsed.path:
                rehosted_val = f"{rehosted_val}{parsed.path}"
            if parsed.query:
                rehosted_val = f"{rehosted_val}?{parsed.query}"
            if parsed.fragment:
                rehosted_val = f"{rehosted_val}#{parsed.fragment}"
            rehosted[key] = rehosted_val

    env.update(rehosted)
    return env


def docker_env_args(names=None):
    """`-e NAME` flags for `docker run`, one pair per name.

    Valueless on purpose: docker reads each value from its own environment and
    omits the variable entirely when the host has not set it. Names in
    `CONTAINER_SET_ENV` are the exception and carry their value.
    """
    if names is None:
        names = FORWARDED_ENV + CONTAINER_AUTH_ENV + tuple(CONTAINER_SET_ENV)
    args = []
    for name in names:
        if name in CONTAINER_SET_ENV:
            args.extend(["-e", f"{name}={CONTAINER_SET_ENV[name]}"])
        else:
            args.extend(["-e", name])
    return args


def format_otel_resource_attributes(
    existing: str | None = None,
    session_id: str | None = None,
    project: str | None = None,
    task_id: str | None = None,
) -> str:
    """Format OTEL_RESOURCE_ATTRIBUTES string by merging/injecting polecat attributes.

    Parses any existing comma-separated key=value attribute string, and merges/injects:
    - polecat.session_id=session_id (if session_id is set)
    - polecat.project=project (if project is set)
    - polecat.task_id=task_id (if task_id is set)
    """
    pairs = []
    if existing:
        for item in str(existing).split(","):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                k, v = item.split("=", 1)
                k = k.strip()
                v = v.strip()
            else:
                k = item.strip()
                v = ""
            if not k:
                continue
            pairs.append((k, v))

    updates = {}
    if session_id is not None and str(session_id).strip() != "":
        updates["polecat.session_id"] = str(session_id)
    if project is not None and str(project).strip() != "":
        updates["polecat.project"] = str(project)
    if task_id is not None and str(task_id).strip() != "":
        updates["polecat.task_id"] = str(task_id)

    result_pairs = []
    seen_keys = set()
    for k, v in pairs:
        if k in seen_keys:
            continue
        seen_keys.add(k)
        if k in updates:
            result_pairs.append(f"{k}={updates[k]}")
        else:
            if v != "":
                result_pairs.append(f"{k}={v}")
            else:
                result_pairs.append(k)

    for k, v in updates.items():
        if k not in seen_keys:
            seen_keys.add(k)
            result_pairs.append(f"{k}={v}")

    return ",".join(result_pairs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--docker-args",
        action="store_true",
        help="Emit the contract as `docker run` flags instead of bare names.",
    )
    parser.add_argument(
        "--telemetry-only",
        action="store_true",
        help="Restrict output to the OpenTelemetry contract.",
    )
    args = parser.parse_args()

    names = (
        TELEMETRY_ENV
        if args.telemetry_only
        else FORWARDED_ENV + CONTAINER_AUTH_ENV + tuple(CONTAINER_SET_ENV)
    )
    if args.docker_args:
        print(" ".join(docker_env_args(names)))
    else:
        print("\n".join(names))


if __name__ == "__main__":
    main()
