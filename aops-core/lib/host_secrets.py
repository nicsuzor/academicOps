"""Host secret-store loader for polecat launch (env-var standardisation).

The polecat wrapper must resolve forwarded secret VALUES (e.g. the Claude/Gemini
OAuth tokens) from the host secret store at launch time — *independent* of the
launching agent's own session env.

**Two-tier load strategy (sops SSoT + ~/.env.local fallback):**

1. ``aops-secrets.env`` — the sops/age-encrypted SSoT in the dotfiles repo
   (``~/dotfiles/containers/nicwin/aops-secrets.env``).  Decrypted in-memory by
   calling ``sops -d``; plaintext never materialises on disk.  This is the
   authoritative single source for all secret classes once bootstrapped.

2. ``~/.env.local`` — the legacy plaintext store.  Used as a fallback during
   transition, and on GHA runners where neither sops nor dotfiles are present.

The two sources are merged: sops values take precedence over ``~/.env.local``
for any key present in both.  Keys present only in ``~/.env.local`` are still
surfaced (covering any keys not yet migrated to the encrypted SSoT).

``polecat.yaml``'s ``container_env_forward:`` list is the *name whitelist* — it
declares WHICH variables cross into the container. This module resolves the
VALUES for those names from the host secret store. Secret values live ONLY in
the sops SSoT or ``~/.env.local``; they are never committed to ``polecat.yaml``.

Parser scope: a deliberately small ``export KEY=VALUE`` / ``KEY=VALUE`` reader.
No shell-out for ``~/.env.local`` (sourcing it would execute arbitrary code).
``sops -d`` is invoked via subprocess — it decrypts the file to stdout without
executing anything from it; the output is then parsed by the same safe parser.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Default host secret store (legacy plaintext). Override via $AOPS_HOST_ENV_FILE.
_DEFAULT_ENV_LOCAL = Path.home() / ".env.local"

# Default sops/age-encrypted SSoT path. Override via $AOPS_SOPS_SECRETS_FILE.
_DEFAULT_SOPS_SECRETS = Path.home() / "dotfiles" / "containers" / "nicwin" / "aops-secrets.env"

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
# — once the operator renames the host var.
#
# GH_TOKEN / GITHUB_TOKEN: both are injected into the container under their
# standard names (used by gh CLI and git respectively), but sourced from the
# AOPS-prefixed host var AOPS_BOT_GH_TOKEN. The container name itself is kept
# as a fallback candidate (see ``resolve_forward_values``), so if the host has
# GH_TOKEN directly it still resolves.
_FORWARD_SOURCE_ALIASES: dict[str, tuple[str, ...]] = {
    "CLAUDE_CODE_OAUTH_TOKEN": ("AOPS_CC_OAUTH_TOKEN",),
    "GH_TOKEN": ("AOPS_BOT_GH_TOKEN",),
    "GITHUB_TOKEN": ("AOPS_BOT_GH_TOKEN",),
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


def _parse_env_text(content: str) -> dict[str, str]:
    """Parse dotenv-format text into {NAME: VALUE}. Last assignment wins."""
    result: dict[str, str] = {}
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


def _load_sops_secrets(sops_file: Path | str | None = None) -> dict[str, str]:
    """Decrypt the sops/age-encrypted SSoT in-memory and return its contents.

    Calls ``sops -d <file>`` to decrypt to stdout; the plaintext output is
    parsed and returned.  No decrypted content is written to disk.

    Returns an empty dict if:
    - the file does not exist (SSoT not yet bootstrapped)
    - ``sops`` is not installed
    - decryption fails (missing key, corrupt file, etc.)

    Never raises — callers fall back to ``~/.env.local``.

    Args:
        sops_file: Override path. Defaults to ``$AOPS_SOPS_SECRETS_FILE`` or
            ``~/dotfiles/containers/nicwin/aops-secrets.env``.

    Returns:
        Dict of decrypted name→value pairs.
    """
    if sops_file is None:
        sops_file = os.environ.get("AOPS_SOPS_SECRETS_FILE") or _DEFAULT_SOPS_SECRETS
    path = Path(sops_file)
    if not path.exists():
        return {}
    try:
        proc = subprocess.run(
            ["sops", "-d", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return _parse_env_text(proc.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {}


def load_host_secrets(
    env_file: Path | str | None = None,
    sops_file: Path | str | None = None,
) -> dict[str, str]:
    """Load host secrets from the sops SSoT and/or ``~/.env.local``.

    Two-tier resolution:

    1. sops/age-encrypted ``aops-secrets.env`` (authoritative when present).
    2. ``~/.env.local`` (legacy fallback; also used during migration for any
       keys not yet added to the encrypted SSoT).

    The sources are merged: values from the sops SSoT win over ``~/.env.local``
    for any key present in both.  Keys present only in ``~/.env.local`` are still
    returned (transition compatibility).

    Returns an empty dict if neither source is available (e.g. GHA runners).
    Never raises on a missing file — callers fall back to the process env.

    Args:
        env_file: Override path for ``~/.env.local``. Defaults to
            ``$AOPS_HOST_ENV_FILE`` or ``~/.env.local``.
        sops_file: Override path for the sops SSoT. Defaults to
            ``$AOPS_SOPS_SECRETS_FILE`` or
            ``~/dotfiles/containers/nicwin/aops-secrets.env``.

    Returns:
        Dict of name→value pairs. sops SSoT wins on conflict.
    """
    if env_file is None:
        env_file = os.environ.get("AOPS_HOST_ENV_FILE") or _DEFAULT_ENV_LOCAL
    path = Path(env_file)

    env_local: dict[str, str] = {}
    if path.exists():
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            env_local = _parse_env_text(content)
        except Exception:
            pass

    sops_secrets = _load_sops_secrets(sops_file)

    # sops SSoT takes precedence; env_local fills any gaps.
    return {**env_local, **sops_secrets}


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
