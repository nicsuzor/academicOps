#!/usr/bin/env python3
"""Tests for gate posture locking at SessionStart (GitHub issue #1234).

Verifies that:
1. Gate posture file is written at SessionStart.
2. Hooks read gate modes from the posture file, not from os.environ.
3. Mid-session env var changes are ignored by gate mode resolution.
4. Backward compat: when no posture file exists, env vars are used.
5. The posture file is written read-only (chmod 444).
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from lib.gate_posture import (
    POSTURE_FILE_ENV,
    get_gate_mode,
    write_posture_file,
)


class TestWritePostureFile:
    """write_posture_file creates a locked JSON snapshot."""

    def test_writes_json_with_all_gate_modes(self, tmp_path):
        """Posture file contains all gate names."""
        env = {
            "HANDOVER_GATE_MODE": "block",
            "QA_GATE_MODE": "warn",
            "ENFORCER_GATE_MODE": "off",
            "HYDRATION_GATE_MODE": "off",
            "IDA_GATE_MODE": "block",
            "ENFORCER_TOOL_CALL_THRESHOLD": "30",
        }
        with patch.dict("os.environ", env, clear=False):
            posture_file = tmp_path / "gate-posture.json"
            write_posture_file(posture_file)

        data = json.loads(posture_file.read_text())
        assert data["handover"] == "block"
        assert data["qa"] == "warn"
        assert data["enforcer"] == "off"
        assert data["hydration"] == "off"
        assert data["ida"] == "block"
        assert data["enforcer_threshold"] == "30"

    def test_file_is_read_only_after_write(self, tmp_path):
        """Posture file must be chmod 444 after write_posture_file."""
        posture_file = tmp_path / "gate-posture.json"
        write_posture_file(posture_file)
        mode = posture_file.stat().st_mode & 0o777
        assert mode == 0o444, f"Expected 0o444, got 0o{mode:o}"

    def test_uses_builtin_defaults_when_env_vars_absent(self, tmp_path):
        """When env vars are unset, write_posture_file uses built-in defaults."""
        clear_env = {
            k: None
            for k in [
                "HANDOVER_GATE_MODE",
                "QA_GATE_MODE",
                "ENFORCER_GATE_MODE",
                "HYDRATION_GATE_MODE",
                "IDA_GATE_MODE",
                "ENFORCER_TOOL_CALL_THRESHOLD",
            ]
        }
        with patch.dict("os.environ", {}, clear=False):
            for k in clear_env:
                os.environ.pop(k, None)
            posture_file = tmp_path / "gate-posture.json"
            write_posture_file(posture_file)

        data = json.loads(posture_file.read_text())
        assert data["handover"] == "warn"
        assert data["hydration"] == "off"
        assert data["enforcer_threshold"] == "50"


class TestGetGateMode:
    """get_gate_mode reads from posture file first, env var fallback, then default."""

    def test_reads_from_posture_file(self, tmp_path):
        """get_gate_mode returns value from posture file when available."""
        posture_file = tmp_path / "gate-posture.json"
        posture_file.write_text(json.dumps({"handover": "block"}))
        with patch.dict(
            "os.environ",
            {
                POSTURE_FILE_ENV: str(posture_file),
                "HANDOVER_GATE_MODE": "warn",  # env var says warn, file says block
            },
        ):
            assert get_gate_mode("handover") == "block"

    def test_mid_session_env_var_change_ignored_when_posture_file_present(self, tmp_path):
        """Core invariant: env var change mid-session does NOT affect gate mode.

        The posture file is locked at SessionStart. Even if the agent later
        writes to CLAUDE_ENV_FILE to change HANDOVER_GATE_MODE, the hook
        reads from the posture file and uses the SessionStart-resolved value.
        """
        posture_file = tmp_path / "gate-posture.json"
        posture_file.write_text(
            json.dumps(
                {
                    "handover": "warn",
                    "qa": "warn",
                    "enforcer": "warn",
                    "hydration": "off",
                    "ida": "warn",
                    "enforcer_threshold": "50",
                }
            )
        )

        with patch.dict(
            "os.environ",
            {
                POSTURE_FILE_ENV: str(posture_file),
                "HANDOVER_GATE_MODE": "warn",
            },
        ):
            # Simulate SessionStart-resolved posture: handover=warn
            assert get_gate_mode("handover") == "warn"

            # Agent mid-session: "weakens" gate by changing env var to off
            os.environ["HANDOVER_GATE_MODE"] = "off"

            # Hook still reads posture file → still warn
            assert get_gate_mode("handover") == "warn", (
                "Gate mode must not change mid-session even if env var is modified"
            )

    def test_falls_back_to_env_var_when_no_posture_file(self):
        """Without a posture file, env var is used (backward compat)."""
        env = {
            "HANDOVER_GATE_MODE": "block",
        }
        with patch.dict("os.environ", env, clear=False):
            os.environ.pop(POSTURE_FILE_ENV, None)
            assert get_gate_mode("handover") == "block"

    def test_falls_back_to_default_when_no_posture_file_and_no_env_var(self):
        """Without posture file or env var, built-in default is returned."""
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop(POSTURE_FILE_ENV, None)
            os.environ.pop("HANDOVER_GATE_MODE", None)
            assert get_gate_mode("handover") == "warn"
            assert get_gate_mode("hydration") == "off"

    def test_posture_file_read_error_falls_back_to_env(self, tmp_path):
        """Corrupted posture file falls back to env var gracefully."""
        posture_file = tmp_path / "gate-posture.json"
        posture_file.write_text("not valid json {{{")
        with patch.dict(
            "os.environ",
            {
                POSTURE_FILE_ENV: str(posture_file),
                "HANDOVER_GATE_MODE": "block",
            },
        ):
            assert get_gate_mode("handover") == "block"


class TestSessionStartWritesPostureFile:
    """SessionStart hook writes posture file and persists AOPS_GATE_POSTURE_FILE."""

    @pytest.fixture(autouse=True)
    def _mock_home(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

    def test_session_start_creates_posture_file(self, tmp_path):
        """run_session_env_setup writes a gate-posture.json to the state dir."""
        from hooks.schemas import HookContext
        from hooks.session_env_setup import run_session_env_setup
        from lib.session_state import SessionState

        env_file = tmp_path / "claude_env"
        env_file.touch()
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        ctx = HookContext(
            session_id="test-posture-lock-123",
            session_short_hash="abc12345",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

        with (
            patch.dict("os.environ", {"CLAUDE_ENV_FILE": str(env_file)}, clear=False),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=state_dir,
            ),
        ):
            run_session_env_setup(ctx, state)

        posture_file = state_dir / "gate-posture.json"
        assert posture_file.exists(), "gate-posture.json must be created at SessionStart"
        data = json.loads(posture_file.read_text())
        assert "handover" in data
        assert "qa" in data
        assert "enforcer" in data

    def test_session_start_persists_posture_file_env_var(self, tmp_path):
        """AOPS_GATE_POSTURE_FILE is written to CLAUDE_ENV_FILE."""
        from hooks.schemas import HookContext
        from hooks.session_env_setup import run_session_env_setup
        from lib.session_state import SessionState

        env_file = tmp_path / "claude_env"
        env_file.touch()
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        ctx = HookContext(
            session_id="test-posture-persist-456",
            session_short_hash="def56789",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

        with (
            patch.dict("os.environ", {"CLAUDE_ENV_FILE": str(env_file)}, clear=False),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=state_dir,
            ),
        ):
            run_session_env_setup(ctx, state)

        content = env_file.read_text()
        assert "AOPS_GATE_POSTURE_FILE" in content, (
            "AOPS_GATE_POSTURE_FILE must be persisted to CLAUDE_ENV_FILE"
        )

    def test_posture_file_is_locked_read_only(self, tmp_path):
        """Posture file written at SessionStart is chmod 444."""
        from hooks.schemas import HookContext
        from hooks.session_env_setup import run_session_env_setup
        from lib.session_state import SessionState

        env_file = tmp_path / "claude_env"
        env_file.touch()
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        ctx = HookContext(
            session_id="test-posture-readonly-789",
            session_short_hash="ghi78901",
            hook_event="SessionStart",
            raw_input={},
        )
        state = SessionState.create(ctx.session_id)

        with (
            patch.dict("os.environ", {"CLAUDE_ENV_FILE": str(env_file)}, clear=False),
            patch(
                "hooks.session_env_setup.get_session_status_dir",
                return_value=state_dir,
            ),
        ):
            run_session_env_setup(ctx, state)

        posture_file = state_dir / "gate-posture.json"
        assert posture_file.exists()
        mode = posture_file.stat().st_mode & 0o777
        assert mode == 0o444, f"gate-posture.json must be read-only (0o444), got 0o{mode:o}"
