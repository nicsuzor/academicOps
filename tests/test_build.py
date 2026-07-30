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
from build.includes import resolve_includes
from build.manifest import merge_one_level, render_template
from build.marketplace import load_marketplace_toml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTDATA = PROJECT_ROOT / "build" / "testdata"
MARKETPLACE = TESTDATA / "marketplace.toml"
VERSION = "0.0.0-test"


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    dist_root = tmp_path_factory.mktemp("build-dist")
    build_all(TESTDATA, dist_root, marketplace_path=MARKETPLACE, version=VERSION)
    return dist_root


# --- stage 1/2: shared injection + include resolution -----------------------


def test_shared_directory_injected_both_clients(built):
    for client in ("claude", "agy"):
        base = built / f"fixture-alpha-{client}"
        assert (base / "doctrine" / "base.md").is_file()
        assert (base / "doctrine" / "greeting.md").is_file()


def test_shared_single_file_injected_both_clients(built):
    for client in ("claude", "agy"):
        assert (built / f"fixture-alpha-{client}" / "hooks" / "hook.py").is_file()


def test_recursive_include_resolved(built):
    content = (built / "fixture-alpha-claude" / "commands" / "greet.md").read_text()
    assert "@include" not in content
    assert "Body of the base fixture doctrine." in content
    assert "before the include" in content
    assert "after the include" in content


def test_missing_include_target_is_hard_error(tmp_path):
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    with pytest.raises(BuildError, match="not found"):
        resolve_includes("@include nope.md\n", lib_dir, "origin.md")


def test_include_cycle_is_hard_error(tmp_path):
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "a.md").write_text("@include b.md\n")
    (lib_dir / "b.md").write_text("@include a.md\n")
    with pytest.raises(BuildError, match="cycle"):
        resolve_includes("@include a.md\n", lib_dir, "origin.md")


# --- stage 3: manifest rendering --------------------------------------------


def _template(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "hooks.template.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_versioned_template_renders_the_client_section(tmp_path):
    """The versioned shape nests client sections under `clients`, keeping the
    top level for plugin identity. Reading the client key at the top level
    instead finds nothing and renders every event away — the plugin builds
    clean and ships with no hooks.json at all."""
    path = _template(
        tmp_path,
        {
            "manifestVersion": "1.0",
            "name": "aops-debug",
            "version": "0.1.0",
            "clients": {
                "claude": {"hooks": {"SessionStart": [], "Stop": []}},
                "agy": {"hooks": {"PreToolUse": []}},
            },
        },
    )
    assert sorted(render_template(path, "claude")["hooks"]) == ["SessionStart", "Stop"]
    assert sorted(render_template(path, "agy")["hooks"]) == ["PreToolUse"]


def test_both_template_shapes_merge_base_the_same_way(tmp_path):
    """`__base__` merging is the shapes' only shared contract, so migrating a
    template between them must not change what it renders."""
    sections = {"__base__": {"hooks": {"Stop": []}}, "claude": {"hooks": {"SessionStart": []}}}
    expected = {"hooks": {"Stop": [], "SessionStart": []}}

    flat = _template(tmp_path, sections)
    assert render_template(flat, "claude") == expected

    versioned = _template(tmp_path, {"manifestVersion": "1.0", "clients": sections})
    assert render_template(versioned, "claude") == expected


def test_versioned_template_without_clients_is_a_hard_error(tmp_path):
    """Rendering it empty would be indistinguishable from a plugin that
    genuinely has no hooks on any client."""
    path = _template(tmp_path, {"manifestVersion": "1.0", "name": "aops-debug"})
    with pytest.raises(BuildError, match="clients"):
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


def test_claude_tarball_contains_directory_prefix(built):
    with tarfile.open(built / "fixture-alpha-claude.tar.gz") as tar:
        names = tar.getnames()
    assert all(n == "fixture-alpha-claude" or n.startswith("fixture-alpha-claude/") for n in names)


def test_agy_tarball_flattens_to_root(built):
    with tarfile.open(built / "fixture-alpha-agy.tar.gz") as tar:
        names = tar.getnames()
    assert all(n == "." or n.startswith("./") for n in names)
    assert "./plugin.json" in names


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
