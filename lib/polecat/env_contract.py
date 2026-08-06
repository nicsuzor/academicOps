#!/usr/bin/env python3
"""The environment contract for containerised agent sessions.

One definition, consumed by every surface that starts a container: `cli.py`
turns it into `docker run -e KEY=VALUE`, and the `docker*` Makefile targets
emit `-e KEY` flags from it via `--docker-args`.

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
    "OTEL_RESOURCE_ATTRIBUTES",
    "OTEL_LOG_USER_PROMPTS",
    "OTEL_LOG_RAW_API_BODIES",
    "OTEL_LOG_TOOL_DETAILS",
    "OTEL_LOG_ASSISTANT_RESPONSES",
    "OTEL_METRIC_EXPORT_INTERVAL",
    "OTEL_LOGS_EXPORT_INTERVAL",
    "OTEL_TRACES_EXPORT_INTERVAL",
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
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
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

# Container-internal paths, given a value rather than forwarded.
#
# CLAUDE_ENV_FILE is where the SessionStart credential hook appends git/gh auth
# config; the hook does nothing at all when the name is unset. Claude Code
# creates its own per-session file and overrides this value, so this path is
# the one used by clients that supply none. It sits outside every bind mount,
# so what it holds dies with the container instead of persisting on the host.
CONTAINER_SET_ENV = {
    "CLAUDE_ENV_FILE": "/tmp/aops-session.env",
}


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
