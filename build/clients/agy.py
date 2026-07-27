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
- axioms with `trigger: always_on` -> rules/<source_file>
"""

import json
import re
import shutil
from pathlib import Path

from build.axioms import load_always_on_axioms
from build.context import BuildContext
from build.errors import BuildError

_PLUGIN_ROOT_RE = re.compile(r'"?\$\{AGY_PLUGIN_ROOT\}/([^"\s]*)"?')
_COMMAND_TYPE_RE = re.compile(r"(?m)^type:\s*command\s*$")
_PLACEHOLDER_RE = re.compile(r"\$\{[^}]*\}")

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
        _write_json(build_dir / "mcp_config.json", _checked_mcp(servers, ctx))

    _convert_commands_to_skills(build_dir)

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

    Nothing here rewrites, because for MCP there is nothing to rewrite to. A
    hook command gets a working directory — agy documents it as the directory
    holding `hooks.json` — so a plugin-relative path resolves. An MCP server is
    spawned by the language server instead, and agy's "MCP Servers
    (`mcp_config.json`)" reference gives its stdio transport exactly three
    fields: `command`, `args`, `env`. No `cwd`, no plugin-root variable, and no
    substitution of any kind anywhere in the file. A `${...}` placeholder is
    therefore delivered to the server process verbatim, as a literal dollar
    sign and brace — which is worse than an empty value, because a launcher
    checking whether its variable is set finds a non-empty string and proceeds.

    So this refuses rather than guesses. The two alternatives were both worse:
    a relative path, which rests on a working directory agy never promised, and
    an absolute one, which bakes an install path into a shipped artifact and is
    barred outright (specs/ARCHITECTURE.md, binding constraints).
    """
    for name, server in sorted(servers.items()):
        leftover = _PLACEHOLDER_RE.search(json.dumps(server))
        if leftover:
            raise BuildError(
                f"{ctx.plugin.directory}: manifest/mcp.template.json leaves "
                f"{leftover.group(0)} unexpanded in MCP server {name!r} (client=agy). "
                f"agy substitutes nothing in mcp_config.json, so this ships to the "
                f"server process as that literal text. Supply the value another way "
                f"or drop the agy section — a config agy cannot act on must not ship."
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
        resolved["command"] = _PLUGIN_ROOT_RE.sub(r"\1", resolved["command"])
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


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
