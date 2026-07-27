#!/usr/bin/env python3
"""Post-install fixups for Gemini/Antigravity config baked into the aops-crew image.

Extracted from inline `python3 -c "..."` blocks in the Dockerfile so the logic
is readable, syntax-highlighted, and diffable outside a RUN instruction.
Invoked as: python3 docker_gemini_fixups.py <subcommand>
"""

import argparse
import glob
import json
import pathlib

GEMINI_HOME = pathlib.Path("/home/worker/.gemini")
KNOWN_MARKETPLACES = pathlib.Path("/home/worker/.claude/plugins/known_marketplaces.json")


def fixup_mcp_config_paths() -> None:
    """Resolve ${extensionPath} / ${CLAUDE_PLUGIN_ROOT} placeholders in mcp_config.json.

    `gemini extensions install` and `agy plugin install` ship mcp_config.json
    files with unresolved template placeholders; replace them with the actual
    on-disk directory of each config file.
    """
    for path_str in glob.glob(str(GEMINI_HOME / "**" / "mcp_config.json"), recursive=True):
        path = pathlib.Path(path_str)
        data = path.read_text()
        json.loads(data)  # fail loudly if a shipped mcp_config.json isn't valid JSON
        plugin_dir = str(path.parent)
        resolved = data.replace("${extensionPath}", plugin_dir).replace(
            "${CLAUDE_PLUGIN_ROOT}", plugin_dir
        )
        if resolved != data:
            json.loads(resolved)  # confirm the replacement didn't corrupt the JSON
            path.write_text(resolved)


def fixup_local_marketplace_name(marketplace_root: str, marketplace_name: str) -> None:
    """Rename a local-dev marketplace.json's `name` field before installing it.

    `scripts/build.py generate_local_marketplace()` deliberately names the
    dist/ marketplace `aops` (not `academicOps`) so a HOST `make install-dev`
    lands in its own namespace, distinct from a real `academicOps` install on
    the same machine (see build.py for the full rationale). Inside a
    `make build-docker` (AOPS_DIST_SOURCE=local) image there is no such
    coexistence risk — the container only ever has one aops install — so we
    rewrite the copied marketplace.json's name to `academicOps` here, making
    the local-build image install under the SAME key
    (`aops@academicOps`) that production/CI builds use. That's what keeps
    `polecat/cli.py`'s staged `pluginConfigs` (hardcoded to `aops@academicOps`)
    matching the installed plugin key regardless of build source.
    """
    marketplace_path = pathlib.Path(marketplace_root) / ".claude-plugin" / "marketplace.json"
    data = json.loads(marketplace_path.read_text())
    data["name"] = marketplace_name
    marketplace_path.write_text(json.dumps(data, indent=2) + "\n")


def fixup_marketplace_cache(marketplace_name: str) -> None:
    """Point known_marketplaces.json + marketplace.json at the durable marketplaces/ dir.

    The marketplace manifest MUST live under ~/.claude/plugins/marketplaces/<name>/,
    NOT under ~/.claude/plugins/cache/<name>/. The cache/ tree is managed by Claude
    Code's plugin in-use sweeper (it stamps .last_inuse_sweep on startup): the sweep
    walks cache/<marketplace>/ treating every child as a <plugin>/<version> install
    and prunes anything not registered as an in-use version in installed_plugins.json.
    A marketplace manifest parked at cache/<name>/.claude-plugin/ is not such a
    version, so the FIRST session's sweep deletes it — and every subsequent session
    fails to load the marketplace with `cache-miss` (the plugins show
    "✘ failed to load"). marketplaces/ is outside the swept tree; that's where
    github-source marketplaces (e.g. claude-plugins-official) durably live, and it
    survives the sweep.

    Plugin *payloads* still live in cache/<name>/<plugin>/<version>/ — that's what
    installed_plugins.json points at and how already-installed plugins load, so only
    the manifest moves. Plugin `source` fields are rewritten to ABSOLUTE cache paths
    (a relative `./<plugin>/<version>` would now resolve under marketplaces/, where
    no payload exists) so a re-install/update can still find the payloads.

    Ordering contract: the Dockerfile copies the manifest to
    marketplaces/<name>/.claude-plugin/marketplace.json BEFORE invoking this, and
    the ephemeral /tmp/aops-dist source is rm -rf'd first, so this is the step that
    gives the marketplace its permanent, sweep-proof home.
    """
    plugin_cache = pathlib.Path(f"/home/worker/.claude/plugins/cache/{marketplace_name}")
    marketplace_dir = pathlib.Path(f"/home/worker/.claude/plugins/marketplaces/{marketplace_name}")

    known = json.loads(KNOWN_MARKETPLACES.read_text())
    known[marketplace_name]["source"] = {"source": "directory", "path": str(marketplace_dir)}
    known[marketplace_name]["installLocation"] = str(marketplace_dir)
    KNOWN_MARKETPLACES.write_text(json.dumps(known, indent=2))

    marketplace_path = marketplace_dir / ".claude-plugin" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text())
    for plugin in marketplace["plugins"]:
        plugin_dir = plugin_cache / plugin["name"]
        if plugin_dir.is_dir():
            version_dir = next(
                (e.name for e in plugin_dir.iterdir() if e.is_dir() and not e.name.startswith(".")),
                "",
            )
            plugin["source"] = str(plugin_dir / version_dir)
    marketplace_path.write_text(json.dumps(marketplace, indent=2))


COMMANDS = {
    "fixup-mcp-config-paths": fixup_mcp_config_paths,
    "fixup-local-marketplace-name": fixup_local_marketplace_name,
    "fixup-marketplace-cache": fixup_marketplace_cache,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument(
        "--marketplace-name",
        default="academicOps",
        help="Marketplace name to fix up (fixup-marketplace-cache / fixup-local-marketplace-name)",
    )
    parser.add_argument(
        "--marketplace-root",
        help="Directory containing .claude-plugin/marketplace.json "
        "(fixup-local-marketplace-name only)",
    )
    args = parser.parse_args()
    if args.command == "fixup-marketplace-cache":
        fixup_marketplace_cache(args.marketplace_name)
    elif args.command == "fixup-local-marketplace-name":
        if not args.marketplace_root:
            parser.error("fixup-local-marketplace-name requires --marketplace-root")
        fixup_local_marketplace_name(args.marketplace_root, args.marketplace_name)
    else:
        COMMANDS[args.command]()


if __name__ == "__main__":
    main()
