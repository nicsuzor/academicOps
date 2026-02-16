#!/usr/bin/env python3
"""
Polecat Swarm: Manage a swarm of parallel polecat workers.

Spawns N claude and M gemini workers, binding them to specific CPUs.
Restarts workers that finish successfully (exit code 0).
Alerts and stops workers that fail (non-zero exit code).
"""

import argparse
import multiprocessing
import os
import random
import shutil
import signal
import subprocess
import sys
import time

# Worker startup delay configuration
MIN_STARTUP_DELAY_S = 0.5
MAX_STARTUP_DELAY_S = 3.0

# Gemini worker launch stagger (seconds between spawns)
# Free tier rate limits are easily exceeded by concurrent sessions
DEFAULT_GEMINI_STAGGER_S = 15.0

# Global event to signal workers to drain
STOP_EVENT = multiprocessing.Event()


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) by setting stop event for graceful drain."""
    print("\n🛑 Received stop signal. Enabling drain mode... (Press Ctrl+C again to force quit)")
    STOP_EVENT.set()


def alert(message: str):
    """Send a system alert if possible, always log to stderr."""
    print(f"\n🚨 ALERT: {message}\n", file=sys.stderr)
    # Try to send a desktop notification if notify-send is available
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", "-u", "critical", "Polecat Swarm Alert", message],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass


def worker_loop(
    agent_type: str,
    cpu_id: int | None,
    project: str | None,
    caller: str,
    dry_run: bool,
    home_dir: str | None = None,
):
    """
    Main loop for a single worker process.

    Args:
        agent_type: 'claude' or 'gemini'
        cpu_id: The CPU core index to bind this process to (0-indexed).
        project: Optional project filter.
        dry_run: If True, do not actually run polecat, just simulate.
        home_dir: Optional polecat home directory override.
    """
    # Set affinity if a CPU ID is provided
    if cpu_id is not None:
        try:
            os.sched_setaffinity(0, {cpu_id})
        except Exception as e:
            print(f"[{agent_type}-{os.getpid()}] ⚠️ Failed to set affinity to CPU {cpu_id}: {e}")

    worker_name = f"{agent_type.upper()}-Worker-{os.getpid()}"
    if cpu_id is not None:
        worker_name += f" (CPU {cpu_id})"

    print(f"[{worker_name}] 🚀 Started.")

    # Random startup delay to stagger workers and prevent race conditions
    # when multiple workers try to claim the same task simultaneously.
    # Skip this delay in dry-run mode and when explicitly disabled via env var
    # to keep CI and local debugging fast and deterministic.
    disable_stagger = dry_run or os.environ.get("POLECAT_DISABLE_STARTUP_STAGGER") == "1"
    if not disable_stagger:
        startup_delay = random.uniform(MIN_STARTUP_DELAY_S, MAX_STARTUP_DELAY_S)
        print(f"[{worker_name}] ⏳ Waiting {startup_delay:.1f}s before first claim...")
        time.sleep(startup_delay)

    aops_path = os.environ.get("AOPS")
    if not aops_path and not dry_run:
        print(f"[{worker_name}] ❌ AOPS environment variable not set. Exiting.")
        return

    while True:
        if dry_run:
            print(f"[{worker_name}] 🧪 Dry run: simulating work...")
            time.sleep(2)
            exit_code = 0
            print(f"[{worker_name}] 🧪 Dry run finished with {exit_code}")
        else:
            assert aops_path is not None  # guaranteed by guard above
            cmd = [
                "uv",
                "run",
                "--project",
                aops_path,
                os.path.join(aops_path, "polecat/cli.py"),
            ]

            # Add --home option before subcommand if specified
            if home_dir:
                cmd.extend(["--home", home_dir])

            cmd.append("run")

            # Claim tasks with the specified caller identity
            cmd.extend(["-c", caller])

            if agent_type == "gemini":
                cmd.append("-g")

            if project:
                cmd.extend(["-p", project])

            print(f"[{worker_name}] 🔄 Starting cycle...")
            try:
                # Run the worker process
                result = subprocess.run(cmd)
                exit_code = result.returncode
            except Exception as e:
                print(f"[{worker_name}] ❌ Execution error: {e}")
                exit_code = 1

        if exit_code == 0:
            print(f"[{worker_name}] ✅ Finished successfully.")
            # Check for stop signal before restarting
            if STOP_EVENT.is_set():
                print(f"[{worker_name}] 🛑 Drain mode active. Exiting.")
                break

            print(f"[{worker_name}] 🔄 Restarting immediately...")
            if not dry_run:
                time.sleep(1)  # Safety buffer
            continue
        elif exit_code == 3:
            # Exit 3 = queue empty (normal drain, not a failure)
            print(f"[{worker_name}] 📭 Queue empty. Stopping worker.")
            break
        else:
            msg = f"Worker {worker_name} failed with exit code {exit_code}. Stopping this worker."
            print(f"[{worker_name}] 🛑 {msg}")
            alert(msg)
            # In case of failure, we always stop this worker to prevent rapid retries of broken state
            break


def run_swarm(
    claude_count: int,
    gemini_count: int,
    project: str | None = None,
    caller: str = "polecat",
    dry_run: bool = False,
    home_dir: str | None = None,
    gemini_stagger: float | None = None,
):
    """Entry point for CLI integration.

    Args:
        claude_count: Number of Claude workers to spawn.
        gemini_count: Number of Gemini workers to spawn.
        project: Optional project filter.
        caller: Identity claiming the tasks (default: bot).
        dry_run: If True, simulate execution.
        home_dir: Optional polecat home directory override.
        gemini_stagger: Seconds to wait between Gemini worker spawns.
            Default: 15s to avoid quota exhaustion on free tier.
    """
    total_workers = claude_count + gemini_count
    if total_workers == 0:
        print(
            "No workers requested. Use --claude <n> and/or --gemini <m>.",
            file=sys.stderr,
        )
        return

    # Calculate affinity
    # We'll just round-robin available CPUs
    try:
        available_cpus = list(os.sched_getaffinity(0))
    except Exception:
        # Fallback if sched_getaffinity not available
        count = os.cpu_count() or 1
        available_cpus = list(range(count))

    print(f"🔥 Spawning swarm: {claude_count} Claude, {gemini_count} Gemini")
    print(f"🖥️  Available CPUs: {len(available_cpus)} {available_cpus}")

    # Register signal handler for the main process
    signal.signal(signal.SIGINT, signal_handler)
    print("ℹ️  Press Ctrl+C to stop gracefully (finish current items). Press twice to force quit.")

    processes = []

    # Assign CPUs in round-robin
    cpu_idx = 0

    # Spawn Claude workers
    for _ in range(claude_count):
        cpu = available_cpus[cpu_idx % len(available_cpus)]
        p = multiprocessing.Process(
            target=worker_loop, args=("claude", cpu, project, caller, dry_run, home_dir)
        )
        p.start()
        processes.append(p)
        cpu_idx += 1

    # Spawn Gemini workers with stagger delay to avoid quota exhaustion
    stagger = gemini_stagger if gemini_stagger is not None else DEFAULT_GEMINI_STAGGER_S
    for i in range(gemini_count):
        # Honor drain/stop requests: do not spawn additional Gemini workers once STOP_EVENT is set.
        if STOP_EVENT.is_set():
            print("🛑 Drain requested; stopping further Gemini worker spawns.")
            break
        if i > 0 and stagger > 0 and not dry_run:
            print(f"⏳ Waiting {stagger:.0f}s before spawning next Gemini worker...")
            time.sleep(stagger)
            if STOP_EVENT.is_set():
                print("🛑 Drain requested during stagger; stopping further Gemini worker spawns.")
                break
        cpu = available_cpus[cpu_idx % len(available_cpus)]
        p = multiprocessing.Process(
            target=worker_loop, args=("gemini", cpu, project, caller, dry_run, home_dir)
        )
        p.start()
        processes.append(p)
        cpu_idx += 1

    print(f"✨ Swarm active with {len(processes)} workers.")

    try:
        # Wait for all processes (they shouldn't exit unless failure/interrupt)
        for p in processes:
            p.join()
        print("👋 Swarm dispersed (all workers finished).")
    except SystemExit:
        # Caused by the double Ctrl+C force quit in signal handler
        print("\n🛑 Force stopping swarm...")
        for p in processes:
            if p.is_alive():
                p.terminate()
        print("👋 Swarm terminated.")


def main():
    parser = argparse.ArgumentParser(description="Run a swarm of Polecat workers.")
    parser.add_argument("--claude", "-c", type=int, default=0, help="Number of Claude workers")
    parser.add_argument("--gemini", "-g", type=int, default=0, help="Number of Gemini workers")
    parser.add_argument("--project", "-p", type=str, help="Project to focus on (default: all)")
    parser.add_argument(
        "--caller",
        type=str,
        default="polecat",
        help="Identity claiming the tasks (default: bot)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without running actual agents",
    )
    parser.add_argument(
        "--home",
        type=str,
        help="Polecat home directory (default: ~/.aops, or POLECAT_HOME env var)",
    )
    parser.add_argument(
        "--gemini-stagger",
        type=float,
        default=None,
        help=f"Seconds between Gemini worker spawns (default: {DEFAULT_GEMINI_STAGGER_S}s)",
    )

    args = parser.parse_args()
    run_swarm(
        args.claude,
        args.gemini,
        args.project,
        args.caller,
        args.dry_run,
        args.home,
        args.gemini_stagger,
    )


if __name__ == "__main__":
    main()
