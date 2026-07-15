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
    """Point known_marketplaces.json + marketplace.json at the single dist clone.

    Both CLIs install from one shallow clone/copy of the dist tree (see
    comment above the git clone in the Dockerfile); this rewrites the
    marketplace metadata to reference the permanent plugin cache location
    instead of the ephemeral /tmp/aops-dist dir that no longer exists
    post-install (rm -rf'd at the end of the plugin-install RUN step).
    """
    plugin_cache = pathlib.Path(f"/home/worker/.claude/plugins/cache/{marketplace_name}")
    known = json.loads(KNOWN_MARKETPLACES.read_text())
    known[marketplace_name]["source"]["path"] = str(plugin_cache)
    known[marketplace_name]["installLocation"] = str(plugin_cache)
    KNOWN_MARKETPLACES.write_text(json.dumps(known, indent=2))

    marketplace_path = plugin_cache / ".claude-plugin" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text())
    for plugin in marketplace["plugins"]:
        plugin_dir = plugin_cache / plugin["name"]
        if plugin_dir.is_dir():
            version_dir = next((e.name for e in plugin_dir.iterdir() if e.is_dir()), "")
            plugin["source"] = f"./{plugin['name']}/{version_dir}"
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
