"""Agent environment variable mapping for headless sessions.

Reads agent-env-map.conf and applies mappings to subprocess environments.
This is the shared library used by:
- tests/conftest.py (headless test harness)
- hooks/session_env_setup.py (Claude CLAUDE_ENV_FILE persistence)

Two config line formats:
    TARGET=SOURCE      — set TARGET to the value of $SOURCE from parent env.
                         Skipped if SOURCE is not set.
    TARGET:=VALUE      — set TARGET to the literal VALUE.
                         Use empty VALUE (TARGET:=) to unset/clear a variable.
    # comment          — ignored
    (blank lines)      — ignored
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Default config file location (relative to aops-core/)
_DEFAULT_CONFIG = Path(__file__).parent.parent / "agent-env-map.conf"


@dataclass(frozen=True)
class EnvEntry:
    """A single environment variable mapping entry.

    Attributes:
        target: The env var name to set in the subprocess.
        value: For mappings (is_literal=False), the SOURCE env var name to read.
               For literals (is_literal=True), the literal value to set.
        is_literal: If True, value is a literal string. If False, value is
                    the name of a SOURCE env var to look up.
    """

    target: str
    value: str
    is_literal: bool = False


def load_env_entries(
    config_path: Path | str | None = None,
) -> list[EnvEntry]:
    """Load all entries from config file.

    Args:
        config_path: Path to config file. Defaults to aops-core/agent-env-map.conf.

    Returns:
        List of EnvEntry objects.
    """
    path = Path(config_path) if config_path else _DEFAULT_CONFIG
    if not path.exists():
        return []

    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Check for literal assignment first (TARGET:=VALUE)
        if ":=" in line:
            target, value = line.split(":=", 1)
            target = target.strip()
            if target:
                entries.append(EnvEntry(target=target, value=value, is_literal=True))
            continue

        # Env-to-env mapping (TARGET=SOURCE)
        if "=" in line:
            target, source = line.split("=", 1)
            target = target.strip()
            source = source.strip()
            if target and source:
                entries.append(EnvEntry(target=target, value=source, is_literal=False))

    return entries


def load_env_mappings(
    config_path: Path | str | None = None,
) -> list[tuple[str, str]]:
    """Load TARGET=SOURCE mappings from config file.

    Legacy convenience function — returns only env-to-env mappings (not literals).

    Args:
        config_path: Path to config file. Defaults to aops-core/agent-env-map.conf.

    Returns:
        List of (target_var, source_var) tuples.
    """
    return [(e.target, e.value) for e in load_env_entries(config_path) if not e.is_literal]


def _resolve_entry(
    entry: EnvEntry,
    source_env: dict[str, str],
) -> tuple[str, str] | None:
    """Resolve one config entry against a source env.

    For literal entries: returns (target, value) verbatim — empty literal
    preserved (this is the deliberate `:=` isolation idiom for vars like
    ``SSH_AUTH_SOCK:=``).

    For mapping entries (TARGET=SOURCE): returns (target, source_env[SOURCE])
    only if the source value is set AND non-empty. Empty-string sources are
    treated identically to unset, closing the credential-leak class flagged
    in ``test_shell_lines_skip_when_source_unset``.
    """
    if entry.is_literal:
        return (entry.target, entry.value)
    value = source_env.get(entry.value)
    if value:
        return (entry.target, value)
    return None


def apply_env_mappings(
    env: dict[str, str],
    config_path: Path | str | None = None,
    source_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Apply agent-env-map.conf entries to a subprocess environment dict.

    For TARGET=SOURCE lines: if SOURCE is set and non-empty in source_env,
        set env[TARGET]. Empty-string sources are skipped (treated as unset).
    For TARGET:=VALUE lines: set env[TARGET] to VALUE (empty literal allowed —
        this is the SSH_AUTH_SOCK="" isolation idiom).

    Args:
        env: The subprocess environment dict to modify (mutated in place).
        config_path: Path to config file. Defaults to aops-core/agent-env-map.conf.
        source_env: Environment to read SOURCE values from. Defaults to os.environ.

    Returns:
        The modified env dict (same object, for chaining).
    """
    if source_env is None:
        source_env = dict(os.environ)

    for entry in load_env_entries(config_path):
        resolved = _resolve_entry(entry, source_env)
        if resolved is not None:
            env[resolved[0]] = resolved[1]

    return env


