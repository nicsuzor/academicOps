#!/usr/bin/env python3
"""
Simple Build script for AcademicOps plugins.
Assembles dist versions of the plugins based on client-specific files.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

# Directories to exclude from copying
EXCLUDES = {
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".venv",
    ".uv-cache",
    ".git",
    ".DS_Store",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def load_axioms(axioms_dir: Path) -> list[dict]:
    """Parse the `trigger: always_on` rule files out of aops/axioms/*.md.

    Axioms carry simple `key: value` frontmatter (no nested YAML needed).
    Only `trigger: always_on` files are universal rules — the other
    axioms/*.md files (RULES.md, HEURISTICS.md, AXIOMS-REVIEW.md) are
    reference docs loaded explicitly elsewhere (by rbg, GHA), not rules that
    should be auto-merged into every session.
    """
    axioms = []
    if not axioms_dir.exists():
        return axioms

    for md_file in sorted(axioms_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue

        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

        if meta.get("trigger") != "always_on":
            continue

        axioms.append(
            {
                "slug": md_file.stem,
                "description": meta.get("description", ""),
                "body": m.group(2).strip(),
                "source_file": md_file.name,
            }
        )

    return axioms


def build_plugin(plugin_name: str, src_dir: Path, dist_root: Path, version: str):
    print(f"Building {plugin_name} (v{version})...")

    for client in ["claude", "antigravity"]:
        if plugin_name == "aops-ts" and client == "antigravity":
            continue

        dist_dir = dist_root / f"{plugin_name}-{client}"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        dist_dir.mkdir(parents=True)


        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDES]

            rel_root = Path(root).relative_to(src_dir)
            dst_root = dist_dir / rel_root
            dst_root.mkdir(parents=True, exist_ok=True)

            for file in files:
                if file in EXCLUDES:
                    continue

                src_file = Path(root) / file

                if file.endswith(".template.json"):
                    stem = file[:-14]

                    with open(src_file) as f:
                        template = json.load(f)

                    data = template.get("__base__", {}).copy()
                    client_data = template.get(client, {})

                    for k, v in client_data.items():
                        if isinstance(v, dict) and k in data and isinstance(data[k], dict):
                            data[k].update(v)
                        else:
                            data[k] = v

                    if stem == plugin_name:
                        data["version"] = version

                    if stem == "mcp" and client == "antigravity":
                        if "mcpServers" in data and "services" in data["mcpServers"]:
                            # Workaround for antigravity-cli#390: agy doesn't resolve ${extensionPath}
                            # and runs MCP servers from the workspace cwd, so relative paths fail.
                            # For GitHub users who don't run `make install-agy`, we must use bash -c
                            # with tilde expansion to the default install location.
                            data["mcpServers"]["services"]["args"] = [
                                "-c",
                                f"~/.gemini/config/plugins/{plugin_name}/scripts/run-mcp.sh",
                            ]
                    elif stem == "hooks" and client == "antigravity":
                        if "hooks" in data:
                            for events in data["hooks"].values():
                                for event in events:
                                    for hook in event.get("hooks", []):
                                        if "command" in hook:
                                            # Remove quotes around the script path because agy execs via argv
                                            cmd = hook["command"]
                                            cmd = cmd.replace(
                                                '"${AGY_PLUGIN_ROOT}/hooks/router.py"',
                                                "hooks/router.py",
                                            )
                                            cmd = cmd.replace(
                                                "${AGY_PLUGIN_ROOT}/hooks/router.py",
                                                "hooks/router.py",
                                            )
                                            hook["command"] = cmd

                    # determine destination
                    if stem == plugin_name:
                        if client == "claude":
                            dst_file = dist_dir / ".claude-plugin" / "plugin.json"
                        else:
                            dst_file = dist_dir / "plugin.json"
                    elif stem == "hooks":
                        if client == "claude":
                            # Claude Code auto-discovers hooks ONLY at
                            # <plugin_root>/hooks/hooks.json — a root-level
                            # hooks.json is silently never read. (Confirmed via
                            # the claude binary's own embedded strings: "The
                            # standard hooks/hooks.json is loaded
                            # automatically...")
                            dst_file = dist_dir / "hooks" / "hooks.json"
                        else:
                            # agy's own convention is root-level hooks.json
                            # (confirmed via its plugin-structure docs).
                            dst_file = dist_dir / "hooks.json"
                    elif stem == "mcp":
                        if client == "claude":
                            dst_file = dist_dir / ".mcp.json"
                        else:
                            dst_file = dist_dir / "mcp_config.json"
                    else:
                        dst_file = dist_dir / rel_root / f"{stem}.json"

                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(dst_file, "w") as f:
                        json.dump(data, f, indent=2)
                    continue

                # Skip the old specific files that might still be lingering
                if any(
                    file.endswith(suffix)
                    for suffix in [
                        ".claude.json",
                        ".agy.json",
                        ".claude-plugin.json",
                        ".antigravity-plugin.json",
                    ]
                ):
                    continue
                    
                # Handle commands to skills for agy. Only antigravity needs the
                # commands->skills conversion; claude falls through to the
                # generic copy below, which preserves the commands/ subdir so
                # Claude Code auto-discovers the slash commands at
                # <plugin_root>/commands/*.md.
                if (rel_root.parts and rel_root.parts[0] == "commands"
                        and file.endswith(".md") and client == "antigravity"):
                    skill_name = file[:-3]
                    dst_file = dist_dir / "skills" / f"cmd-{skill_name}" / "SKILL.md"
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    content = src_file.read_text(encoding="utf-8")
                    content = re.sub(r"(?m)^type:\s*command\s*$", "type: skill", content)
                    dst_file.write_text(content, encoding="utf-8")
                    continue

                dst_file = dst_root / file
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)

        # Wire always-on axioms into each client's native rule mechanism.
        # axioms/*.md is already copied verbatim above (part of the generic
        # file walk) but that's inert content — neither client treats an
        # arbitrary "axioms/" folder as anything special. This makes the
        # `trigger: always_on` axioms actually take effect:
        #   - agy: plugins/<name>/rules/*.md is the canonical location whose
        #     contents get merged into the active rule set (confirmed from
        #     the agy binary's embedded assets/external/skills/
        #     agy-customizations/docs/plugins.md).
        #   - Claude Code: no equivalent plugin-level "rules" folder exists,
        #     so we ship a JSONL data file (axioms.jsonl) as the durable,
        #     version-controlled transport. Claude Code reads autoMode from
        #     ~/.claude/settings.json (not from an installed plugin's
        #     manifest, which it doesn't recognize), so `make install-dev`
        #     runs scripts/install_automode.py to read axioms.jsonl and merge
        #     the rules into settings.json separately.
        axioms_dir = src_dir / "axioms"
        axioms = load_axioms(axioms_dir)
        if axioms:
            if client == "antigravity":
                rules_dir = dist_dir / "rules"
                rules_dir.mkdir(parents=True, exist_ok=True)
                for axiom in axioms:
                    shutil.copy2(
                        axioms_dir / axiom["source_file"], rules_dir / axiom["source_file"]
                    )
            elif client == "claude":
                jsonl_path = dist_dir / "axioms.jsonl"
                with open(jsonl_path, "w") as f:
                    for axiom in axioms:
                        f.write(json.dumps(axiom) + "\n")

        # Cleanup any empty directories that might have been left over
        for dirpath, _dirnames, _filenames in os.walk(dist_dir, topdown=False):
            if not os.listdir(dirpath):
                os.rmdir(dirpath)

        import tarfile

        archive_name = f"{dist_dir.name}.tar.gz"
        archive_path = dist_root / archive_name

        with tarfile.open(archive_path, "w:gz") as tar:
            if client == "claude":
                # Claude expects the directory itself inside the archive
                tar.add(dist_dir, arcname=dist_dir.name)
            else:
                # Antigravity expects contents at the root of the archive
                tar.add(dist_dir, arcname=".")

        print(f"  ✓ Built {dist_dir.name} and packaged into {archive_name}")


def generate_local_marketplace(dist_root: Path):
    """Generate the local marketplace JSON so claude can install from dist/.

    Only lists plugins whose dist/<name>-claude dir was actually built —
    a plugin whose source dir doesn't exist is skipped by build_plugin(),
    so listing it here would leave a dangling `source` entry.
    """

    marketplace_dir = dist_root / ".claude-plugin"
    marketplace_dir.mkdir(exist_ok=True)

    candidates = [
        ("aops-core", "aops-core-claude"),
        ("aops", "aops-claude"),
        ("aops-tools", "aops-tools-claude"),
        ("aops-ts", "aops-ts-claude"),
    ]
    plugins = [
        {"name": name, "source": f"./{dirname}"}
        for name, dirname in candidates
        if (dist_root / dirname).exists()
    ]

    marketplace = {
        "name": "aops",
        "description": "Local dev marketplace",
        "owner": {"name": "Local Dev"},
        "plugins": plugins,
    }
    with open(marketplace_dir / "marketplace.json", "w") as f:
        json.dump(marketplace, f, indent=2)
    print("✓ Generated local marketplace.json")


def get_project_version(project_root: Path) -> str:
    # Read version from pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        return "0.1.0"
    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', content)
    if match:
        version = match.group(1)
    else:
        version = "0.1.0"

    # Try to append git metadata
    try:
        sha_res = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if sha_res.returncode == 0:
            sha = sha_res.stdout.strip()
            if sha:
                dirty_res = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                is_dirty = dirty_res.returncode == 0 and bool(dirty_res.stdout.strip())
                meta = f"g{sha}{'.dirty' if is_dirty else ''}"
                if is_dirty and "-" not in version:
                    parts = version.split(".")
                    if len(parts) == 3 and all(p.isdigit() for p in parts):
                        major, minor, patch = parts
                        version = f"{major}.{minor}.{int(patch) + 1}-dev.0"
                version = f"{version}+{meta}"
    except Exception:
        pass
    return version


def main():
    parser = argparse.ArgumentParser(description="Simple build script for plugins")
    parser.add_argument(
        "--plugins",
        nargs="+",
        default=["aops-core", "aops", "aops-tools", "aops-ts"],
        help="Plugins to build",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit",
    )
    parser.add_argument(
        "--set-version",
        type=str,
        default=None,
        help="Override the version to build with",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    if args.version:
        print(get_project_version(project_root))
        return

    if args.set_version:
        version = args.set_version
    else:
        version = get_project_version(project_root)

    dist_root = project_root / "dist"
    dist_root.mkdir(exist_ok=True)

    for plugin in args.plugins:
        src_dir = project_root / plugin
        if not src_dir.exists():
            print(f"Warning: Plugin source {src_dir} does not exist. Skipping.")
            continue
        build_plugin(plugin, src_dir, dist_root, version)

    generate_local_marketplace(dist_root)


if __name__ == "__main__":
    main()
