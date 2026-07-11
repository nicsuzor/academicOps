"""Tests for aops-core/lib/polecat_config.py — the SSoT config loader.

Schema is FOUR explicit, independently-required per-surface sections (face,
crew, worker, subagent) — no overlay, no shared "defaults" base
(note_296e5520 §4). Every section has the identical full shape; nothing is
inherited between them.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from textwrap import dedent

import pytest
from lib.polecat_config import (
    CONFIG_PATH_ENV,
    SURFACES,
    PolecatConfig,
    load_polecat_config,
    resolve_polecat_home,
)

_SURFACE_BLOCK = dedent(
    """
    hooks_enabled: true
    claude_model: claude-sonnet-4-6
    gemini_model: gemini-3.1-pro-preview
    antigravity_model: agy
    debug: false
    gates:
      handover: warn
      qa: warn
      rbg: warn
      hydration: off
      ida: warn
      rbg_review: off
      rbg_threshold: 15
    """
).strip("\n")


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in text.splitlines())


def _surfaces_block(blocks: dict[str, str] | None = None) -> str:
    """Render all four `<surface>:\\n  <block>` sections (no dedent — the
    interpolated blocks already carry their own indentation, which `dedent`
    would corrupt by computing a common-whitespace prefix across differently
    indented lines)."""
    blocks = blocks or {}
    parts = []
    for name in ("face", "crew", "worker", "subagent"):
        parts.append(f"{name}:\n{_indent(blocks.get(name, _SURFACE_BLOCK), 2)}")
    return "\n".join(parts)


CANONICAL_YAML = (
    _surfaces_block()
    + "\n"
    + dedent(
        """
        docker:
          image: ghcr.io/nicsuzor/aops-crew
        external_agents:
          github:
            enabled: true
            workflows: [agent-qa]
          jules:
            enabled: false
        """
    ).strip()
)


@pytest.fixture
def cfg_path(tmp_path: Path) -> Path:
    # polecat_home is now a REQUIRED key. Point it at tmp_path so overlay tests
    # can drop a local.yaml beside it; tmp_path has none by default (machine None).
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML + f"\npolecat_home: {tmp_path}\n")
    return p


def test_load_canonical(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    assert isinstance(cfg, PolecatConfig)
    assert cfg.face.hooks_enabled is True
    assert cfg.face.claude_model == "claude-sonnet-4-6"
    assert cfg.face.gemini_model == "gemini-3.1-pro-preview"
    assert cfg.face.antigravity_model == "agy"
    assert cfg.face.model_for("claude") == "claude-sonnet-4-6"
    assert cfg.face.model_for("gemini") == "gemini-3.1-pro-preview"
    assert cfg.face.model_for("antigravity") == "agy"
    assert cfg.face.debug is False
    assert cfg.face.gates.handover == "warn"
    assert cfg.face.gates.hydration == "off"
    assert cfg.face.gates.rbg_threshold == 15
    assert cfg.docker.image == "ghcr.io/nicsuzor/aops-crew"
    assert cfg.external_agents["github"].enabled is True
    assert cfg.external_agents["jules"].enabled is False
    assert cfg.polecat_home == cfg_path.parent
    assert cfg.machine is None  # no local.yaml overlay present


def test_all_four_surfaces_present_and_equal_shape(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    assert set(SURFACES) == {"face", "crew", "worker", "subagent"}
    for name in SURFACES:
        sd = cfg.for_surface(name)
        assert sd.claude_model == "claude-sonnet-4-6"
        assert sd.gates.rbg_threshold == 15


def test_for_surface_rejects_unknown_name(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    with pytest.raises(ValueError, match="unknown surface"):
        cfg.for_surface("bogus")


def test_surfaces_are_independent_not_overlaid(tmp_path: Path) -> None:
    """No overlay/inheritance: crew can differ completely from face."""
    crew_block = _SURFACE_BLOCK.replace("hooks_enabled: true", "hooks_enabled: false").replace(
        "handover: warn", "handover: block"
    )
    yaml_text = (
        _surfaces_block({"crew": crew_block})
        + "\n"
        + dedent(
            """
        docker:
          image: ghcr.io/nicsuzor/aops-crew
        """
        ).strip()
    )
    p = tmp_path / "polecat.yaml"
    p.write_text(yaml_text + f"\npolecat_home: {tmp_path}\n")
    cfg = load_polecat_config(p)
    assert cfg.face.hooks_enabled is True
    assert cfg.crew.hooks_enabled is False
    assert cfg.crew.gates.handover == "block"
    assert cfg.face.gates.handover == "warn"  # unaffected by crew's override


def test_container_env_forward_defaults_when_absent(cfg_path: Path) -> None:
    # CANONICAL_YAML has no container_env_forward → built-in default (the OAuth
    # tokens). This is the "limited list" for hold-for-delegation secrets.
    cfg = load_polecat_config(cfg_path)
    assert cfg.container_env_forward == (
        "CLAUDE_CODE_OAUTH_TOKEN",
        "AOPS_CC_OAUTH_TOKEN",
        "GEMINI_API_KEY",
        "PKB_MCP_URL",
        "AOPS_BOT_GH_TOKEN",
    )


def test_container_env_forward_explicit_list(tmp_path: Path) -> None:
    p = tmp_path / "polecat.yaml"
    p.write_text(
        CANONICAL_YAML
        + f"\npolecat_home: {tmp_path}\n"
        + dedent(
            """
            container_env_forward:
              - CLAUDE_CODE_OAUTH_TOKEN
              - GEMINI_API_KEY
              - SOME_OTHER_NAME
            """
        )
    )
    cfg = load_polecat_config(p)
    assert cfg.container_env_forward == (
        "CLAUDE_CODE_OAUTH_TOKEN",
        "GEMINI_API_KEY",
        "SOME_OTHER_NAME",
    )


def test_container_env_forward_rejects_values_with_equals(tmp_path: Path) -> None:
    # Guard: operators must list NAMES, never values. A '=' (i.e. someone pasted
    # NAME=secretvalue) is a hard load-time failure — secrets live in ~/.env.local.
    p = tmp_path / "polecat.yaml"
    p.write_text(
        CANONICAL_YAML
        + dedent(
            """
            container_env_forward:
              - CLAUDE_CODE_OAUTH_TOKEN=sk-leaked-secret
            """
        )
    )
    with pytest.raises(RuntimeError, match="container_env_forward must list var NAMES"):
        load_polecat_config(p)


def test_container_env_forward_rejects_non_list(tmp_path: Path) -> None:
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML + "\ncontainer_env_forward: CLAUDE_CODE_OAUTH_TOKEN\n")
    with pytest.raises(RuntimeError, match="must be a list of strings"):
        load_polecat_config(p)


def test_overrides_via_with_overrides(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    overridden = cfg.with_overrides(
        "crew", {"hooks_enabled": True, "claude_model": "opus", "antigravity_model": "agy-fast"}
    )
    assert overridden.hooks_enabled is True
    assert overridden.claude_model == "opus"
    assert overridden.antigravity_model == "agy-fast"


def test_model_for_rejects_unknown_client(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    with pytest.raises(ValueError, match="unknown client"):
        cfg.face.model_for("openai")


def test_overrides_supports_dotted_gates_key(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    overridden = cfg.with_overrides("worker", {"gates.handover": "block"})
    assert overridden.gates.handover == "block"
    # Other gate fields preserved
    assert overridden.gates.qa == "warn"


def test_overrides_rejects_unknown_top_level_key(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    with pytest.raises(ValueError, match="unknown override key"):
        cfg.with_overrides("crew", {"bogus": 1})


def test_overrides_rejects_invalid_gate_mode(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    with pytest.raises(ValueError, match="invalid gate mode"):
        cfg.with_overrides("crew", {"gates.handover": "scream"})


def test_missing_file_hard_fails(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="file not found"):
        load_polecat_config(tmp_path / "no-such.yaml")


def test_missing_required_field_hard_fails(tmp_path: Path) -> None:
    p = tmp_path / "polecat.yaml"
    p.write_text(_surfaces_block())  # docker missing
    with pytest.raises(RuntimeError, match="missing or non-mapping 'docker'"):
        load_polecat_config(p)


@pytest.mark.parametrize("surface", ["face", "crew", "worker", "subagent"])
def test_missing_required_key_in_any_surface_hard_fails_the_whole_load(
    tmp_path: Path, surface: str
) -> None:
    """AC: removing a required key from ANY ONE surface section fails config
    load for every surface — there is no lazy/partial per-surface validation.
    This is the empirical proof behind the acceptance criterion 'removing any
    required key produces a hard error on every surface': the load is eager
    and whole-file, so whichever surface launches first hits the same error.
    """
    surfaces = {}
    for name in ("face", "crew", "worker", "subagent"):
        block = _SURFACE_BLOCK
        if name == surface:
            # Remove the required rbg_threshold key from this one surface.
            block = "\n".join(line for line in block.splitlines() if "rbg_threshold" not in line)
        surfaces[name] = block
    yaml_text = "\n".join(f"{name}:\n{_indent(block, 2)}" for name, block in surfaces.items())
    yaml_text += "\ndocker:\n  image: ghcr.io/nicsuzor/aops-crew\n"
    p = tmp_path / "polecat.yaml"
    p.write_text(yaml_text + f"\npolecat_home: {tmp_path}\n")
    with pytest.raises(ValueError, match="missing required gates.rbg_threshold"):
        load_polecat_config(p)


def test_invalid_gate_mode_at_load_hard_fails(tmp_path: Path) -> None:
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML.replace("handover: warn", "handover: maybe"))
    with pytest.raises(ValueError, match="invalid gate mode for 'handover'"):
        load_polecat_config(p)


def test_missing_surface_section_hard_fails(tmp_path: Path) -> None:
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML.replace("subagent:", "not_subagent:"))
    with pytest.raises(RuntimeError, match="missing or non-mapping 'subagent'"):
        load_polecat_config(p)


def test_env_var_path_resolution(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "elsewhere.yaml"
    p.write_text(CANONICAL_YAML + f"\npolecat_home: {tmp_path}\n")
    monkeypatch.setenv(CONFIG_PATH_ENV, str(p))
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    cfg = load_polecat_config()
    assert cfg.source_path == p


def test_aops_sessions_default(tmp_path: Path, monkeypatch) -> None:
    sessions = tmp_path / "sess-cfg"
    sessions.mkdir()
    (sessions / "polecat.yaml").write_text(CANONICAL_YAML + f"\npolecat_home: {sessions}\n")
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions))
    monkeypatch.delenv(CONFIG_PATH_ENV, raising=False)
    cfg = load_polecat_config()
    assert cfg.face.claude_model == "claude-sonnet-4-6"
    assert cfg.face.antigravity_model == "agy"


def test_unset_env_hard_fails(monkeypatch) -> None:
    # No builtin config, no warn-and-continue: unlocatable config is an error.
    monkeypatch.delenv(CONFIG_PATH_ENV, raising=False)
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    with pytest.raises(RuntimeError, match="is not set"):
        load_polecat_config()


def test_missing_polecat_home_hard_fails(tmp_path: Path) -> None:
    # polecat_home is required — no default, no env fallback, no guess.
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML)  # note: no polecat_home line
    with pytest.raises(RuntimeError, match="polecat_home"):
        load_polecat_config(p)


def test_polecat_home_expands_env_and_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PCHOME", str(tmp_path / "cache"))
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML + "\npolecat_home: ${PCHOME}\n")
    cfg = load_polecat_config(p)
    assert cfg.polecat_home == tmp_path / "cache"


def test_local_overlay_machine_and_gates(tmp_path: Path) -> None:
    # The per-machine local.yaml overlay supplies `machine:` and overrides
    # gates UNIFORMLY across all four surfaces.
    home = tmp_path / "home"
    home.mkdir()
    (home / "local.yaml").write_text("machine: dev-box\ngates:\n  handover: block\n")
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML + f"\npolecat_home: {home}\n")
    cfg = load_polecat_config(p)
    assert cfg.machine == "dev-box"
    assert cfg.face.gates.handover == "block"  # overlaid
    assert cfg.crew.gates.handover == "block"  # overlaid on every surface
    assert cfg.worker.gates.handover == "block"
    assert cfg.subagent.gates.handover == "block"
    assert cfg.face.gates.qa == "warn"  # untouched base value


def test_local_overlay_rejects_bad_gate_mode(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "local.yaml").write_text("gates:\n  handover: scream\n")
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML + f"\npolecat_home: {home}\n")
    with pytest.raises(ValueError, match="invalid gate mode"):
        load_polecat_config(p)


def test_resolve_polecat_home_via_env(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "cache"
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML + f"\npolecat_home: {home}\n")
    monkeypatch.setenv(CONFIG_PATH_ENV, str(p))
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    assert resolve_polecat_home() == home


def test_dataclasses_are_frozen(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.face.hooks_enabled = False  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.face.gates.handover = "block"  # type: ignore[misc]
