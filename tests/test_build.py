"""Tests for the academicOps build system (build/build.py).

Runs the real builder against the fixture plugins in build/testdata/ (two
throwaway plugins, "alpha" and "beta" — see build/testdata/marketplace.toml)
and asserts the output tree for both clients. plugins/ and lib/ don't exist
in the real repo yet, so these fixtures are the only thing exercising the
builder end to end until they land.
"""

import json
import re
import tarfile
import zipfile
from pathlib import Path

import pytest

from build.build import build_all, discover_plugins
from build.errors import BuildError
from build.manifest import merge_one_level, render_template
from build.marketplace import load_marketplace_toml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTDATA = PROJECT_ROOT / "build" / "testdata"
MARKETPLACE = TESTDATA / "marketplace.toml"
REAL_MARKETPLACE = PROJECT_ROOT / "build" / "marketplace.toml"
VERSION = "0.0.0-test"


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    dist_root = tmp_path_factory.mktemp("build-dist")
    build_all(TESTDATA, dist_root, marketplace_path=MARKETPLACE, version=VERSION)
    return dist_root


@pytest.fixture(scope="module")
def built_orchestrate(tmp_path_factory) -> Path:
    """The real orchestrate plugin, not a fixture — its agents carry the
    per-client frontmatter semantics these tests assert."""
    dist_root = tmp_path_factory.mktemp("build-dist-orchestrate")
    build_all(
        PROJECT_ROOT,
        dist_root,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["orchestrate"],
        version=VERSION,
    )
    return dist_root


def test_polecat_cli_ships_with_orchestrate(built_orchestrate):
    """The polecat launcher agent (`plugins/orchestrate/agents/pc.md`) invokes
    `${CLAUDE_PLUGIN_ROOT}/polecat/cli.py`. What puts that module inside a plugin
    root at all is `plugins/orchestrate/manifest/plugin.toml`, which injects it
    from `lib/polecat/`.

    Drop those `[[shared]]` stanzas and nothing fails at build time; the launch
    fails at runtime, with file-not-found. This is the check that turns that into
    a build-time failure instead.

    The sibling modules are read off cli.py's own fallback imports rather than
    listed here, because a hand-kept list is exactly what let `notify.py` be
    added to cli.py and left out of the manifest.
    """
    siblings = set(
        re.findall(r"from polecat\.(\w+) import", (PROJECT_ROOT / "lib/polecat/cli.py").read_text())
    )
    assert "env_contract" in siblings, "cli.py's fallback imports no longer parse"
    for client in ("claude", "agy"):
        polecat = built_orchestrate / f"orchestrate-{client}" / "polecat"
        assert (polecat / "cli.py").is_file(), f"orchestrate-{client} ships no polecat/cli.py"
        for module in siblings:
            assert (polecat / f"{module}.py").is_file(), (
                f"orchestrate-{client} ships cli.py without the {module} it imports"
            )
        # Image-build inputs, not plugin content — they must NOT be shipped.
        assert not (polecat / "defaults").exists()
        assert not (polecat / "entrypoint.sh").exists()


# --- stage 1/2: shared injection + include resolution -----------------------


def test_shared_single_file_injected_both_clients(built):
    for client in ("claude", "agy"):
        assert (built / f"fixture-alpha-{client}" / "hooks" / "hook.py").is_file()


# --- stage 3: manifest rendering --------------------------------------------


