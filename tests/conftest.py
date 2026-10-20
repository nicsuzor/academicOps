"""Pytest fixtures for aOps framework tests.

Provides the shared test-environment fixture. All paths resolve relative to
the repo root; ACA_DATA and AOPS_SESSIONS are always redirected into
`tmp_path` so no test can write into a developer's real data vault.
"""

import fcntl
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The temp directory every xdist worker of this run shares.

    Under xdist each worker's basetemp is `<run>/popen-gwN`; without it the
    basetemp is the run directory itself.
    """
    basetemp = tmp_path_factory.getbasetemp()
    return basetemp.parent if os.environ.get("PYTEST_XDIST_WORKER") else basetemp


@pytest.fixture(scope="session")
def shared_uv_cache(tmp_path_factory) -> Path:
    """One uv cache for the whole run, shared by every worker and test.

    Kept inside the run's temp directory rather than the host cache, which a
    sandboxed run (macOS Seatbelt) cannot write. uv locks its cache, so
    concurrent workers share it safely and each wheel is fetched once per run.
    """
    cache = _run_root(tmp_path_factory) / "uv_cache"
    cache.mkdir(exist_ok=True)
    return cache


@pytest.fixture(scope="session")
def build_once(tmp_path_factory) -> Callable[[str, Callable[[Path], object]], Path]:
    """Build a directory once per run, shared by every xdist worker.

    `build_once(name, build)` returns `<run>/<name>`, calling `build(path)` to
    fill it only if no worker has completed it yet. A worker that finds another
    mid-build waits on the lock. A build that raised leaves no completion
    marker, so the next caller starts it again from empty.
    """
    root = _run_root(tmp_path_factory)

    def _build(name: str, build: Callable[[Path], object]) -> Path:
        target = root / name
        done = root / f"{name}.done"
        with open(root / f"{name}.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not done.exists():
                shutil.rmtree(target, ignore_errors=True)
                target.mkdir()
                build(target)
                done.touch()
        return target

    return _build


@pytest.fixture(autouse=True)
def ensure_test_environment(monkeypatch, tmp_path, shared_uv_cache):
    """Ensure ACA_DATA is set and directories exist for all tests.

    This provides a fallback test environment if ACA_DATA is not set externally.
    """
    # ALWAYS use tmp_path for ACA_DATA to prevent tests from mutating host environment
    data_dir = tmp_path / "aca_data"
    monkeypatch.setenv("ACA_DATA", str(data_dir))

    # Ensure required structure exists
    (data_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (data_dir / "projects").mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    (data_dir / "goals").mkdir(parents=True, exist_ok=True)
    (data_dir / "context").mkdir(parents=True, exist_ok=True)
    # Always use tmp_path for AOPS_SESSIONS to ensure full test isolation
    # (avoids writing alongside external ACA_DATA paths when ACA_DATA is set externally)
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))

    # Redirect UV cache to prevent PermissionError in a host-level uv cache
    # This is required for hooks to run successfully under macOS Seatbelt
    monkeypatch.setenv("UV_CACHE_DIR", str(shared_uv_cache))

    # Strip any leaked host environment variables that hardcode paths or route OTel telemetry
    #
    # NOTE: POLECAT_HOME is deliberately NOT scrubbed here.
    # Some test fixtures spawn a polecat subprocess and then assert against
    # its output from within the same (function-scoped) test — scrubbing
    # POLECAT_HOME here would desync which `POLECAT_HOME` the subprocess and
    # the assertion side see. Tests that need POLECAT_HOME isolation set it
    # explicitly via `monkeypatch.setenv("POLECAT_HOME", str(tmp_path))`;
    # that setenv still wins after this fixture runs.
    scrub_keys = {
        "AOPS_HOOK_LOG_PATH",
        "CLAUDE_PROJECT_DIR",
        "AOPS_SESSION_ID",
        "AOPS_SESSION_STATE_DIR",
        "AOPS_SRC_DIR",
        "AOPS_TASK_ID",
        "POLECAT_TARGET_TASK",
        "POLECAT_TASK",
        "PKB_MCP_URL",
        "PKB_MCP_HEADERS",
        "DISPATCHER_MCP_TOKEN",
        "WORKER_MCP_TOKEN",
        "WORKER_MCP_TOKEN_ID",
        "WORKER_MCP_TOKEN_SECRET",
        "DISPATCHER_MCP_TOKEN_ID",
        "DISPATCHER_MCP_TOKEN_SECRET",
        "GENAI_ENGINE_TRACE_ENDPOINT",
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TRACE_PROTOCOL",
        "GENAI_ENGINE_TASK_ID",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
        "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
        "PHOENIX_PROJECT_NAME",
        "OTEL_SERVICE_NAME",
        "OTEL_RESOURCE_ATTRIBUTES",
        "GITHUB_ACTIONS",
    }
    for key in list(os.environ.keys()):
        if key.startswith("AOPS_GATE_FILE_") or key in scrub_keys:
            monkeypatch.delenv(key, raising=False)
