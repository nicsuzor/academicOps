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

# Source-name indirection for forwarded secrets (aops-b368109a).
#
# A forwarded secret crosses into the container under the name the agent runtime
# expects (the dict KEY — e.g. ``CLAUDE_CODE_OAUTH_TOKEN``, what headless
# ``claude`` reads), but the launching/host env sources it from a DIFFERENT
# variable (the dict VALUE candidates, tried in order). This closes the
# OAuth-token leak at the agent: the orchestrator (junior) session holds only
# ``AOPS_CC_OAUTH_TOKEN`` and never the official-named token, so the official
# name cannot be used or leaked from the agent's own session — yet workers still
# authenticate, because polecat resolves the value here at launch and injects it
# under the official name.
#
# The container name itself is appended as the final fallback candidate (see
# ``resolve_forward_values``), so during rollout — before the host var is
# renamed — the token can still ride on its official name. Once the host renames
# ``CLAUDE_CODE_OAUTH_TOKEN`` → ``AOPS_CC_OAUTH_TOKEN`` the alias source wins.
#
# GEMINI symmetry (recommendation, deliberately NOT wired): the parallel
# indirection for Gemini would be a single line here —
#     "GEMINI_API_KEY": ("AOPS_GEMINI_API_KEY",),
# — once the operator renames the host var. It is left out until then so this
# change touches only the Claude token (per task scope); the mechanism is
# generic and ready for it.
_FORWARD_SOURCE_ALIASES: dict[str, tuple[str, ...]] = {
    "CLAUDE_CODE_OAUTH_TOKEN": ("AOPS_CC_OAUTH_TOKEN",),
}

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
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    for line in content.splitlines():
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

    Each name is the CONTAINER variable name (the name the agent runtime reads).
    Its value may be sourced from a DIFFERENT host variable via
    ``_FORWARD_SOURCE_ALIASES`` (the source→container-name indirection that
    closes the OAuth-token leak — see that constant). Candidate source names are
    tried in order: the configured alias source(s) first, then the container
    name itself as the transitional fallback.

    For each candidate, resolution order is:
      1. The host secret store ``~/.env.local`` (authoritative — the wrapper
         sources this itself, independent of the launching session's env).
      2. The process env (``source_env``) as a fallback — covers vars set by
         the host shell profile but absent from ``~/.env.local`` (e.g. path
         locators), and the GHA surface where secrets arrive via process env.

    Empty / unset values are skipped (a forwarded empty credential would make
    headless CLIs 401 on a deliberate-empty-key, per the existing
    ``get_container_env_forwards`` contract).

    Args:
        names: Container variable names declared in ``polecat.yaml``
            ``container_env_forward``.
        source_env: Process env fallback. Defaults to ``os.environ``.
        env_file: Override secret-store path (for tests).

    Returns:
        Dict of {CONTAINER_NAME: VALUE} for names that resolved to a non-empty
        value (keyed by the container name, regardless of which source supplied
        the value).
    """
    if source_env is None:
        source_env = dict(os.environ)
    host = load_host_secrets(env_file)

    resolved: dict[str, str] = {}
    for name in names:
        # Alias source(s) first, then the container name itself as a fallback.
        candidates = (*_FORWARD_SOURCE_ALIASES.get(name, ()), name)
        for src in candidates:
            value = host.get(src) or source_env.get(src)
            if value:
                resolved[name] = value
                break
    return resolved
