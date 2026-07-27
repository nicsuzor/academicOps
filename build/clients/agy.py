"""Antigravity (agy) client adapter.

- manifest/plugin.json  -> plugin.json
- manifest/hooks.json   -> hooks.json, with quotes stripped from
  `${AGY_PLUGIN_ROOT}/...` script paths inside hook `command`/`args` strings —
  agy execs hooks via argv with no shell expansion, so a quoted path never
  resolves. Generalised over any script path, not hardcoded to one hook.
- manifest/mcp.json     -> mcp_config.json
- commands/<name>.md    -> skills/cmd-<name>/SKILL.md, frontmatter
  `type: command` rewritten to `type: skill`; the commands/ dir itself is
  dropped (agy has no commands/ concept).
- axioms with `trigger: always_on` -> rules/<source_file>
"""

import json
import re
import shutil
from pathlib import Path

from build.axioms import load_always_on_axioms
from build.context import BuildContext
from build.errors import BuildError

_QUOTED_PATH_RE = re.compile(r'"(\$\{AGY_PLUGIN_ROOT\}/[^"]*)"')
_COMMAND_TYPE_RE = re.compile(r"(?m)^type:\s*command\s*$")


def adapt(build_dir: Path, ctx: BuildContext) -> None:
    manifests = ctx.manifests
    if "plugin" not in manifests:
        raise BuildError(
            f"{ctx.plugin.directory}: manifest/plugin.template.json is required (client=agy)"
        )
    _write_json(build_dir / "plugin.json", manifests["plugin"])

    # A template with no `agy` section renders to `{}` — the plugin has no
    # hooks on agy, which is stated by shipping no hooks.json, not by shipping
    # an empty one.
    if manifests.get("hooks"):
        _write_json(build_dir / "hooks.json", _unquote_script_paths(manifests["hooks"]))

    if "mcp" in manifests:
        _write_json(build_dir / "mcp_config.json", manifests["mcp"])

    _convert_commands_to_skills(build_dir)

    always_on = load_always_on_axioms(build_dir / "axioms")
    if always_on:
        rules_dir = build_dir / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        for axiom in always_on:
            shutil.copy2(
                build_dir / "axioms" / axiom["source_file"], rules_dir / axiom["source_file"]
            )


def _unquote_script_paths(hooks_config: dict) -> dict:
    for event_entries in hooks_config.get("hooks", {}).values():
        for entry in event_entries:
            for hook in entry.get("hooks", []):
                if "command" in hook:
                    hook["command"] = _QUOTED_PATH_RE.sub(r"\1", hook["command"])
                if "args" in hook:
                    hook["args"] = [_QUOTED_PATH_RE.sub(r"\1", a) for a in hook["args"]]
    return hooks_config


def _convert_commands_to_skills(build_dir: Path) -> None:
    commands_dir = build_dir / "commands"
    if not commands_dir.is_dir():
        return

    for md_file in sorted(commands_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        content = _COMMAND_TYPE_RE.sub("type: skill", content)
        dst = build_dir / "skills" / f"cmd-{md_file.stem}" / "SKILL.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")

    shutil.rmtree(commands_dir)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
