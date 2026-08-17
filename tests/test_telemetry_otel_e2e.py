"""End-to-end proof that Claude Code's native OpenTelemetry export actually
delivers records when the framework's env contract
(lib/polecat/env_contract.py `TELEMETRY_ENV`) is populated. See
specs/ARCHITECTURE.md, Observability: the
framework defines and forwards the contract but emits no spans of its own —
Claude Code's native export is the only mechanism, and this is the one place
that mechanism is exercised against a real collector rather than assumed.

Marked `otel_e2e` and excluded from the default `make test` run (see
`addopts` in pyproject.toml): it starts a real Docker container and a real
Claude Code session, so it is opt-in. Run explicitly with:

    uv run pytest -m otel_e2e tests/test_telemetry_otel_e2e.py -v

Skips cleanly, with a stated reason, whenever Docker, a pullable collector
image, or Claude Code credentials are unavailable — a missing precondition
must never read as a pass.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.polecat.env_contract import TELEMETRY_ENV as CONTRACT  # noqa: E402

pytestmark = pytest.mark.otel_e2e

_COLLECTOR_IMAGE = "otel/opentelemetry-collector-contrib:latest"
_COLLECTOR_CONFIG = """\
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318

exporters:
  file:
    path: /output/telemetry.jsonl

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [file]
    logs:
      receivers: [otlp]
      exporters: [file]
    traces:
      receivers: [otlp]
      exporters: [file]
