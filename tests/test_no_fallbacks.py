"""Tests verifying that infrastructure errors halt loudly without fallbacks or silent downgrades.

Guards against regressions of:
- rules.py: swallowing OSError on unreadable rule files/directories into DEGRADED;
- evaluator.py: defaulting on failure for invalid COPE_EVALUATOR_TIMEOUT;
- evaluator.py: swallowing trace sink exceptions in _emit;
- claude_code_tracer.py: falling back to Console exporter or returning None on exporter failure;
- generate_pdf.py: defaulting to 'academic' on unreadable input files;
- dispatch.py: swallowing handler import/load errors into an empty handler list;
- clean_plugins.py: swallowing corrupt manifest JSON with continue/pass;
- premise_check_gate.py: swallowing corrupt state JSON into empty dict;
- tree.py: swallowing OSError in has_shebang;
- version.py: swallowing subprocess errors in _git_build_metadata and _git_tags.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_rules_load_raises_on_unreadable_rule_file(tmp_path):
    """When a rule file cannot be read, load() raises OSError rather than returning DEGRADED."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "plugins" / "rbg" / "hooks"))
    import rules

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    bad_rule = rules_dir / "unreadable.md"
    bad_rule.write_text("---\ntrigger: always_on\n---\nbody\n")
    bad_rule.chmod(0o000)

    try:
        with pytest.raises(OSError):
            rules._parse(bad_rule, 2)
    finally:
        bad_rule.chmod(0o644)


def test_evaluator_timeout_raises_on_invalid_number(monkeypatch):
    """When COPE_EVALUATOR_TIMEOUT is non-numeric, _timeout raises ValueError rather than defaulting."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "plugins" / "rbg" / "hooks"))
    import evaluator

    monkeypatch.setenv("COPE_EVALUATOR_TIMEOUT", "not-a-number")
    with pytest.raises(ValueError, match="is not a number"):
        evaluator._timeout()


def test_evaluator_timeout_raises_on_non_positive_number(monkeypatch):
    """When COPE_EVALUATOR_TIMEOUT is non-positive, _timeout raises ValueError rather than defaulting."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "plugins" / "rbg" / "hooks"))
    import evaluator

    monkeypatch.setenv("COPE_EVALUATOR_TIMEOUT", "-5")
    with pytest.raises(ValueError, match="is not positive"):
        evaluator._timeout()


def test_evaluator_emit_does_not_swallow_sink_exception():
    """When on_outcome raises, evaluator.check does not swallow it with pass."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "plugins" / "rbg" / "hooks"))
    import evaluator

    config = evaluator.Config(
        url="http://127.0.0.1:9999",
        protocol="cope",
        model="test",
        api_key=None,
        timeout=1.0,
    )

    def failing_sink(outcome):
        raise RuntimeError("sink crash")

    with patch.object(evaluator, "_label_call", return_value=(0, 0.9, "ok")):
        with pytest.raises(RuntimeError, match="sink crash"):
            evaluator.check(
                config=config,
                policies=[("p1", "policy text")],
                content="test",
                hooks_dir=REPO_ROOT / "plugins" / "rbg" / "hooks",
                on_outcome=failing_sink,
            )


def test_claude_code_tracer_create_exporter_raises_on_failure():
    """_create_exporter does not fall back to Console exporter or None when HTTP exporter fails."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "plugins" / "ida" / "hooks"))
    import claude_code_tracer

    with patch(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
        side_effect=RuntimeError("connection refused"),
    ):
        with pytest.raises(RuntimeError, match="connection refused"):
            claude_code_tracer._create_exporter(
                endpoint="http://127.0.0.1:4318",
                protocol="http/protobuf",
            )


def test_generate_pdf_detect_doc_type_raises_on_unreadable_file(tmp_path):
    """detect_document_type raises OSError on missing/unreadable file instead of defaulting to academic."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "plugins" / "tools" / "skills" / "pdf" / "scripts"))
    import generate_pdf

    missing_file = tmp_path / "nonexistent.md"
    with pytest.raises(OSError):
        generate_pdf.detect_document_type(missing_file)


def test_dispatch_load_handlers_raises_on_spec_or_exec_failure(tmp_path):
    """_load_handlers raises RuntimeError if handlers.py cannot be loaded, instead of returning []."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "plugins" / "ida" / "hooks"))
    import dispatch

    broken_handlers = tmp_path / "handlers.py"
    broken_handlers.write_text("raise SyntaxError('broken handler')\n")

    with pytest.raises(SyntaxError):
        dispatch._load_handlers("UserPromptSubmit", tmp_path)


def test_clean_plugins_raises_on_corrupted_manifest(tmp_path, monkeypatch):
    """clean_gui raises json.JSONDecodeError on invalid JSON manifest instead of continuing."""
    from scripts import clean_plugins

    base = tmp_path / "sessions"
    rpm_dir = base / "s1" / "rpm"
    rpm_dir.mkdir(parents=True)
    manifest = rpm_dir / "manifest.json"
    manifest.write_text("{not valid json")

    monkeypatch.setattr(clean_plugins, "get_cowork_bases", lambda: [base])
    with pytest.raises(json.JSONDecodeError):
        clean_plugins.clean_gui()


def test_premise_check_gate_load_state_raises_on_corrupt_json(tmp_path, monkeypatch):
    """_load_state raises json.JSONDecodeError on corrupt JSON state instead of returning {}."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "plugins" / "ida" / "hooks"))
    import premise_check_gate

    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path))
    state_file = tmp_path / "sess_corrupt.json"
    state_file.write_text("corrupted json payload")

    with pytest.raises(json.JSONDecodeError):
        premise_check_gate._load_state("sess_corrupt")


def test_tree_has_shebang_raises_on_unreadable_file(tmp_path):
    """has_shebang raises OSError on missing or unreadable file instead of returning False."""
    from build.tree import has_shebang

    missing_file = tmp_path / "missing.sh"
    with pytest.raises(OSError):
        has_shebang(missing_file)


def test_version_git_metadata_raises_on_git_failure(tmp_path):
    """_git_build_metadata raises subprocess.CalledProcessError when git fails instead of returning ''."""
    from build.version import _git_build_metadata

    # tmp_path is not a git repo, so git rev-parse fails
    with pytest.raises(subprocess.CalledProcessError):
        _git_build_metadata(tmp_path)


def test_version_git_tags_raises_on_git_failure(tmp_path):
    """_git_tags raises subprocess.CalledProcessError when git fails instead of returning []."""
    from build.version import _git_tags

    # tmp_path is not a git repo, so git tag fails
    with pytest.raises(subprocess.CalledProcessError):
        _git_tags(tmp_path)
