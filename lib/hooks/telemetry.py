"""Telemetry contract check: reports whether Claude Code's native OpenTelemetry
export is configured. Reports only — never sets a value, never supplies a
default endpoint. See specs/ARCHITECTURE.md, Observability.
"""

from __future__ import annotations

import os

CONTRACT: tuple[str, ...] = (
    "CLAUDE_CODE_ENABLE_TELEMETRY",
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


def configured_vars() -> list[str]:
    """Contract vars that are actually set in the environment. Read-only."""
    return [name for name in CONTRACT if os.environ.get(name)]


def report() -> str:
    """One-line, human-readable report of contract coverage.

    Never sets a value and never supplies a default endpoint — reports only.
    """
    configured = configured_vars()
    if not configured:
        return "telemetry: not configured"
    enabled = os.environ.get("CLAUDE_CODE_ENABLE_TELEMETRY") == "1"
    if enabled:
        return f"telemetry: enabled ({len(configured)}/{len(CONTRACT)} contract vars set)"
    return (
        f"telemetry: {len(configured)}/{len(CONTRACT)} contract vars set, "
        'but CLAUDE_CODE_ENABLE_TELEMETRY is not "1"'
    )
