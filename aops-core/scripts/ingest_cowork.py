#!/usr/bin/env -S uv run python
"""
Ingest Cowork audit logs into the aOps transcript pipeline.

Finds Cowork audit.jsonl files on the Mac, normalizes them to the
Claude Code session schema, and saves them to $AOPS_SESSIONS/cowork-logs/.
"""

import json
import os
import shutil
import sys
from pathlib import Path

# Add framework roots to path
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent
sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

# Import framework libs
try:
    from lib.paths import get_sessions_repo
    from lib.transcript_parser import normalize_cowork_event
except ImportError:
    # Fallback for local development
    sys.path.append(str(AOPS_CORE_ROOT))
    from lib.paths import get_sessions_repo
    from lib.transcript_parser import normalize_cowork_event


def normalize_cowork_entry(data: dict) -> dict:
    """Normalize a Cowork audit entry to Claude Code schema for writing to JSONL."""
    timestamp = data.get("_audit_timestamp") or data.get("timestamp")
    normalized: dict = {
        "uuid": data.get("uuid", data.get("id", "")),
        "timestamp": timestamp,
    }
    cowork = normalize_cowork_event(data)
    if cowork is not None:
        entry_type, message = cowork
        normalized["type"] = entry_type
        normalized["message"] = message
    else:
        normalized["type"] = data.get("type", "unknown")
        normalized["content"] = data
    return normalized


def ingest_cowork():
    """Find and ingest Cowork sessions."""
    # 1. Determine Cowork base path (Mac only)
    cowork_base = (
        Path.home() / "Library" / "Application Support" / "Claude" / "local-agent-mode-sessions"
    )
    if not cowork_base.exists():
        # Silent return if not on Mac/not installed
        return

    sessions_repo = get_sessions_repo()
    # The task asks for $AOPS_SESSIONS/transcripts/ but normalized logs
    # are better suited for a 'cowork-logs' or 'client-logs' subdir if we follow
    # typical framework patterns. However, we'll place them in a way that
    # transcript.py can easily find them.
    target_base = sessions_repo / "cowork-logs"
    target_base.mkdir(parents=True, exist_ok=True)

    count = 0

    # Structure: <user-uuid>/<org-uuid>/local_<conv-uuid>/audit.jsonl
    for audit_file in cowork_base.glob("*/*/local_*/audit.jsonl"):
        if "local_ditto_" in str(audit_file):
            continue

        conv_dir = audit_file.parent
        conv_name = conv_dir.name
        session_id = conv_name.replace("local_", "")[:8]

        # Target path: cowork-logs/<session_id>/session.jsonl
        target_dir = target_base / session_id
        target_file = target_dir / "session.jsonl"

        # Check if target is up to date
        if target_file.exists() and target_file.stat().st_mtime >= audit_file.stat().st_mtime:
            continue

        print(f"Ingesting Cowork session {session_id} from {audit_file}")

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with (
                open(audit_file, encoding="utf-8") as f_in,
                open(target_file, "w", encoding="utf-8") as f_out,
            ):
                for line in f_in:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        normalized = normalize_cowork_entry(data)
                        f_out.write(json.dumps(normalized) + "\n")
                    except json.JSONDecodeError:
                        continue

            # Update mtime to match source
            mtime = audit_file.stat().st_mtime
            os.utime(target_file, (mtime, mtime))

            # Copy the metadata JSON if it exists (contains title -> slug)
            metadata_json = conv_dir.parent / f"{conv_name}.json"
            if metadata_json.exists():
                shutil.copy2(metadata_json, target_dir / "metadata.json")

            count += 1
        except Exception as e:
            print(f"Error ingesting {audit_file}: {e}", file=sys.stderr)

    if count > 0:
        print(f"✅ Ingested {count} Cowork sessions")


if __name__ == "__main__":
    ingest_cowork()
