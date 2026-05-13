"""Tests for aops-core/lib/polecat_config.py — the SSoT config loader."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from textwrap import dedent

import pytest
from lib.polecat_config import (
    CONFIG_PATH_ENV,
    PolecatConfig,
    load_polecat_config,
)

CANONICAL_YAML = dedent(
    """
    session_defaults:
      hooks_enabled: true
      model: claude-sonnet-4-6
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
    assert cfg.session_defaults.model == "claude-sonnet-4-6"
    assert cfg.session_defaults.debug is False
    assert cfg.session_defaults.gates.handover == "warn"
    assert cfg.session_defaults.gates.hydration == "off"
    assert cfg.session_defaults.gates.enforcer_threshold == 50
    assert cfg.docker.image == "ghcr.io/nicsuzor/aops-crew"
    assert cfg.external_agents["github"].enabled is True
    assert cfg.external_agents["jules"].enabled is False


def test_for_mode_crew_overlays_hooks(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    crew = cfg.for_mode("crew")
    assert crew.hooks_enabled is False
    assert crew.model == "claude-sonnet-4-6"  # inherited
    run = cfg.for_mode("run")
    assert run.hooks_enabled is True  # falls through to session_defaults


def test_overrides_via_with_overrides(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    overridden = cfg.with_overrides("crew", {"hooks_enabled": True, "model": "opus"})
    assert overridden.hooks_enabled is True
    assert overridden.model == "opus"


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
              model: foo
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
    assert cfg.session_defaults.model == "claude-sonnet-4-6"


def test_unset_env_hard_fails(monkeypatch) -> None:
    monkeypatch.delenv(CONFIG_PATH_ENV, raising=False)
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    with pytest.raises(RuntimeError, match=r"\$AOPS_SESSIONS is not set"):
        load_polecat_config()


def test_dataclasses_are_frozen(cfg_path: Path) -> None:
    cfg = load_polecat_config(cfg_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.session_defaults.hooks_enabled = False  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.session_defaults.gates.handover = "block"  # type: ignore[misc]
