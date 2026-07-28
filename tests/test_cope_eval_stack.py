"""Tests for the stack launcher (scripts/cope_eval_stack.py).

Two kinds of assertion. The decisions the launcher makes are pure functions and
are tested as such: which rules are worth warming, whether a process is already
up, and whether the PID on file is still the process that was recorded — the
last of which is what stands between `stop` and killing a stranger that
inherited the number.

Then a lifecycle test drives `start`, `status` and `stop` for real against a
stub binary standing in for llama-server, with the actual shim in front of it.
No real llama-server is launched anywhere here. Because those children are
deliberately detached, the stub carries its own watchdog and the fixture sweeps
by command line on the way out — a failing assertion must not leave a process
on the machine.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import cope_eval_stack as stack  # noqa: E402

# A stand-in for llama-server: answers /health, and answers a chat completion
# with the single "1" token the shim expects, so the real shim can sit in front
# of it. It takes the serving flags and ignores them. The watchdog is the
# point — this process is detached by design, so it must be unable to outlive
# the test run even if pytest is killed outright.
_FAKE_SERVER = """\
#!/usr/bin/env python3
import json, os, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[sys.argv.index("--port") + 1])
threading.Timer(120, os._exit, args=(0,)).start()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.reply({"status": "ok"})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.reply(
            {
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "1"},
                        "logprobs": {"content": [{"token": "1", "logprob": -0.05}]},
                        "finish_reason": "length",
                    }
                ]
            }
        )

    def reply(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
"""


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _sweep(marker: str) -> None:
    """Backstop for a detached child that outlived its record: kill anything
    whose command line still carries `marker`. Linux only, which is where these
    tests spawn."""
    proc = Path("/proc")
    if not proc.is_dir():
        return
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (
                (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
            )
        except OSError:
            continue
        if marker in cmdline:
            try:
                os.kill(int(entry.name), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


# ---------------------------------------------------------------------------
# Which rules get warmed
# ---------------------------------------------------------------------------


@pytest.fixture()
def rules_dir(tmp_path: Path) -> Path:
    path = tmp_path / "rules"
    path.mkdir()
    (path / "halt-on-failure.md").write_text(
        "---\ntrigger: always_on\ndescription: A rule.\n---\n\nNever bypass a failing check.\n"
    )
    (path / "manual.md").write_text("---\ntrigger: manual\n---\n\nOnly when asked.\n")
    (path / "index.md").write_text("---\ndescription: Reference material.\n---\n\nA path table.\n")
    (path / "plain.md").write_text("No frontmatter at all.\n")
    (path / "notes.txt").write_text("---\ntrigger: always_on\n---\n\nNot markdown.\n")
    (path / "broken.md").mkdir()  # a rule file that is not a file
    return path


def test_only_always_on_rules_are_warmed(rules_dir):
    """The same marker cope evaluates on. Warming a file cope never sends is
    wasted; missing one it does send leaves the first real call cold."""
    assert [slug for slug, _ in stack.always_on_policies(rules_dir)] == ["halt-on-failure"]


def test_the_warmed_policy_is_the_body_without_its_frontmatter(rules_dir):
    """cope sends the rule body as the policy, so warming has to send the same
    text — a prefix cached against different bytes is not cached at all."""
    policies = stack.always_on_policies(rules_dir)
    assert len(policies) == 1
    _, body = policies[0]
    assert body == "Never bypass a failing check."
    assert "trigger" not in body
    assert "---" not in body


def test_a_missing_rules_directory_warms_nothing(tmp_path):
    assert stack.always_on_policies(tmp_path / "absent") == []


def test_a_rule_that_is_all_frontmatter_is_not_warmed(tmp_path):
    path = tmp_path / "rules"
    path.mkdir()
    (path / "empty.md").write_text("---\ntrigger: always_on\n---\n")
    assert stack.always_on_policies(path) == []


# ---------------------------------------------------------------------------
# Whether to launch at all
# ---------------------------------------------------------------------------


def test_a_healthy_endpoint_is_not_started_again():
    assert stack.should_launch(endpoint_healthy=True, recorded_alive=False) is False


def test_a_process_still_loading_its_model_is_not_started_again():
    """The window a health check alone misses: the process is up, the model is
    not loaded, so nothing answers yet. Starting a second one here is how you
    get two servers fighting over one GPU."""
    assert stack.should_launch(endpoint_healthy=False, recorded_alive=True) is False


def test_nothing_running_means_launch():
    assert stack.should_launch(endpoint_healthy=False, recorded_alive=False) is True


# ---------------------------------------------------------------------------
# Never kill a recycled PID
# ---------------------------------------------------------------------------


def test_a_matching_cmdline_is_the_recorded_process():
    cmdline = "/opt/bin/llama-server --port 8090 -ngl 99"
    assert stack.cmdline_matches(cmdline, ["llama-server", "8090"])


def test_a_reused_pid_running_something_else_is_not_matched():
    """The assertion `stop` rests on. This PID is now somebody's editor."""
    assert not stack.cmdline_matches("vim notes.md", ["llama-server", "8090"])


def test_the_same_binary_on_a_different_port_is_not_matched():
    assert not stack.cmdline_matches("llama-server --port 9999", ["llama-server", "8090"])


def test_a_dead_pid_reports_no_cmdline_and_never_matches():
    assert stack.cmdline_matches(None, ["llama-server"]) is False


def test_an_empty_fingerprint_matches_nothing():
    """Otherwise `all([])` is True and every process matches — which would make
    `stop` a machine-wide hazard."""
    assert stack.cmdline_matches("llama-server --port 8090", []) is False


def test_a_record_whose_process_is_gone_yields_no_pid(tmp_path):
    pid_file = tmp_path / "gone.pid.json"
    pid_file.write_text(json.dumps({"pid": 2**22, "fingerprint": ["llama-server", "8090"]}))
    assert stack.live_pid(pid_file) is None


def test_a_record_naming_a_live_pid_that_does_not_match_yields_nothing(tmp_path):
    """A live PID is not enough — the fingerprint has to still be on it. PID 1
    is running init, not llama-server."""
    pid_file = tmp_path / "recycled.pid.json"
    pid_file.write_text(json.dumps({"pid": 1, "fingerprint": ["llama-server", "8090"]}))
    assert stack.live_pid(pid_file) is None


def test_a_missing_or_corrupt_record_yields_no_pid(tmp_path):
    assert stack.live_pid(tmp_path / "absent.pid.json") is None
    corrupt = tmp_path / "corrupt.pid.json"
    corrupt.write_text("not json")
    assert stack.live_pid(corrupt) is None


# ---------------------------------------------------------------------------
# The serving command
# ---------------------------------------------------------------------------


def test_the_serving_command_carries_the_tuned_flags():
    command = stack.llama_command("/opt/bin/llama-server", "/m/cope.gguf", "127.0.0.1", 8090, [])

    assert command[0] == "/opt/bin/llama-server"
    assert command[command.index("--model") + 1] == "/m/cope.gguf"
    assert command[command.index("--port") + 1] == "8090"
    # Without this one, Gemma-4's sliding window disables prefix caching and
    # every sweep pays full prompt processing again.
    assert "--swa-full" in command


def test_extra_args_land_last_so_they_can_override():
    command = stack.llama_command("llama-server", "m.gguf", "127.0.0.1", 8090, ["--threads", "4"])
    assert command[-2:] == ["--threads", "4"]
    assert command.index("--threads") > command.index("--swa-full")


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------


class _LabelStub(BaseHTTPRequestHandler):
    seen: list[dict] = []
    status = 200

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        type(self).seen.append(payload)
        body = json.dumps({"label": 0, "confidence": 0.9}).encode()
        self.send_response(type(self).status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture()
def label_stub():
    _LabelStub.seen = []
    _LabelStub.status = 200
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LabelStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v1/label"
    server.shutdown()
    server.server_close()


def test_warmup_classifies_every_rule_once(label_stub):
    policies = [("one", "First rule."), ("two", "Second rule."), ("three", "Third rule.")]
    answered, elapsed = stack.warm(label_stub, policies, timeout=10.0)

    assert answered == 3
    assert elapsed >= 0
    assert sorted(row["criteria_text"] for row in _LabelStub.seen) == [
        "First rule.",
        "Second rule.",
        "Third rule.",
    ]
    assert {row["content_text"] for row in _LabelStub.seen} == {stack.WARMUP_CONTENT}


def test_warmup_counts_what_failed_instead_of_raising(label_stub):
    """A stack that will not warm is still a stack that is up, so this reports
    a number rather than throwing into the middle of a start."""
    _LabelStub.status = 500
    answered, _ = stack.warm(label_stub, [("one", "First rule.")], timeout=10.0)
    assert answered == 0


# ---------------------------------------------------------------------------
# start / status / stop, for real, against a stub binary
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_stack(tmp_path):
    """The argv for a stack pointed at a stub server, with both processes
    guaranteed stopped again however the test ends."""
    server_bin = tmp_path / "fake_llama_server.py"
    server_bin.write_text(_FAKE_SERVER)
    server_bin.chmod(0o755)
    model = tmp_path / "cope.gguf"
    model.write_text("not really a model")
    log_dir = tmp_path / "logs"
    upstream_port, shim_port = _free_port(), _free_port()

    common = [
        "--log-dir", str(log_dir),
        "--upstream-port", str(upstream_port),
        "--shim-port", str(shim_port),
    ]  # fmt: skip
    start = [
        "start",
        *common,
        "--server-bin", str(server_bin),
        "--model", str(model),
        "--startup-timeout", "30",
    ]  # fmt: skip

    yield {
        "start": start,
        "status": ["status", *common],
        "stop": ["stop", *common],
        "logs": log_dir,
        "shim_port": shim_port,
    }

    try:
        stack.main(["stop", *common])
    except SystemExit:
        pass
    for pid_file in log_dir.glob("*.pid.json"):
        pid = stack.live_pid(pid_file)
        if pid is not None:
            stack.terminate(pid, grace=2.0)
    _sweep(f"--port {shim_port}")
    _sweep(f"--port {upstream_port}")


def test_start_brings_both_processes_up_and_stop_takes_them_down(live_stack):
    assert stack.main(live_stack["start"]) == 0
    assert stack.main(live_stack["status"]) == 0

    records = sorted(live_stack["logs"].glob("*.pid.json"))
    assert [path.name for path in records] == ["llama-server.pid.json", "shim.pid.json"]
    pids = [stack.live_pid(path) for path in records]
    assert all(pid is not None for pid in pids), "a recorded process is not the one recorded"

    assert stack.main(live_stack["stop"]) == 0
    assert list(live_stack["logs"].glob("*.pid.json")) == []
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and any(stack.process_cmdline(pid) for pid in pids):
        time.sleep(0.2)
    assert not any(stack.process_cmdline(pid) for pid in pids), "a process outlived stop"
    assert stack.main(live_stack["status"]) == 1


def test_starting_twice_leaves_the_first_pair_running(live_stack, capsys):
    """Idempotence is the whole point of health-gating the launch: running the
    command again must not put a second server on the GPU."""
    assert stack.main(live_stack["start"]) == 0
    first = {path.name: stack.live_pid(path) for path in live_stack["logs"].glob("*.pid.json")}

    capsys.readouterr()
    assert stack.main(live_stack["start"]) == 0
    assert "already up" in capsys.readouterr().out

    second = {path.name: stack.live_pid(path) for path in live_stack["logs"].glob("*.pid.json")}
    assert second == first


def test_start_warms_the_rules_through_the_real_shim(live_stack, rules_dir, capsys):
    """End to end: the launcher's warmup POSTs to the shim it started, which
    translates and calls the stub upstream. Proves the two halves meet."""
    assert stack.main([*live_stack["start"], "--warmup", str(rules_dir)]) == 0
    assert "warmup: 1/1 rules classified" in capsys.readouterr().out


def test_a_warmup_that_finds_no_rules_still_starts(live_stack, tmp_path, capsys):
    empty = tmp_path / "empty-rules"
    empty.mkdir()
    assert stack.main([*live_stack["start"], "--warmup", str(empty)]) == 0
    assert "nothing to warm" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# stop only touches what it started
# ---------------------------------------------------------------------------


class _HealthStub(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        body = b'{"status": "ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_stop_leaves_a_server_it_did_not_start_alone(tmp_path, capsys):
    """`stop` is not "kill whatever is on that port". Something answering there
    with no record behind it is somebody else's process, and it is reported
    rather than signalled."""
    servers = [ThreadingHTTPServer(("127.0.0.1", 0), _HealthStub) for _ in range(2)]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    ports = [str(server.server_address[1]) for server in servers]
    try:
        argv = [
            "stop",
            "--log-dir", str(tmp_path),
            "--upstream-port", ports[0],
            "--shim-port", ports[1],
        ]  # fmt: skip
        assert stack.main(argv) == 0
        captured = capsys.readouterr()
        assert captured.err.count("left alone") == 2
        # Still serving: nothing was signalled.
        assert stack.healthy(f"http://127.0.0.1:{ports[0]}/health")
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


def test_stop_clears_a_record_whose_process_is_gone(tmp_path, capsys):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    stale = log_dir / "llama-server.pid.json"
    stale.write_text(json.dumps({"pid": 2**22, "fingerprint": ["llama-server", "8090"]}))

    assert (
        stack.main(["stop", "--log-dir", str(log_dir), "--upstream-port", str(_free_port())]) == 0
    )
    assert not stale.exists()
    assert "stale record removed" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Configuration has no defaults
# ---------------------------------------------------------------------------


def test_the_operators_paths_have_no_defaults(monkeypatch, tmp_path):
    for name in ("COPE_STACK_LOG_DIR", "COPE_STACK_SERVER_BIN", "COPE_STACK_MODEL"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(SystemExit) as missing_log_dir:
        stack.main(["status"])
    assert "--log-dir" in str(missing_log_dir.value)

    with pytest.raises(SystemExit) as missing_binary:
        stack.main(["start", "--log-dir", str(tmp_path)])
    assert "--server-bin" in str(missing_binary.value)

    with pytest.raises(SystemExit) as missing_model:
        stack.main(["start", "--log-dir", str(tmp_path), "--server-bin", "/opt/bin/llama-server"])
    assert "--model" in str(missing_model.value)


def test_status_reports_down_without_touching_anything(tmp_path, capsys):
    argv = [
        "status",
        "--log-dir", str(tmp_path),
        "--upstream-port", str(_free_port()),
        "--shim-port", str(_free_port()),
    ]  # fmt: skip
    assert stack.main(argv) == 1
    assert "[down]" in capsys.readouterr().out
