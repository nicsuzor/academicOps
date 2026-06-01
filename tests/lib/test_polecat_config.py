"""Tests for aops-core/lib/polecat_config.py — the SSoT config loader."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from textwrap import dedent

import pytest
from lib.polecat_config import (
    BUILTIN_SESSION_DEFAULTS,
    CONFIG_PATH_ENV,
    PolecatConfig,
    load_polecat_config,
)

CANONICAL_YAML = dedent(
    """
    session_defaults:
      hooks_enabled: true
      claude_model: claude-sonnet-4-6
      antigravity_model: agy
      debug: false
      gates:
        handover: warn
        qa: warn
        enforcer: warn
        hydration: off
        ida: warn
        enforcer_threshold: 50
    crew_defaults:
      hooks_enabled: false
    run_defaults: {}
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


@pytest.fixture
def cfg_path(tmp_path: Path) -> Path:
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML)
    return p


def test_load_canonical(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    assert isinstance(cfg, PolecatConfig)
    assert cfg.session_defaults.hooks_enabled is True
    assert cfg.session_defaults.claude_model == "claude-sonnet-4-6"
    assert cfg.session_defaults.antigravity_model == "agy"
    assert cfg.session_defaults.model_for("claude") == "claude-sonnet-4-6"
    assert cfg.session_defaults.model_for("antigravity") == "agy"
    assert cfg.session_defaults.debug is False
    assert cfg.session_defaults.gates.handover == "warn"
    assert cfg.session_defaults.gates.hydration == "off"
    assert cfg.session_defaults.gates.enforcer_threshold == 50
    assert cfg.docker.image == "ghcr.io/nicsuzor/aops-crew"
    assert cfg.external_agents["github"].enabled is True
    assert cfg.external_agents["jules"].enabled is False


def test_container_env_forward_defaults_when_absent(cfg_path: Path) -> None:
    # CANONICAL_YAML has no container_env_forward → built-in default (the OAuth
    # tokens). This is the "limited list" for hold-for-delegation secrets.
    cfg = load_polecat_config(cfg_path)
    assert cfg.container_env_forward == (
        "CLAUDE_CODE_OAUTH_TOKEN",
        "AOPS_CC_OAUTH_TOKEN",
        "GEMINI_API_KEY",
    )


def test_container_env_forward_explicit_list(tmp_path: Path) -> None:
    p = tmp_path / "polecat.yaml"
    p.write_text(
        CANONICAL_YAML
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


def test_for_mode_crew_overlays_hooks(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    crew = cfg.for_mode("crew")
    assert crew.hooks_enabled is False
    assert crew.claude_model == "claude-sonnet-4-6"  # inherited
    assert crew.antigravity_model == "agy"  # inherited
    run = cfg.for_mode("run")
    assert run.hooks_enabled is True  # falls through to session_defaults


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
        cfg.session_defaults.model_for("openai")


def test_overrides_supports_dotted_gates_key(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    overridden = cfg.with_overrides("run", {"gates.handover": "block"})
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
    p.write_text(
        dedent(
            """
            session_defaults:
              hooks_enabled: true
              claude_model: foo
              antigravity_model: agy
              debug: false
              gates:
                handover: warn
                qa: warn
                enforcer: warn
                hydration: off
                ida: warn
                enforcer_threshold: 50
            crew_defaults: {}
            run_defaults: {}
            # docker missing
            """
        ).strip()
    )
    with pytest.raises(RuntimeError, match="missing or non-mapping 'docker'"):
        load_polecat_config(p)


def test_invalid_gate_mode_at_load_hard_fails(tmp_path: Path) -> None:
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML.replace("handover: warn", "handover: maybe"))
    with pytest.raises(ValueError, match="invalid gate mode for 'handover'"):
        load_polecat_config(p)


def test_missing_per_mode_overlay_hard_fails(tmp_path: Path) -> None:
    p = tmp_path / "polecat.yaml"
    p.write_text(CANONICAL_YAML.replace("run_defaults: {}", ""))
    with pytest.raises(RuntimeError, match="'run_defaults' block missing"):
        load_polecat_config(p)


def test_env_var_path_resolution(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "elsewhere.yaml"
    p.write_text(CANONICAL_YAML)
    monkeypatch.setenv(CONFIG_PATH_ENV, str(p))
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    cfg = load_polecat_config()
    assert cfg.source_path == p


def test_aops_sessions_default(tmp_path: Path, monkeypatch) -> None:
    sessions = tmp_path / "sess-cfg"
    sessions.mkdir()
    (sessions / "polecat.yaml").write_text(CANONICAL_YAML)
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions))
    monkeypatch.delenv(CONFIG_PATH_ENV, raising=False)
    cfg = load_polecat_config()
    assert cfg.session_defaults.claude_model == "claude-sonnet-4-6"
    assert cfg.session_defaults.antigravity_model == "agy"


def test_unset_env_returns_builtin_defaults(monkeypatch) -> None:
    monkeypatch.delenv(CONFIG_PATH_ENV, raising=False)
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    cfg = load_polecat_config()
    assert isinstance(cfg, PolecatConfig)
    assert cfg.source_path.name == "<builtin>"
    assert cfg.session_defaults == BUILTIN_SESSION_DEFAULTS
    assert cfg.session_defaults.gates.handover == "warn"


def test_dataclasses_are_frozen(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.session_defaults.hooks_enabled = False  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.session_defaults.gates.handover = "block"  # type: ignore[misc]
