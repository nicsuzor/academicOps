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


def apply_env_mappings(
    env: dict[str, str],
    config_path: Path | str | None = None,
    source_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Apply agent-env-map.conf entries to a subprocess environment dict.

    For TARGET=SOURCE lines: if SOURCE exists in source_env, set env[TARGET].
    For TARGET:=VALUE lines: set env[TARGET] to VALUE (empty string clears it).

    Args:
        env: The subprocess environment dict to modify (mutated in place).
        config_path: Path to config file. Defaults to aops-core/agent-env-map.conf.
        source_env: Environment to read SOURCE values from. Defaults to os.environ.

    Returns:
        The modified env dict (same object, for chaining).
    """
    if source_env is None:
        source_env = os.environ

    for entry in load_env_entries(config_path):
        if entry.is_literal:
            env[entry.target] = entry.value
        else:
            value = source_env.get(entry.value)
            if value is not None:
                env[entry.target] = value

    return env


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
    if source_env is None:
        source_env = os.environ

    result = {}
    for entry in load_env_entries(config_path):
        if entry.is_literal:
            result[entry.target] = entry.value
        else:
            value = source_env.get(entry.value)
            if value is not None:
                result[entry.target] = value

    return result
