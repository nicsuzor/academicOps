"""Host secret-store loader for polecat launch (env-var standardisation).

The polecat wrapper must resolve forwarded secret VALUES (e.g. the Claude/Gemini
OAuth tokens) from the host secret store ``~/.env.local`` at launch time —
*independent* of the launching agent's own session env. This closes the
OAuth-token leak: a general agent (junior) never persists those tokens into its
own ``CLAUDE_ENV_FILE``, yet the polecat container still receives them because
the launcher sources them here directly from ``~/.env.local``.

``polecat.yaml``'s ``container_env_forward:`` list is the *name whitelist* — it
declares WHICH variables cross into the container. This module resolves the
VALUES for those names from the host secret store. Secret values live ONLY in
``~/.env.local``; they are never committed to ``polecat.yaml``.

Parser scope: a deliberately small ``export KEY=VALUE`` / ``KEY=VALUE`` reader.
No shell-out (sourcing ``~/.env.local`` via a subprocess would execute arbitrary
code and is forbidden). Handles single/double quotes and inline ``export``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Default host secret store. Override via $AOPS_HOST_ENV_FILE for tests.
_DEFAULT_ENV_LOCAL = Path.home() / ".env.local"

# KEY=VALUE with optional leading `export `. KEY is a POSIX-ish env name.
_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _strip_value(raw: str) -> str:
    """Strip a single layer of matching quotes and trailing inline comment.

    Unquoted values: a trailing ``# comment`` is removed (shell semantics).
    Quoted values: returned verbatim inside the quotes (``#`` is literal).
    """
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        return raw[1:-1]
    # Unquoted: drop an inline comment if present.
    hash_idx = raw.find(" #")
    if hash_idx != -1:
        raw = raw[:hash_idx]
    return raw.strip()


def load_host_secrets(env_file: Path | str | None = None) -> dict[str, str]:
    """Parse ``~/.env.local`` into a dict of {NAME: VALUE}.

    Returns an empty dict if the file does not exist (e.g. on GHA runners,
    which inject secrets via Actions and have no ``~/.env.local``). Never
    raises on a missing file — callers fall back to the process env.

    Args:
        env_file: Override path. Defaults to ``$AOPS_HOST_ENV_FILE`` or
            ``~/.env.local``.

    Returns:
        Dict of parsed name→value pairs. Last assignment wins.
    """
    if env_file is None:
        env_file = os.environ.get("AOPS_HOST_ENV_FILE") or _DEFAULT_ENV_LOCAL
    path = Path(env_file)
    if not path.exists():
        return {}

    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _LINE_RE.match(stripped)
        if not m:
            continue
        key, raw_value = m.group(1), m.group(2)
        result[key] = _strip_value(raw_value)
    return result


def resolve_forward_values(
    names: list[str],
    source_env: dict[str, str] | None = None,
    env_file: Path | str | None = None,
) -> dict[str, str]:
    """Resolve VALUES for a whitelist of variable NAMES.

    Resolution order for each name:
      1. The host secret store ``~/.env.local`` (authoritative — the wrapper
         sources this itself, independent of the launching session's env).
      2. The process env (``source_env``) as a fallback — covers vars set by
         the host shell profile but absent from ``~/.env.local`` (e.g. path
         locators), and the GHA surface where secrets arrive via process env.

    Empty / unset values are skipped (a forwarded empty credential would make
    headless CLIs 401 on a deliberate-empty-key, per the existing
    ``get_container_env_forwards`` contract).

    Args:
        names: Variable names declared in ``polecat.yaml`` ``container_env_forward``.
        source_env: Process env fallback. Defaults to ``os.environ``.
        env_file: Override secret-store path (for tests).

    Returns:
        Dict of {NAME: VALUE} for names that resolved to a non-empty value.
    """
    if source_env is None:
        source_env = dict(os.environ)
    host = load_host_secrets(env_file)

    resolved: dict[str, str] = {}
    for name in names:
        value = host.get(name) or source_env.get(name)
        if value:
            resolved[name] = value
    return resolved