def get_container_env_forwards(
    source_env: dict[str, str] | None = None,
    config_path: Path | str | None = None,
) -> dict[str, str]:
    """Return TARGET → VALUE pairs to forward into a polecat/crew container.

    The conf-driven counterpart to ``apply_env_mappings``: rather than mutating
    a subprocess env, this returns the dict the caller will emit as
    ``-e KEY=VALUE`` flags on a ``docker run`` command.

    Empty-string source values are skipped for TARGET=SOURCE rules — preventing
    the empty-credential leak (e.g. ``ANTHROPIC_API_KEY=""`` from the host
    shell) that headless Claude/Gemini would otherwise treat as a deliberate
    empty key and 401 on. Literals (``TARGET:=VALUE``) are emitted verbatim,
    preserving the ``SSH_AUTH_SOCK:=`` isolation idiom.

    Args:
        source_env: Environment to read SOURCE values from. Defaults to os.environ.
        config_path: Path to config file. Defaults to aops-core/agent-env-map.conf.

    Returns:
        Dict of {TARGET: VALUE} pairs to forward into the container.
    """
    if source_env is None:
        source_env = dict(os.environ)

    result: dict[str, str] = {}
    for entry in load_env_entries(config_path):
        resolved = _resolve_entry(entry, source_env)
        if resolved is not None:
            result[resolved[0]] = resolved[1]
    return result


def get_env_mapping_persist_dict(
    source_env: dict[str, str] | None = None,
    config_path: Path | str | None = None,
) -> dict[str, str]:
    """Get the dict of env vars to persist (for hook CLAUDE_ENV_FILE writes).

    For TARGET=SOURCE: included only if SOURCE has a value in the environment.
    For TARGET:=VALUE: always included.

    Args:
        source_env: Environment to read SOURCE values from. Defaults to os.environ.
        config_path: Path to config file.

    Returns:
        Dict of {TARGET: value} to persist.
    """
    return apply_env_mappings(env={}, config_path=config_path, source_env=source_env)


def get_env_mapping_shell_lines(
    config_path: Path | str | None = None,
) -> list[str]:
    """Return shell `export` lines for agent-env-map.conf entries.

    Unlike `get_env_mapping_persist_dict()`, these lines defer SOURCE
    resolution to shell-evaluation time. This matters when the SOURCE
    var is set by the user's shell profile (e.g., AOPS_BOT_GH_TOKEN
    from ~/.zshenv) and is therefore visible to the post-snapshot
    shell but NOT to the Python hook that writes CLAUDE_ENV_FILE
    (which inherits the launchd env, not the shell env).

    Literals (TARGET:=VALUE) are excluded — they are already written verbatim
    by `get_env_mapping_persist_dict()` / `set_persistent_env()` at hook time,
    so there is no need to defer them.

    Output format (env-to-env mappings only):
      - Mapping (TARGET=SOURCE):  [ -n "${SOURCE:+x}" ] && export TARGET="${SOURCE}"
        (Conditional: only set TARGET if SOURCE is set AND non-empty —
        empty-string sources are skipped to avoid leaking empty credentials.)

    Returns:
        List of shell-syntax lines suitable for CLAUDE_ENV_FILE.
    """
    lines: list[str] = []
    for entry in load_env_entries(config_path):
        if entry.is_literal:
            # Already handled by get_env_mapping_persist_dict(); skip.
            continue
        # Defer SOURCE resolution to shell time. ${SOURCE:+x} is "x" iff
        # SOURCE is defined AND non-empty. The colon is load-bearing — it
        # mirrors the truthiness check in apply_env_mappings and closes the
        # empty-credential regression class documented at
        # test_shell_lines_skip_when_source_unset_or_empty.
        lines.append(
            f'[ -n "${{{entry.value}:+x}}" ] && export {entry.target}="${{{entry.value}}}"'
        )
    return lines
