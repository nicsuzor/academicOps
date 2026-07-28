#!/usr/bin/env python3
"""Start, stop, and inspect the local CoPE evaluation stack.

Two processes: ``llama-server`` holding the classifier, and
``scripts/cope_eval_shim.py`` in front of it translating the CoPE label API
onto single-token completions. This starts both, or reports on both, or stops
both.

    cope_eval_stack.py start --server-bin <path> --model <path> --log-dir <dir>
    cope_eval_stack.py start ... --warmup .agents/rules
    cope_eval_stack.py status --log-dir <dir>
    cope_eval_stack.py stop --log-dir <dir>

``start`` is idempotent: an endpoint that already answers, or a process this
launcher recorded and that is still alive, is left alone rather than started
twice. ``stop`` kills only what this launcher recorded, and only after checking
the live process is still the one recorded — a PID is reused, so a PID alone is
not enough to kill on.

The server binary, the model, and the log directory are the operator's, and
have no defaults here. Both children inherit this process's environment, which
is how ``LD_LIBRARY_PATH`` reaches CUDA where the loader needs help finding it.

Standard library only, so it runs under a bare ``python3``.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

#: llama-server's serving parameters for this model. Not endpoints and not
#: credentials — how the classifier is served, which is the same wherever it
#: runs. ``--swa-full`` is load-bearing: without it Gemma-4's sliding-window
#: attention disables prefix caching, and every rule re-processes its policy
#: from scratch on every tool call.
SERVING_FLAGS = (
    "-ngl", "99",
    "--n-cpu-moe", "99",
    "--swa-full",
    "--ctx-size", "24576",
    "--parallel", "8",
    "-ub", "1024",
    "--jinja",
    "--threads", "20",
    "--threads-batch", "26",
)  # fmt: skip

#: Sent as the content of every warmup request. Short on purpose: warmup exists
#: to cache the policy prefixes, and the content sits after them.
WARMUP_CONTENT = 'Tool: Read\nInput: {"file_path": "warmup"}'

#: How many warmup requests are in flight at once — the same width cope
#: evaluates a rule set at, so the warmed state matches the real one.
WARMUP_CONCURRENCY = 8

#: Longest wait for a child to answer its health endpoint. A cold model load
#: is most of it.
STARTUP_TIMEOUT = 300.0

#: Grace between SIGTERM and SIGKILL.
STOP_GRACE = 10.0


@dataclass(frozen=True)
class Endpoint:
    """One of the two processes, and how to find, check, and recognise it."""

    name: str
    health_url: str
    pid_file: Path
    log_file: Path


@dataclass(frozen=True)
class Stack:
    host: str
    upstream_port: int
    shim_port: int
    log_dir: Path

    @property
    def upstream_base(self) -> str:
        return f"http://{self.host}:{self.upstream_port}"

    @property
    def shim_base(self) -> str:
        return f"http://{self.host}:{self.shim_port}"

    @property
    def label_url(self) -> str:
        return f"{self.shim_base}/v1/label"

    def endpoints(self) -> tuple[Endpoint, Endpoint]:
        return (
            Endpoint(
                "llama-server",
                f"{self.upstream_base}/health",
                self.log_dir / "llama-server.pid.json",
                self.log_dir / "llama-server.log",
            ),
            Endpoint(
                "shim",
                f"{self.shim_base}/v1/health",
                self.log_dir / "shim.pid.json",
                self.log_dir / "shim.log",
            ),
        )


# --- Health, processes, and the decisions that depend on them ---------------


def healthy(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (TimeoutError, urllib.error.URLError, OSError):
        return False


def wait_healthy(url: str, timeout: float, poll: float = 0.5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if healthy(url):
            return True
        time.sleep(poll)
    return False


def process_cmdline(pid: int) -> str | None:
    """The live command line for ``pid``, or None if there is no such process."""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        pass
    else:
        # A zombie has an empty cmdline. It cannot serve anything and must not
        # be waited on as though it were still going.
        return raw.replace(b"\0", b" ").decode("utf-8", "replace").strip() or None
    try:
        done = subprocess.run(
            ["ps", "-o", "command=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() or None


def cmdline_matches(cmdline: str | None, fingerprint: list[str]) -> bool:
    """Whether the live process is the one that was recorded.

    PIDs are reused, so the recorded number alone is never enough to send a
    signal to. Every token of the fingerprint has to still be there.
    """
    if not cmdline or not fingerprint:
        return False
    return all(token in cmdline for token in fingerprint)


def should_launch(endpoint_healthy: bool, recorded_alive: bool) -> bool:
    """Whether ``start`` launches this process, or leaves what is there alone.

    Health alone would double-start a server that is up but still loading its
    model, which answers nothing yet — hence the second condition.
    """
    return not (endpoint_healthy or recorded_alive)


def read_record(pid_file: Path) -> dict | None:
    try:
        record = json.loads(pid_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def live_pid(pid_file: Path) -> int | None:
    """The recorded PID, if it is still running the thing that was recorded."""
    record = read_record(pid_file)
    if not record:
        return None
    pid = record.get("pid")
    fingerprint = record.get("fingerprint")
    if not isinstance(pid, int) or not isinstance(fingerprint, list):
        return None
    return pid if cmdline_matches(process_cmdline(pid), fingerprint) else None


def spawn(command: list[str], log_file: Path, pid_file: Path, fingerprint: list[str]) -> int:
    """Launch ``command`` detached, recording what was launched.

    The child inherits this process's environment — the route ``LD_LIBRARY_PATH``
    takes to a CUDA build that needs it.
    """
    handle = log_file.open("ab")
    try:
        process = subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    finally:
        handle.close()
    pid_file.write_text(
        json.dumps({"pid": process.pid, "fingerprint": fingerprint, "command": command}),
        encoding="utf-8",
    )
    return process.pid


def terminate(pid: int, grace: float = STOP_GRACE) -> None:
    """SIGTERM, then SIGKILL if it is still there. A process that exits on its
    own in between is not an error — it is the outcome asked for."""
    try:
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            if process_cmdline(pid) is None:
                return
            time.sleep(0.2)
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


# --- Warmup -----------------------------------------------------------------


def _frontmatter_and_body(text: str) -> tuple[dict[str, str], str]:
    """Split a rule file's frontmatter fields from its body."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fields: dict[str, str] = {}
    for line in text[3:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields, text[end + len("\n---") :]


def always_on_policies(rules_dir: Path) -> list[tuple[str, str]]:
    """Every ``trigger: always_on`` rule under ``rules_dir``, body only.

    The same marker cope evaluates on, so warming these warms what the hook
    will actually ask about. An unreadable file is skipped: warmup is best
    effort by construction.
    """
    policies: list[tuple[str, str]] = []
    try:
        paths = sorted(rules_dir.glob("*.md"))
    except OSError:
        return policies
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        fields, body = _frontmatter_and_body(text)
        if fields.get("trigger") == "always_on" and body.strip():
            policies.append((path.stem, body.strip()))
    return policies


def _label(url: str, policy: str, timeout: float) -> bool:
    request = urllib.request.Request(
        url,
        data=json.dumps({"content_text": WARMUP_CONTENT, "criteria_text": policy}).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except (TimeoutError, urllib.error.URLError, OSError):
        return False


def warm(url: str, policies: list[tuple[str, str]], timeout: float) -> tuple[int, float]:
    """Classify a throwaway tool call against every policy, in parallel.

    Returns how many answered and how long the sweep took. Nothing here can
    fail a start: a stack that will not warm is still a stack that is up.
    """
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=WARMUP_CONCURRENCY) as pool:
        answered = sum(pool.map(lambda item: _label(url, item[1], timeout), policies))
    return answered, time.monotonic() - started


# --- Subcommands ------------------------------------------------------------


def llama_command(server_bin: str, model: str, host: str, port: int, extra: list[str]) -> list[str]:
    """The serving command. ``extra`` lands last, so it can override a flag above."""
    return [
        server_bin,
        "--host",
        host,
        "--port",
        str(port),
        "--model",
        model,
        *SERVING_FLAGS,
        *extra,
    ]


def shim_command(host: str, shim_port: int, upstream: str) -> list[str]:
    shim = Path(__file__).resolve().parent / "cope_eval_shim.py"
    if not shim.is_file():
        raise SystemExit(f"the shim is missing: {shim}")
    return [
        sys.executable,
        str(shim),
        "--host",
        host,
        "--port",
        str(shim_port),
        "--upstream",
        upstream,
    ]


def do_start(args: argparse.Namespace, stack: Stack) -> int:
    stack.log_dir.mkdir(parents=True, exist_ok=True)
    upstream, shim = stack.endpoints()

    plans = [
        (
            upstream,
            llama_command(
                args.server_bin, args.model, stack.host, stack.upstream_port, args.extra_args
            ),
            [Path(args.server_bin).name, str(stack.upstream_port)],
        ),
        (
            shim,
            shim_command(stack.host, stack.shim_port, stack.upstream_base),
            ["cope_eval_shim.py", str(stack.shim_port)],
        ),
    ]

    for endpoint, command, fingerprint in plans:
        if not should_launch(healthy(endpoint.health_url), live_pid(endpoint.pid_file) is not None):
            print(f"{endpoint.name}: already up on {endpoint.health_url}")
            continue
        pid = spawn(command, endpoint.log_file, endpoint.pid_file, fingerprint)
        print(f"{endpoint.name}: started (pid {pid}), logging to {endpoint.log_file}")
        if not wait_healthy(endpoint.health_url, args.startup_timeout):
            print(
                f"{endpoint.name}: no health answer within {args.startup_timeout:g}s — "
                f"see {endpoint.log_file}",
                file=sys.stderr,
            )
            return 1

    if args.warmup:
        _do_warmup(Path(args.warmup), stack, args.startup_timeout)

    print(_status_line(stack))
    return 0


def _do_warmup(rules_dir: Path, stack: Stack, timeout: float) -> None:
    policies = always_on_policies(rules_dir)
    if not policies:
        print(f"warmup: no `trigger: always_on` rules under {rules_dir} — nothing to warm")
        return
    answered, elapsed = warm(stack.label_url, policies, timeout)
    print(f"warmup: {answered}/{len(policies)} rules classified in {elapsed:.1f}s")
    if answered < len(policies):
        print(
            f"warmup: {len(policies) - answered} rule(s) went unanswered; the stack is up anyway",
            file=sys.stderr,
        )


def do_stop(_args: argparse.Namespace, stack: Stack) -> int:
    for endpoint in stack.endpoints():
        pid = live_pid(endpoint.pid_file)
        if pid is None:
            if endpoint.pid_file.exists():
                endpoint.pid_file.unlink()
                print(f"{endpoint.name}: not running (stale record removed)")
            elif healthy(endpoint.health_url):
                print(
                    f"{endpoint.name}: answering on {endpoint.health_url} but not started from "
                    f"{endpoint.pid_file} — left alone",
                    file=sys.stderr,
                )
            else:
                print(f"{endpoint.name}: not running")
            continue
        terminate(pid)
        endpoint.pid_file.unlink(missing_ok=True)
        print(f"{endpoint.name}: stopped (pid {pid})")
    return 0


def do_status(_args: argparse.Namespace, stack: Stack) -> int:
    print(_status_line(stack))
    return 0 if all(healthy(e.health_url) for e in stack.endpoints()) else 1


def _status_line(stack: Stack) -> str:
    parts = [
        f"{endpoint.name} {endpoint.health_url} "
        f"[{'up' if healthy(endpoint.health_url) else 'down'}]"
        for endpoint in stack.endpoints()
    ]
    return f"cope-eval-stack: {'  '.join(parts)}  label {stack.label_url}  logs {stack.log_dir}"


# --- CLI --------------------------------------------------------------------


def _required(value: str | None, flag: str, env: str) -> str:
    if not value:
        raise SystemExit(f"{flag} is required (or set {env}); this launcher has no default for it")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start, stop, and inspect the local CoPE evaluation stack."
    )
    parser.add_argument("command", choices=("start", "stop", "status"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--upstream-port", type=int, default=8090)
    parser.add_argument("--shim-port", type=int, default=8099)
    parser.add_argument(
        "--log-dir", default=os.environ.get("COPE_STACK_LOG_DIR"), help="[$COPE_STACK_LOG_DIR]"
    )
    parser.add_argument(
        "--server-bin",
        default=os.environ.get("COPE_STACK_SERVER_BIN"),
        help="llama-server binary [$COPE_STACK_SERVER_BIN]",
    )
    parser.add_argument(
        "--model", default=os.environ.get("COPE_STACK_MODEL"), help="GGUF path [$COPE_STACK_MODEL]"
    )
    parser.add_argument(
        "--extra-args",
        default=os.environ.get("COPE_STACK_EXTRA_ARGS", ""),
        help="extra llama-server flags, appended last so they override [$COPE_STACK_EXTRA_ARGS]",
    )
    parser.add_argument(
        "--warmup", default=None, help="rules directory to classify once, priming the prefix cache"
    )
    parser.add_argument("--startup-timeout", type=float, default=STARTUP_TIMEOUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    log_dir = _required(args.log_dir, "--log-dir", "COPE_STACK_LOG_DIR")
    stack = Stack(
        host=args.host,
        upstream_port=args.upstream_port,
        shim_port=args.shim_port,
        log_dir=Path(log_dir).expanduser(),
    )
    if args.command == "start":
        args.server_bin = _required(args.server_bin, "--server-bin", "COPE_STACK_SERVER_BIN")
        args.model = _required(args.model, "--model", "COPE_STACK_MODEL")
        args.extra_args = shlex.split(args.extra_args or "")
        return do_start(args, stack)
    if args.command == "stop":
        return do_stop(args, stack)
    return do_status(args, stack)


if __name__ == "__main__":
    raise SystemExit(main())