def _template(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "hooks.template.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_template_renders_the_client_section(tmp_path):
    """Client sections nest under `clients`, keeping the top level for plugin
    identity. Reading the client key at the top level instead finds nothing and
    renders every event away — the plugin builds clean and ships with no
    hooks.json at all."""
    path = _template(
        tmp_path,
        {
            "manifestVersion": "1.0",
            "name": "aops-debug",
            "clients": {
                "claude": {"hooks": {"SessionStart": [], "Stop": []}},
                "agy": {"hooks": {"PreToolUse": []}},
            },
        },
    )
    assert sorted(render_template(path, "claude")["hooks"]) == ["SessionStart", "Stop"]
    assert sorted(render_template(path, "agy")["hooks"]) == ["PreToolUse"]


def test_base_section_merges_under_the_client_section(tmp_path):
    """`__base__` carries what every client shares; the client's own section
    merges on top of it."""
    path = _template(
        tmp_path,
        {
            "manifestVersion": "1.0",
            "clients": {
                "__base__": {"hooks": {"Stop": []}},
                "claude": {"hooks": {"SessionStart": []}},
            },
        },
    )
    assert render_template(path, "claude") == {"hooks": {"Stop": [], "SessionStart": []}}


def test_template_without_clients_is_a_hard_error(tmp_path):
    """Rendering it empty would be indistinguishable from a plugin that
    genuinely has no hooks on any client."""
    path = _template(tmp_path, {"manifestVersion": "1.0", "name": "aops-debug"})
    with pytest.raises(BuildError, match="clients"):
        render_template(path, "claude")


def test_template_without_a_manifest_version_is_a_hard_error(tmp_path):
    """The pre-versioned shape keyed sections at the top level. Still reading
    them there would render a versioned template's identity keys as clients, so
    the absent version is refused rather than guessed at."""
    path = _template(tmp_path, {"__base__": {}, "claude": {"hooks": {"Stop": []}}})
    with pytest.raises(BuildError, match="manifestVersion"):
        render_template(path, "claude")


def test_unknown_manifest_version_is_a_hard_error(tmp_path):
    path = _template(tmp_path, {"manifestVersion": "2.0", "clients": {"claude": {}}})
    with pytest.raises(BuildError, match="manifestVersion"):
        render_template(path, "claude")


def test_plugin_json_version_stamped(built):
    for path in (
        built / "fixture-alpha-claude" / ".claude-plugin" / "plugin.json",
        built / "fixture-alpha-agy" / "plugin.json",
    ):
        data = json.loads(path.read_text())
        assert data["version"] == VERSION
        assert data["name"] == "fixture-alpha"


def test_hooks_json_rendered_per_client(built):
    """One template, two files that agree about nothing.

    Claude Code keys by event under a `hooks` wrapper and expands a plugin-root
    variable. agy keys by hook NAME with the events one level down, and defines
    no plugin-root variable at all — it runs the command from the directory
    holding `hooks.json`, so the path is rewritten relative to the plugin root.
    """
    claude_hooks = json.loads((built / "fixture-alpha-claude" / "hooks" / "hooks.json").read_text())
    agy_hooks = json.loads((built / "fixture-alpha-agy" / "hooks.json").read_text())

    claude_cmd = claude_hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert claude_cmd == '"${CLAUDE_PLUGIN_ROOT}/hooks/hook.py"'

    assert list(agy_hooks) == ["fixture-alpha"]
    group = agy_hooks["fixture-alpha"]["PreToolUse"][0]
    assert group["matcher"] == "*"  # no matcher in the template means every tool
    assert group["hooks"][0]["command"] == "hooks/hook.py"


def test_agy_rejects_an_event_it_cannot_fire(tmp_path):
    """agy fires five hook events and no session-level event of any kind. A
    template wiring one anyway would ship a key agy silently ignores — a hook
    indistinguishable from a working one — so the build stops instead."""
    from build.clients.agy import _to_agy_hooks
    from build.context import BuildContext, Plugin

    ctx = BuildContext(
        plugin=Plugin(
            directory="ts",
            marketplace_name="aops-ts",
            description="desc",
            category="productivity",
            source_dir=tmp_path,
        ),
        client="agy",
        version=VERSION,
        manifests={},
    )
    config = {"hooks": {"SessionStart": [{"hooks": [{"command": "bash up.sh"}]}]}}
    with pytest.raises(BuildError, match="SessionStart"):
        _to_agy_hooks(config, ctx)


def _agy_ctx(tmp_path, directory="aops-core", name="aops-core"):
    from build.context import BuildContext, Plugin

    return BuildContext(
        plugin=Plugin(
            directory=directory,
            marketplace_name=name,
            description="desc",
            category="productivity",
            source_dir=tmp_path,
        ),
        client="agy",
        version=VERSION,
        manifests={},
    )


def test_agy_rejects_an_mcp_server_it_would_launch_with_an_unexpanded_variable(tmp_path):
    """The exact config that shipped: a plugin-root variable agy does not have,
    in a file agy substitutes nothing in. It reaches the launcher as the
    literal text `${AGY_PLUGIN_ROOT}/scripts/run-mcp.sh`, so the server never
    starts and its tools never appear — with no error anyone sees."""
    from build.clients.agy import _checked_mcp

    servers = {
        "services": {
            "command": "bash",
            "args": ["${AGY_PLUGIN_ROOT}/scripts/run-mcp.sh"],
            "env": {"PKB_MCP_URL": "${PKB_MCP_URL}"},
        }
    }
    with pytest.raises(BuildError, match=r"AGY_PLUGIN_ROOT"):
        _checked_mcp(servers, _agy_ctx(tmp_path))


def test_agy_allows_the_two_placeholders_its_post_install_fixup_resolves(tmp_path):
    """`${extensionPath}` and `${CLAUDE_PLUGIN_ROOT}` are the one exception: the
    aops-crew image's `docker_gemini_fixups.py fixup-mcp-config-paths` rewrites
    either token, in any installed plugin's `mcp_config.json`, to that plugin's
    real on-disk install directory — after `agy plugin install` has copied it
    there. This is the mechanism a plugin-relative command path needs, applied
    post-install instead of at template-render time, and it is available to
    every plugin the same way, not just this one."""
    from build.clients.agy import _checked_mcp

    servers = {
        "services": {
            "command": "bash",
            "args": ["${extensionPath}/scripts/run-mcp.sh"],
        }
    }
    assert _checked_mcp(servers, _agy_ctx(tmp_path)) == {"mcpServers": servers}

    servers_claude_root = {
        "services": {"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/run-mcp.sh"]}
    }
    assert _checked_mcp(servers_claude_root, _agy_ctx(tmp_path)) == {
        "mcpServers": servers_claude_root
    }


