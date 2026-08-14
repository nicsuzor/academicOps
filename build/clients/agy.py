"""Antigravity (agy) client adapter.

- manifest/plugin.json  -> plugin.json
- manifest/hooks.json   -> hooks.json, reshaped from the Claude Code hook
  config the templates are written in into agy's own schema, and with
  `${AGY_PLUGIN_ROOT}/...` script paths rewritten plugin-root-relative. See
  `_to_agy_hooks` for the schema and where it is documented.
- manifest/mcp.json     -> mcp_config.json
- commands/<name>.md    -> skills/cmd-<name>/SKILL.md, frontmatter
  `type: command` rewritten to `type: skill`; the commands/ dir itself is
  dropped (agy has no commands/ concept).
- agents/<name>.md      -> agents/<name>.md (agy's own read format)
- axioms with `trigger: always_on` -> rules/<source_file>
"""

import json
import re
import shutil
from pathlib import Path

import yaml

from build.axioms import load_always_on_axioms
from build.context import BuildContext
from build.errors import BuildError
from build.tools import (
    extract_agy_mcp_servers,
    load_tool_config,
    process_agent_tools_agy,
    validate_agent_name_and_desc,
)

_PLUGIN_ROOT_RE = re.compile(r'"?\$\{AGY_PLUGIN_ROOT\}/([^"\s]*)"?')
_PLUGIN_ROOT_BARE_RE = re.compile(r'"\$\{AGY_PLUGIN_ROOT\}"')
_COMMAND_TYPE_RE = re.compile(r"(?m)^type:\s*command\s*$")
_PLACEHOLDER_RE = re.compile(r"\$\{[^}]*\}")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)

# agy's five hook events, split by the structure each one takes. The tool
# events group their handlers under a `matcher` regex; the rest take a flat
# list of handlers. Both lists, and the split between them, are agy's own:
# the CLI binary embeds its "Lifecycle Hooks (`hooks.json`)" reference, whose
# "Hook Spec Fields" and "Supported Event Types" sections define them.
_GROUPED_EVENTS = ("PreToolUse", "PostToolUse")
_FLAT_EVENTS = ("PreInvocation", "PostInvocation", "Stop")


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
        _write_json(build_dir / "hooks.json", _to_agy_hooks(manifests["hooks"], ctx))

    # Same rule as hooks: no servers means no file, not an empty one.
    servers = (manifests.get("mcp") or {}).get("mcpServers") or {}
    if servers:
        mcp_str = json.dumps(servers).replace("${PLUGIN_ROOT}", "${CLAUDE_PLUGIN_ROOT}")
        servers = json.loads(mcp_str)
        _write_json(build_dir / "mcp_config.json", _checked_mcp(servers, ctx))

    _convert_commands_to_skills(build_dir)
    _adapt_agents(build_dir, ctx)

    always_on = load_always_on_axioms(build_dir / "axioms")
    if always_on:
        rules_dir = build_dir / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        for axiom in always_on:
            shutil.copy2(
                build_dir / "axioms" / axiom["source_file"], rules_dir / axiom["source_file"]
            )


