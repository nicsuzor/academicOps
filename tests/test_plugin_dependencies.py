"""Tests for plugin dependency declarations and premise-check verdict OTel requirements.

Verifies that the plugin dependency template and built ida plugin distributions
declare the OpenTelemetry packages required for premise-check verdict span emission,
asserting against policy in tests/policy.toml.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from build.build import build_all

_REPO_ROOT = Path(__file__).resolve().parent.parent
_POLICY_FILE = _REPO_ROOT / "tests" / "policy.toml"
_policy = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8")) if _POLICY_FILE.exists() else {}
_REQUIRED_PACKAGES = _policy.get("plugins", {}).get("dependencies", {}).get("otel_packages", [])

_TEMPLATE_PATH = _REPO_ROOT / "templates" / "plugin" / "pyproject.template.toml"
_MARKETPLACE_PATH = _REPO_ROOT / "build" / "marketplace.toml"


def _get_dependencies_from_toml(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    data = tomllib.loads(content)
    return data.get("project", {}).get("dependencies", [])


def _declares_package(dependencies: list[str], package_name: str) -> bool:
    for dep in dependencies:
        pkg = dep.split(">=")[0].split("==")[0].split("<")[0].split(";")[0].strip()
        if pkg == package_name:
            return True
    return False


def test_plugin_template_declares_required_otel_dependencies():
    """Verify that templates/plugin/pyproject.template.toml declares every package required by policy."""
    assert _TEMPLATE_PATH.is_file(), f"Missing {_TEMPLATE_PATH}"
    assert _REQUIRED_PACKAGES, "tests/policy.toml must define plugins.dependencies.otel_packages"

    dependencies = _get_dependencies_from_toml(_TEMPLATE_PATH)
    for pkg in _REQUIRED_PACKAGES:
        assert _declares_package(dependencies, pkg), (
            f"templates/plugin/pyproject.template.toml does not declare required package: {pkg}"
        )


def test_built_ida_plugin_carries_declared_dependencies(tmp_path):
    """Verify that building the ida plugin produces pyproject.toml declaring required OTel packages."""
    assert _MARKETPLACE_PATH.is_file(), f"Missing {_MARKETPLACE_PATH}"
    assert _REQUIRED_PACKAGES, "tests/policy.toml must define plugins.dependencies.otel_packages"

    dist_root = tmp_path / "dist"
    build_all(
        _REPO_ROOT,
        dist_root,
        marketplace_path=_MARKETPLACE_PATH,
        plugins=["ida"],
        version="0.10.10-test",
    )

    for client in ("claude", "agy"):
        plugin_dir = dist_root / f"ida-{client}"
        assert plugin_dir.is_dir(), f"Expected built plugin dir at {plugin_dir}"
        pyproject_path = plugin_dir / "pyproject.toml"
        assert pyproject_path.is_file(), f"Expected pyproject.toml in {plugin_dir}"

        dependencies = _get_dependencies_from_toml(pyproject_path)
        for pkg in _REQUIRED_PACKAGES:
            assert _declares_package(dependencies, pkg), (
                f"{client} build of ida plugin does not declare required package: {pkg}"
            )


def test_premise_check_verdict_resolves_claude_code_tracer_and_otel():
    """Verify that premise_check_verdict imports claude_code_tracer and can resolve OTel SDK."""
    import sys

    ida_hooks = _REPO_ROOT / "plugins" / "ida" / "hooks"
    if str(ida_hooks) not in sys.path:
        sys.path.insert(0, str(ida_hooks))

    import claude_code_tracer  # noqa: F401
    import premise_check_verdict as pcv

    tracer = pcv._import_claude_code_tracer()
    assert tracer is not None, "pcv._import_claude_code_tracer() failed to import tracer"

    # Verify OpenTelemetry SDK and OTLP proto HTTP exporter are imported
    import opentelemetry.exporter.otlp.proto.http  # noqa: F401
    import opentelemetry.sdk.trace  # noqa: F401
    import requests  # noqa: F401

    assert opentelemetry.sdk.trace.TracerProvider is not None
