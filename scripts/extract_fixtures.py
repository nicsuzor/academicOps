#!/usr/bin/env python3
"""Extract test fixtures from real hook invocation logs.

Reads JSONL hook logs (Claude or Gemini) and produces parameterized
test fixture scenarios with provenance metadata tracing each scenario
back to the exact source log line.

Usage:
    python scripts/extract_fixtures.py <log_file> [--output fixtures.json]
    python scripts/extract_fixtures.py --all  # regenerate from all known logs

The ONLY approved way to create test fixture scenarios. Never hand-author
fixture data — always extract from real logs.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from hooks.gate_config import COMPLIANCE_SUBAGENT_TYPES

# Maximum number of scenarios to collect per group from a single log.
# Caps breadth without deduplication — ensures no single session floods a group.
SCENARIO_GROUP_LIMIT = 50


def _detect_platform(events: list[dict]) -> str:
    """Detect whether log is from Claude Code or Gemini CLI."""
    # Gemini logs have .gemini in transcript_path
    for e in events:
        tp = e.get("transcript_path") or ""
        if ".gemini" in tp:
            return "gemini"
    # Fallback: check for Gemini-specific tool names
    tools = {e.get("tool_name") for e in events if e.get("tool_name")}
    gemini_tools = {
        "read_file",
        "write_file",
        "run_shell_command",
        "delegate_to_agent",
        "activate_skill",
    }
    if tools & gemini_tools:
        return "gemini"
    return "claude"


def _make_provenance(log_path: str, line_idx: int, event: dict) -> dict:
    """Create provenance metadata for a fixture scenario."""
    event_json = json.dumps(event, sort_keys=True, separators=(",", ":"))
    event_hash = hashlib.sha256(event_json.encode()).hexdigest()[:16]
    return {
        "source_log": str(log_path),
        "line_index": line_idx,
        "session_id": event.get("session_id", "unknown"),
        "logged_at": event.get("logged_at", "unknown"),
        "event_hash": event_hash,
        "extracted_at": datetime.now(UTC).isoformat(),
    }


def _event_to_scenario(event, line_idx, log_path, platform, group):
    """Convert a single log event to a fixture scenario."""
    output = event.get("output") or {}
    verdict = output.get("verdict", "allow")

    # Infer gate state from system messages for gate_overrides
    gate_overrides = {}
    sys_msg = output.get("system_message", "") or ""
    if "Hydration required" in sys_msg or (
        "hydrate" in sys_msg.lower() and "New user prompt" not in sys_msg
    ):
        gate_overrides["hydration"] = {
            "status": "closed",
            "metrics": {"temp_path": "/tmp/hydration.md"},
        }
    if "Compliance" in sys_msg and ("check required" in sys_msg or "OVERDUE" in sys_msg):
        gate_overrides["custodiet"] = {"ops_since_open": 15}

    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input", {})
    subagent_type = event.get("subagent_type")

    scenario = {
        "id": f"{platform}-{event['hook_event'].lower()}-{(tool_name or 'none').lower()}-L{line_idx}",
        "hook_event": event["hook_event"],
        "tool_name": tool_name,
        "tool_input": tool_input,
        "subagent_type": subagent_type,
        "is_subagent": event.get("is_subagent", False),
        "expected": {"verdict": verdict},
        "_provenance": _make_provenance(log_path, line_idx, event),
    }
    if gate_overrides:
        scenario["gate_overrides"] = gate_overrides
    return scenario


def extract_scenarios_from_log(log_path, scenario_groups=None):
    path = Path(log_path)
    if not path.exists():
        print(f"ERROR: Log file not found: {log_path}", file=sys.stderr)
        return {}

    events = []
    with path.open() as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:
                try:
                    events.append((i, json.loads(line)))
                except json.JSONDecodeError:
                    print(f"WARNING: Skipping malformed JSON at line {i}", file=sys.stderr)

    platform = _detect_platform([e for _, e in events])
    if scenario_groups is None:
        scenario_groups = {}

    # 1. Hydration gate: tools warned/denied when gate is closed
    hydration_blocked = []
    for idx, event in events:
        if event.get("hook_event") != "PreToolUse":
            continue
        output = event.get("output") or {}
        sys_msg = output.get("system_message", "") or ""
        if "Hydration required" in sys_msg or (
            "hydrate" in sys_msg.lower() and "New user prompt" not in sys_msg
        ):
            s = _event_to_scenario(event, idx, str(path), platform, "hydration_gate_blocks_tools")
            s["gate_overrides"] = {
                "hydration": {"status": "closed", "metrics": {"temp_path": "/tmp/hydration.md"}}
            }
            hydration_blocked.append(s)

    if hydration_blocked:
        group_name = f"{platform}_hydration_gate_blocks_tools"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        # Add new scenarios if we haven't reached the limit (e.g., 50 per group)
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(hydration_blocked[:remaining])

    # 2. Compliance agents: hydrator/custodiet calls that should be allowed
    compliance_allowed = []
    for idx, event in events:
        if event.get("hook_event") != "PreToolUse":
            continue
        st = event.get("subagent_type") or ""
        tn = event.get("tool_name") or ""
        if st in COMPLIANCE_SUBAGENT_TYPES or tn in COMPLIANCE_SUBAGENT_TYPES:
            s = _event_to_scenario(event, idx, str(path), platform, "compliance_agent_allowed")
            compliance_allowed.append(s)

    if compliance_allowed:
        group_name = f"{platform}_compliance_agent_allowed"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(compliance_allowed[:remaining])

    # 3. Always-available tools that bypass gates
    always_available = []
    for idx, event in events:
        if event.get("hook_event") != "PreToolUse":
            continue
        output = event.get("output") or {}
        verdict = output.get("verdict", "allow")
        tn = event.get("tool_name") or ""
        if verdict == "allow" and tn in (
            "Agent",
            "TaskCreate",
            "TaskUpdate",
            "TaskGet",
            "TaskList",
            "AskUserQuestion",
        ):
            s = _event_to_scenario(event, idx, str(path), platform, "always_available_bypass")
            always_available.append(s)

    if always_available:
        group_name = f"{platform}_always_available_bypass"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(always_available[:remaining])

    # 4. Custodiet threshold warnings/blocks
    custodiet_blocked = []
    for idx, event in events:
        if event.get("hook_event") != "PreToolUse":
            continue
        output = event.get("output") or {}
        sys_msg = output.get("system_message", "") or ""
        if "Compliance" in sys_msg and ("check required" in sys_msg or "OVERDUE" in sys_msg):
            s = _event_to_scenario(event, idx, str(path), platform, "custodiet_threshold")
            custodiet_blocked.append(s)

    if custodiet_blocked:
        group_name = f"{platform}_custodiet_threshold"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(custodiet_blocked[:remaining])

    # 5. SubagentStart/SubagentStop events
    subagent_events = []
    for idx, event in events:
        if event.get("hook_event") in ("SubagentStart", "SubagentStop"):
            s = _event_to_scenario(event, idx, str(path), platform, "subagent_events")
            subagent_events.append(s)

    if subagent_events:
        group_name = f"{platform}_subagent_events"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(subagent_events[:remaining])

    # 6. Stop events
    stop_events = []
    for idx, event in events:
        if event.get("hook_event") == "Stop":
            s = _event_to_scenario(event, idx, str(path), platform, "stop_events")
            stop_events.append(s)

    if stop_events:
        group_name = f"{platform}_stop_events"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(stop_events[:remaining])

    # 7. UserPromptSubmit events
    prompt_events = []
    for idx, event in events:
        if event.get("hook_event") == "UserPromptSubmit":
            s = _event_to_scenario(event, idx, str(path), platform, "user_prompt_events")
            prompt_events.append(s)

    if prompt_events:
        group_name = f"{platform}_user_prompt_events"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(prompt_events[:remaining])

    # 8. Read-only tools
    read_only_events = []
    for idx, event in events:
        if event.get("hook_event") != "PreToolUse":
            continue
        tn = event.get("tool_name") or ""
        if tn in ("Read", "Grep", "Glob", "read_file", "search_files", "list_files"):
            s = _event_to_scenario(event, idx, str(path), platform, "read_only_tools")
            read_only_events.append(s)

    if read_only_events:
        group_name = f"{platform}_read_only_tools"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(read_only_events[:remaining])

    # 9. Write tools
    write_events = []
    for idx, event in events:
        if event.get("hook_event") != "PreToolUse":
            continue
        tn = event.get("tool_name") or ""
        if tn in ("Bash", "Write", "Edit", "NotebookEdit", "run_shell_command", "write_file"):
            s = _event_to_scenario(event, idx, str(path), platform, "write_tools")
            write_events.append(s)

    if write_events:
        group_name = f"{platform}_write_tools"
        if group_name not in scenario_groups:
            scenario_groups[group_name] = []
        if len(scenario_groups[group_name]) < SCENARIO_GROUP_LIMIT:
            remaining = SCENARIO_GROUP_LIMIT - len(scenario_groups[group_name])
            scenario_groups[group_name].extend(write_events[:remaining])

    return scenario_groups


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract test fixtures from hook logs")
    parser.add_argument("log_files", nargs="+", help="JSONL log files to extract from")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    args = parser.parse_args()

    log_files = args.log_files

    all_scenarios = {}
    for lf in log_files:
        if Path(lf).exists():
            print(f"Extracting from: {lf}", file=sys.stderr)
            extract_scenarios_from_log(lf, all_scenarios)
        else:
            print(f"SKIP (not found): {lf}", file=sys.stderr)

    total = sum(len(v) for v in all_scenarios.values())
    print(f"\nExtracted {total} scenarios in {len(all_scenarios)} groups:", file=sys.stderr)
    for group, scenarios in sorted(all_scenarios.items()):
        print(f"  {group}: {len(scenarios)}", file=sys.stderr)

    output = args.output or "tests/hooks/fixtures/gate_scenarios_live.json"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(all_scenarios, f, indent=2, sort_keys=False)
    print(f"\nWritten to: {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
