#!/usr/bin/env -S uv run python
"""Single source of truth for polecat / crew session configuration.

The whole framework — polecat (the docker runner) and aops-core (the hooks
running inside the resulting Claude/Gemini sessions) — reads its operational
defaults from one YAML file: ``$AOPS_SESSIONS/polecat.yaml`` (or the path
named by ``AOPS_POLECAT_CONFIG``).

Per AXIOMS ``halt-on-failure`` (fail-fast) and ``single-source-of-truth`` (DRY, no
defaults, no backwards-compat):
- Missing or unlocatable file ⇒ hard-fail (A14). There are no built-in defaults
  and no warn-and-continue. Config must be present or the process exits.
  A present-but-malformed file also hard-fails.
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
        antigravity_model: str               # model id passed to `agy --model`
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

# Permitted session registers (WS6/WS7 register-scaling). Mirrors the reader's
# accepted set in hooks/gate_config.py::get_session_register(). A session's
# register is its *stakes* declaration: 'capture'/'personal' drop review-grade
# ceremony (qa/enforcer/ida gates), 'working' is the default, 'review' is
# review-grade. Validated at the config/CLI boundary so a typo fails fast rather
# than silently falling back to 'working' inside the container.
_REGISTERS = frozenset({"capture", "personal", "working", "review"})


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
    antigravity_model: str
    debug: bool
    gates: GatesConfig
    # Session register (stakes declaration) forwarded to the in-container hooks
    # as AOPS_SESSION_REGISTER. ``None`` means "unset" — the launcher then does
    # NOT stamp the var, and the in-container reader fail-closes to 'working'
    # (full ceremony). A lighter register ('capture'/'personal') is only ever
    # set on an explicit operator/config signal, never inferred — this preserves
    # the reader's fail-closed contract (an absent/unknown value never buys
    # *less* ceremony). See WS6/WS7 register-scaling (note-36c15a69).
    register: str | None = None

    def model_for(self, client: str) -> str:
        """Return the model id for the given client.

        ``gemini`` (npm/nvm Gemini CLI) and ``antigravity``/``agy`` (the agy
        wrapper around a Gemini model) are distinct clients with their own
        configured model ids.
        """
        if client == "claude":
            return self.claude_model
        if client == "gemini":
            return self.gemini_model
        if client in ("antigravity", "agy"):
            return self.antigravity_model
        raise ValueError(
            f"unknown client: {client!r} (expected 'claude', 'gemini', or 'antigravity')"
        )


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
    # Local cache root (worktrees, sessions/, polecats/ transcripts, the bare
    # mirror). REQUIRED top-level key — no default, no env fallback, no guess
    # (A14). The host resolves it and injects POLECAT_HOME into containers.
    polecat_home: Path
    # Per-machine short name for artifact filenames. Sourced from the local.yaml
    # overlay (``machine:``); None when the overlay omits it. The host injects it
    # into containers as AOPS_MACHINE so worker artifacts carry the HOST's name.
    machine: str | None
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
        if key == "register":
            patch["register"] = _validate_register(value)
            continue
        if key not in {
            "hooks_enabled",
            "claude_model",
            "gemini_model",
            "antigravity_model",
            "debug",
        }:
            raise ValueError(f"unknown override key: {key!r}")
        patch[key] = value
    if gates_patch:
        new_gates = replace(base.gates, **_validate_gates(gates_patch, allow_partial=True))
        patch["gates"] = new_gates
    return replace(base, **patch)


def _validate_register(value: Any) -> str:
    """Coerce + validate a ``register`` value against the permitted set.

    Accepts a string (case-insensitive); rejects anything outside ``_REGISTERS``
    so a typo (e.g. ``capure``) hard-fails at the config/CLI boundary instead of
    silently degrading to 'working' inside the container. Returns the normalised
    lowercase register.
    """
    normalised = str(value).strip().lower()
    if normalised not in _REGISTERS:
        raise ValueError(f"invalid register: {value!r}; expected one of {sorted(_REGISTERS)}")
    return normalised


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
# DEFAULTS — NONE.
# =============================================================================
# Per A14 (fail-fast) and the operator directive: config comes from where we
# expect (polecat.yaml, located via $AOPS_POLECAT_CONFIG or $AOPS_SESSIONS) or
# we hard-fail. There is NO builtin config, NO warn-and-continue, NO guessed
# path. A missing or unlocatable file is an error, not a fresh-install convenience.
#
# The ONE remaining default is the container-forwarding whitelist below: it is
# an optional key whose omission yields the OAuth-token list. That is a
# transitional default for an optional secrets list, NOT a guessed config
# location — distinct from the no-guessing rule above.

# Default container forwarding whitelist (PKB note-b5347f83, Q2). The secrets a
# polecat/crew worker needs but the launching general agent deliberately does
# NOT persist into its own session env. NAMES only — values resolved at launch
# from ~/.env.local by lib/host_secrets. The shipped polecat.yaml.example sets
# the same list explicitly so operators can see and edit it.
_DEFAULT_CONTAINER_ENV_FORWARD: tuple[str, ...] = (
    "CLAUDE_CODE_OAUTH_TOKEN",
    "AOPS_CC_OAUTH_TOKEN",
    "GEMINI_API_KEY",
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


def resolve_polecat_home() -> Path:
    """Resolve the required ``polecat_home`` from polecat.yaml (host-only).

    The single owner of polecat_home resolution — used by polecat/manager.py so
    the home path has exactly one source of truth (A16). No env fallback, no
    ``~/.polecat`` default, no guessing (A14): the key is required and the file
    must be locatable, or this raises.
    """
    cfg_path = _resolve_config_path(None)
    if not cfg_path.exists():
        raise RuntimeError(
            f"polecat config: file not found at {cfg_path}; cannot resolve polecat_home."
        )
    with open(cfg_path) as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"polecat config: {cfg_path} must be a YAML mapping")
    return Path(_expand_path(_require_str(raw, "polecat_home", cfg_path)))


def load_polecat_config(path: Path | str | None = None) -> PolecatConfig:
    """Load and validate ``polecat.yaml`` (host-only; never read in-container).

    Config is located via ``$AOPS_POLECAT_CONFIG`` or ``$AOPS_SESSIONS`` (or an
    explicit ``path``). If it cannot be located, or the file is absent or
    malformed, this HARD-FAILS (A14). There is no builtin config and no
    warn-and-continue — config comes from where we expect or not at all.

    The resolved config also folds in the per-machine ``local.yaml`` overlay
    found at ``<polecat_home>/local.yaml`` (``machine:`` and ``gates:``
    overrides). The host injects the resolved values into containers as env
    vars; containers never read either YAML file.

    Pass ``path`` to bypass env-var resolution (used by tests).
    """
    explicit_path = Path(path) if isinstance(path, str) else path

    cfg_path = _resolve_config_path(explicit_path)

    if not cfg_path.exists():
        raise RuntimeError(
            f"polecat config: file not found at {cfg_path}.\n"
            "Copy polecat/defaults/polecat.yaml.example into "
            "$AOPS_SESSIONS/polecat.yaml and edit to taste."
        )
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
        antigravity_model=_require_str(sd_raw, "antigravity_model", cfg_path),
        debug=_require_bool(sd_raw, "debug", cfg_path),
        gates=gates,
        # Optional — absent ⇒ None ⇒ launcher does not stamp AOPS_SESSION_REGISTER
        # ⇒ in-container reader fail-closes to 'working'. No schema migration is
        # forced on existing polecat.yaml files (unlike the required gates block).
        register=(_validate_register(sd_raw["register"]) if "register" in sd_raw else None),
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

    # polecat_home — REQUIRED, no default/fallback/guess (A14). The host's local
    # cache root; resolved here and injected into containers as POLECAT_HOME.
    polecat_home = Path(_expand_path(_require_str(raw, "polecat_home", cfg_path)))

    # Per-machine overlay at <polecat_home>/local.yaml. Optional file; when
    # present it may carry `machine:` (→ AOPS_MACHINE) and `gates:` overrides
    # applied on top of session_defaults.gates. This is the SSoT home for the
    # per-machine knobs that used to be loose outer-env vars.
    machine, session_defaults = _apply_local_overlay(polecat_home, session_defaults)

    return PolecatConfig(
        session_defaults=session_defaults,
        crew_defaults=crew_defaults,
        run_defaults=run_defaults,
        docker=docker,
        external_agents=external_agents,
        source_path=cfg_path,
        polecat_home=polecat_home,
        machine=machine,
        container_env_forward=container_env_forward,
    )


def _expand_path(value: str) -> str:
    """Expand ``~`` and ``${VAR}`` in a config path string."""
    return os.path.expandvars(os.path.expanduser(value))


def _apply_local_overlay(
    polecat_home: Path, session_defaults: SessionDefaults
) -> tuple[str | None, SessionDefaults]:
    """Fold the per-machine ``<polecat_home>/local.yaml`` overlay into the config.

    Returns ``(machine, session_defaults)``. The overlay is OPTIONAL — a missing
    file yields ``(None, session_defaults)`` unchanged (this is not a config
    *location* guess; it is a documented optional per-machine file). A present
    file must be a mapping; a malformed one hard-fails (A14). Recognised keys:

        machine: <str>        # short host name → AOPS_MACHINE
        gates: {<name>: ...}  # partial gate-mode overrides over session_defaults
    """
    local_path = polecat_home / "local.yaml"
    if not local_path.exists():
        return None, session_defaults
    with open(local_path) as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"polecat config: {local_path} must be a YAML mapping")

    machine = raw.get("machine")
    if machine is not None and not isinstance(machine, str):
        raise RuntimeError(f"polecat config: {local_path}: 'machine' must be a string")

    gates_raw = raw.get("gates")
    if gates_raw is not None:
        if not isinstance(gates_raw, dict):
            raise RuntimeError(f"polecat config: {local_path}: 'gates' must be a mapping")
        merged = replace(session_defaults.gates, **_validate_gates(gates_raw, allow_partial=True))
        session_defaults = replace(session_defaults, gates=merged)

    return machine, session_defaults


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
