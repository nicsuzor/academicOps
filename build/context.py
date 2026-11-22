"""Shared data types passed between the orchestrator and client adapters."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Every client the builder can target. build.CLIENT_ADAPTERS holds one adapter
# per entry; tests/test_build.py keeps the two in step.
CLIENTS: tuple[str, ...] = ("claude", "agy", "openclaw")


@dataclass(frozen=True)
class SharedAsset:
    """One shared file or directory under `lib/` injected into a plugin build."""

    src: str  # repo-relative path under lib/
    dst: str  # plugin-relative destination path
    clients: tuple[str, ...] = CLIENTS


@dataclass(frozen=True)
class Plugin:
    """A plugin discovered under plugins/<directory>, with its marketplace identity.

    The mapping from source directory to marketplace name is declared once,
    in build/marketplace.toml — never duplicated in plugin.toml.
    """

    directory: str  # plugins/<directory> — source dir name
    marketplace_name: str  # ships as dist/<marketplace_name>-<client>
    description: str
    category: str
    source_dir: Path  # plugins/<directory>
    clients: tuple[str, ...] = CLIENTS  # the clients this plugin ships for
    shared: tuple[SharedAsset, ...] = ()  # lib/ assets injected at build time


@dataclass
class BuildContext:
    """Everything a client adapter needs to finish packaging one plugin build."""

    plugin: Plugin
    client: str  # "claude" | "agy"
    version: str
    manifests: dict[str, dict[str, Any]]  # template stem -> rendered dict
