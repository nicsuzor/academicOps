"""Tests for filing premise-check argdown claims to OTEL / Phoenix.

Covers:
1. Validating and emitting premise_check_claim spans with correct attributes.
2. Handling fenced markdown blocks and raw argdown text.
3. Proper error handling for empty claim IDs, invalid argdown syntax, and missing asks.
4. Export failure and unconfigured tracing handling.
5. CLI execution for file_claims.py and premise_check_verdict.py claim subcommand.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _REPO_ROOT / "plugins" / "ida" / "hooks"
_DUMP_SCRIPTS = _REPO_ROOT / "plugins" / "ida" / "skills" / "dump" / "scripts"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
if str(_DUMP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DUMP_SCRIPTS))

import file_claims
import premise_check_verdict as pcv
import report_argument as ra

_POLICY = tomllib.loads((_REPO_ROOT / "tests" / "policy.toml").read_text(encoding="utf-8"))[
    "premise_check"
]
_VOCAB = ra.load_vocabulary(_REPO_ROOT / _POLICY["vocabulary"])
_CLAIM_TOOL = _POLICY["claim_tool_name"]
_CLAIM_STATUS = _POLICY["claim_status"]

_VALID_ARGDOWN = """===
asks:
  task-1/AC1: is the feature implemented?
  task-1/AC2: do tests pass?
answers:
  task-1/AC1: 3
  task-1/AC2: 3
notes:
  a: src/feature.py:10
===

(1) The code changes implement the feature. -- I read it ^a
(2) Test suite passes green. -- I did it: 10 passed
-- When code implements the feature and tests pass, the acceptance criteria hold. Unless: unexpected runtime fault; not ruled out. --
(3) So the feature is complete and verified.
"""

_FENCED_REPORT = f"""# Handover Report

Some context before the block.

```argdown
{_VALID_ARGDOWN}
```

Trailing notes.
"""


class _StubTracer:
    """Stand-in for claude_code_tracer."""

    def __init__(self, config: dict[str, Any] | None, export_ok: bool = True, raises=None):
        self._config = config
        self._export_ok = export_ok
        self._raises = raises
        self.exported: list[dict[str, Any]] = []

    def discover_config(self, data=None):
        return self._config

    def _new_trace_id(self):
        return "1" * 32

    def _new_span_id(self):
        return "2" * 16

    def _load_state(self, session_id):
        return {}

    def _truncate(self, value):
        return value if isinstance(value, str) else json.dumps(value)

    def _build_tool_span_record(self, **kwargs):
        return {
            "name": kwargs["tool_name"],
            "attributes": {
                "openinference.span.kind": "TOOL",
                "tool.name": kwargs["tool_name"],
                "input.value": self._truncate(kwargs["tool_input"]),
            },
        }

    def _build_and_export_spans(self, *, span_records, **_kw):
        self.exported.extend(span_records)
        if self._raises is not None:
            raise self._raises
        return self._export_ok


def _configured(export_ok: bool = True, raises=None) -> _StubTracer:
    return _StubTracer({"endpoint": "http://127.0.0.1:4317"}, export_ok=export_ok, raises=raises)


def test_record_claims_emits_span_with_attributes():
    tracer = _configured()
    res = pcv.record_claims(
        session_id="s-test",
        claim_id="task-123",
        argdown_text=_VALID_ARGDOWN,
        title="Test Task Claims",
        tracer_mod=tracer,
    )

    assert res["ok"] is True
    assert res["claim_id"] == "task-123"
    assert res["status"] == _CLAIM_STATUS
    assert res["ask_ids"] == ["task-1/AC1", "task-1/AC2"]
    assert res["title"] == "Test Task Claims"
    assert res["span_emitted"] is True

    assert len(tracer.exported) == 1
    span = tracer.exported[0]
    assert span["name"] == _CLAIM_TOOL

    attrs = span["attributes"]
    assert attrs["premise_check.claim_id"] == "task-123"
    assert attrs["premise_check.status"] == _CLAIM_STATUS
    assert attrs["premise_check.ask_ids"] == ["task-1/AC1", "task-1/AC2"]
    assert attrs["premise_check.has_block"] is True
    assert attrs["premise_check.title"] == "Test Task Claims"
    assert attrs["premise_check.inference_count"] == 1
    assert attrs["premise_check.premise_count"] == 2
    assert attrs["premise_check.weakest_basis"] == "I read it"
    assert attrs["premise_check.weakest_basis_term"] == "observed"
    assert (
        attrs["premise_check.argdown_sha256"]
        == hashlib.sha256(_VALID_ARGDOWN.strip().encode("utf-8")).hexdigest()
    )


def test_record_claims_extracts_from_fenced_markdown():
    tracer = _configured()
    res = pcv.record_claims(
        session_id="s-test",
        claim_id="task-fenced",
        argdown_text=_FENCED_REPORT,
        tracer_mod=tracer,
    )
    assert res["ok"] is True
    assert res["claim_id"] == "task-fenced"
    assert res["ask_ids"] == ["task-1/AC1", "task-1/AC2"]

    assert len(tracer.exported) == 1
    attrs = tracer.exported[0]["attributes"]
    assert attrs["premise_check.has_block"] is True
    assert attrs["premise_check.inference_count"] == 1


def test_record_claims_rejects_missing_or_empty_claim_id():
    tracer = _configured()
    with pytest.raises(ValueError, match="claims need a claim id"):
        pcv.record_claims(
            session_id="s-test",
            claim_id="   ",
            argdown_text=_VALID_ARGDOWN,
            tracer_mod=tracer,
        )


def test_record_claims_rejects_empty_argdown():
    tracer = _configured()
    with pytest.raises(ValueError, match="claims need argdown content"):
        pcv.record_claims(
            session_id="s-test",
            claim_id="task-1",
            argdown_text="",
            tracer_mod=tracer,
        )


def test_record_claims_rejects_unparseable_argdown():
    tracer = _configured()
    with pytest.raises(ValueError, match="failed to parse argdown block"):
        pcv.record_claims(
            session_id="s-test",
            claim_id="task-1",
            argdown_text="===\nasks:\n  task-1/AC1: test\n",  # unclosed frontmatter fence
            tracer_mod=tracer,
        )


def test_record_claims_rejects_block_with_no_asks():
    tracer = _configured()
    no_asks = """===