def test_agy_rejects_an_mcp_server_that_is_neither_stdio_nor_remote(tmp_path):
    """agy's own rule: a server must have either `command` or `serverUrl`, and
    cannot have both."""
    from build.clients.agy import _checked_mcp

    with pytest.raises(BuildError, match="exactly one"):
        _checked_mcp({"services": {"args": ["x"]}}, _agy_ctx(tmp_path))
    with pytest.raises(BuildError, match="exactly one"):
        _checked_mcp(
            {"services": {"command": "bash", "serverUrl": "https://example.invalid/sse"}},
            _agy_ctx(tmp_path),
        )


def test_agy_accepts_a_server_it_can_actually_launch(tmp_path):
    """The guard must not be a blanket refusal — both transports agy documents
    pass through untouched."""
    from build.clients.agy import _checked_mcp

    stdio = {"services": {"command": "pkb-mcp-server", "args": ["--stdio"]}}
    assert _checked_mcp(stdio, _agy_ctx(tmp_path)) == {"mcpServers": stdio}

    remote = {"services": {"serverUrl": "https://mcp.example.invalid/sse"}}
    assert _checked_mcp(remote, _agy_ctx(tmp_path)) == {"mcpServers": remote}


def test_mcp_json_rendered_per_client(built):
    assert (built / "fixture-alpha-claude" / ".mcp.json").is_file()
    assert (built / "fixture-alpha-agy" / "mcp_config.json").is_file()


def test_minimal_plugin_has_no_optional_manifests(built):
    for base in (built / "fixture-beta-claude", built / "fixture-beta-agy"):
        assert not (base / "hooks").exists()
        assert not (base / ".mcp.json").exists()
        assert not (base / "mcp_config.json").exists()


def test_merge_one_level_dict_merges_shallow():
    base = {"a": {"x": 1, "y": 2}, "b": "base"}
    override = {"a": {"y": 3}, "c": "new"}
    assert merge_one_level(base, override) == {"a": {"x": 1, "y": 3}, "b": "base", "c": "new"}


def test_merge_one_level_list_replaces_outright():
    assert merge_one_level({"items": [1, 2, 3]}, {"items": [4]}) == {"items": [4]}


# --- stage 4: client adaptation ---------------------------------------------


def test_claude_manifest_paths(built):
    base = built / "fixture-alpha-claude"
    assert (base / ".claude-plugin" / "plugin.json").is_file()
    assert (base / "hooks" / "hooks.json").is_file()
    assert (base / ".mcp.json").is_file()
    # Claude auto-discovers commands/*.md — the source stays put, untouched.
    assert (base / "commands" / "greet.md").is_file()


def test_agy_manifest_paths(built):
    base = built / "fixture-alpha-agy"
    assert (base / "plugin.json").is_file()
    assert (base / "hooks.json").is_file()
    assert (base / "mcp_config.json").is_file()


def test_agy_command_converted_to_skill(built):
    skill = built / "fixture-alpha-agy" / "skills" / "cmd-greet" / "SKILL.md"
    assert skill.is_file()
    content = skill.read_text()
    assert "type: skill" in content
    assert "type: command" not in content
    assert not (built / "fixture-alpha-agy" / "commands").exists()


def test_agy_agent_frontmatter_tool_translation(tmp_path_factory):
    dist_root = tmp_path_factory.mktemp("build-dist-agents")
    build_all(
        PROJECT_ROOT,
        dist_root,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["aops-core", "orchestrate"],
        version=VERSION,
    )

    import yaml

    # Check agy dist saves agents/ida.md directly as agents/ida.md (agy's own
    # read format — see build/clients/agy.py's _adapt_agents docstring).
    agy_ida_md = dist_root / "aops-core-agy" / "agents" / "ida.md"
    assert agy_ida_md.is_file()
    assert not (dist_root / "aops-core-agy" / "agents" / "ida" / "agent.md").exists()

    raw = agy_ida_md.read_text()
    fm, _, body = raw.partition("---\n")[2].partition("---\n")
    agy_agent = yaml.safe_load(fm)
    assert agy_agent["name"] == "ida"
    assert "strategic face" in agy_agent["description"]
    assert "hidden" not in agy_agent
    assert "includeSections" not in agy_agent
    # ida declares no `mcpServers:` and reaches no MCP tool, so the build must
    # not invent a server for it. The normalisation of a declared list is
    # covered by test_pauli_agy_frontmatter.
    assert "mcpServers" not in agy_agent

    # pc declares tools: [Bash] which translates to run_command for agy
    agy_pc_md = dist_root / "orchestrate-agy" / "agents" / "pc.md"
    assert agy_pc_md.is_file()
    pc_fm, _, _ = agy_pc_md.read_text().partition("---\n")[2].partition("---\n")
    agy_pc = yaml.safe_load(pc_fm)
    assert agy_pc["tools"] == ["run_command"]

    body = body.lstrip("\n")
    assert body.startswith("# Agent System Instructions")
    assert "# Ida" in body


