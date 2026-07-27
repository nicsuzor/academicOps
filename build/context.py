"""Shared data types passed between the orchestrator and client adapters."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Plugin:
    """A plugin discovered under plugins/<directory>, with its marketplace identity.

    The mapping from source directory to marketplace name is declared once,
    in build/marketplace.toml — never duplicated in plugin.toml.
    """

    directory: str  # plugins/<directory> — source dir name
    marketplace_name: str  # ships as dist/<marketplace_name>-<client>
    source_dir: Path  # plugins/<directory>


@dataclass
class BuildContext:
    """Everything a client adapter needs to finish packaging one plugin build."""

    plugin: Plugin
    client: str  # "claude" | "agy"
    version: str
    manifests: dict[str, dict[str, Any]]  # template stem -> rendered dict
