import json
from pathlib import Path

from lib.transcript_parser import UsageStats
from lib.transcripts.adapters.agy import AgyAdapter
from lib.transcripts.adapters.claude import ClaudeAdapter


def extract_cost_data(session_path: Path) -> UsageStats:
    stats = UsageStats()
    if not session_path.exists():
        return stats

    # Read first lines to determine adapter
    content = session_path.read_text().splitlines()
    if not content:
        return stats

    # Simple heuristic
    is_agy = any("timestamp" in line and "sender" in line for line in content[:10])

    if is_agy:
        adapter = AgyAdapter()
    else:
        adapter = ClaudeAdapter()

    for line in content:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue

        usage = adapter.extract_usage(entry)
        if usage:
            stats.input_tokens += usage.get("input_tokens", 0)
            stats.output_tokens += usage.get("output_tokens", 0)
            stats.cache_creation_input_tokens += usage.get("cache_creation_input_tokens", 0)
            stats.cache_read_input_tokens += usage.get("cache_read_input_tokens", 0)

    return stats