def test_agy_agent_tool_names_are_translated(built):
    import yaml

    claude_agent = built / "fixture-alpha-claude" / "agents" / "alpha-agent.md"
    claude_fm = yaml.safe_load(claude_agent.read_text().split("---")[1])
    assert claude_fm["tools"] == ["Read", "Write", "Agent", "AskUserQuestion", "Grep"]

    agy_agent = built / "fixture-alpha-agy" / "agents" / "alpha-agent.md"
    agy_fm = yaml.safe_load(agy_agent.read_text().split("---")[1])
    assert agy_fm["tools"] == [
        "view_file",
        "write_to_file",
        "invoke_subagent",
        "manage_subagents",
        "send_message",
        "ask_question",
        "grep_search",
    ]


def test_agent_no_tools_key_semantics(built_orchestrate):
    """marsha.md sets no `tools:` key in source frontmatter.
    Claude: leaves tools unset (inherits everything).
    agy: emits full 21 accepted tools vocabulary.
    """
    import yaml

    from build.tools import load_tool_config

    accepted_tools, _ = load_tool_config()

    claude_agent = built_orchestrate / "orchestrate-claude" / "agents" / "marsha.md"
    claude_fm = yaml.safe_load(claude_agent.read_text().split("---")[1])
    assert "tools" not in claude_fm

    agy_agent = built_orchestrate / "orchestrate-agy" / "agents" / "marsha.md"
    agy_fm = yaml.safe_load(agy_agent.read_text().split("---")[1])
    assert agy_fm["tools"] == accepted_tools


def test_agy_agent_drops_claude_model_name(built_orchestrate):
    import yaml

    agy_agent = built_orchestrate / "orchestrate-agy" / "agents" / "james.md"
    agy_fm = yaml.safe_load(agy_agent.read_text().split("---")[1])
    assert "model" not in agy_fm

    claude_agent = built_orchestrate / "orchestrate-claude" / "agents" / "james.md"
    claude_fm = yaml.safe_load(claude_agent.read_text().split("---")[1])
    assert claude_fm.get("model") == "opus" or "model" not in claude_fm

    agy_marsha = built_orchestrate / "orchestrate-agy" / "agents" / "marsha.md"
    agy_marsha_fm = yaml.safe_load(agy_marsha.read_text().split("---")[1])
    assert agy_marsha_fm["color"] == "pink"


