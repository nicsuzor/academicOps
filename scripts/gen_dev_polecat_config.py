#!/usr/bin/env -S uv run python
"""
Generate a dev-only polecat.yaml that mounts this checkout's editable plugin
source (hooks/, lib/, skills/, commands/, agents/, scripts/, .agents/,
.claude-plugin/) live into the `aops-crew:dev` image (see `make
build-docker-dev`), for BOTH the claude and antigravity CLIs. Never touches
the real $AOPS_SESSIONS/polecat.yaml or the `:latest` image.

See tests/harness/README.md § "Dev-loop" for how this fits into the wider
edit -> observe loop (scripts/dev-crew.sh).
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

AOPS_ROOT = Path(__file__).resolve().parent.parent

# Immediate subdirs that constitute EDITABLE plugin source. Anything else
# (generated artifacts: .venv, .uv-cache, tests/, __pycache__, .git, plus
# top-level files like pyproject.toml/uv.lock/plugin.json/BUILD.md) is
# deliberately left out of this list, so it's simply never considered.
EDITABLE_SUBDIRS = [
    "hooks",
    "lib",
    "skills",
    "commands",
    "agents",
    "scripts",
    ".agents",
    ".claude-plugin",
]

# (dist dir name, plugin name in marketplace.json, container dest builder)
CLAUDE_PLUGINS = [
    ("aops-claude", "aops-core"),
    ("aops-tools-claude", "aops-tools"),
    ("aops-pkb-claude", "aops-pkb"),
    ("aops-extras-claude", "aops-extras"),
]
ANTIGRAVITY_PLUGINS = [
    ("aops-antigravity", "aops-core"),
    ("aops-tools-antigravity", "aops-tools"),
    ("aops-pkb-antigravity", "aops-pkb"),
    ("aops-extras-antigravity", "aops-extras"),
]

CLAUDE_CACHE_ROOT = "/home/worker/.claude/plugins/cache/academicOps"
# NOT ~/.gemini/antigravity-cli/plugins/ (that's `agy plugin install`'s
# COPY SOURCE, baked in once at image-build time — the Dockerfile installs
# from it but agy never re-reads it after). The path agy's hook router
# actually executes from at runtime, every invocation, is this one —
# confirmed live by bind-mounting the wrong root, watching a router.py fix
# have zero effect on a running container, then manually patching THIS path
# instead and observing it take effect immediately (task_499355a9).
AGY_PLUGIN_ROOT = "/home/worker/.gemini/config/plugins"


def read_plugin_versions(aops_root: Path) -> dict[str, str]:
    """Read each plugin's current version from .claude-plugin/marketplace.json.

    Read fresh every run — the version changes on every build and must never
    be hardcoded (it's baked into the Claude cache path: cache/academicOps/
    <plugin-name>/<version>/).
    """
    marketplace_path = aops_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        print(
            f"error: {marketplace_path} not found — run `make build-dev` first "
            "(it generates the root marketplace.json).",
            file=sys.stderr,
        )
        sys.exit(1)
    data = json.loads(marketplace_path.read_text())
    versions = {}
    for plugin in data["plugins"]:  # required field — fail fast if marketplace.json is malformed
        versions[plugin["name"]] = plugin["version"]
    return versions


def editable_mounts(dist_dir: Path, container_dest: str) -> list[dict]:
    """Bind-mount entries for the editable subdirs actually present in dist_dir."""
    mounts = []
    for sub in EDITABLE_SUBDIRS:
        src = dist_dir / sub
        if src.is_dir():
            mounts.append(
                {
                    "host": str(src),
                    "container": f"{container_dest}/{sub}",
                    "mode": "ro",
                }
            )
    return mounts


def build_config(aops_root: Path, polecat_home: str) -> dict:
    versions = read_plugin_versions(aops_root)
    dist_root = aops_root / "dist"

    mounts: list[dict] = []

    for dist_name, plugin_name in CLAUDE_PLUGINS:
        version = versions.get(plugin_name)
        if not version:
            print(
                f"warning: no version found for {plugin_name!r} — skipping claude mounts",
                file=sys.stderr,
            )
            continue
        dist_dir = dist_root / dist_name
        if not dist_dir.is_dir():
            print(
                f"warning: {dist_dir} not found — skipping (run `make build-dev`)", file=sys.stderr
            )
            continue
        container_dest = f"{CLAUDE_CACHE_ROOT}/{plugin_name}/{version}"
        mounts.extend(editable_mounts(dist_dir, container_dest))

    for dist_name, plugin_name in ANTIGRAVITY_PLUGINS:
        dist_dir = dist_root / dist_name
        if not dist_dir.is_dir():
            print(
                f"warning: {dist_dir} not found — skipping (run `make build-dev`)", file=sys.stderr
            )
            continue
        container_dest = f"{AGY_PLUGIN_ROOT}/{plugin_name}"
        mounts.extend(editable_mounts(dist_dir, container_dest))

    return {
        "polecat_home": polecat_home,
        # Required block — aops-core/lib/polecat_config.py hard-fails without
        # every one of these keys (A14: no builtin defaults, no guessing).
        "session_defaults": {
            "hooks_enabled": True,
            "claude_model": "sonnet",
            "gemini_model": "gemini-3.1-pro-preview",
            "antigravity_model": "agy",
            "debug": False,
            "gates": {
                "handover": "warn",
                "qa": "warn",
                "rbg": "warn",
                "hydration": "off",
                "ida": "warn",
                "rbg_review": "warn",
                "rbg_threshold": 50,
            },
        },
        "crew_defaults": {},
        "run_defaults": {},
        "docker": {"image": "ghcr.io/nicsuzor/aops-crew:dev"},
        "projects": {
            "aops-dev": {
                "repo": "academicOps",
                "default_branch": "dev",
                "aliases": ["aopsdev"],
                "sessions_access": True,
                "mounts": mounts,
            }
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate the dev-only polecat.yaml for the aops-crew:dev live-editing loop."
    )
    parser.add_argument(
        "--out",
        default="~/.polecat-dev/polecat.yaml",
        help="Output path for the generated polecat.yaml (default: ~/.polecat-dev/polecat.yaml)",
    )
    parser.add_argument(
        "--polecat-home",
        default="~/.polecat-dev",
        help="polecat_home value written into the config (default: ~/.polecat-dev)",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    config = build_config(AOPS_ROOT, args.polecat_home)

    header = (
        "# GENERATED — do not hand-edit, re-run scripts/gen_dev_polecat_config.py\n"
        "#\n"
        "# Dev-only polecat.yaml for live-editing academicOps plugin source against\n"
        "# both the claude and antigravity CLIs inside the aops-crew:dev image. See\n"
        '# tests/harness/README.md § "Dev-loop" for the full workflow. This is a\n'
        "# SEPARATE profile from the real $AOPS_SESSIONS/polecat.yaml and never\n"
        "# touches it.\n"
    )
    with open(out_path, "w") as f:
        f.write(header)
        yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)

    n_mounts = len(config["projects"]["aops-dev"]["mounts"])
    print(f"✓ Wrote {out_path} ({n_mounts} mounts)")


if __name__ == "__main__":
    main()
