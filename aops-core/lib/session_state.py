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
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from lib.session_paths import get_session_file_path, get_session_short_hash, get_session_status_dir


class GateState(BaseModel):
    """State of a specific gate."""
    status: str = "closed"  # open, closed
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Additional fields can be stored in metadata or added here if common
    blocked: bool = False
    block_reason: Optional[str] = None


class HydrationState(BaseModel):
    """Hydration-specific state."""
    original_prompt: Optional[str] = None
    hydrated_intent: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    critic_verdict: Optional[str] = None
    turns_since_hydration: int = -1
    turns_since_critic: int = -1
    temp_path: Optional[str] = None


class MainAgentState(BaseModel):
    """Main agent tracking."""
    current_task: Optional[str] = None
    task_binding_source: str = "unknown"
    task_binding_ts: Optional[str] = None
    task_cleared_ts: Optional[str] = None
    todos_completed: int = 0
    todos_total: int = 0


class SessionState(BaseModel):
    """Unified session state per flow.md spec."""

    # Core identifiers
    session_id: str
    date: str  # YYYY-MM-DD
    started_at: str  # ISO timestamp
    ended_at: Optional[str] = None

    # Session type detection (polecat vs interactive)
    session_type: str = "interactive"

    # Execution state (legacy bag + structured)
    # We keep 'state' dict for backward compatibility/generic storage during migration
    state: Dict[str, Any] = Field(default_factory=dict)

    # Structured components
    gates: Dict[str, GateState] = Field(default_factory=dict)
    hydration: HydrationState = Field(default_factory=HydrationState)
    main_agent: MainAgentState = Field(default_factory=MainAgentState)

    # Subagent tracking: agent_name -> data dict
    subagents: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Session insights (written at close)
    insights: Optional[Dict[str, Any]] = None

    @classmethod
    def create(cls, session_id: str) -> "SessionState":
        """Create new session state."""
        now = datetime.now().astimezone().replace(microsecond=0)

        # Detect session type
        stype = "interactive"
        if "POLECAT_SESSION_TYPE" in os.environ:
            val = os.environ["POLECAT_SESSION_TYPE"].lower()
            if val in ("polecat", "crew"):
                stype = val

        instance = cls(
            session_id=session_id,
            date=now.isoformat(),
            started_at=now.isoformat(),
            session_type=stype,
        )

        # Initialize default gate states
        # hydration: closed
        instance.gates["hydration"] = GateState(status="closed")
        # task: open (initially)
        instance.gates["task"] = GateState(status="open")
        # critic: open
        instance.gates["critic"] = GateState(status="open")
        # custodiet: open
        instance.gates["custodiet"] = GateState(status="open")
        # qa: closed
        instance.gates["qa"] = GateState(status="closed")
        # handover: open
        instance.gates["handover"] = GateState(status="open")

        # Initialize legacy flags in 'state' dict for compatibility if needed
        # (Though we are removing legacy code, some hooks might access .state directly)
        instance.state["hydration_pending"] = True
        instance.state["handover_skill_invoked"] = True

        return instance

    @classmethod
    def load(cls, session_id: str, retries: int = 3) -> "SessionState":
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
                        except json.JSONDecodeError:
                            if attempt < retries - 1:
                                time.sleep(0.01)
                                continue
                            return cls.create(session_id) # Fallback to new? Or fail?
                        except Exception:
                            pass

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
            self.gates[name] = GateState()
        return self.gates[name]

    def is_gate_open(self, name: str) -> bool:
        return self.get_gate(name).status == "open"

    def open_gate(self, name: str):
        gate = self.get_gate(name)
        gate.status = "open"
        self.gates[name] = gate

    def close_gate(self, name: str):
        gate = self.get_gate(name)
        gate.status = "closed"
        self.gates[name] = gate