def test_agent_empty_tools_list_raises_build_error(tmp_path):
    from build.clients.agy import adapt as adapt_agy
    from build.clients.claude import adapt as adapt_claude
    from build.context import BuildContext, Plugin

    plugin_dir = tmp_path / "bad-agent-plugin"
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "bad.md").write_text(
        "---\nname: bad\ndescription: Bad agent\ntools: []\n---\n\nBody", encoding="utf-8"
    )

    ctx = BuildContext(
        plugin=Plugin(
            directory="bad-agent-plugin",
            marketplace_name="bad-agent",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="agy",
        version=VERSION,
        manifests={"plugin": {"name": "bad-agent"}},
    )

    with pytest.raises(BuildError, match="empty 'tools' list"):
        adapt_agy(plugin_dir, ctx)

    ctx_claude = BuildContext(
        plugin=Plugin(
            directory="bad-agent-plugin",
            marketplace_name="bad-agent",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="claude",
        version=VERSION,
        manifests={"plugin": {"name": "bad-agent"}},
    )

    with pytest.raises(BuildError, match="empty 'tools' list"):
        adapt_claude(plugin_dir, ctx_claude)


def test_agent_all_no_equivalent_tools_raises_build_error(tmp_path):
    from build.clients.agy import adapt as adapt_agy
    from build.context import BuildContext, Plugin

    plugin_dir = tmp_path / "no-eq-plugin"
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "noeq.md").write_text(
        "---\nname: noeq\ndescription: No eq agent\ntools:\n  - Monitor\n  - TodoWrite\n---\n\nBody",
        encoding="utf-8",
    )

    ctx = BuildContext(
        plugin=Plugin(
            directory="no-eq-plugin",
            marketplace_name="no-eq",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="agy",
        version=VERSION,
        manifests={"plugin": {"name": "no-eq"}},
    )

    with pytest.raises(BuildError, match="yielded 0 tools"):
        adapt_agy(plugin_dir, ctx)


def test_agent_partial_no_equivalent_tools_drops_them_and_succeeds(tmp_path):
    import yaml

    from build.clients.agy import adapt as adapt_agy
    from build.context import BuildContext, Plugin

    plugin_dir = tmp_path / "partial-eq-plugin"
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "partial.md").write_text(
        "---\nname: partial\ndescription: Partial eq agent\ntools:\n  - Read\n  - Monitor\n---\n\nBody",
        encoding="utf-8",
    )

    ctx = BuildContext(
        plugin=Plugin(
            directory="partial-eq-plugin",
            marketplace_name="partial-eq",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="agy",
        version=VERSION,
        manifests={"plugin": {"name": "partial-eq"}},
    )

    adapt_agy(plugin_dir, ctx)
    res = yaml.safe_load((agents_dir / "partial.md").read_text().split("---")[1])
    assert res["tools"] == ["view_file"]


def test_agent_emitted_tool_not_in_vocabulary_raises_build_error(tmp_path):
    from build.tools import process_agent_tools_agy

    with pytest.raises(BuildError, match="not in agy accepted tool vocabulary"):
        process_agent_tools_agy(
            raw_tools=["Read"],
            has_tools_key=True,
            agent_name="test-agent",
            file_path=tmp_path / "test.md",
            accepted_tools=["run_command"],
            tool_map={"Read": ["view_file"]},
        )


def test_agent_invalid_name_raises_build_error(tmp_path):
    from build.clients.agy import adapt as adapt_agy
    from build.clients.claude import adapt as adapt_claude
    from build.context import BuildContext, Plugin

    plugin_dir = tmp_path / "invalid-name-plugin"
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "invalid_name.md").write_text(
        "---\nname: invalid_name\ndescription: Invalid name agent\n---\n\nBody",
        encoding="utf-8",
    )

    ctx = BuildContext(
        plugin=Plugin(
            directory="invalid-name-plugin",
            marketplace_name="invalid-name",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="agy",
        version=VERSION,
        manifests={"plugin": {"name": "invalid-name"}},
    )

    with pytest.raises(BuildError, match="invalid agent name"):
        adapt_agy(plugin_dir, ctx)

    ctx_claude = BuildContext(
        plugin=Plugin(
            directory="invalid-name-plugin",
            marketplace_name="invalid-name",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="claude",
        version=VERSION,
        manifests={"plugin": {"name": "invalid-name"}},
    )

    with pytest.raises(BuildError, match="invalid agent name"):
        adapt_claude(plugin_dir, ctx_claude)


def test_resolve_client_agents_renames_matching_and_deletes_other(tmp_path):
    from build.agents import resolve_client_agents

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "james.claude.md").write_text("claude content", encoding="utf-8")
    (agents_dir / "james.agy.md").write_text("agy content", encoding="utf-8")
    (agents_dir / "shared.md").write_text("shared content", encoding="utf-8")

    resolve_client_agents(agents_dir, "claude")

    assert (agents_dir / "james.md").read_text(encoding="utf-8") == "claude content"
    assert not (agents_dir / "james.claude.md").exists()
    assert not (agents_dir / "james.agy.md").exists()
    assert (agents_dir / "shared.md").read_text(encoding="utf-8") == "shared content"


def test_resolve_client_agents_for_agy(tmp_path):
    from build.agents import resolve_client_agents

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "james.claude.md").write_text("claude content", encoding="utf-8")
    (agents_dir / "james.agy.md").write_text("agy content", encoding="utf-8")

    resolve_client_agents(agents_dir, "agy")

    assert (agents_dir / "james.md").read_text(encoding="utf-8") == "agy content"
    assert not (agents_dir / "james.claude.md").exists()
    assert not (agents_dir / "james.agy.md").exists()


def test_resolve_client_agents_collision_raises(tmp_path):
    from build.agents import resolve_client_agents

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "james.md").write_text("base", encoding="utf-8")
    (agents_dir / "james.claude.md").write_text("claude", encoding="utf-8")

    with pytest.raises(BuildError, match="both james.md and james.claude.md exist"):
        resolve_client_agents(agents_dir, "claude")


def test_resolve_client_agents_unknown_client_raises(tmp_path):
    from build.agents import resolve_client_agents

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    with pytest.raises(BuildError, match="unknown client"):
        resolve_client_agents(agents_dir, "unknown")


def test_agent_tools_serialised_as_yaml_list(built):
    claude_raw = (built / "fixture-alpha-claude" / "agents" / "alpha-agent.md").read_text()
    agy_raw = (built / "fixture-alpha-agy" / "agents" / "alpha-agent.md").read_text()

    assert (
        "tools:\n- Read" in claude_raw
        or "tools:\n  - Read" in claude_raw
        or "\ntools:\n-" in claude_raw
    )
    assert (
        "tools:\n- view_file" in agy_raw
        or "tools:\n  - view_file" in agy_raw
        or "\ntools:\n-" in agy_raw
    )


def test_axioms_always_on_wired_per_client(built):
    claude_jsonl = (built / "fixture-alpha-claude" / "axioms.jsonl").read_text().splitlines()
    assert len(claude_jsonl) == 1
    axiom = json.loads(claude_jsonl[0])
    assert axiom == {
        "slug": "always-on-rule",
        "description": "Fixture always-on rule.",
        "body": "Body of the always-on rule.",
        "source_file": "always-on-rule.md",
    }

    agy_rules = built / "fixture-alpha-agy" / "rules"
    assert (agy_rules / "always-on-rule.md").is_file()
    assert not (agy_rules / "reference-rule.md").exists()


