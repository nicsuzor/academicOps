"""Telemetry contract check: reports whether Claude Code's native OpenTelemetry
export is configured. Reports only — never sets a value, never supplies a
default endpoint. See specs/ARCHITECTURE.md, Observability.
"""

from __future__ import annotations

import os

# Claude Code's own two feature-flag vars. Confirmed empirically (not
# assumed) that a live SessionStart hook subprocess sees these: setting or
# unsetting either one at session-launch time flips what the hook observes
# via os.environ, reproducibly. These are the only two names in CONTRACT a
# SessionStart hook can ever actually see.
ENABLEMENT_VARS: tuple[str, ...] = (
    "CLAUDE_CODE_ENABLE_TELEMETRY",
    "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA",
)

# The OTel exporter configuration proper — real, and forwarded into polecat
# containers and CI by plugins/aops/polecat/env_contract.py. Never visible to
# a SessionStart hook subprocess: a live session with every one of these set
# at process launch still reported none of them there, while the same
# session's Bash tool saw all of them (a separate, settings-managed
# environment, not the hook's). A hook can confirm telemetry is switched on;
# it cannot confirm export is configured, so this half of the contract is
# excluded from `report()`'s count — see that function's docstring.
EXPORT_VARS: tuple[str, ...] = (
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

# The full forwarding contract, unchanged in membership — everything
# plugins/aops/polecat/env_contract.py forwards into containers and CI, and
# what tests/test_telemetry_otel_e2e.py populates for a real end-to-end run.
CONTRACT: tuple[str, ...] = ENABLEMENT_VARS + EXPORT_VARS


def configured_vars() -> list[str]:
    """Contract vars that are actually set in the environment. Read-only."""
    return [name for name in CONTRACT if os.environ.get(name)]


def report() -> str:
    """One-line, human-readable report of contract coverage.

    Never sets a value and never supplies a default endpoint — reports only.

    Counts against `ENABLEMENT_VARS` (2), not the full `CONTRACT` (15). A
    SessionStart hook subprocess only ever observes
    `CLAUDE_CODE_ENABLE_TELEMETRY` and `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` —
    confirmed empirically, see `EXPORT_VARS` above. The 13 `OTEL_*`
    export-config vars can be genuinely configured on the host and still read
    as unset here; that is this hook's own blind spot, not a
    misconfiguration, so counting them in the denominator would report a gap
    that no amount of correct configuration could ever close.
    """
    configured = [name for name in ENABLEMENT_VARS if os.environ.get(name)]
    if not configured:
        return "telemetry: not configured"
    enabled = os.environ.get("CLAUDE_CODE_ENABLE_TELEMETRY") == "1"
    if enabled:
        return f"telemetry: enabled ({len(configured)}/{len(ENABLEMENT_VARS)} contract vars set)"
    return (
        f"telemetry: {len(configured)}/{len(ENABLEMENT_VARS)} contract vars set, "
        'but CLAUDE_CODE_ENABLE_TELEMETRY is not "1"'
    )
