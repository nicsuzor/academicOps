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

    # Current Cowork audit logs already emit native Claude Code records
    # (type=user/assistant/system with a top-level `message` envelope, plus
    # `_audit_*` bookkeeping fields). Pass these through verbatim so the
    # transcript parser's Entry.from_dict reads `message` directly. Wrapping
    # them under `content` (the old fallback) buried the envelope one level too
    # deep and produced empty transcripts.
    if "message" in data:
        normalized = dict(data)
        normalized["timestamp"] = timestamp
        normalized.pop("_audit_timestamp", None)
        normalized.pop("_audit_hmac", None)
        normalized.setdefault(
            "uuid", data.get("id", "")
        )  # allow-fallback: legacy/native event may lack both uuid and id; empty uuid is non-fatal (Entry.from_dict tolerates it)
        return normalized

    # Legacy Cowork audit schema (type=message/tool_call/tool_result): synthesize
    # the Claude Code message envelope from the flat event.
    normalized = {
        "uuid": data.get("uuid")
        or data.get(
            "id"
        ),  # allow-fallback: legacy event may lack both uuid and id; empty uuid is non-fatal (Entry.from_dict tolerates it)
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


def ingest_subagent_bundles(conv_dir: Path, conv_id: str, target_base: Path) -> int:
    """Ingest the native Claude Code task bundles nested inside a Cowork conversation.

    When a Cowork session delegates to parallel agents, Claude Code writes each
    task as a *native* session bundle under
    ``<conv_dir>/.claude/projects/<encoded-cwd>/<task-uuid>.jsonl`` with its
    subagents at ``<encoded-cwd>/<task-uuid>/subagents/agent-*.jsonl``. These
    records are already in native Claude Code schema (``message``/``type``/
    ``sessionId``/``isSidechain``) — the parent ``audit.jsonl`` only captures the
    dispatch prompt and final result, so the bulk of the work (file reads, greps,
    verification reasoning) lives ONLY in these files.

    The old ingest globbed ``audit.jsonl`` exclusively and dropped this entire
    tree, so delegation-heavy sessions lost most of their content downstream
    (GH #1621). We copy each bundle VERBATIM into its own top-level
    ``cowork-logs/<conv8>-<task8>/`` directory in native layout. ``find_sessions``
    then discovers ``<task-uuid>.jsonl`` like any Claude Code session, and
    ``_load_agent_files`` links the ``<task-uuid>/subagents/`` transcripts with no
    reader/transcriber changes.

    Returns the number of bundles (re)ingested.
    """
    projects_root = conv_dir / ".claude" / "projects"
    if not projects_root.exists():
        return 0

    copied = 0
    # Subagents sit at <encoded-cwd>/<task-uuid>/subagents/ — two levels under
    # the projects root. Anchor on the subagents dir and walk back up.
    for subagents_dir in projects_root.glob("*/*/subagents"):
        if not subagents_dir.is_dir():
            continue
        agent_files = [p for p in subagents_dir.glob("agent-*.jsonl") if p.suffix == ".jsonl"]
        if not agent_files:
            continue

        task_dir = subagents_dir.parent  # <encoded-cwd>/<task-uuid>
        task_uuid = task_dir.name
        main_file = task_dir.parent / f"{task_uuid}.jsonl"
        if not main_file.exists():
            # Subagents with no parent thread to attach to — skip (rare).
            continue

        bundle_dir = target_base / f"{conv_id}-{task_uuid[:8]}"
        target_main = bundle_dir / f"{task_uuid}.jsonl"

        # Up-to-date skip, mirroring the parent-session logic.
        if target_main.exists() and target_main.stat().st_mtime >= main_file.stat().st_mtime:
            continue

        target_subagents = bundle_dir / task_uuid / "subagents"
        target_subagents.mkdir(parents=True, exist_ok=True)

        # Native records — copy verbatim (preserves mtime, sessionId, isSidechain).
        shutil.copy2(main_file, target_main)
        for agent_file in agent_files:
            shutil.copy2(agent_file, target_subagents / agent_file.name)
            # Carry the .meta.json sidecar if present (harmless; may hold type).
            meta = agent_file.with_suffix(".meta.json")
            if meta.exists():
                shutil.copy2(meta, target_subagents / meta.name)

        print(f"  ↳ ingested subagent bundle {conv_id}-{task_uuid[:8]} ({len(agent_files)} agents)")
        copied += 1

    return copied


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
    bundle_count = 0

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

        try:
            # Write the parent thread unless it's already up to date. (The nested
            # subagent bundles are ingested below regardless, since they can be
            # updated independently of the parent audit.jsonl.)
            parent_current = (
                target_file.exists() and target_file.stat().st_mtime >= audit_file.stat().st_mtime
            )
            if not parent_current:
                print(f"Ingesting Cowork session {session_id} from {audit_file}")
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

            # Ingest nested native task bundles (main thread + subagents) that
            # the parent audit.jsonl does not contain (GH #1621).
            bundle_count += ingest_subagent_bundles(conv_dir, session_id, target_base)
        except Exception as e:
            print(f"Error ingesting {audit_file}: {e}", file=sys.stderr)

    if count > 0 or bundle_count > 0:
        print(f"✅ Ingested {count} Cowork sessions, {bundle_count} subagent bundles")


if __name__ == "__main__":
    ingest_cowork()
