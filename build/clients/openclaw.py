"""OpenClaw client adapter.

- manifest/plugin.json  -> .claude-plugin/plugin.json
- manifest/hooks.json   -> hooks/hooks.json
- manifest/mcp.json     -> .mcp.json
- axioms with `trigger: always_on` -> axioms.jsonl, one JSON object per line
"""

import json
import re
from pathlib import Path
from typing import Any

import yaml

from build.agents import resolve_client_agents
from build.axioms import load_always_on_axioms
from build.context import BuildContext
from build.errors import BuildError
from build.tools import (
    load_tool_config,
    process_agent_tools_claude,
    validate_agent_name_and_desc,
)

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def adapt(build_dir: Path, ctx: BuildContext) -> None:
    manifests = ctx.manifests
    if "plugin" not in manifests:
        raise BuildError(
            f"{ctx.plugin.directory}: manifest/plugin.template.json is required (client=openclaw)"
        )
    _write_json(build_dir / ".claude-plugin" / "plugin.json", manifests["plugin"])

    if manifests.get("hooks"):
        _write_json(build_dir / "hooks" / "hooks.json", manifests["hooks"])

    if "mcp" in manifests:
        mcp_str = json.dumps(manifests["mcp"]).replace("${PLUGIN_ROOT}", "${CLAUDE_PLUGIN_ROOT}")
        _write_json(build_dir / ".mcp.json", json.loads(mcp_str))

    _adapt_agents(build_dir)

    always_on = load_always_on_axioms(build_dir / "axioms")
    if always_on:
        jsonl_path = build_dir / "axioms.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for axiom in always_on:
                f.write(json.dumps(axiom) + "\n")


def _adapt_agents(build_dir: Path) -> None:
    """Validate and rewrite each agent under `agents/` for OpenClaw."""
    agents_dir = build_dir / "agents"
    if not agents_dir.is_dir():
        return

    resolve_client_agents(agents_dir, "openclaw")

    md_files = sorted(agents_dir.rglob("*.md"))
    if not md_files:
        return

    _, tool_map = load_tool_config()

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(content)
        if not m:
            continue

        try:
            frontmatter = yaml.safe_load(m.group(1))
        except yaml.YAMLError as e:
            raise BuildError(f"{md_file}: failed to parse YAML frontmatter: {e}") from e

        if not isinstance(frontmatter, dict):
            continue

        name = frontmatter.get("name")
        if not name:
            name = md_file.parent.name if md_file.stem == "agent" else md_file.stem

        description = frontmatter.get("description")
        name = validate_agent_name_and_desc(name, description, md_file)

        body = m.group(2).lstrip("\n")

        openclaw_frontmatter: dict[str, Any] = {
            k: v for k, v in frontmatter.items() if k not in ("name", "description", "tools")
        }
        openclaw_frontmatter = {
            "name": name,
            "description": str(description).strip(),
            **openclaw_frontmatter,
        }

        has_tools_key = "tools" in frontmatter
        raw_tools = frontmatter.get("tools")
        processed_tools = process_agent_tools_claude(
            raw_tools,
            has_tools_key,
            name,
            md_file,
            tool_map,
        )
        if processed_tools is not None:
            openclaw_frontmatter["tools"] = processed_tools

        target = agents_dir / f"{name}.md"
        _write_agent_md(target, openclaw_frontmatter, body.strip())
        if md_file != target:
            md_file.unlink()
            if (
                md_file.parent != agents_dir
                and md_file.parent.is_dir()
                and not any(md_file.parent.iterdir())
            ):
                md_file.parent.rmdir()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _write_agent_md(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{fm_text}---\n\n{body}\n", encoding="utf-8")
