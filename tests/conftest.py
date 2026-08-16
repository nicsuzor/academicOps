"""Pytest fixtures for aOps framework tests.

Provides the shared test-environment fixture. All paths resolve relative to
the repo root; ACA_DATA and AOPS_SESSIONS are always redirected into
`tmp_path` so no test can write into a developer's real data vault.
"""

import os
from pathlib import Path

import pytest

# Point AOPS_POLECAT_CONFIG at the canonical example *before* any test module
# is imported. lib/polecat_config.py hard-fails when no config is found. Tests
# that need a different config monkeypatch it per-test via the autouse
# `ensure_test_environment` fixture below.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_POLECAT_EXAMPLE = _REPO_ROOT / "plugins" / "aops" / "polecat" / "defaults" / "polecat.yaml.example"
if _POLECAT_EXAMPLE.exists():
    os.environ["AOPS_POLECAT_CONFIG"] = str(_POLECAT_EXAMPLE)

# Staging base for DooD environments (so that tmp files are accessible to host Docker)
_STAGING_BASE = _REPO_ROOT / ".aops" / "tmp" / "staging"
os.environ.setdefault("POLECAT_STAGING_BASE", str(_STAGING_BASE))


@pytest.fixture(autouse=True)
def ensure_test_environment(monkeypatch, tmp_path):
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

    # Seed a polecat.yaml inside the per-test sessions dir; clear the
    # module-level AOPS_POLECAT_CONFIG override so $AOPS_SESSIONS/polecat.yaml
    # is what tests resolve.
    if _POLECAT_EXAMPLE.exists():
        (sessions_dir / "polecat.yaml").write_text(_POLECAT_EXAMPLE.read_text())
    monkeypatch.delenv("AOPS_POLECAT_CONFIG", raising=False)

    # Redirect UV cache to prevent PermissionError in /opt/suzor/cache/uv
    # This is required for hooks to run successfully under macOS Seatbelt
    uv_cache = tmp_path / "uv_cache"
    uv_cache.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("UV_CACHE_DIR", str(uv_cache))

    # Strip any leaked host environment variables that hardcode paths (e.g. from polecat sessions)
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
    }
    for key in list(os.environ.keys()):
        if key.startswith("AOPS_GATE_FILE_") or key in scrub_keys:
            monkeypatch.delenv(key, raising=False)

    # No test may post to the developer's real Discord channel. Tests that care
    # about the notification patch this themselves.
    monkeypatch.setattr("lib.polecat.notify._post_discord", lambda line: None)
