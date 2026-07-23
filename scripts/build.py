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

# Cowork-only content markers. Skill/command sources wrap Cowork-specific
# instructions in <!-- cowork:only --> ... <!-- /cowork:only -->. The cowork
# dist (generate_cowork_dist) keeps the content with the markers stripped;
# the claude/antigravity builds drop both the markers AND the content.
# (Restored 2026-07-16 — the old build_aops_core carried this and it was lost
# in the generic-builder rewrite, which shipped the blocks verbatim everywhere.)
_COWORK_OPEN = "<!-- cowork:only -->"
_COWORK_CLOSE = "<!-- /cowork:only -->"
_COWORK_BLOCK_RE = re.compile(
    r"\n*[ \t]*"
    + re.escape(_COWORK_OPEN)
    + r"[ \t]*\n(.*?)\n*[ \t]*"
    + re.escape(_COWORK_CLOSE)
    + r"[ \t]*\n*",
    re.DOTALL,
)


def process_cowork_markers(text: str, keep: bool) -> str:
    """Apply cowork-only marker handling.

    keep=True (cowork dist): replace each block with its content, markers
    stripped, padded by one blank line so neighbouring sections stay separated.
    keep=False (claude/antigravity): remove the markers and the content,
    leaving a single blank line.
    """
    if keep:
        return _COWORK_BLOCK_RE.sub(lambda m: "\n\n" + m.group(1).strip() + "\n\n", text)
    return _COWORK_BLOCK_RE.sub("\n\n", text)


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
                    content = process_cowork_markers(content, keep=False)
                    dst_file.write_text(content, encoding="utf-8")
                    continue

                dst_file = dst_root / file
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                # Strip cowork-only blocks from every shipped markdown file —
                # the cowork dist re-applies the kept content from source
                # (see generate_cowork_dist).
                if file.endswith(".md"):
                    text = src_file.read_text(encoding="utf-8")
                    if _COWORK_OPEN in text:
                        dst_file.write_text(
                            process_cowork_markers(text, keep=False), encoding="utf-8"
                        )
                        continue
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