def _to_agy_hooks(hooks_config: dict, ctx: BuildContext) -> dict:
    """Reshape a Claude Code hook config into agy's `hooks.json` schema.

    Templates are written once, in Claude Code's shape — a `hooks` wrapper
    holding event names, each an array of `{matcher?, hooks: [handler]}`
    groups. agy's file is a different shape at every level, so the whole
    translation lives here, which is where specs/ARCHITECTURE.md puts a
    client-specific workaround.

    agy keys the file by hook NAME; the events live one level down, inside
    that name's spec. A file with `hooks` at the top level is read as a hook
    literally named "hooks" and fails to load — which is what every plugin
    shipped until this function existed. Tool events keep a `matcher` group;
    the other three take handlers directly. An event agy does not have is a
    build failure rather than a key it will silently ignore, because a hook
    that never fires is indistinguishable from a working one.
    """
    spec: dict = {}
    for event, entries in hooks_config.get("hooks", {}).items():
        if event in _GROUPED_EVENTS:
            spec[event] = [
                {
                    # No matcher means every tool, which agy spells "*".
                    "matcher": entry.get("matcher", "*"),
                    "hooks": [_handler(hook) for hook in entry.get("hooks", [])],
                }
                for entry in entries
            ]
        elif event in _FLAT_EVENTS:
            spec[event] = [_handler(hook) for entry in entries for hook in entry.get("hooks", [])]
        else:
            raise BuildError(
                f"{ctx.plugin.directory}: manifest/hooks.template.json wires {event!r} "
                f"for client=agy, which has no such hook event. agy fires only "
                f"{', '.join((*_GROUPED_EVENTS, *_FLAT_EVENTS))}."
            )
    return {ctx.plugin.marketplace_name: spec}


def _checked_mcp(servers: dict, ctx: BuildContext) -> dict:
    """agy's `mcp_config.json`, refused if agy could not act on it.

    agy itself substitutes nothing in this file — no `cwd`, no plugin-root
    variable, and no template expansion of any kind. A `${...}` placeholder is
    therefore delivered to the server process verbatim, as a literal dollar
    sign and brace — worse than an empty value, because a launcher checking
    whether its variable is set finds a non-empty string and proceeds.

    `${extensionPath}` and `${CLAUDE_PLUGIN_ROOT}` are the one exception:
    `agy plugin install` copies this plugin to its own on-disk directory
    inside `~/.gemini/config/plugins/`, and the aops-crew image's
    `docker_gemini_fixups.py fixup-mcp-config-paths` (run from the Dockerfile,
    after install) rewrites either token, wherever it appears in any installed
    plugin's `mcp_config.json`, to that plugin's actual install directory —
    the resolution mechanism a plugin-relative `command`/`args` path needs,
    just done post-install instead of at template-render time. Outside that
    image (a bare host `agy plugin install`) nothing performs this rewrite, so
    a plugin relying on it only works inside an aops-crew container; that is
    a real gap, not one this function can close. `${AGY_PLUGIN_ROOT}` is NOT
    one of the two tokens the fixup knows: it appears nowhere in the agy CLI
    binary and nothing ever rewrites it, so it still refuses.

    Every other placeholder still refuses rather than guesses. The remaining
    alternatives were both worse: a bare relative path, which rests on a
    working directory agy never promised, and a baked-in absolute one, which
    bakes an install path into a shipped artifact and is barred outright
    (specs/ARCHITECTURE.md, binding constraints).
    """
    allowed = {"${extensionPath}", "${CLAUDE_PLUGIN_ROOT}"}
    for name, server in sorted(servers.items()):
        leftover = [
            token for token in _PLACEHOLDER_RE.findall(json.dumps(server)) if token not in allowed
        ]
        if leftover:
            raise BuildError(
                f"{ctx.plugin.directory}: manifest/mcp.template.json leaves "
                f"{leftover[0]} unexpanded in MCP server {name!r} (client=agy). "
                f"agy substitutes nothing in mcp_config.json, so this ships to the "
                f"server process as that literal text. Supply the value another way "
                f"or drop the agy section — a config agy cannot act on must not ship. "
                f"(${{extensionPath}} and ${{CLAUDE_PLUGIN_ROOT}} are the only tokens "
                f"the aops-crew image's post-install fixup resolves; this one is not "
                f"among them.)"
            )
        # agy's own rule, enforced by the CLI: "MCP server %q must have either
        # command or serverUrl" / "cannot have both".
        if ("command" in server) == ("serverUrl" in server):
            raise BuildError(
                f"{ctx.plugin.directory}: MCP server {name!r} (client=agy) must set "
                f"exactly one of 'command' (stdio) or 'serverUrl' (remote); agy "
                f"rejects a server with both or neither."
            )
    return {"mcpServers": servers}


