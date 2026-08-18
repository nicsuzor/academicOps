"""Unit tests for lib/polecat/env_contract.py."""

import pytest

from lib.polecat import env_contract


def test_telemetry_env_contains_genai_and_otel_trace_protocol_names():
    """TELEMETRY_ENV must include GenAI engine and OTLP trace protocol variables."""
    expected = (
        "GENAI_ENGINE_TRACE_ENDPOINT",
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TASK_ID",
        "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
    )
    for name in expected:
        assert name in env_contract.TELEMETRY_ENV, f"{name} missing from TELEMETRY_ENV"


def test_forwarded_env_contains_genai_and_otel_trace_protocol_names():
    """FORWARDED_ENV must include GenAI engine and OTLP trace protocol variables."""
    expected = (
        "GENAI_ENGINE_TRACE_ENDPOINT",
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TASK_ID",
        "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
    )
    for name in expected:
        assert name in env_contract.FORWARDED_ENV, f"{name} missing from FORWARDED_ENV"


def test_docker_env_args_emits_genai_and_otel_trace_names():
    """docker_env_args() emits valueless -e flags for forwarded variables."""
    args = env_contract.docker_env_args()
    for name in (
        "GENAI_ENGINE_TRACE_ENDPOINT",
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TASK_ID",
        "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
    ):
        assert name in args
        assert args[args.index(name) - 1] == "-e"


@pytest.mark.parametrize(
    "key,input_val,expected_val",
    [
        (
            "GENAI_ENGINE_TRACE_ENDPOINT",
            "http://127.0.0.1:8000/v1/traces",
            "http://host.docker.internal:8000/v1/traces",
        ),
        (
            "GENAI_ENGINE_TRACE_ENDPOINT",
            "http://localhost:8000",
            "http://host.docker.internal:8000",
        ),
        (
            "GENAI_ENGINE_TRACE_ENDPOINT",
            "localhost:8000",
            "host.docker.internal:8000",
        ),
        (
            "GENAI_ENGINE_TRACE_ENDPOINT",
            "127.0.0.1:8000/v1/traces",
            "host.docker.internal:8000/v1/traces",
        ),
        (
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://127.0.0.1:4318",
            "http://host.docker.internal:4318",
        ),
        (
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "localhost:4317",
            "host.docker.internal:4317",
        ),
        (
            "BETA_TRACING_ENDPOINT",
            "http://localhost:4318",
            "http://host.docker.internal:4318",
        ),
        (
            "COPE_EVALUATOR_URL",
            "http://127.0.0.1:8099/v1/label",
            "http://host.docker.internal:8099/v1/label",
        ),
        (
            "GENAI_ENGINE_TRACE_ENDPOINT",
            "http://remote.host.example:8000/v1/traces",
            "http://remote.host.example:8000/v1/traces",
        ),
        (
            "GENAI_ENGINE_API_KEY",
            "sk-secret-12345",
            "sk-secret-12345",
        ),
    ],
)
def test_rehost_loopback_urls_rehosts_expected_endpoints(key, input_val, expected_val):
    """_rehost_loopback_urls rewrites loopback hosts to host.docker.internal."""
    env = {key: input_val}
    rehosted = env_contract._rehost_loopback_urls(env)
    assert rehosted[key] == expected_val