notes:
  a: ptr
===
(1) Premise. -- rule
-- Warrant. Unless: def; status. --
(2) So conclusion.
"""
    with pytest.raises(ValueError, match="argdown block carries no ask ids"):
        pcv.record_claims(
            session_id="s-test",
            claim_id="task-1",
            argdown_text=no_asks,
            tracer_mod=tracer,
        )


def test_record_claims_raises_on_unconfigured_tracer():
    tracer = _StubTracer(config=None)
    with pytest.raises(RuntimeError, match="tracing is not configured"):
        pcv.record_claims(
            session_id="s-test",
            claim_id="task-1",
            argdown_text=_VALID_ARGDOWN,
            tracer_mod=tracer,
        )


def test_record_claims_raises_on_export_failure():
    tracer = _configured(export_ok=False)
    with pytest.raises(RuntimeError, match="OTel span export failed"):
        pcv.record_claims(
            session_id="s-test",
            claim_id="task-1",
            argdown_text=_VALID_ARGDOWN,
            tracer_mod=tracer,
        )

    tracer_raises = _configured(raises=OSError("network down"))
    with pytest.raises(RuntimeError, match="OTel span export failed"):
        pcv.record_claims(
            session_id="s-test",
            claim_id="task-1",
            argdown_text=_VALID_ARGDOWN,
            tracer_mod=tracer_raises,
        )


def test_file_claims_cli_runner_success(monkeypatch, tmp_path, capsys):
    tracer = _configured()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)

    argdown_file = tmp_path / "report.md"
    argdown_file.write_text(_FENCED_REPORT, encoding="utf-8")

    rc = file_claims.main(
        [
            "--claim",
            "task-cli-1",
            "--argdown-file",
            str(argdown_file),
            "--session",
            "s-cli-test",
            "--title",
            "CLI Claim Test",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["claim_id"] == "task-cli-1"
    assert data["status"] == _CLAIM_STATUS
    assert data["ask_ids"] == ["task-1/AC1", "task-1/AC2"]
    assert len(tracer.exported) == 1


def test_file_claims_cli_runner_stdin(monkeypatch, capsys):
    tracer = _configured()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    monkeypatch.setattr(sys, "stdin", type("Stdin", (), {"read": lambda self: _VALID_ARGDOWN})())

    rc = file_claims.main(
        [
            "--claim",
            "task-stdin",
            "--argdown-file",
            "-",
            "--session",
            "s-stdin",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["claim_id"] == "task-stdin"
    assert len(tracer.exported) == 1


def test_file_claims_cli_runner_failure(monkeypatch, capsys):
    tracer = _configured()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)

    rc = file_claims.main(["--claim", "task-bad", "--argdown", "bad argdown"])
    assert rc != 0
    captured = capsys.readouterr()
    assert "file_claims.py:" in captured.err


def test_premise_check_verdict_claim_subcommand(monkeypatch, capsys):
    tracer = _configured()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)

    rc = pcv.main(
        [
            "claim",
            "--claim",
            "task-subcmd",
            "--argdown",
            _VALID_ARGDOWN,
            "--session",
            "s-subcmd",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["claim_id"] == "task-subcmd"
    assert len(tracer.exported) == 1
