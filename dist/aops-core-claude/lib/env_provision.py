"""Per-surface env-var provisioning contract (env-var standardisation).

The single provisioning entry point called by ``hooks/session_env_setup.py``
*after* it applies ``agent-env-map.conf``. Validates that the required env vars
for the detected surface are present, and renders a PROMINENT success/failure
block reusing the ok/warn/fail visual style from ``scripts/setup-machine.sh``.

Design decisions (see PKB note-b5347f83):
  - Surfaces: GHA (skip — Actions injects its own secrets), host general agent
    (junior — the default), and host worker (polecat container; validated at
    launch, not here).
  - Missing required host var → loud FAILURE block but the hook still returns
    ALLOW (Q1: never hard-DENY — that would brick the very session needed to
    fix the var). ``halt-on-failure`` "fail loud" is satisfied by the unmissable block.
  - OAuth tokens (CLAUDE_CODE_OAUTH_TOKEN / GEMINI_API_KEY) are HOLD-for-
    delegation on the host general-agent surface: they are NOT required for
    junior's own inference and are NOT persisted to CLAUDE_ENV_FILE. The
    polecat launcher resolves them from the process env (lib/host_secrets), so
    we do not check them here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum

# Visual style helpers live in the shared diag_style SSoT (re-exported here so
# this module's existing internal references keep working unchanged).
from lib.diag_style import (
    _BOLD,
    _GREEN,
    _NC,
    _RED,
    _fail,
    _ok,
    section_header,
)

__all__ = [
    "ProvisionReport",
    "Surface",
    "detect_surface",
    "validate_surface",
]


class Surface(StrEnum):
    """The provisioning surface a session is running on."""

    GHA = "gha"
    HOST = "host"  # host general agent (junior) — the default interactive surface


# Required vars per surface. The canonical minimum set (PKB note-b5347f83).
# Path locators + the bot token are genuinely required for the host general
# agent. PKB transport is required so the agent can reach the PKB MCP. OAuth
# tokens are deliberately NOT here (hold-for-delegation, resolved by polecat).
_HOST_REQUIRED: tuple[str, ...] = (
    "AOPS_BOT_GH_TOKEN",
    "ACA_DATA",
    "AOPS",
    "AOPS_SESSIONS",
    "PKB_MCP_URL",
)

# Secret names → redact in output (show only length + last 4 chars).
_SECRET_NAMES = frozenset(
    {
        "AOPS_BOT_GH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "GEMINI_API_KEY",
        "PKB_MCP_TOKEN",
        "AOPS_DIST_PAT",
    }
)


@dataclass
class ProvisionReport:
    """Outcome of a per-surface provisioning check."""

    surface: Surface
    ok: bool
    present: dict[str, str] = field(default_factory=dict)  # name → redacted value
    missing: list[str] = field(default_factory=list)
    skipped: bool = False
    lines: list[str] = field(default_factory=list)  # rendered message lines


def detect_surface(env: dict[str, str] | None = None) -> Surface:
    """Detect the provisioning surface from the environment.

    GHA is identified by ``GITHUB_ACTIONS=true`` (set by every GitHub Actions
    runner). Everything else is the host general-agent surface.
    """
    if env is None:
        env = dict(os.environ)
    if env.get("GITHUB_ACTIONS") == "true":
        return Surface.GHA
    return Surface.HOST


def _redact(name: str, value: str) -> str:
    """Redact secret values to ``len=N …abcd``; show non-secrets verbatim."""
    if name in _SECRET_NAMES:
        last4 = value[-4:] if len(value) >= 4 else "?"
        return f"<len={len(value)} …{last4}>"
    return value


def validate_surface(env: dict[str, str] | None = None) -> ProvisionReport:
    """Validate required env vars for the detected surface.

    Returns a :class:`ProvisionReport` whose ``lines`` render a prominent
    SUCCESS or FAILURE block. The caller (session_env_setup) appends these to
    the hook's system_message. This function NEVER raises and NEVER blocks —
    the hook decides the verdict (always ALLOW per Q1).
    """
    if env is None:
        env = dict(os.environ)
    surface = detect_surface(env)

    # --- GHA: skip provisioning. Actions injects its own secrets. ---
    if surface is Surface.GHA:
        return ProvisionReport(
            surface=surface,
            ok=True,
            skipped=True,
            lines=[
                "",
                section_header("ENV provisioning"),
                _ok("GHA surface: secrets injected by Actions; provisioning skipped"),
                "",
            ],
        )

    # --- Host general agent: check the canonical required set. ---
    present: dict[str, str] = {}
    missing: list[str] = []
    for name in _HOST_REQUIRED:
        value = env.get(name)
        if value:
            present[name] = _redact(name, value)
        else:
            missing.append(name)

    lines: list[str] = ["", section_header("ENV provisioning", "host")]

    if not missing:
        lines.append(f"{_GREEN}{_BOLD}✅ ENV OK — all required vars present [host]{_NC}")
        for name in _HOST_REQUIRED:
            lines.append(_ok(f"{name}={present[name]}"))
        lines.append("")
        return ProvisionReport(surface=surface, ok=True, present=present, missing=[], lines=lines)

    # FAILURE block — loud, names each missing var + the fix. Verdict stays
    # ALLOW (Q1): we do not brick the session needed to fix the var.
    lines.append(f"{_RED}{_BOLD}❌ ENV INCOMPLETE — required var(s) missing [host]{_NC}")
    for name in _HOST_REQUIRED:
        if name in present:
            lines.append(_ok(f"{name}={present[name]}"))
        else:
            lines.append(_fail(f"{name} is not set"))
    lines.append("")
    lines.append(f"  {_BOLD}Fix:{_NC} export the missing var(s) in your environment, e.g.:")
    for name in missing:
        lines.append(f"      export {name}=...")
    lines.append("  Then start a new session. (Session continues; auth/PKB ops may fail.)")
    lines.append("")
    return ProvisionReport(surface=surface, ok=False, present=present, missing=missing, lines=lines)
