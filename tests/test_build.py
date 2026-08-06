"""Tests for the academicOps build system (build/build.py).

Runs the real builder against the fixture plugins in build/testdata/ (two
throwaway plugins, "alpha" and "beta" — see build/testdata/marketplace.toml)
and asserts the output tree for both clients. plugins/ and lib/ don't exist
in the real repo yet, so these fixtures are the only thing exercising the
builder end to end until they land.
"""

import json
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
    """The real orchestrate plugin, not a fixture — see
    test_polecat_cli_ships_with_orchestrate."""
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
    """James invokes `${CLAUDE_PLUGIN_ROOT}/polecat/cli.py` via
    `skills/dispatch` (`plugins/orchestrate/agents/james.md`,
    `plugins/orchestrate/skills/dispatch/SKILL.md`), and that path is true only
    because `plugins/orchestrate/manifest/plugin.toml` injects it from
    `lib/polecat/`.

    Drop those `[[shared]]` stanzas and nothing fails at build time. Dispatch
    fails at runtime, inside a container, with file-not-found. This is the check
    that turns that into a build-time failure instead.
    """
    for client in ("claude", "agy"):
        polecat = built_orchestrate / f"orchestrate-{client}" / "polecat"
        assert (polecat / "cli.py").is_file(), f"orchestrate-{client} ships no polecat/cli.py"
        assert (polecat / "env_contract.py").is_file(), (
            f"orchestrate-{client} ships cli.py without the env_contract it imports"
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


def _agy_ctx(tmp_path, directory="pkb", name="aops-pkb"):
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
        plugins=["ida"],
        version=VERSION,
    )

    import yaml

    # Check agy dist saves agents/ida.md directly as agents/ida.md (agy's own
    # read format — see build/clients/agy.py's _adapt_agents docstring).
    agy_ida_md = dist_root / "ida-agy" / "agents" / "ida.md"
    assert agy_ida_md.is_file()
    assert not (dist_root / "ida-agy" / "agents" / "ida" / "agent.md").exists()

    raw = agy_ida_md.read_text()
    fm, _, body = raw.partition("---\n")[2].partition("---\n")
    agy_agent = yaml.safe_load(fm)
    assert agy_agent["name"] == "ida"
    assert "interactive face" in agy_agent["description"]
    assert agy_agent["hidden"] is False

    # plugins/ida/agents/ida.md sets no `tools:` — Claude Code semantics is
    # "unrestricted", and the agy output must not narrow that to zero tools.
    assert "tools" not in agy_agent

    body = body.lstrip("\n")
    assert body.startswith("# Agent System Instructions")
    assert "# Ida — The Interactive Face" in body


def test_agy_agent_tool_names_are_translated(built):
    """The tool-name map, against the fixture agent rather than a real one.

    Which tools a shipped agent is granted is a permission decision that moves —
    grants are currently cleared and are being restored one at a time — so a
    production agent's `tools:` list is the wrong subject for a test about the
    build's rename map. The fixture agent carries a list chosen to cover both
    branches instead.
    """
    import yaml

    claude_agent = built / "fixture-alpha-claude" / "agents" / "alpha-agent.md"
    claude_fm = yaml.safe_load(claude_agent.read_text().split("---")[1])
    assert claude_fm["tools"] == ["Read", "Skill", "Agent", "AskUserQuestion", "Dispatch"]

    agy_agent = built / "fixture-alpha-agy" / "agents" / "alpha-agent.md"
    agy_fm = yaml.safe_load(agy_agent.read_text().split("---")[1])
    # `Skill` and `Dispatch` have no entry in the agy tool map, so they cross
    # untranslated — the map renames what agy calls by another name and leaves
    # everything else alone.
    assert agy_fm["tools"] == [
        "read_file",
        "Skill",
        "invoke_subagent",
        "ask_question",
        "Dispatch",
    ]


def test_agy_agent_without_tools_key_ships_unrestricted(built_orchestrate):
    """plugins/orchestrate/agents/james.md sets no `tools:` key at all — full,
    unrestricted access in Claude Code. The agy build must not narrow that to
    an empty list: `tools: []` reads to agy as "grant nothing", not "no
    opinion", so a forced-empty default silently zeroed every such agent's
    tool access on agy.
    """
    import yaml

    agy_agent = built_orchestrate / "orchestrate-agy" / "agents" / "james.md"
    agy_fm = yaml.safe_load(agy_agent.read_text().split("---")[1])
    assert "tools" not in agy_fm


def test_agy_agent_drops_claude_model_name(built_orchestrate):
    """plugins/orchestrate/agents/james.md pins `model: opus` — a Claude Code
    model name absent from agy's own set (`agy models`). Forwarding it
    verbatim doesn't degrade gracefully: agy silently drops an agent whose
    frontmatter names a model it doesn't recognize, confirmed by direct
    behavioral test. There is no reliable opus/sonnet -> agy-model mapping to
    substitute, so the field must be absent, not translated.
    """
    import yaml

    agy_agent = built_orchestrate / "orchestrate-agy" / "agents" / "james.md"
    agy_fm = yaml.safe_load(agy_agent.read_text().split("---")[1])
    assert "model" not in agy_fm
    # `color` has no such failure mode and is not agy-specific handling —
    # it should still cross untouched.
    assert agy_fm["color"] == "orange"


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
