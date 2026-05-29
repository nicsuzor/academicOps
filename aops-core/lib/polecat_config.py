#!/usr/bin/env -S uv run python
"""Single source of truth for polecat / crew session configuration.

The whole framework — polecat (the docker runner) and aops-core (the hooks
running inside the resulting Claude/Gemini sessions) — reads its operational
defaults from one YAML file: ``$AOPS_SESSIONS/polecat.yaml`` (or the path
named by ``AOPS_POLECAT_CONFIG``).

Per AXIOMS A14 (fail-fast) and A16 (DRY, no defaults, no backwards-compat):
- Missing file ⇒ stderr warning + built-in defaults (see ``BUILTIN_SESSION_DEFAULTS``).
  This supports fresh-install machines where polecat.yaml has not been created yet.
  A present-but-malformed file still hard-fails (A14).
- No legacy env-var override paths. ``AOPS_POLECAT_CONFIG`` is the only env
  var that *names* the config; every config *value* lives in the YAML.
- CLI flags override the loaded config in-process; they do not mutate it.

Config locations (resolution order):

    1. ``$AOPS_POLECAT_CONFIG``                (explicit path; used to stage
                                                 the file inside containers)
    2. ``$AOPS_SESSIONS/polecat.yaml``         (host default)

Schema (see ``polecat/defaults/polecat.yaml.example`` for the canonical doc):

    session_defaults:                         # applied to every session
        hooks_enabled: bool                   # legacy field, must be true (#940)
        claude_model: str                     # model id passed to `claude --model`
        gemini_model: str                     # model id passed to `gemini --model`
        debug: bool                           # forwarded as DEBUG_HOOKS=1
        gates:
            handover: warn|block|off
            qa: warn|block|off
            enforcer: warn|block|off
            hydration: warn|block|off
            ida: warn|block|off            # Ida B. Wells reminder gate
            enforcer_threshold: int
    crew_defaults: {...}                          # overlay for `polecat crew`
    run_defaults:  {...}                          # overlay for `polecat run`
    docker:
        image: str
    external_agents:
        <name>: { enabled: bool, ... }

``hooks_enabled`` is retained in the schema for back-compat with existing
``polecat.yaml`` files but no longer branches behaviour: hooks are always
on, plan-mode is the only claude path, the vanilla settings template is
gone (issue #940). Setting it to false is silently ignored.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

# The single env var that *names* the config file. No env var holds a config
# *value*. Polecat sets this when staging the file into a container.
CONFIG_PATH_ENV = "AOPS_POLECAT_CONFIG"

# Permitted gate verdict modes. Anything else ⇒ ValueError at load time.
_GATE_MODES = frozenset({"warn", "block", "off"})


@dataclass(frozen=True)
class GatesConfig:
    handover: str
    qa: str
    enforcer: str
    hydration: str
    ida: str
    enforcer_threshold: int


@dataclass(frozen=True)
class SessionDefaults:
    hooks_enabled: bool
    claude_model: str
    gemini_model: str
    debug: bool
    gates: GatesConfig

    def model_for(self, client: str) -> str:
        """Return the model id for the given client (``claude`` or ``gemini``)."""
        if client == "claude":
            return self.claude_model
        if client == "gemini":
            return self.gemini_model
        raise ValueError(f"unknown client: {client!r} (expected 'claude' or 'gemini')")


@dataclass(frozen=True)
class DockerConfig:
    image: str


@dataclass(frozen=True)
class ExternalAgent:
    name: str
    enabled: bool
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolecatConfig:
    """Frozen, fully-resolved session config.

    Two-level access:
        cfg.session_defaults.<key>      — global defaults
        cfg.for_mode("crew").<key>      — defaults overlaid with crew/run block

    ``for_mode`` returns a new ``SessionDefaults`` with the per-mode overrides
    applied; the underlying config is never mutated.
    """

    session_defaults: SessionDefaults
    crew_defaults: dict[str, Any]
    run_defaults: dict[str, Any]
    docker: DockerConfig
    external_agents: dict[str, ExternalAgent]
    source_path: Path
    # Explicit container forwarding whitelist (PKB note-b5347f83, Q2). The
    # legible "limited list" of env-var NAMES that cross into polecat/crew
    # containers. NAMES only — VALUES are resolved at launch from the host
    # secret store (~/.env.local) by lib/host_secrets, NEVER committed here.
    # This is the canonical source of "what the container gets" for secrets the
    # launching session deliberately does not hold (OAuth tokens).
    container_env_forward: tuple[str, ...] = ()

    def for_mode(self, mode: str) -> SessionDefaults:
        if mode == "crew":
            overlay = self.crew_defaults
        elif mode == "run":
            overlay = self.run_defaults
        else:
            raise ValueError(f"unknown session mode: {mode!r} (expected 'crew' or 'run')")
        return _apply_overlay(self.session_defaults, overlay)

    def with_overrides(self, mode: str, overrides: dict[str, Any]) -> SessionDefaults:
        """Return ``for_mode(mode)`` with CLI-supplied overrides applied."""
        return _apply_overlay(self.for_mode(mode), overrides)


def _apply_overlay(base: SessionDefaults, overlay: dict[str, Any]) -> SessionDefaults:
    """Apply a shallow overlay dict to a SessionDefaults instance.

    Supports nested ``gates.<name>`` keys. Unknown keys ⇒ ValueError.
    """
    if not overlay:
        return base
    patch: dict[str, Any] = {}
    gates_patch: dict[str, Any] = {}
    for key, value in overlay.items():
        if key == "gates" and isinstance(value, dict):
            gates_patch.update(value)
            continue
        if "." in key:
            head, tail = key.split(".", 1)
            if head != "gates":
                raise ValueError(f"unsupported nested override: {key!r}")
            gates_patch[tail] = value
            continue
        if key not in {"hooks_enabled", "claude_model", "gemini_model", "debug"}:
            raise ValueError(f"unknown override key: {key!r}")
        patch[key] = value
    if gates_patch:
        new_gates = replace(base.gates, **_validate_gates(gates_patch, allow_partial=True))
        patch["gates"] = new_gates
    return replace(base, **patch)


def _validate_gates(raw: dict[str, Any], allow_partial: bool = False) -> dict[str, Any]:
    """Coerce + validate the ``gates`` block.

    ``allow_partial`` is True when applying CLI overrides (only specified keys
    are validated); False when loading the YAML (all keys required).
    """
    out: dict[str, Any] = {}
    for name in ("handover", "qa", "enforcer", "hydration", "ida"):
        if name in raw:
            raw_value = raw[name]
            # YAML 1.1 parses bare `off` / `on` as booleans. Translate False→"off"
            # so users can write `hydration: off` without quoting. Bare True has
            # no meaningful gate mode and is rejected.
            if raw_value is False:
                value = "off"
            elif raw_value is True:
                raise ValueError(
                    f"invalid gate mode for {name!r}: True; expected one of {sorted(_GATE_MODES)}"
                )
            else:
                value = str(raw_value).lower()
            if value not in _GATE_MODES:
                raise ValueError(
                    f"invalid gate mode for {name!r}: {raw[name]!r}; "
                    f"expected one of {sorted(_GATE_MODES)}"
                )
            out[name] = value
        elif not allow_partial:
            raise ValueError(f"missing required gates.{name}")
    if "enforcer_threshold" in raw:
        val = raw["enforcer_threshold"]
        try:
            out["enforcer_threshold"] = int(val)
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                f"polecat config: gates.enforcer_threshold must be an integer"
                f" (got {type(val).__name__}: {val!r})"
            ) from exc
    elif not allow_partial:
        raise ValueError("missing required gates.enforcer_threshold")
    unknown = set(raw) - {
        "handover",
        "qa",
        "enforcer",
        "hydration",
        "ida",
        "enforcer_threshold",
    }
    if unknown:
        raise ValueError(f"unknown gates keys: {sorted(unknown)}")
    return out


# =============================================================================
# BUILT-IN DEFAULTS
# =============================================================================
# Used when no polecat.yaml is found (fresh install / minimal test environments
# that have not set up $AOPS_SESSIONS). These values are the same as the
# example YAML defaults. YAML config always overrides them — they are never
# silently preferred over explicit configuration.
#
# Gate modes: all 'warn' except hydration (off). This is the safe-minimum
# posture: warnings appear in context so the agent sees them, but nothing is
# blocked on a machine that has no config yet.

BUILTIN_GATES = GatesConfig(
    handover="warn",
    qa="warn",
    enforcer="warn",
    hydration="off",
    ida="warn",
    enforcer_threshold=50,
)

# Default container forwarding whitelist (PKB note-b5347f83, Q2). The secrets a
# polecat/crew worker needs but the launching general agent deliberately does
# NOT persist into its own session env. NAMES only — values resolved at launch
# from ~/.env.local by lib/host_secrets. Used when no polecat.yaml is present
# (fresh install / builtin config). The shipped polecat.yaml.example sets the
# same list explicitly so operators can see and edit it.
_DEFAULT_CONTAINER_ENV_FORWARD: tuple[str, ...] = (
    "CLAUDE_CODE_OAUTH_TOKEN",
    "GEMINI_API_KEY",
)

BUILTIN_SESSION_DEFAULTS = SessionDefaults(
    hooks_enabled=True,
    claude_model="claude-sonnet-4-6",
    gemini_model="gemini-2.5-pro",
    debug=False,
    gates=BUILTIN_GATES,
)


def _builtin_config() -> PolecatConfig:
    """Return a minimal PolecatConfig using built-in defaults (no YAML needed)."""
    return PolecatConfig(
        session_defaults=BUILTIN_SESSION_DEFAULTS,
        crew_defaults={"hooks_enabled": False},
        run_defaults={},
        docker=DockerConfig(image="ghcr.io/nicsuzor/aops-crew"),
        external_agents={},
        source_path=Path("<builtin>"),
        container_env_forward=_DEFAULT_CONTAINER_ENV_FORWARD,
    )


def _warn_no_config(detail: str) -> None:
    import sys

    print(
        f"[aops-core] WARNING: {detail}\n"
        "Using built-in defaults (all gates 'warn'). "
        "Copy polecat/defaults/polecat.yaml.example to "
        "$AOPS_SESSIONS/polecat.yaml to configure.",
        file=sys.stderr,
    )


def _resolve_config_path(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit
    env_path = os.environ.get(CONFIG_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    sessions = os.environ.get("AOPS_SESSIONS")
    if not sessions:
        raise RuntimeError(
            "polecat config: $AOPS_SESSIONS is not set and "
            f"${CONFIG_PATH_ENV} is not set; cannot locate polecat.yaml.\n"
            "Set $AOPS_SESSIONS to your sessions repo (containing polecat.yaml) "
            f"or set ${CONFIG_PATH_ENV} to an explicit path."
        )
    return Path(sessions).expanduser() / "polecat.yaml"


def load_polecat_config(path: Path | str | None = None) -> PolecatConfig:
    """Load and validate ``polecat.yaml``.

    When no config file can be located (env vars unset or default path absent),
    returns built-in defaults and emits a stderr warning — no traceback.  This
    supports fresh-install machines where polecat.yaml has not yet been created.

    If a file IS found but is malformed, hard-fails (A14 fail-fast principle):
    a broken config is an active error, not a missing-config situation.

    Pass ``path`` to bypass env-var resolution (used by tests).
    """
    explicit_path = Path(path) if isinstance(path, str) else path

    try:
        cfg_path = _resolve_config_path(explicit_path)
    except RuntimeError as e:
        # Neither AOPS_POLECAT_CONFIG nor AOPS_SESSIONS is set and no explicit
        # path was given — no config available at all (fresh install).
        _warn_no_config(str(e))
        return _builtin_config()

    if not cfg_path.exists():
        if explicit_path is not None:
            # Caller explicitly requested a path that doesn't exist — hard fail.
            raise RuntimeError(
                f"polecat config: file not found at {cfg_path}.\n"
                "Copy polecat/defaults/polecat.yaml.example into "
                "$AOPS_SESSIONS/polecat.yaml and edit to taste."
            )
        # Default path resolved from env vars but file is absent — fresh install.
        _warn_no_config(f"polecat config: file not found at {cfg_path}.")
        return _builtin_config()
    with open(cfg_path) as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise RuntimeError(
            f"polecat config: {cfg_path} must be a YAML mapping (got {type(raw).__name__})"
        )

    sd_raw = _require_mapping(raw, "session_defaults", cfg_path)
    gates = GatesConfig(**_validate_gates(_require_mapping(sd_raw, "gates", cfg_path)))
    session_defaults = SessionDefaults(
        hooks_enabled=_require_bool(sd_raw, "hooks_enabled", cfg_path),
        claude_model=_require_str(sd_raw, "claude_model", cfg_path),
        gemini_model=_require_str(sd_raw, "gemini_model", cfg_path),
        debug=_require_bool(sd_raw, "debug", cfg_path),
        gates=gates,
    )

    crew_defaults = _coerce_overlay(raw.get("crew_defaults"), "crew_defaults", cfg_path)
    run_defaults = _coerce_overlay(raw.get("run_defaults"), "run_defaults", cfg_path)

    docker_raw = _require_mapping(raw, "docker", cfg_path)
    docker = DockerConfig(image=_require_str(docker_raw, "image", cfg_path))

    ext_raw = raw.get("external_agents") or {}
    if not isinstance(ext_raw, dict):
        raise RuntimeError(f"polecat config: external_agents must be a mapping in {cfg_path}")
    external_agents: dict[str, ExternalAgent] = {}
    for name, body in ext_raw.items():
        body = body or {}
        if not isinstance(body, dict):
            raise RuntimeError(
                f"polecat config: external_agents.{name} must be a mapping in {cfg_path}"
            )
        enabled = bool(body.get("enabled", False))
        extra = {k: v for k, v in body.items() if k != "enabled"}
        external_agents[str(name)] = ExternalAgent(name=str(name), enabled=enabled, extra=extra)

    # container_env_forward — explicit whitelist of env-var NAMES forwarded into
    # containers, values resolved at launch from ~/.env.local (PKB note-b5347f83).
    # Optional: absent ⇒ the built-in default (OAuth tokens). If present it must
    # be a list of strings; reject anything that looks like a KEY=VALUE (a guard
    # against operators pasting secret VALUES into the name whitelist).
    cef_raw = raw.get("container_env_forward")
    if cef_raw is None:
        container_env_forward = _DEFAULT_CONTAINER_ENV_FORWARD
    else:
        if not isinstance(cef_raw, list) or not all(isinstance(x, str) for x in cef_raw):
            raise RuntimeError(
                f"polecat config: container_env_forward must be a list of strings in {cfg_path}"
            )
        for item in cef_raw:
            if "=" in item:
                raise RuntimeError(
                    f"polecat config: container_env_forward must list var NAMES, not "
                    f"values — found '=' in {item!r} in {cfg_path}. Secret values live "
                    "in ~/.env.local, never in polecat.yaml."
                )
        container_env_forward = tuple(cef_raw)

    return PolecatConfig(
        session_defaults=session_defaults,
        crew_defaults=crew_defaults,
        run_defaults=run_defaults,
        docker=docker,
        external_agents=external_agents,
        source_path=cfg_path,
        container_env_forward=container_env_forward,
    )


def _require_mapping(d: dict[str, Any], key: str, src: Path) -> dict[str, Any]:
    val = d.get(key)
    if not isinstance(val, dict):
        raise RuntimeError(f"polecat config: {src}: missing or non-mapping {key!r}")
    return val


def _require_str(d: dict[str, Any], key: str, src: Path) -> str:
    val = d.get(key)
    if not isinstance(val, str) or not val:
        raise RuntimeError(f"polecat config: {src}: missing or empty string {key!r}")
    return val


def _require_bool(d: dict[str, Any], key: str, src: Path) -> bool:
    if key not in d:
        raise RuntimeError(f"polecat config: {src}: missing required boolean {key!r}")
    val = d[key]
    if not isinstance(val, bool):
        raise RuntimeError(
            f"polecat config: {src}: {key!r} must be a boolean (got {type(val).__name__})"
        )
    return val


def _coerce_overlay(raw: Any, name: str, src: Path) -> dict[str, Any]:
    """Coerce a per-mode overlay block to a dict (empty if absent).

    Both ``crew_defaults`` and ``run_defaults`` must exist in the YAML for
    schema clarity, but may be empty mappings.
    """
    if raw is None:
        raise RuntimeError(
            f"polecat config: {src}: {name!r} block missing. "
            "Both crew_defaults and run_defaults must be present (use {} for empty)."
        )
    if not isinstance(raw, dict):
        raise RuntimeError(f"polecat config: {src}: {name!r} must be a mapping")
    # Validate any gates keys eagerly so YAML errors surface at load time.
    if "gates" in raw and isinstance(raw["gates"], dict):
        _validate_gates(raw["gates"], allow_partial=True)
    return dict(raw)