def _handler(hook: dict) -> dict:
    """One hook handler, with its script path made plugin-root-relative.

    agy defines no plugin-root variable — `${AGY_PLUGIN_ROOT}` appears nowhere
    in the CLI binary, so it expands to nothing and the path never resolves.
    What agy does guarantee is the working directory: it runs the command
    through a shell with the cwd set to the directory holding `hooks.json`,
    which for a plugin is its root. So the path relative to that root is the
    one form that resolves, and the quotes come off with the variable.
    """
    resolved = dict(hook)
    if "command" in resolved:
        command = _PLUGIN_ROOT_BARE_RE.sub(".", resolved["command"])
        resolved["command"] = _PLUGIN_ROOT_RE.sub(r"\1", command)
    return resolved


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


def _adapt_agents(build_dir: Path, ctx: BuildContext | None = None) -> None:
    """Rewrite each agent under `agents/` into agy's `agents/<name>.md`.

    agy's runtime reads `<name>.md` — YAML frontmatter plus a Markdown body —
    the same shape Claude Code agents already ship in; it does not read
    `agent.json` or subdirectories. So this function is a frontmatter transform,
    not a format conversion — `tools` gets translated, `model` and an absent
    `tools:` key get the handling documented below, and the body is carried
    through unchanged.
    """
    agents_dir = build_dir / "agents"
    if not agents_dir.is_dir():
        return

    md_files = sorted(agents_dir.rglob("*.md"))
    if not md_files:
        return

    accepted_tools, tool_map = load_tool_config()
    plugin_name = ctx.plugin.marketplace_name if ctx else ""

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

        # Carry every source field through except those handled explicitly below:
        # (name, description, tools, hidden, includeSections, model, disallowedTools, mcpServers).
        extra_fields: dict = {
            k: v
            for k, v in frontmatter.items()
            if k
            not in (
                "name",
                "description",
                "tools",
                "hidden",
                "includeSections",
                "model",
                "disallowedTools",
                "mcpServers",
            )
        }

        # `model` names a Claude Code model ("opus", "sonnet", ...); agy silently
        # drops the agent from `agy agents` when its frontmatter carries an
        # unrecognized model value. `--agent <name>` then silently falls back
        # to a full unnamed session with every tool (56 tools). That is a
        # privilege escalation, not a cosmetic bug. Thus `model` is dropped.

        has_tools_key = "tools" in frontmatter
        raw_tools = frontmatter.get("tools")
        has_disallowed_key = "disallowedTools" in frontmatter
        raw_disallowed = frontmatter.get("disallowedTools")

        processed_tools = process_agent_tools_agy(
            raw_tools,
            has_tools_key,
            name,
            md_file,
            accepted_tools,
            tool_map,
            plugin_name=plugin_name,
            raw_disallowed_tools=raw_disallowed,
            has_disallowed_tools_key=has_disallowed_key,
        )

        mcp_servers = extract_agy_mcp_servers(frontmatter, plugin_name=plugin_name)

        agy_frontmatter: dict = {
            "name": name,
            "description": str(description).strip(),
            **extra_fields,
        }
        if mcp_servers:
            agy_frontmatter["mcpServers"] = mcp_servers
        agy_frontmatter["tools"] = processed_tools

        if not body.startswith("# Agent System Instructions"):
            body = f"# Agent System Instructions\n\n{body}"

        target = agents_dir / f"{name}.md"
        _write_agent_md(target, agy_frontmatter, body.strip())
        if md_file != target:
            md_file.unlink()
            if (
                md_file.parent != agents_dir
                and md_file.parent.is_dir()
                and not any(md_file.parent.iterdir())
            ):
                md_file.parent.rmdir()


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _write_agent_md(path: Path, frontmatter: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{fm_text}---\n\n{body}\n", encoding="utf-8")
