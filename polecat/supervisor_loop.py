#!/usr/bin/env python3
"""
Supervisor Loop: LLM-driven batch orchestration for polecat workers.

Each iteration:
1. PLAN: LLM reviews task queue + previous results, selects (task, runner) pairs
2. EXECUTE: Dispatches workers in parallel, waits for completion
3. VERIFY: LLM checks results (PRs on GitHub, etc.), decides whether to continue

Usage:
    python polecat/supervisor_loop.py -p aops -n 3
    python polecat/supervisor_loop.py -p aops -n 2 --supervisor gemini
    python polecat/supervisor_loop.py -p aops -n 2 --max-rounds 5 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPERVISOR_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "safe_to_continue": {
                "type": "boolean",
                "description": "Whether previous results (if any) look safe. Always true on first round.",
            },
            "issues": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Problems found in previous batch results (empty on first round).",
            },
            "pairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "runner": {"type": "string", "enum": ["claude", "gemini"]},
                    },
                    "required": ["task_id", "runner"],
                },
                "description": "Tasks to dispatch next. Empty array = stop dispatching.",
            },
            "reasoning": {"type": "string"},
        },
        "required": ["safe_to_continue", "pairs", "reasoning"],
    }
)

# Signal handling for clean shutdown
_STOP_REQUESTED = False


def _handle_signal(signum, frame):
    global _STOP_REQUESTED
    if _STOP_REQUESTED:
        print("\n[supervisor] Force quit.", file=sys.stderr)
        sys.exit(1)
    _STOP_REQUESTED = True
    print(
        "\n[supervisor] Stop requested. Waiting for current workers to finish...",
        file=sys.stderr,
    )


def _install_signal_handlers():
    """Install signal handlers for graceful shutdown. Call from entry points only."""
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


# ---------------------------------------------------------------------------
# Run history (persists across invocations)
# ---------------------------------------------------------------------------


def _state_path(project: str) -> Path:
    """State file lives at $POLECAT_HOME/supervisor-state.json."""
    home = os.environ.get("POLECAT_HOME", os.path.expanduser("~/.polecat"))
    return Path(home) / f"supervisor-state-{project}.json"


def load_state(project: str) -> dict:
    """Load persistent supervisor state."""
    path = _state_path(project)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(project: str, state: dict) -> None:
    """Save persistent supervisor state."""
    path = _state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, default=str) + "\n")


def record_round(state: dict, round_result: dict) -> None:
    """Append a round result to history."""
    if "history" not in state:
        state["history"] = []
    state["history"].append(round_result)


def format_history_for_prompt(state: dict) -> str:
    """Format recent run history for the supervisor LLM."""
    history = state.get("history", [])
    if not history:
        return "No previous supervisor runs recorded."

    # Show last 10 rounds across invocations
    recent = history[-10:]
    lines = [f"Recent supervisor history ({len(history)} total rounds recorded):"]
    for entry in recent:
        ts = entry.get("timestamp", "?")
        invocation = entry.get("invocation_id", "?")
        round_num = entry.get("round", "?")
        duration_s = entry.get("duration_s", 0)
        pairs = entry.get("pairs", [])
        outcomes = []
        for p in pairs:
            status = "OK" if p.get("exit_code") == 0 else f"FAIL({p.get('exit_code')})"
            outcomes.append(f"{p.get('task_id', '?')}({p.get('runner', '?')})={status}")
        duration_str = f"{duration_s // 60}m{duration_s % 60}s" if duration_s else "?"
        lines.append(
            f"  [{ts}] inv={invocation[:8]} round={round_num} "
            f"duration={duration_str} | {', '.join(outcomes) or 'no workers'}"
        )

    # Total runtime across all invocations
    total_s = sum(e.get("duration_s", 0) for e in history)
    total_rounds = len(history)
    lines.append(
        f"  Totals: {total_rounds} rounds, {total_s // 3600}h{(total_s % 3600) // 60}m runtime"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------

# Set up aops-core imports once at module level
_aops_core_path = os.path.join(os.path.dirname(__file__), "..", "aops-core")
if _aops_core_path not in sys.path:
    sys.path.insert(0, _aops_core_path)


def get_ready_tasks(project: str) -> str:
    """Get ready task queue as formatted text. Raises on failure."""
    from lib.task_storage import TaskStorage

    storage = TaskStorage()
    tasks = storage.get_ready_tasks(project=project)

    if not tasks:
        return "No ready tasks in queue."

    lines = [f"Ready tasks ({len(tasks)} total):"]
    # Show top 30 to keep prompt manageable
    for t in tasks[:30]:
        assignee = t.assignee or "unassigned"
        lines.append(f"  - {t.id}: {t.title} (P{t.priority}, assignee={assignee})")
    if len(tasks) > 30:
        lines.append(f"  ... and {len(tasks) - 30} more")
    return "\n".join(lines)


def get_recent_prs() -> str:
    """Get recent open PRs from GitHub. Raises on failure."""
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--state=open",
            "--limit=20",
            "--json=number,title,headRefName,statusCheckRollup",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh pr list failed: {result.stderr.strip()}")

    prs = json.loads(result.stdout)
    if not prs:
        return "No open PRs."

    lines = ["Open PRs:"]
    for pr in prs:
        checks = pr.get("statusCheckRollup") or []
        check_summary = ""
        if checks:
            states = [c.get("conclusion") or c.get("status", "?") for c in checks]
            check_summary = f" [checks: {', '.join(states)}]"
        lines.append(f"  #{pr['number']} ({pr['headRefName']}){check_summary}")
    return "\n".join(lines)


def get_in_progress_tasks(project: str) -> str:
    """Get tasks currently in progress. Raises on failure."""
    from lib.task_storage import TaskStatus, TaskStorage

    storage = TaskStorage()
    tasks = storage.list_tasks(project=project, status=TaskStatus.IN_PROGRESS)

    if not tasks:
        return "No tasks currently in progress."

    lines = [f"In-progress tasks ({len(tasks)}):"]
    for t in tasks:
        assignee = t.assignee or "unassigned"
        lines.append(f"  - {t.id}: {t.title} (assignee={assignee})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------


def _parse_llm_json(raw: str, supervisor: str) -> dict:
    """Extract JSON from LLM output, handling various wrapper formats."""
    text = raw

    # Claude --output-format json wraps in {"type":"result","result":"..."}
    if supervisor == "claude":
        try:
            wrapper = json.loads(text)
            if isinstance(wrapper, dict) and "result" in wrapper:
                if wrapper.get("is_error"):
                    raise RuntimeError(f"Claude error: {wrapper.get('result', 'unknown')}")
                result = wrapper["result"]
                if not isinstance(result, str):
                    return result if isinstance(result, dict) else {}
                text = result
        except json.JSONDecodeError:
            pass  # not a wrapper, try parsing as-is

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    # Try again after stripping
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Last resort: find first { ... } block
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    print(
        f"[supervisor] Could not parse JSON from output (first 500 chars): {raw[:500]}",
        file=sys.stderr,
    )
    raise RuntimeError("Failed to parse JSON from LLM output")


def call_supervisor_llm(
    prompt: str,
    json_schema: str,
    supervisor: str = "claude",
    model: str | None = None,
) -> dict:
    """Call the supervisor LLM and parse structured JSON output.

    Returns parsed dict or raises on failure.
    """
    # Both Claude and Gemini: ask for JSON in the prompt, parse from output
    prompt += (
        "\n\nIMPORTANT: Respond with ONLY a valid JSON object matching this schema. "
        f"No markdown, no explanation, just the JSON:\n{json_schema}"
    )

    if supervisor == "claude":
        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--tools",
            "",
            "--no-session-persistence",
        ]
        if model:
            cmd.extend(["--model", model])
    elif supervisor == "gemini":
        cmd = [
            "gemini",
            "-p",
            prompt,
        ]
        if model:
            cmd.extend(["--model", model])
    else:
        raise ValueError(f"Unknown supervisor: {supervisor}")

    print(f"[supervisor] Calling {supervisor} LLM...", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"[supervisor] stderr: {result.stderr[:500]}", file=sys.stderr)
        print(f"[supervisor] stdout: {result.stdout[:500]}", file=sys.stderr)
        raise RuntimeError(
            f"{supervisor} exited with code {result.returncode}: {result.stderr.strip()[:200]}"
        )

    stdout = result.stdout.strip()
    if not stdout:
        print(f"[supervisor] stderr (empty stdout): {result.stderr[:500]}", file=sys.stderr)
        raise RuntimeError(
            f"{supervisor} returned empty output. stderr: {result.stderr.strip()[:200]}"
        )

    return _parse_llm_json(stdout, supervisor)


# ---------------------------------------------------------------------------
# Worker dispatch
# ---------------------------------------------------------------------------


def dispatch_workers(
    pairs: list[dict],
    project: str,
    dry_run: bool = False,
) -> list[dict]:
    """Dispatch polecat workers for each (task_id, runner) pair.

    Runs all workers in parallel, waits for completion.
    Returns list of result dicts with exit codes.
    """
    if dry_run:
        print(f"[supervisor] DRY RUN: would dispatch {len(pairs)} workers:")
        for p in pairs:
            print(
                f"  polecat run -t {p['task_id']} -p {project} {'[-g]' if p['runner'] == 'gemini' else ''}"
            )
        return [
            {"task_id": p["task_id"], "runner": p["runner"], "exit_code": 0, "dry_run": True}
            for p in pairs
        ]

    aops_path = os.environ.get("AOPS")
    if not aops_path:
        print("[supervisor] ERROR: AOPS environment variable not set.", file=sys.stderr)
        sys.exit(1)

    processes: list[tuple[dict, subprocess.Popen]] = []

    for pair in pairs:
        cmd = [
            "uv",
            "run",
            "--project",
            aops_path,
            os.path.join(aops_path, "polecat/cli.py"),
            "run",
            "-t",
            pair["task_id"],
            "-p",
            project,
            "-c",
            "supervisor-loop",
        ]
        if pair["runner"] == "gemini":
            cmd.append("-g")

        print(f"[supervisor] Dispatching: {pair['task_id']} -> {pair['runner']}")
        proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
        processes.append((pair, proc))

        # Stagger launches slightly to avoid lock contention
        time.sleep(1)

    # Wait for all workers
    results = []
    for pair, proc in processes:
        proc.wait()
        result = {
            "task_id": pair["task_id"],
            "runner": pair["runner"],
            "exit_code": proc.returncode,
        }
        status = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        print(f"[supervisor] Finished: {pair['task_id']} -> {status}")
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def build_supervisor_prompt(
    project: str,
    max_pairs: int,
    previous_results: list[dict] | None,
    round_num: int,
    state: dict | None = None,
) -> str:
    """Build a single prompt that both verifies previous results AND selects next tasks."""
    task_queue = get_ready_tasks(project)
    in_progress = get_in_progress_tasks(project)
    prs = get_recent_prs()
    history = format_history_for_prompt(state or {})

    previous_section = ""
    verify_instructions = ""
    if previous_results:
        lines = ["Previous batch results:"]
        for r in previous_results:
            status = "SUCCESS" if r["exit_code"] == 0 else f"FAILED (exit {r['exit_code']})"
            dry = " [dry-run]" if r.get("dry_run") else ""
            lines.append(f"  - {r['task_id']} ({r['runner']}): {status}{dry}")
        previous_section = "\n".join(lines)
        verify_instructions = textwrap.dedent("""\
            ## Step 1: Verify Previous Results

            Check the previous batch:
            1. Did workers exit successfully (exit code 0)?
            2. For successful workers, is there a corresponding PR on GitHub?
               (Branch name should contain the task ID, e.g. polecat/task-id)
            3. Any signs of systemic failure (all failed, infrastructure issues)?

            Set safe_to_continue=false and return empty pairs if:
            - All workers failed
            - Infrastructure problems (git, network, etc.)
            - Something looks fundamentally broken

            Otherwise set safe_to_continue=true and proceed to select next tasks.
        """)

    return textwrap.dedent(f"""\
        You are a swarm supervisor. Review previous results (if any) and select
        the next batch of tasks for parallel polecat workers.

        ## Current State (Round {round_num})

        ### Task Queue
        {task_queue}

        ### In-Progress Tasks
        {in_progress}

        ### Open PRs
        {prs}

        {previous_section}

        ### Run History (across invocations)
        {history}

        {verify_instructions}

        ## {"Step 2: " if previous_results else ""}Select Tasks to Dispatch

        Select up to {max_pairs} (task_id, runner) pairs.

        Rules:
        - Only select tasks from the ready queue above
        - Only select tasks with assignee=polecat or assignee=bot (skip nic-assigned and unassigned)
        - runner must be "claude" or "gemini" — there is NO performance difference between them.
          Distribute evenly across both runners. Do NOT try to match task complexity to runner.
          The only reason to prefer one over the other is if run history shows one is failing
          while the other succeeds (e.g. infrastructure issue with one provider).
        - Do NOT select tasks that are already in-progress
        - Do NOT select tasks that already have an open PR (check branch names)
        - Prefer higher priority tasks (P0 > P1 > P2 > P3)
        - If no suitable tasks exist, return an empty pairs array

        ## Response

        Return a JSON object with:
        - safe_to_continue: bool (true if previous results OK or first round; false to halt)
        - issues: string[] (problems found, empty if none)
        - pairs: array of {{task_id, runner}} (empty if halting or no tasks)
        - reasoning: brief explanation
    """)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _save_round(
    state: dict,
    project: str,
    invocation_id: str,
    round_num: int,
    round_start: float,
    results: list[dict],
    safe: bool,
    exit_reason: str | None = None,
) -> None:
    """Record a round in persistent state and save to disk."""
    round_duration = int(time.monotonic() - round_start)
    record = {
        "invocation_id": invocation_id,
        "round": round_num,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_s": round_duration,
        "pairs": results,
        "safe_to_continue": safe,
    }
    if exit_reason:
        record["exit_reason"] = exit_reason
    record_round(state, record)
    save_state(project, state)


def supervisor_loop(
    project: str,
    max_pairs: int,
    max_rounds: int,
    supervisor: str,
    model: str | None,
    dry_run: bool,
):
    """Main supervisor loop."""
    _install_signal_handlers()
    state = load_state(project)
    invocation_id = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    total_history_rounds = len(state.get("history", []))
    print("[supervisor] Starting supervisor loop")
    print(f"[supervisor]   project={project}, max_pairs={max_pairs}, max_rounds={max_rounds}")
    print(f"[supervisor]   supervisor={supervisor}, dry_run={dry_run}")
    print(f"[supervisor]   invocation={invocation_id}, prior_rounds={total_history_rounds}")
    print("[supervisor]   Ctrl+C to stop after current batch\n")

    previous_results: list[dict] | None = None
    round_num = 0

    for round_num in range(1, max_rounds + 1):
        if _STOP_REQUESTED:
            print("[supervisor] Stop requested. Exiting.")
            break

        print(f"\n{'=' * 60}")
        print(f"  ROUND {round_num}/{max_rounds} (total: {total_history_rounds + round_num})")
        print(f"{'=' * 60}\n")

        round_start = time.monotonic()

        # ----- SUPERVISOR CALL: verify previous + select next -----
        print("[supervisor] === SUPERVISOR DECISION ===")
        prompt = build_supervisor_prompt(project, max_pairs, previous_results, round_num, state)

        try:
            decision = call_supervisor_llm(prompt, SUPERVISOR_SCHEMA, supervisor, model)
        except Exception as e:
            print(f"[supervisor] LLM call failed: {e}", file=sys.stderr)
            _save_round(
                state,
                project,
                invocation_id,
                round_num,
                round_start,
                previous_results or [],
                False,
                "llm_call_failed",
            )
            sys.exit(1)

        safe = decision.get("safe_to_continue", True)
        issues = decision.get("issues", [])
        pairs = decision.get("pairs", [])
        reasoning = decision.get("reasoning", "")

        print(f"[supervisor] Reasoning: {reasoning}")
        if issues:
            print("[supervisor] Issues:")
            for issue in issues:
                print(f"  - {issue}")

        if not safe:
            print("[supervisor] Previous results unsafe. Halting.")
            _save_round(
                state,
                project,
                invocation_id,
                round_num,
                round_start,
                previous_results or [],
                False,
                "verification_unsafe",
            )
            sys.exit(1)

        print(f"[supervisor] Selected {len(pairs)} pairs:")
        for p in pairs:
            print(f"  {p['task_id']} -> {p['runner']}")

        if not pairs:
            print("[supervisor] No tasks selected (n=0). Exiting.")
            sys.exit(0)

        # ----- EXECUTE -----
        print(f"\n[supervisor] === EXECUTE ({len(pairs)} workers) ===")
        batch_results = dispatch_workers(pairs, project, dry_run)

        # Record round
        all_failed = all(r["exit_code"] != 0 for r in batch_results) and not dry_run
        _save_round(
            state,
            project,
            invocation_id,
            round_num,
            round_start,
            batch_results,
            not all_failed,
            "all_workers_failed" if all_failed else None,
        )

        if all_failed:
            print("[supervisor] ALL workers failed. Exiting.", file=sys.stderr)
            sys.exit(1)

        if _STOP_REQUESTED:
            print("[supervisor] Stop requested after execution. Exiting.")
            break

        previous_results = batch_results
        elapsed = int(time.monotonic() - round_start)
        print(f"\n[supervisor] Round {round_num} complete ({elapsed}s). Continuing...")

    print(f"\n[supervisor] Supervisor loop finished ({round_num} rounds).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="LLM-driven supervisor loop for polecat swarm dispatch.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python polecat/supervisor_loop.py -p aops -n 3
              python polecat/supervisor_loop.py -p aops -n 2 --supervisor gemini
              python polecat/supervisor_loop.py -p aops -n 2 --max-rounds 5 --dry-run
        """),
    )
    parser.add_argument("-p", "--project", required=True, help="Project to pull tasks from")
    parser.add_argument(
        "-n",
        "--max-pairs",
        type=int,
        default=3,
        help="Max (task, runner) pairs per round (default: 3)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=10,
        help="Max supervisor loop iterations (default: 10)",
    )
    parser.add_argument(
        "--supervisor",
        choices=["claude", "gemini"],
        default="claude",
        help="Which LLM to use as supervisor (default: claude)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model override for supervisor LLM (e.g. sonnet, haiku)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be dispatched without running workers",
    )

    args = parser.parse_args()
    supervisor_loop(
        project=args.project,
        max_pairs=args.max_pairs,
        max_rounds=args.max_rounds,
        supervisor=args.supervisor,
        model=args.model,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
