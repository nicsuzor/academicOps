"""Tests for Claude Code cloud session Python environment and setup scripts.

Issue nicsuzor/academicOps#2835 / Task aops_e2188df7:
In Claude Code cloud sessions (host vm, cwd /home/user/<repo>), premise-check
verdict.py runs from the ida plugin cache using the ambient python3 environment.
Without opentelemetry-sdk, opentelemetry-exporter-otlp-proto-http, and requests,
verdict calls fail to emit OpenTelemetry spans to Phoenix (returning span_emitted: false
with ModuleNotFoundError: No module named 'opentelemetry.sdk').

The cloud session python3 environment is defined in the repo's cloud session setup
script (.claude/setup.sh) and templates/cloud_setup.sh.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SETUP_SH = _REPO_ROOT / ".claude" / "setup.sh"
_TEMPLATE_SH = _REPO_ROOT / "templates" / "cloud_setup.sh"

try:
    import opentelemetry.exporter.otlp.proto.http  # noqa: F401
    import opentelemetry.sdk  # noqa: F401
    import requests  # noqa: F401

    HAS_OTEL_SDK = True
except ImportError:
    HAS_OTEL_SDK = False


def test_setup_sh_installs_opentelemetry_sdk_and_exporters():
    """Verify .claude/setup.sh installs opentelemetry-sdk, OTLP http exporter, and requests."""
    assert _SETUP_SH.is_file(), f"Missing {_SETUP_SH}"
    content = _SETUP_SH.read_text(encoding="utf-8")
    assert "pip install" in content, ".claude/setup.sh must include a pip install invocation"
    assert "opentelemetry-sdk" in content, ".claude/setup.sh must install opentelemetry-sdk"
    assert "opentelemetry-exporter-otlp-proto-http" in content, (
        ".claude/setup.sh must install opentelemetry-exporter-otlp-proto-http"
    )
    assert "requests" in content, ".claude/setup.sh must install requests for OTLP proxy routing"


def test_cloud_setup_template_installs_opentelemetry_sdk_and_exporters():
    """Verify templates/cloud_setup.sh installs opentelemetry-sdk, OTLP http exporter, and requests."""
    assert _TEMPLATE_SH.is_file(), f"Missing {_TEMPLATE_SH}"
    content = _TEMPLATE_SH.read_text(encoding="utf-8")
    assert "pip install" in content, (
        "templates/cloud_setup.sh must include a pip install invocation"
    )
    assert "opentelemetry-sdk" in content, "templates/cloud_setup.sh must install opentelemetry-sdk"
    assert "opentelemetry-exporter-otlp-proto-http" in content, (
        "templates/cloud_setup.sh must install opentelemetry-exporter-otlp-proto-http"
    )
    assert "requests" in content, (
        "templates/cloud_setup.sh must install requests for OTLP proxy routing"
    )


@pytest.mark.skipif(not HAS_OTEL_SDK, reason="needs environment with opentelemetry-sdk installed")
def test_cloud_session_python_can_import_opentelemetry_sdk():
    """Verify that Python environment can import opentelemetry.sdk and requests."""
    import opentelemetry.exporter.otlp.proto.http
    import opentelemetry.sdk
    import requests

    assert opentelemetry.sdk is not None
    assert opentelemetry.exporter.otlp.proto.http is not None
    assert requests is not None
