"""Single session file management for v1.0 core loop.

Provides atomic CRUD operations for unified session state file.
State enables cross-hook coordination per specs/flow.md.

Session file: ~/writing/sessions/status/YYYYMMDD-sessionID.json

IMPORTANT: State is keyed by session_id, NOT project cwd. Each Claude client session
is independent - multiple sessions can run from the same project directory and must
not share state. Session ID is the unique identifier provided by Claude Code.

Location: Sessions are stored in a centralized flat directory for easy access and
cleanup. Files are named by date and session hash (e.g., 20260121-abc12345.json).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from importlib import metadata
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from lib.gate_types import GateState, GateStatus
from lib.session_paths import (
    get_session_file_path,
    get_session_short_hash,
    get_session_status_dir,
)


class MainAgentState(BaseModel):
    """Main agent tracking."""

    current_task: str | None = None
    task_binding_source: str = "unknown"
    task_binding_ts: str | None = None
    task_cleared_ts: str | None = None
    todos_completed: int = 0
    todos_total: int = 0


class SessionState(BaseModel):
    """Unified session state per flow.md spec."""

    # Core identifiers
    session_id: str
    date: str  # YYYY-MM-DD
    started_at: str  # ISO timestamp
    ended_at: str | None = None
    version: str = "unknown"

    # Global turn counter (increments on user prompt)
    global_turn_count: int = 0

    # Session type detection (polecat vs interactive)
    session_type: str = "interactive"

    # Execution state (legacy bag + structured)
    state: dict[str, Any] = Field(default_factory=dict)

    # Structured components
    gates: dict[str, GateState] = Field(default_factory=dict)

    # Main Agent / Task tracking (could move to 'task' gate metrics, but useful globally)
    main_agent: MainAgentState = Field(default_factory=MainAgentState)

    # Subagent tracking: agent_name -> data dict
    subagents: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Session insights (written at close)
    insights: dict[str, Any] | None = None

    @classmethod
    def create(cls, session_id: str) -> SessionState:
        """Create new session state."""
        now = datetime.now().astimezone().replace(microsecond=0)

        # Detect session type
        stype = "interactive"
        if "POLECAT_SESSION_TYPE" in os.environ:
            val = os.environ["POLECAT_SESSION_TYPE"].lower()
            if val in ("polecat", "crew"):
                stype = val

        try:
            ver = metadata.version("academicops")
        except metadata.PackageNotFoundError:
            ver = "unknown"

        instance = cls(
            session_id=session_id,
            date=now.isoformat(),
            started_at=now.isoformat(),
            session_type=stype,
            version=ver,
        )

        # Initialize default gate states
        default_gates = {
            "hydration": GateStatus.CLOSED,
            "task": GateStatus.OPEN,
            "critic": GateStatus.OPEN,
            "custodiet": GateStatus.OPEN,
            "qa": GateStatus.CLOSED,
            "handover": GateStatus.OPEN,
        }

        for name, status in default_gates.items():
            instance.gates[name] = GateState(status=status)

        # Initialize legacy flags in 'state' dict for compatibility if needed
        instance.state["hydration_pending"] = True
        instance.state["handover_skill_invoked"] = True

        return instance

    @classmethod
    def load(cls, session_id: str, retries: int = 3) -> SessionState:
        """Load session state from disk."""
        now = datetime.now()
        today = now.strftime("%Y%m%d")
        yesterday = (now - timedelta(days=1)).strftime("%Y%m%d")

        short_hash = get_session_short_hash(session_id)
        status_dir = get_session_status_dir(session_id)

        # Search for files matching this session_id on today or yesterday
        for date_compact in [today, yesterday]:
            # New format: YYYYMMDD-HH-hash.json (try all hours)
            new_pattern = f"{date_compact}-??-{short_hash}.json"
            # Legacy format: YYYYMMDD-hash.json
            legacy_pattern = f"{date_compact}-{short_hash}.json"

            for pattern in [new_pattern, legacy_pattern]:
                matches = list(status_dir.glob(pattern))
                if matches:
                    # Use the most recent file if multiple matches
                    path = max(matches, key=lambda p: p.stat().st_mtime)
                    for attempt in range(retries):
                        try:
                            text = path.read_text()
                            data = json.loads(text)
                            # Convert dict to Pydantic
                            return cls.model_validate(data)
                        except json.JSONDecodeError as e:
                            if attempt < retries - 1:
                                time.sleep(0.01)
                                continue
                            print(f"WARNING: SessionState JSON decode error: {e}", file=sys.stderr)
                            # Return new state on failure to avoid blocking
                            return cls.create(session_id)
                        except ValidationError as e:
                            print(f"WARNING: SessionState validation error: {e}", file=sys.stderr)
                            # Schema mismatch -> Create new (migration via reset)
                            return cls.create(session_id)
                        except Exception as e:
                            print(f"WARNING: SessionState load error: {e}", file=sys.stderr)
                            # Unknown error -> Create new? Or retry?
                            if attempt < retries - 1:
                                time.sleep(0.01)
                                continue
                            return cls.create(session_id)

        # Not found, create new
        return cls.create(session_id)

    def save(self) -> None:
        """Save session state to disk."""
        # Ensure directory exists
        path = get_session_file_path(self.session_id, self.date)
        path.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_path_str = tempfile.mkstemp(
            prefix=f"aops-{self.date}-", suffix=".tmp", dir=str(path.parent)
        )
        temp_path = Path(temp_path_str)

        try:
            # Dump with exclude_none=False to preserve structure?
            # Or use mode='json'
            data = self.model_dump_json(indent=2)
            os.write(fd, data.encode())
            os.close(fd)
            temp_path.rename(path)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            temp_path.unlink(missing_ok=True)
            raise

    # --- Helper methods for common checks ---

    def get_gate(self, name: str) -> GateState:
        if name not in self.gates:
            # Default to OPEN if unknown gate accessed, or create closed?
            # Safer to default to OPEN (non-blocking) for unknown gates unless configured otherwise
            self.gates[name] = GateState(status=GateStatus.OPEN)
        return self.gates[name]

    def is_gate_open(self, name: str) -> bool:
        return self.get_gate(name).status == GateStatus.OPEN

    def open_gate(self, name: str):
        gate = self.get_gate(name)
        if gate.status != GateStatus.OPEN:
            gate.status = GateStatus.OPEN
            gate.last_open_ts = time.time()
            gate.last_open_turn = self.global_turn_count
            gate.ops_since_open = 0
        self.gates[name] = gate

    def close_gate(self, name: str):
        gate = self.get_gate(name)
        if gate.status != GateStatus.CLOSED:
            gate.status = GateStatus.CLOSED
            gate.last_close_ts = time.time()
            gate.last_close_turn = self.global_turn_count
            gate.ops_since_close = 0
        self.gates[name] = gate