def test_axioms_raw_dir_shipped_both_clients(built):
    for client in ("claude", "agy"):
        axioms_dir = built / f"fixture-alpha-{client}" / "axioms"
        assert (axioms_dir / "always-on-rule.md").is_file()
        assert (axioms_dir / "reference-rule.md").is_file()


# --- stage 5: packaging ------------------------------------------------------


def test_tarballs_contain_directory_prefix(built):
    for client in ("claude", "agy"):
        with tarfile.open(built / f"fixture-alpha-{client}.tar.gz") as tar:
            names = tar.getnames()
        prefix = f"fixture-alpha-{client}"
        assert all(n == prefix or n.startswith(f"{prefix}/") for n in names)
        if client == "claude":
            assert f"{prefix}/.claude-plugin/plugin.json" in names
        else:
            assert f"{prefix}/plugin.json" in names


def test_no_stage_directory_left_behind(built):
    assert not (built / ".stage").exists()


# --- marketplace manifests ----------------------------------------------------


def test_local_marketplace_named_aops(built):
    data = json.loads((built / ".claude-plugin" / "marketplace.json").read_text())
    assert data["name"] == "aops"
    assert {p["name"] for p in data["plugins"]} == {"fixture-alpha", "fixture-beta"}
    for p in data["plugins"]:
        assert p["source"] == f"./{p['name']}-claude"
        assert p["version"] == VERSION


def test_production_marketplace_named_from_toml(built):
    data = json.loads((built / "marketplace-production.json").read_text())
    assert data["name"] == "academicOps-fixtures"
    assert {p["name"] for p in data["plugins"]} == {"fixture-alpha", "fixture-beta"}


def test_cowork_dist(built):
    marketplace = json.loads((built / "cowork" / ".claude-plugin" / "marketplace.json").read_text())
    assert marketplace["name"] == "academicOps-cowork"
    assert {p["name"] for p in marketplace["plugins"]} == {"fixture-alpha", "fixture-beta"}
    assert (built / "cowork" / "fixture-alpha" / ".claude-plugin" / "plugin.json").is_file()

    zip_path = built / "cowork" / f"fixture-alpha-v{VERSION}.zip"
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert "fixture-alpha/.claude-plugin/plugin.json" in names


def test_cowork_does_not_bake_urls(built):
    """Hard constraint: no URL/endpoint/token is ever baked into a shipped
    artifact — the cowork copy's .mcp.json must be byte-identical to the
    claude dist's, not rewritten."""
    claude_mcp = (built / "fixture-alpha-claude" / ".mcp.json").read_bytes()
    cowork_mcp = (built / "cowork" / "fixture-alpha" / ".mcp.json").read_bytes()
    assert claude_mcp == cowork_mcp


# --- hard-error paths ---------------------------------------------------------


def test_unknown_client_is_hard_error(tmp_path):
    with pytest.raises(BuildError, match="unknown client"):
        build_all(
            TESTDATA,
            tmp_path / "dist",
            marketplace_path=MARKETPLACE,
            clients=("bogus",),
            version=VERSION,
        )


def test_requested_plugin_not_declared_is_hard_error():
    decl = load_marketplace_toml(MARKETPLACE)
    with pytest.raises(BuildError, match="not declared"):
        discover_plugins(TESTDATA, decl, ["not-a-real-plugin"])


def test_plugin_missing_source_dir_is_hard_error():
    decl = load_marketplace_toml(MARKETPLACE)
    decl["plugins"].append(
        {
            "directory": "ghost",
            "name": "fixture-ghost",
            "description": "x",
            "category": "productivity",
        }
    )
    with pytest.raises(BuildError, match="plugin source missing"):
        discover_plugins(TESTDATA, decl, ["ghost"])


def test_new_tool_mappings():
    from build.tools import load_tool_config

    _, tool_map = load_tool_config()
    assert tool_map["SendMessage"] == ["send_message"]
    assert tool_map["TaskCreate"] == ["manage_task"]
    assert tool_map["TaskGet"] == ["manage_task"]
    assert tool_map["TaskList"] == ["manage_task"]
    assert tool_map["TaskUpdate"] == ["manage_task"]
    assert tool_map["TaskStop"] == ["manage_task"]
    assert tool_map["Skill"] == []
    assert tool_map["ToolSearch"] == []


