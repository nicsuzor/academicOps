"""Claude Code client adapter.

- manifest/plugin.json  -> .claude-plugin/plugin.json
- manifest/hooks.json   -> hooks/hooks.json (the ONLY path Claude Code reads —
  a root-level hooks.json is silently ignored)
- manifest/mcp.json     -> .mcp.json
- axioms with `trigger: always_on` -> axioms.jsonl, one JSON object per line
"""

import json
from pathlib import Path

from build.axioms import load_always_on_axioms
from build.context import BuildContext
from build.errors import BuildError


def adapt(build_dir: Path, ctx: BuildContext) -> None:
    manifests = ctx.manifests
    if "plugin" not in manifests:
        raise BuildError(
            f"{ctx.plugin.directory}: manifest/plugin.template.json is required (client=claude)"
        )
    _write_json(build_dir / ".claude-plugin" / "plugin.json", manifests["plugin"])

    # A template with no section for this client renders to `{}` — the plugin
    # has no hooks on this client, which is stated by shipping no hooks.json,
    # not by shipping an empty one.
    if manifests.get("hooks"):
        _write_json(build_dir / "hooks" / "hooks.json", manifests["hooks"])

    if "mcp" in manifests:
        mcp_str = json.dumps(manifests["mcp"]).replace("${PLUGIN_ROOT}", "${CLAUDE_PLUGIN_ROOT}")
        _write_json(build_dir / ".mcp.json", json.loads(mcp_str))

    always_on = load_always_on_axioms(build_dir / "axioms")
    if always_on:
        jsonl_path = build_dir / "axioms.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for axiom in always_on:
                f.write(json.dumps(axiom) + "\n")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