def generate_cowork_dist(project_root: Path, dist_root: Path, version: str):
    """Assemble the Cowork distribution at dist/cowork.

    Cowork ships the SAME plugins as Claude Code — `aops` + `aops-tools` +
    `aops-jr`, in their Claude-shaped builds — there is no separate cowork
    plugin build. But Cowork has no marketplace mechanism on personal
    accounts, and its RemotePluginManager.syncPlugins nukes github-source
    marketplaces on every restart (cf. claude-code #38429/#40600), so the
    Cowork install channel must be a LOCAL DIRECTORY marketplace. dist/cowork
    is that directory:

        dist/cowork/.claude-plugin/marketplace.json   (name: academicOps-cowork)
        dist/cowork/aops/                             (copy of dist/aops-claude)
        dist/cowork/aops-tools/                       (copy of dist/aops-tools-claude)
        dist/cowork/aops-jr/                          (copy of dist/aops-jr-claude)
        dist/cowork/aops-ts/                          (copy of dist/aops-ts-claude)
        dist/cowork/aops-v{version}.zip               (manual-upload fallback)
        dist/cowork/aops-tools-v{version}.zip         (manual-upload fallback)
        dist/cowork/aops-jr-v{version}.zip            (manual-upload fallback)
        dist/cowork/aops-ts-v{version}.zip            (manual-upload fallback)

    The marketplace name is `academicOps-cowork`, isolated from both the
    released `academicOps` marketplace and the local-dev `aops` one, so the
    Makefile's install-cowork/uninstall-cowork can manage it independently.
    The per-plugin zips serve the manual path (Claude desktop → Cowork →
    Customize → Add plugins → Upload a file) for accounts where even a local
    marketplace isn't usable.
    """
    import zipfile

    cowork_root = dist_root / "cowork"
    if cowork_root.exists():
        shutil.rmtree(cowork_root)
    cowork_root.mkdir(parents=True)

    template_path = project_root / "templates" / "marketplace.json"
    if not template_path.exists():
        raise FileNotFoundError(f"templates/marketplace.json not found at {template_path}")
    with open(template_path) as f:
        data = json.load(f)

    # The cowork channel ships these plugins (Nic ruling 2026-07-16), reusing
    # the Claude-shaped builds verbatim. aops-ts is included because CLOUD
    # Cowork sessions need the tailnet bring-up to reach the PKB MCP (a
    # tailnet-only URL); it stays opt-in on local machines (install-cowork
    # doesn't auto-install it — see the Makefile).
    wanted = {
        "aops": "aops-claude",
        "aops-tools": "aops-tools-claude",
        "aops-jr": "aops-jr-claude",
        "aops-ts": "aops-ts-claude",
        "aops-pkb": "aops-pkb-claude",
    }
    plugins = []
    for plugin in data.get("plugins", []):
        name = plugin.get("name")
        if name not in wanted:
            continue
        src = dist_root / wanted[name]
        if not src.exists():
            print(f"Warning: {src} missing — skipping {name} in cowork dist")
            continue
        dst = cowork_root / name
        shutil.copytree(src, dst)
        plugin["version"] = version
        plugin["source"] = f"./{name}"
        plugins.append(plugin)

        # Re-apply cowork-only content. The claude build this copy came from
        # has the <!-- cowork:only --> blocks REMOVED (build_plugin strips
        # them), so rewrite any marker-carrying source .md here with the
        # content KEPT and the markers dropped.
        src_plugin = project_root / name
        for md in src_plugin.rglob("*.md"):
            if any(part in EXCLUDES for part in md.parts):
                continue
            text = md.read_text(encoding="utf-8")
            if _COWORK_OPEN not in text:
                continue
            rel = md.relative_to(src_plugin)
            out = dst / rel
            if out.parent.exists():
                out.write_text(process_cowork_markers(text, keep=True), encoding="utf-8")
                print(f"    kept cowork:only content in {name}/{rel}")

        # Versioned zip for the manual Cowork upload path. The plugin directory
        # itself sits at the zip root (same convention as the claude tarballs).
        #
        # The ZIP variant's .mcp.json differs from the directory copy: the
        # claude.ai upload validator rejects `${user_config.pkb_mcp_url}`
        # placeholders, and Cowork won't install remote-HTTP plugin MCP
        # servers at all (Nic ruling 2026-07-16) — so the zip replaces the
        # HTTP transport with the STDIO launcher the plugin already ships
        # (scripts/run-mcp.sh, which proxies PKB_MCP_URL over stdio via
        # `uvx fastmcp run`). $PKB_MCP_URL at build time is baked into the
        # server's env block; without it the launcher hard-fails at runtime
        # unless the session env supplies PKB_MCP_URL. The directory copy
        # keeps the HTTP-transport placeholder — `claude plugin install
        # --config` resolves it there.
        def _zip_mcp_json(mcp_path: Path) -> str:
            data = json.loads(mcp_path.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            baked_url = os.environ.get("PKB_MCP_URL", "").strip()
            for sname, cfg in list(servers.items()):
                if "${user_config" not in str(cfg.get("url", "")):
                    continue
                stdio = {
                    "command": "bash",
                    "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/run-mcp.sh"],
                }
                if baked_url:
                    stdio["env"] = {"PKB_MCP_URL": baked_url}
                    print(f"    zip: '{sname}' → stdio launcher, PKB_MCP_URL baked ({name})")
                else:
                    print(
                        f"    zip: '{sname}' → stdio launcher WITHOUT baked URL ({name}) — "
                        "set PKB_MCP_URL at build time or the session env must supply it"
                    )
                servers[sname] = stdio
            return json.dumps(data, indent=2)

        zip_path = cowork_root / f"{name}-v{version}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(dst.rglob("*")):
                if not path.is_file():
                    continue
                arcname = str(path.relative_to(cowork_root))
                if path.name == ".mcp.json" and path.parent == dst:
                    zf.writestr(arcname, _zip_mcp_json(path))
                else:
                    zf.write(path, arcname)
        print(f"  ✓ Cowork: {name} → dist/cowork/{name} + {zip_path.name}")

    data["name"] = "academicOps-cowork"
    data["description"] = (
        "academicOps Cowork channel — local directory marketplace "
        "(github-source marketplaces get nuked on Cowork restart)"
    )
    data["plugins"] = plugins

    marketplace_dir = cowork_root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    with open(marketplace_dir / "marketplace.json", "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"✓ Generated cowork dist at {cowork_root} (plugins: {[p['name'] for p in plugins]})")


def generate_local_marketplace(project_root: Path, dist_root: Path, version: str):
    """Generate the LOCAL-dev Claude marketplace at dist/.claude-plugin/marketplace.json.

    Same plugin set as the root marketplace, but with TWO deliberate differences:
      • name is `aops` (not `academicOps`) so `make dev` installs land in their own
        marketplace/plugin namespace (`aops@aops`) — visibly distinct from the
        released `academicOps` install.
      • plugin sources are rewritten ./dist/aops-* → ./aops-* because THIS
        marketplace root is dist/ (not the repo root), so a co-located ./aops-claude
        resolves to dist/aops-claude.
    """
    template_path = project_root / "templates" / "marketplace.json"
    if not template_path.exists():
        raise FileNotFoundError(f"templates/marketplace.json not found at {template_path}")

    with open(template_path) as f:
        data = json.load(f)

    data["name"] = "aops"
    data["description"] = (
        "academicOps LOCAL dev build — distinct from the released 'academicOps' marketplace"
    )
    data["owner"] = {"name": "Local Dev"}

    plugins = []
    for plugin in data.get("plugins", []):
        plugin["version"] = version
        src = plugin.get("source", "")
        if src.startswith("./dist/"):
            dirname = src[len("./dist/"):]
            if (dist_root / dirname).exists():
                plugin["source"] = "./" + dirname
                plugins.append(plugin)

    data["plugins"] = plugins

    marketplace_dir = dist_root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    marketplace = marketplace_dir / "marketplace.json"
    with open(marketplace, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print("✓ Generated local marketplace.json")


def generate_production_marketplace(project_root: Path, dist_root: Path, version: str):
    """Generate the production marketplace JSON to be placed at the root of the dist branch.

    Loads from templates/marketplace.json, updates versions, filters to built plugins,
    and writes to dist/marketplace-production.json.

    Plugin dirs are published to the dist BRANCH ROOT (dist:aops-claude, not
    dist:dist/aops-claude — see build-extension.yml's "Publish distribution to
    dist" step), so sources are rewritten ./dist/aops-* → ./aops-* exactly like
    generate_local_marketplace, keeping both marketplaces' relative-path
    convention identical to the actual on-branch layout.
    """
    template_path = project_root / "templates" / "marketplace.json"
    if not template_path.exists():
        raise FileNotFoundError(f"templates/marketplace.json not found at {template_path}")

    with open(template_path) as f:
        data = json.load(f)

    plugins = []
    for plugin in data.get("plugins", []):
        plugin["version"] = version
        src = plugin.get("source", "")
        if src.startswith("./dist/"):
            dirname = src[len("./dist/"):]
            if (dist_root / dirname).exists():
                plugin["source"] = "./" + dirname
                plugins.append(plugin)
        else:
            plugins.append(plugin)

    data["plugins"] = plugins

    marketplace_file = dist_root / "marketplace-production.json"
    with open(marketplace_file, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"✓ Generated production marketplace.json at {marketplace_file}")


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
        default=["aops", "aops-tools", "aops-jr", "aops-ts", "aops-pkb", "reflexes-cope"],
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

    generate_local_marketplace(project_root, dist_root, version)
    generate_production_marketplace(project_root, dist_root, version)
    generate_cowork_dist(project_root, dist_root, version)


if __name__ == "__main__":
    main()