def test_scoped_tool_translation_and_warning(capsys, tmp_path):
    import yaml

    from build.clients.agy import adapt as adapt_agy
    from build.clients.claude import adapt as adapt_claude
    from build.context import BuildContext, Plugin

    plugin_dir = tmp_path / "scoped-tool-plugin"
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "scoped.md").write_text(
        "---\nname: scoped\ndescription: Scoped agent\ntools:\n  - Bash(agy *)\n---\n\nBody",
        encoding="utf-8",
    )

    ctx_claude = BuildContext(
        plugin=Plugin(
            directory="scoped-tool-plugin",
            marketplace_name="scoped-tool",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="claude",
        version=VERSION,
        manifests={"plugin": {"name": "scoped-tool"}},
    )
    adapt_claude(plugin_dir, ctx_claude)
    claude_res = yaml.safe_load((agents_dir / "scoped.md").read_text().split("---")[1])
    assert claude_res["tools"] == ["Bash(agy *)"]

    ctx_agy = BuildContext(
        plugin=Plugin(
            directory="scoped-tool-plugin",
            marketplace_name="scoped-tool",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="agy",
        version=VERSION,
        manifests={"plugin": {"name": "scoped-tool"}},
    )
    adapt_agy(plugin_dir, ctx_agy)
    captured = capsys.readouterr()
    assert (
        "warning: scoped-tool/scoped: 'Bash(agy *)' scope dropped for agy; run_command is unrestricted"
        in captured.out
        or captured.err
    )
    agy_res = yaml.safe_load((agents_dir / "scoped.md").read_text().split("---")[1])
    assert agy_res["tools"] == ["run_command"]


def test_disallowed_tools_subtraction(tmp_path):
    import yaml

    from build.clients.agy import adapt as adapt_agy
    from build.clients.claude import adapt as adapt_claude
    from build.context import BuildContext, Plugin
    from build.tools import load_tool_config

    accepted_tools, _ = load_tool_config()

    # Case 1: explicit tools + disallowedTools
    plugin_dir1 = tmp_path / "disallowed-explicit"
    agents_dir1 = plugin_dir1 / "agents"
    agents_dir1.mkdir(parents=True)
    (agents_dir1 / "agent1.md").write_text(
        "---\nname: agent1\ndescription: Explicit tools\ntools:\n  - Read\n  - Write\ndisallowedTools: Write\n---\n\nBody",
        encoding="utf-8",
    )
    ctx1 = BuildContext(
        plugin=Plugin(
            directory="disallowed-explicit",
            marketplace_name="disallowed-explicit",
            description="desc",
            category="productivity",
            source_dir=plugin_dir1,
        ),
        client="agy",
        version=VERSION,
        manifests={"plugin": {"name": "disallowed-explicit"}},
    )
    adapt_agy(plugin_dir1, ctx1)
    res1 = yaml.safe_load((agents_dir1 / "agent1.md").read_text().split("---")[1])
    assert res1["tools"] == ["view_file"]
    assert "disallowedTools" not in res1

    # Case 2: no tools key + disallowedTools (subtraction from all 54)
    plugin_dir2 = tmp_path / "disallowed-implicit"
    agents_dir2 = plugin_dir2 / "agents"
    agents_dir2.mkdir(parents=True)
    (agents_dir2 / "agent2.md").write_text(
        "---\nname: agent2\ndescription: Implicit tools\ndisallowedTools: Write, Edit\n---\n\nBody",
        encoding="utf-8",
    )
    ctx2 = BuildContext(
        plugin=Plugin(
            directory="disallowed-implicit",
            marketplace_name="disallowed-implicit",
            description="desc",
            category="productivity",
            source_dir=plugin_dir2,
        ),
        client="agy",
        version=VERSION,
        manifests={"plugin": {"name": "disallowed-implicit"}},
    )
    adapt_agy(plugin_dir2, ctx2)
    res2 = yaml.safe_load((agents_dir2 / "agent2.md").read_text().split("---")[1])
    expected_tools = [
        t for t in accepted_tools if t not in ("write_to_file", "replace_file_content")
    ]
    assert res2["tools"] == expected_tools
    assert len(res2["tools"]) == len(expected_tools)
    assert "disallowedTools" not in res2

    # Case 3: claude retains disallowedTools unchanged
    plugin_dir3 = tmp_path / "disallowed-claude"
    agents_dir3 = plugin_dir3 / "agents"
    agents_dir3.mkdir(parents=True)
    (agents_dir3 / "agent3.md").write_text(
        "---\nname: agent3\ndescription: Implicit tools\ndisallowedTools: Write, Edit\n---\n\nBody",
        encoding="utf-8",
    )
    ctx3_claude = BuildContext(
        plugin=Plugin(
            directory="disallowed-claude",
            marketplace_name="disallowed-claude",
            description="desc",
            category="productivity",
            source_dir=plugin_dir3,
        ),
        client="claude",
        version=VERSION,
        manifests={"plugin": {"name": "disallowed-claude"}},
    )
    adapt_claude(plugin_dir3, ctx3_claude)
    res3_claude = yaml.safe_load((agents_dir3 / "agent3.md").read_text().split("---")[1])
    assert res3_claude["disallowedTools"] == "Write, Edit"


def test_mcpservers_dropped_for_agy_kept_for_claude(tmp_path):
    import yaml

    from build.clients.agy import adapt as adapt_agy
    from build.clients.claude import adapt as adapt_claude
    from build.context import BuildContext, Plugin

    plugin_dir = tmp_path / "mcp-agent-plugin"
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "mcpagent.md").write_text(
        "---\nname: mcpagent\ndescription: MCP agent\nmcpServers:\n  - services\n  - pkb\n---\n\nBody",
        encoding="utf-8",
    )

    ctx_claude = BuildContext(
        plugin=Plugin(
            directory="mcp-agent-plugin",
            marketplace_name="mcp-agent",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="claude",
        version=VERSION,
        manifests={"plugin": {"name": "mcp-agent"}},
    )
    adapt_claude(plugin_dir, ctx_claude)
    res_claude = yaml.safe_load((agents_dir / "mcpagent.md").read_text().split("---")[1])
    assert res_claude["mcpServers"] == ["services", "pkb"]

    ctx_agy = BuildContext(
        plugin=Plugin(
            directory="mcp-agent-plugin",
            marketplace_name="mcp-agent",
            description="desc",
            category="productivity",
            source_dir=plugin_dir,
        ),
        client="agy",
        version=VERSION,
        manifests={"plugin": {"name": "mcp-agent"}},
    )
    adapt_agy(plugin_dir, ctx_agy)
    res_agy = yaml.safe_load((agents_dir / "mcpagent.md").read_text().split("---")[1])
    assert "mcpServers" not in res_agy
    assert "hidden" not in res_agy
    assert "includeSections" not in res_agy


def test_pauli_agy_frontmatter(tmp_path):
    import yaml

    from build.tools import load_tool_config

    dist_root = tmp_path / "dist"
    build_all(
        PROJECT_ROOT,
        dist_root,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["aops-core"],
        version=VERSION,
    )

    pauli_md = dist_root / "aops-core-agy" / "agents" / "pauli.md"
    assert pauli_md.is_file()
    fm, _, _ = pauli_md.read_text().partition("---\n")[2].partition("---\n")
    agent = yaml.safe_load(fm)

    assert agent["name"] == "pauli"
    assert "mcpServers" not in agent
    accepted_tools, _ = load_tool_config()
    assert agent["tools"] == accepted_tools
    assert "hidden" not in agent
    assert "includeSections" not in agent
    assert "call_mcp_tool" not in agent["tools"]


def test_openclaw_dist_built_and_packaged(tmp_path):
    dist_root = tmp_path / "dist"
    build_all(
        PROJECT_ROOT,
        dist_root,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["aops-core", "orchestrate"],
        clients=("claude", "agy", "openclaw"),
        version=VERSION,
    )

    openclaw_root = dist_root / "openclaw"
    assert openclaw_root.is_dir()

    # Verify directory marketplace manifest
    manifest_path = openclaw_root / ".claude-plugin" / "marketplace.json"
    assert manifest_path.is_file()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["name"] == "academicOps-openclaw"
    assert {p["name"] for p in data["plugins"]} == {"aops-core", "orchestrate"}
    for p in data["plugins"]:
        assert p["source"] == f"./{p['name']}"
        assert p["version"] == VERSION

    # Verify per-plugin directories and zip packages
    for name in ("aops-core", "orchestrate"):
        plugin_dir = openclaw_root / name
        assert plugin_dir.is_dir()
        assert (plugin_dir / ".claude-plugin" / "plugin.json").is_file()

        zip_path = openclaw_root / f"{name}-v{VERSION}.zip"
        assert zip_path.is_file()
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert f"{name}/.claude-plugin/plugin.json" in names

    # Verify openclaw dist directory
    assert (dist_root / "aops-core-openclaw" / ".claude-plugin" / "plugin.json").is_file()
    assert (dist_root / "aops-core-openclaw.tar.gz").is_file()


def test_openclaw_does_not_bake_urls(tmp_path):
    dist_root = tmp_path / "dist"
    build_all(
        PROJECT_ROOT,
        dist_root,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["aops-core"],
        clients=("claude", "openclaw"),
        version=VERSION,
    )

    claude_mcp = (dist_root / "aops-core-claude" / ".mcp.json").read_bytes()
    openclaw_mcp = (dist_root / "openclaw" / "aops-core" / ".mcp.json").read_bytes()
    assert claude_mcp == openclaw_mcp


def test_openclaw_ida_face_configuration(tmp_path):
    import yaml

    dist_root = tmp_path / "dist"
    build_all(
        PROJECT_ROOT,
        dist_root,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["aops-core"],
        clients=("openclaw",),
        version=VERSION,
    )

    ida_md = dist_root / "aops-core-openclaw" / "agents" / "ida.md"
    assert ida_md.is_file()
    fm, _, body = ida_md.read_text().partition("---\n")[2].partition("---\n")
    agent = yaml.safe_load(fm)

    assert agent["name"] == "ida"
    assert "strategic face" in agent["description"]
    assert "# Ida" in body