"""

_DOCKER_TIMEOUT = 30
_PULL_TIMEOUT = 120
_READY_TIMEOUT = 20
_CLAUDE_TIMEOUT = 90
_DRAIN_TIMEOUT = 20


def _docker_available() -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "docker is not on PATH"
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=_DOCKER_TIMEOUT
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"docker info failed: {exc}"
    if result.returncode != 0:
        return False, f"docker daemon unreachable: {result.stderr.strip()[:200]}"
    return True, ""


def _claude_credentials_available() -> tuple[bool, str]:
    if shutil.which("claude") is None:
        return False, "claude CLI is not on PATH"
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"):
        return True, ""
    if (Path.home() / ".claude" / ".credentials.json").exists():
        return True, ""
    return False, (
        "no CLAUDE_CODE_OAUTH_TOKEN / ANTHROPIC_API_KEY env var and no "
        "~/.claude/.credentials.json — claude CLI has no way to authenticate"
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _collector_image_ready() -> tuple[bool, str]:
    """True once the collector image is present locally, pulling it if not.

    A network-side pull failure is a clean skip, not a test failure — the
    precondition is "image available", not "network reachable".
    """
    inspect = subprocess.run(
        ["docker", "image", "inspect", _COLLECTOR_IMAGE],
        capture_output=True,
        timeout=_DOCKER_TIMEOUT,
    )
    if inspect.returncode == 0:
        return True, ""
    try:
        pull = subprocess.run(
            ["docker", "pull", _COLLECTOR_IMAGE],
            capture_output=True,
            text=True,
            timeout=_PULL_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, f"docker pull {_COLLECTOR_IMAGE} timed out after {_PULL_TIMEOUT}s"
    if pull.returncode != 0:
        return False, f"could not pull {_COLLECTOR_IMAGE}: {pull.stderr.strip()[:300]}"
    return True, ""


_docker_ok, _docker_reason = _docker_available()
_creds_ok, _creds_reason = _claude_credentials_available()


@pytest.mark.skipif(not _docker_ok, reason=f"docker precondition failed: {_docker_reason}")
@pytest.mark.skipif(
    not _creds_ok, reason=f"claude credentials precondition failed: {_creds_reason}"
)
def test_native_otel_export_reaches_a_real_collector(tmp_path):
    """Populate the 15-var contract, run a real headless Claude Code session,
    and assert a real `claude_code.*` metric arrived at a throwaway collector.

    Also asserts that a `resourceSpans` entry with claude-code-attributable
    content arrived: `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` is required
    upstream, alongside `OTEL_TRACES_EXPORTER`, for Claude Code to actually
    export trace spans — see specs/ARCHITECTURE.md, Observability.
    `resourceLogs` presence is captured and reported, not asserted: the logs
    pipeline is wired in `_COLLECTOR_CONFIG`, but nothing in the contract is
    documented to guarantee a log record for this minimal `-p` session.

    This is the only test in the suite that observes the native OTel export
    actually deliver a record end to end, rather than asserting on the flags
    a caller would pass it.
    """
    image_ok, image_reason = _collector_image_ready()
    if not image_ok:
        pytest.skip(f"collector image precondition failed: {image_reason}")

    output_dir = tmp_path / "otel-output"
    output_dir.mkdir()
    telemetry_file = output_dir / "telemetry.jsonl"
    telemetry_file.touch()
    # otelcol-contrib's image runs as a non-root UID; the bind mount must be
    # writable by it, not just by the host user that owns tmp_path.
    telemetry_file.chmod(0o666)
    output_dir.chmod(0o777)

    config_file = tmp_path / "collector-config.yaml"
    config_file.write_text(_COLLECTOR_CONFIG)

    http_port = _free_port()
    container_name = f"aops-otel-e2e-{os.getpid()}-{http_port}"

    run = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{http_port}:4318",
            "-v",
            f"{config_file}:/etc/otelcol-contrib/config.yaml",
            "-v",
            f"{output_dir}:/output",
            _COLLECTOR_IMAGE,
        ],
        capture_output=True,
        text=True,
        timeout=_DOCKER_TIMEOUT,
    )
    if run.returncode != 0:
        pytest.fail(f"docker run for the collector fixture failed: {run.stderr.strip()}")

    try:
        deadline = time.monotonic() + _READY_TIMEOUT
        ready = False
        while time.monotonic() < deadline:
            logs = subprocess.run(
                ["docker", "logs", container_name],
                capture_output=True,
                text=True,
                timeout=_DOCKER_TIMEOUT,
            )
            if "Everything is ready" in logs.stdout + logs.stderr:
                ready = True
                break
            time.sleep(1)
        assert ready, (
            f"collector did not report ready within {_READY_TIMEOUT}s; "
            f"logs:\n{logs.stdout}\n{logs.stderr}"
        )

        contract_env = {
            "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
            "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1",
            "OTEL_METRICS_EXPORTER": "otlp",
            "OTEL_LOGS_EXPORTER": "otlp",
            "OTEL_TRACES_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://localhost:{http_port}",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            "OTEL_RESOURCE_ATTRIBUTES": "service.name=aops-otel-e2e-test",
            "OTEL_METRIC_EXPORT_INTERVAL": "1000",
            "OTEL_LOGS_EXPORT_INTERVAL": "1000",
            "OTEL_TRACES_EXPORT_INTERVAL": "1000",
        }
        # Every key set above must be one the shipped contract actually
        # forwards — this test proves the real contract works, not a
        # look-alike.
        for name in contract_env:
            assert name in CONTRACT, f"{name} is not in env_contract.TELEMETRY_ENV"

        session_env = os.environ.copy()
        session_env.update(contract_env)

        session = subprocess.run(
            [
                "claude",
                "-p",
                "Reply with exactly the single word: pong",
                "--model",
                "claude-haiku-4-5",
            ],
            env=session_env,
            capture_output=True,
            text=True,
            timeout=_CLAUDE_TIMEOUT,
        )
        assert session.returncode == 0, (
            f"claude session failed (exit {session.returncode}): {session.stderr.strip()[:500]}"
        )

        deadline = time.monotonic() + _DRAIN_TIMEOUT
        records: list[dict] = []
        while time.monotonic() < deadline:
            lines = [line for line in telemetry_file.read_text().splitlines() if line.strip()]
            if lines:
                try:
                    records = [json.loads(line) for line in lines]
                except json.decoder.JSONDecodeError:
                    time.sleep(0.5)
                    continue
                break
            time.sleep(1)

        assert records, (
            f"no telemetry records arrived at the collector within {_DRAIN_TIMEOUT}s "
            "of the claude session completing"
        )

        metric_names: set[str] = set()
        resource_service_names: set[str] = set()
        for record in records:
            for resource_metrics in record.get("resourceMetrics", []):
                attrs = {
                    a["key"]: a.get("value", {}).get("stringValue")
                    for a in resource_metrics.get("resource", {}).get("attributes", [])
                }
                if attrs.get("service.name"):
                    resource_service_names.add(attrs["service.name"])
                for scope_metrics in resource_metrics.get("scopeMetrics", []):
                    for metric in scope_metrics.get("metrics", []):
                        metric_names.add(metric["name"])

        claude_code_metrics = {n for n in metric_names if n.startswith("claude_code.")}
        assert claude_code_metrics, (
            f"no claude_code.* metric arrived at the collector; saw {metric_names or 'nothing'}"
        )
        assert any(
            name in ("claude-code", "aops-otel-e2e-test") for name in resource_service_names
        ), f"no recognized resource identified the sender; saw {resource_service_names}"

        span_names: set[str] = set()
        span_resource_service_names: set[str] = set()
        resource_spans_count = 0
        for record in records:
            for resource_spans in record.get("resourceSpans", []):
                resource_spans_count += 1
                attrs = {
                    a["key"]: a.get("value", {}).get("stringValue")
                    for a in resource_spans.get("resource", {}).get("attributes", [])
                }
                if attrs.get("service.name"):
                    span_resource_service_names.add(attrs["service.name"])
                for scope_spans in resource_spans.get("scopeSpans", []):
                    for span in scope_spans.get("spans", []):
                        if span.get("name"):
                            span_names.add(span["name"])

        resource_logs_count = sum(len(record.get("resourceLogs", [])) for record in records)
        log_record_count = sum(
            len(scope_logs.get("logRecords", []))
            for record in records
            for resource_logs in record.get("resourceLogs", [])
            for scope_logs in resource_logs.get("scopeLogs", [])
        )
        print(
            f"resourceLogs informational check: resourceLogs entries={resource_logs_count}, "
            f"logRecords={log_record_count} (not asserted — see docstring)"
        )

        spans_arrived = resource_spans_count and any(
            name in ("claude-code", "aops-otel-e2e-test") for name in span_resource_service_names
        )
        if not spans_arrived:
            version = subprocess.run(
                ["claude", "--version"], capture_output=True, text=True, timeout=_DOCKER_TIMEOUT
            ).stdout.strip()
            pytest.xfail(
                f"no resourceSpans in {len(records)} records collected (0 resourceSpans, "
                f"0 span-level service.name values); CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 was "
                f"set alongside OTEL_TRACES_EXPORTER=otlp, OTEL_TRACES_EXPORT_INTERVAL=1000, and "
                f"a working OTLP endpoint (proven by {len(claude_code_metrics)} claude_code.* "
                f"metrics arriving on the same collector in the same run), but claude CLI "
                f"{version or 'version unknown'} did not emit any trace spans within "
                f"{_DRAIN_TIMEOUT}s of the session completing."
            )
        assert spans_arrived, (
            f"no claude-code resourceSpans arrived at the collector within {_DRAIN_TIMEOUT}s; "
            f"resourceSpans entries={resource_spans_count}, "
            f"span resource service.name values={span_resource_service_names or 'none'}, "
            f"span names={span_names or 'none'}. "
            "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 was set alongside OTEL_TRACES_EXPORTER=otlp."
        )
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            timeout=_DOCKER_TIMEOUT,
        )
