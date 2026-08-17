#!/usr/bin/env python3
import contextlib
import fcntl
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.WARNING,
    format="[otel_tracer] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("otel_tracer")


def _load_config_file(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        log.debug("Failed to read config %s: %s", path, e)
    return {}


def discover_config() -> dict | None:
    api_key = os.environ.get("GENAI_ENGINE_API_KEY", "")
    task_id = os.environ.get("GENAI_ENGINE_TASK_ID", "")
    endpoint = os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT", "")
    protocol = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_PROTOCOL", "") or os.environ.get(
        "OTEL_EXPORTER_OTLP_PROTOCOL", ""
    )

    if not (api_key and task_id and endpoint):
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        project_cfg = _load_config_file(
            Path(project_dir) / ".claude" / "arthur_config.json",
        )
        api_key = api_key or project_cfg.get("api_key", "")
        task_id = task_id or project_cfg.get("task_id", "")
        endpoint = endpoint or project_cfg.get("endpoint", "")
        protocol = protocol or project_cfg.get("protocol", "")

    if not (api_key and task_id and endpoint):
        global_cfg = _load_config_file(Path.home() / ".claude" / "arthur_config.json")
        api_key = api_key or global_cfg.get("api_key", "")
        task_id = task_id or global_cfg.get("task_id", "")
        endpoint = endpoint or global_cfg.get("endpoint", "")
        protocol = protocol or global_cfg.get("protocol", "")

    if not (api_key and task_id and endpoint):
        endpoint = (
            endpoint
            or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "")
            or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        )
        task_id = task_id or os.environ.get("OTEL_SERVICE_NAME", "") or "claude-code"
        api_key = (
            api_key
            or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS", "")
            or os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")
        )
        protocol = (
            protocol
            or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_PROTOCOL", "")
            or os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "")
        )

    if not endpoint:
        return None

    cfg = {"api_key": api_key, "task_id": task_id, "endpoint": endpoint}
    if protocol:
        cfg["protocol"] = protocol
    return cfg


STATE_DIR = Path.home() / ".claude" / "tracer"
STATE_MAX_AGE_S = 48 * 3600


def _state_path(session_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = (STATE_DIR / f"{session_id}.json").resolve()
    if not path.is_relative_to(STATE_DIR.resolve()):
        raise ValueError(f"Invalid session_id: {session_id!r}")
    return path


def _load_state(session_id: str) -> dict:
    path = _state_path(session_id)
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        log.debug("Failed to load state for %s: %s", session_id, e)
    return {}


def _save_state(session_id: str, state: dict) -> None:
    try:
        _state_path(session_id).write_text(json.dumps(state))
    except Exception as e:
        log.warning("Failed to save state for %s: %s", session_id, e)


def _delete_state(session_id: str) -> None:
    try:
        p = _state_path(session_id)
        if p.exists():
            p.unlink()
    except Exception as e:
        log.debug("Failed to delete state for %s: %s", session_id, e)


def _cleanup_stale_states() -> None:
    try:
        now = time.time()
        for p in STATE_DIR.glob("*.json"):
            if now - p.stat().st_mtime > STATE_MAX_AGE_S:
                p.unlink()
    except Exception as e:
        log.debug("Stale state cleanup failed: %s", e)


def _new_trace_id() -> str:
    import secrets

    return secrets.token_hex(16)


def _new_span_id() -> str:
    import secrets

    return secrets.token_hex(8)


@contextlib.contextmanager
def _session_lock(session_id: str):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = (STATE_DIR / f"{session_id}.lock").resolve()
    if not lock_path.is_relative_to(STATE_DIR.resolve()):
        raise ValueError(f"Invalid session_id: {session_id!r}")

    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
