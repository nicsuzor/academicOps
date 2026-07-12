"""Shared visual style for session-start self-diagnostic blocks.

Single SSoT for the "new style" diagnostic grammar used across the session-start
system message: ANSI colour constants, the ``ok``/``warn``/``FAIL`` row helpers,
and the bold ``── TITLE [surface] ──`` section header. The styling mirrors
``scripts/setup-machine.sh`` so every diagnostic block (ENV provisioning, the
Session block, autoMode, daily note, …) renders identically.

Consumers:
  - ``lib/env_provision.py`` — the ENV provisioning block.
  - ``hooks/session_env_setup.py`` — the Session / autoMode / daily-note blocks.
"""

from __future__ import annotations

# ANSI styling mirrored from scripts/setup-machine.sh (single visual SSoT).
_RED = "\033[0;31m"
_GREEN = "\033[0;32m"
_YELLOW = "\033[0;33m"
_BOLD = "\033[1m"
_NC = "\033[0m"


def _ok(msg: str) -> str:
    """Render a green ``ok`` status row."""
    return f"  {_GREEN}ok{_NC}    {msg}"


def _warn(msg: str) -> str:
    """Render a yellow ``warn`` status row."""
    return f"  {_YELLOW}warn{_NC}  {msg}"


def _fail(msg: str) -> str:
    """Render a red ``FAIL`` status row."""
    return f"  {_RED}FAIL{_NC}  {msg}"


def section_header(title: str, surface: str | None = None) -> str:
    """Render a bold ``── TITLE ──`` section header.

    When ``surface`` is given, the header reads ``── TITLE [surface] ──``.
    """
    tag = f" [{surface}]" if surface else ""
    return f"{_BOLD}── {title}{tag} ──{_NC}"
