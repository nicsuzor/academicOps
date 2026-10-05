"""The OTLP HTTP span exporter honours the environment proxy, and only when one applies."""

from __future__ import annotations

import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

_ENV_VARS = (
    "HTTPS_PROXY",
    "https_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "ALL_PROXY",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "SSL_CERT_FILE",
    "OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE",
    "OTEL_EXPORTER_OTLP_CERTIFICATE",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def recording_server():
    """A local HTTP server that answers 200 and records each request line's target."""
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            seen.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", seen
    finally:
        server.shutdown()
        server.server_close()


def _export_one_span(endpoint: str) -> SpanExportResult:
    exporter = claude_code_tracer._create_exporter(
        endpoint, {"x-test": "1"}, protocol="http/protobuf"
    )
    results: list[SpanExportResult] = []

    class Recording(SpanExporter):
        def export(self, spans):
            result = exporter.export(spans)
            results.append(result)
            return result

        def shutdown(self):
            exporter.shutdown()

    provider = TracerProvider(resource=Resource.create({"service.name": "proxy-test"}))
    provider.add_span_processor(SimpleSpanProcessor(Recording()))
    with provider.get_tracer("proxy-test").start_as_current_span("span"):
        pass
    provider.shutdown()
    assert len(results) == 1
    return results[0]


def test_export_goes_through_env_proxy(monkeypatch, recording_server):
    proxy_url, seen = recording_server
    monkeypatch.setenv("HTTP_PROXY", proxy_url)
    endpoint = "http://collector.example.invalid/v1/traces"

    assert _export_one_span(endpoint) == SpanExportResult.SUCCESS
    # A forward proxy receives the absolute URL of the real destination.
    assert seen == [endpoint]


def test_export_is_direct_without_proxy(recording_server):
    server_url, seen = recording_server

    assert claude_code_tracer._proxy_http_kwargs(f"{server_url}/v1/traces") == {}
    assert _export_one_span(f"{server_url}/v1/traces") == SpanExportResult.SUCCESS
    assert seen == ["/v1/traces"]


def test_no_proxy_bypasses_proxy(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "collector.example.com")

    assert claude_code_tracer._proxy_http_kwargs("https://collector.example.com/v1/traces") == {}


def test_https_proxy_uses_session_and_env_ca_bundle(monkeypatch, tmp_path):
    bundle = tmp_path / "ca-bundle.crt"
    bundle.write_text("")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("SSL_CERT_FILE", str(bundle))

    kwargs = claude_code_tracer._proxy_http_kwargs("https://collector.example.com/v1/traces")

    assert kwargs["session"].trust_env
    assert kwargs["certificate_file"] == str(bundle)


def test_otel_certificate_env_wins_over_ca_bundle(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/env/ca.crt")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_CERTIFICATE", "/otel/ca.crt")

    kwargs = claude_code_tracer._proxy_http_kwargs("https://collector.example.com/v1/traces")

    assert "session" in kwargs
    assert "certificate_file" not in kwargs
