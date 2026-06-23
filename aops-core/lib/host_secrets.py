"""Forwarded secret-NAME resolution for polecat launch (env-only).

The polecat wrapper forwards a whitelist of secret VALUES (e.g. the Claude
OAuth token, the bot GitHub token) into the container at launch. This module
resolves those VALUES **from the process environment only**.

AOPS has NO knowledge of how secrets are stored. It does not read ``sops``,
``~/.env.local``, dotfiles, or any other file. Populating the process
environment with the required secrets — via the operator's own dotfiles, a
secret manager, ``sops``, CI secret injection, or anything else — is the
OPERATOR's responsibility and is explicitly OUT OF SCOPE for this module.

What this module does:

  - ``polecat.yaml``'s ``container_env_forward:`` list is the *name whitelist* —
    it declares WHICH variables cross into the container. This module resolves
    the VALUE for each declared name from the process env.

  - Source-name indirection (``_FORWARD_SOURCE_ALIASES``): a forwarded secret
    crosses into the container under the name the agent runtime expects (e.g.
    ``CLAUDE_CODE_OAUTH_TOKEN``, what headless ``claude`` reads) but is sourced
    from a DIFFERENT process-env variable (e.g. ``AOPS_CC_OAUTH_TOKEN``). This
    is a pure NAME map: candidate source names are tried in order, all WITHIN
    the process env. It is renaming, NOT a file fallback.

  - Fail-loud: when a caller declares a name REQUIRED and it resolves to
    absent/empty in the process env, ``resolve_forward_values`` raises
    :class:`MissingForwardSecretError` naming the missing variable(s). Required
    secrets are never silently skipped.
"""

from __future__ import annotations

import os

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
# This is a NAME map only: every candidate is looked up in the process env.
# There is NO file fallback anywhere — the operator is responsible for putting
# the value into the environment under one of the candidate names.
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


class MissingForwardSecretError(RuntimeError):
    """Raised when a REQUIRED forwarded secret is absent/empty in the env.

    Carries the list of missing CONTAINER names so callers can surface them.
    """

    def __init__(self, missing: list[str]) -> None:
        self.missing = list(missing)
        joined = ", ".join(self.missing)
        super().__init__(
            "Required forwarded secret(s) absent or empty in the process "
            f"environment: {joined}. AOPS reads secrets from the environment "
            "only — export the variable(s) (or a configured source alias) "
            "before launch. Populating the environment is the operator's "
            "responsibility."
        )


def resolve_forward_values(
    names: list[str],
    source_env: dict[str, str] | None = None,
    required: list[str] | set[str] | None = None,
) -> dict[str, str]:
    """Resolve VALUES for a whitelist of variable NAMES from the process env.

    Each name is the CONTAINER variable name (the name the agent runtime reads).
    Its value may be sourced from a DIFFERENT process-env variable via
    ``_FORWARD_SOURCE_ALIASES`` (the source→container-name indirection that
    closes the OAuth-token leak — see that constant). Candidate source names are
    tried in order, ALL within the process env: the configured alias source(s)
    first, then the container name itself as the transitional fallback.

    Resolution reads the PROCESS ENV ONLY (``source_env``, default
    ``os.environ``). There is no file reading of any kind — populating the env
    is the operator's responsibility (sops, ~/.env.local, etc. are out of
    scope).

    Fail-loud: for each name in ``required`` that resolves to absent/empty,
    collect it and raise :class:`MissingForwardSecretError` naming all of them.
    Required secrets are NEVER silently skipped. Names NOT in ``required`` that
    resolve empty are simply omitted from the result (forward-if-present
    semantics for the bulk whitelist).

    Args:
        names: Container variable names declared in ``polecat.yaml``
            ``container_env_forward``.
        source_env: Process env to read from. Defaults to ``os.environ``.
        required: Container names that MUST resolve to a non-empty value. Any
            that do not cause a :class:`MissingForwardSecretError`. ``None``
            (the default) means no name is required.

    Returns:
        Dict of {CONTAINER_NAME: VALUE} for names that resolved to a non-empty
        value (keyed by the container name, regardless of which source supplied
        the value).

    Raises:
        MissingForwardSecretError: if any required name resolves empty/absent.
    """
    if source_env is None:
        source_env = os.environ
    required_set = set(required or ())

    resolved: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        # Alias source(s) first, then the container name itself as a fallback.
        # Every candidate is looked up in the process env only.
        candidates = (*_FORWARD_SOURCE_ALIASES.get(name, ()), name)
        value = ""
        for src in candidates:
            candidate_value = source_env.get(src)
            if candidate_value:
                value = candidate_value
                break
        if value:
            resolved[name] = value
        elif name in required_set:
            missing.append(name)

    if missing:
        raise MissingForwardSecretError(missing)
    return resolved
