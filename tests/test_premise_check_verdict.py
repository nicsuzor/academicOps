"""Tests for premise-check verdict recording, slot guards, and fail-closed OTel emission."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugins" / "ida"
_HOOKS_DIR = _PLUGIN_ROOT / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import hearsay_gate as hg
import premise_check_verdict as pcv


class _StubTracer:
    """Minimal stub for claude_code_tracer."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        export_ok: bool = True,
        raises: BaseException | None = None,
    ):
        self._config = config
        self._export_ok = export_ok
        self._raises = raises
        self.exported: list[dict[str, Any]] = []

    def discover_config(self):
        return self._config

    def _new_trace_id(self):
        return "1" * 32

    def _new_span_id(self):
        return "2" * 16

    def _load_state(self, session_id):
        return {}

    def _truncate(self, value):
        return value if isinstance(value, str) else str(value)

    def _build_tool_span_record(self, **kwargs):
        return {
            "trace_id_hex": kwargs["trace_id"],
            "span_id_hex": self._new_span_id(),
            "parent_span_id_hex": kwargs["root_span_id"],
            "name": kwargs["tool_name"],
            "kind": None,
            "start_ns": kwargs["start_ns"],
            "end_ns": kwargs["end_ns"],
            "attributes": {
                "openinference.span.kind": "TOOL",
                "tool.name": kwargs["tool_name"],
            },
            "force_span_id": False,
        }

    def _build_and_export_spans(self, *, config, session_id, username, span_records, **_kw):
        if self._raises is not None:
            raise self._raises
        self.exported.append(
            {
                "config": config,
                "session_id": session_id,
                "username": username,
                "spans": span_records,
            }
        )
        return self._export_ok


def _configured_tracer(export_ok: bool = True, raises: BaseException | None = None) -> _StubTracer:
    return _StubTracer(
        config={"endpoint": "http://localhost:4317"}, export_ok=export_ok, raises=raises
    )


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate_state"))
    monkeypatch.setenv("AOPS_SESSION_ID", "test-verdict-session")
    yield


def test_task_record_handback_refusal_when_unarmed_reproduction():
    """Task-record handback verdicts succeed on an unarmed session without arming the gate."""
    tracer = _configured_tracer()
    session_id = "test-unarmed-session"
    task_id = "task_fixture_01"

    assert not hg.is_armed(session_id)

    reason = (
        f"REVISE {task_id}: the report's conclusion asserts runtime verification, "
        "but the cited premise only confirms static import."
    )

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason,
        tracer_mod=tracer,
    )
    assert res["ok"] is True
    assert res["claim_id"] == task_id
    assert res["verification_id"].startswith("verdict-")


def test_task_record_handback_verdict_records_with_task_id_and_verification_id():
    """Task-record handback verdict records task_id as claim_id and mints a verification_id."""
    tracer = _configured_tracer()
    session_id = "supervisor-session-1"
    task_id = "task_fixture_02"

    reason = (
        f"REVISE {task_id}: the defect observed in the runtime trace undercuts the claim "
        "that AC1 was satisfied."
    )

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason,
        title="task record check",
        tracer_mod=tracer,
    )

    assert res["ok"] is True
    assert res["claim_id"] == task_id
    assert res["verdict"] == "REVISE"
    assert res["verification_id"].startswith("verdict-")
    assert "task-record-check" in res["verification_id"]
    assert len(tracer.exported) == 1
    span = tracer.exported[0]["spans"][0]
    assert span["attributes"]["premise_check.claim_id"] == task_id
    assert span["attributes"]["premise_check.verification_id"] == res["verification_id"]
    assert span["attributes"]["premise_check.verdict"] == "REVISE"
    assert span["attributes"]["premise_check.reason_text"] == reason


def test_non_task_claim_refused_when_unarmed():
    """Non-task claim ids refuse with 'no premise check is currently armed' when unarmed."""
    tracer = _configured_tracer()
    session_id = "unarmed-non-task"
    claim_id = "claim-12345678"

    with pytest.raises(ValueError, match="no premise check is currently armed"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id=claim_id,
            verdict="REVISE",
            reason="some reason",
            tracer_mod=tracer,
        )


@pytest.mark.parametrize(
    ("verdict", "reason"),
    [
        (
            "PASS",
            "The premises support the conclusion directly; the change is reversible and low-stakes, "
            "and every part of the ask is answered from observed outputs.",
        ),
        (
            "REVISE",
            "The reasoning is valid as stated, but the deliverable misses the edge case in scope; "
            "revise to address empty inputs before resubmitting.",
        ),
        (
            "FAIL",
            "The conclusion depends on an unsupported assumption about upstream state that is "
            "contradicted by the cited log excerpt.",
        ),
    ],
)
def test_free_form_natural_language_reasons_accepted_and_emit_flat_span_attributes(
    verdict: str, reason: str
):
    """Free-form natural-language reasons are accepted for PASS/REVISE/FAIL on prose reports."""
    tracer = _configured_tracer()
    session_id = f"sess-freeform-{verdict}"
    claim_id = f"claim-free-{verdict.lower()}"
    judged_text = "Natural-language report without any fenced argdown block."

    hg.arm(
        session_id=session_id,
        claim_id=claim_id,
        judged_text=judged_text,
        judged_ref="toolu_freeform",
    )

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict=verdict,
        reason=reason,
        tracer_mod=tracer,
    )

    assert res["ok"] is True
    assert res["verdict"] == verdict
    assert res["disarmed"] is True
    assert res["no_claim"] is False
    assert hg.is_armed(session_id) is False

    attrs = tracer.exported[0]["spans"][0]["attributes"]
    assert attrs["premise_check.claim_id"] == claim_id
    assert attrs["premise_check.verdict"] == verdict
    assert attrs["premise_check.reason_text"] == reason
    assert attrs["premise_check.verification_id"] == res["verification_id"]
    assert attrs["premise_check.judged_ref"] == "toolu_freeform"
    assert (
        attrs["premise_check.judged_text_sha256"]
        == hashlib.sha256(judged_text.encode()).hexdigest()
    )
    assert attrs["premise_check.no_claim"] is False

    # No attribute is both a leaf and a dotted prefix (Phoenix nests dotted keys).
    keys = list(attrs)
    assert not [k for k in keys if any(o.startswith(k + ".") for o in keys)]


def test_explicit_no_claim_flag_sets_no_claim_while_prose_words_do_not(monkeypatch, tmp_path: Path):
    """--no-claim / no_claim=True sets premise_check.no_claim; prose mentioning 'no claim' without the flag does not."""
    tracer = _configured_tracer()

    # 1. Explicit no_claim=True via record_verdict with ordinary natural-language reason
    sess_flag = "sess-nc-explicit-flag"
    hg.arm(sess_flag, claim_id="claim-nc-flag", judged_text="Acknowledged.", judged_ref="ref-1")
    res_flag = pcv.record_verdict(
        session_id=sess_flag,
        claim_id="claim-nc-flag",
        verdict="PASS",
        reason="Routine coordination ping carrying no assertions to rely on.",
        no_claim=True,
        tracer_mod=tracer,
    )
    assert res_flag["ok"] is True
    assert res_flag["no_claim"] is True
    assert hg.get_state(sess_flag)["last_verdict"]["no_claim"] is True
    assert tracer.exported[0]["spans"][0]["attributes"]["premise_check.no_claim"] is True

    # 2. CLI --no-claim sets premise_check.no_claim=True cleanly
    sess_cli = "sess-nc-cli-flag"
    hg.arm(sess_cli, claim_id="claim-nc-cli", judged_text="Standing by.", judged_ref="ref-2")
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    reason_file = tmp_path / "nc_reason.txt"
    reason_file.write_text("Status acknowledgement only.", encoding="utf-8")
    rc = pcv.main(
        [
            "--claim",
            "claim-nc-cli",
            "--verdict",
            "PASS",
            "--no-claim",
            "--reason-file",
            str(reason_file),
            "--session",
            sess_cli,
        ]
    )
    assert rc == 0
    assert hg.get_state(sess_cli)["last_verdict"]["no_claim"] is True
    assert tracer.exported[1]["spans"][0]["attributes"]["premise_check.no_claim"] is True

    # 3. Prose containing "no claim" or "[no claim]" WITHOUT --no-claim stays no_claim=False
    for idx, prose_reason in enumerate(
        (
            "no claim: acknowledgement with no assertions to rely on",
            "[no claim] routine coordination ping",
            "Judged: claim-nc; no claim -- status acknowledgment only",
        ),
        start=1,
    ):
        sess_prose = f"sess-nc-prose-{idx}"
        cid = f"claim-nc-prose-{idx}"
        hg.arm(sess_prose, claim_id=cid, judged_text="Substantive report.", judged_ref=cid)
        res_prose = pcv.record_verdict(
            session_id=sess_prose,
            claim_id=cid,
            verdict="PASS",
            reason=prose_reason,
            tracer_mod=tracer,
        )
        assert res_prose["ok"] is True
        assert res_prose["no_claim"] is False
        assert "no_claim" not in hg.get_state(sess_prose)["last_verdict"]
        assert tracer.exported[-1]["spans"][0]["attributes"]["premise_check.no_claim"] is False


def test_unarmed_task_record_pass_records_without_gate_storage_and_hashes_judged_file(
    tmp_path: Path,
):
    """Out-of-band task PASS succeeds with or without --judged-file and hashes file content when given."""
    tracer = _configured_tracer()
    session_id = "sess-task-out-of-band"
    task_id = "task_fixture_03"

    res_no_file = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="PASS",
        reason="All stated task criteria follow from the recorded command outputs.",
        tracer_mod=tracer,
    )
    assert res_no_file["ok"] is True
    assert res_no_file["verdict"] == "PASS"
    attrs_no_file = tracer.exported[0]["spans"][0]["attributes"]
    assert attrs_no_file["premise_check.judged_text_sha256"] == ""

    report_text = "Task handback prose: all checks passed cleanly."
    judged_file = tmp_path / "handback.md"
    judged_file.write_text(report_text, encoding="utf-8")

    res_with_file = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="PASS",
        reason="Reviewed full handback file; reasoning supports completion.",
        tracer_mod=tracer,
        judged_file=str(judged_file),
    )
    assert res_with_file["ok"] is True
    attrs_with_file = tracer.exported[1]["spans"][0]["attributes"]
    assert (
        attrs_with_file["premise_check.judged_text_sha256"]
        == hashlib.sha256(report_text.encode()).hexdigest()
    )


@pytest.mark.parametrize(
    "tracer",
    [_configured_tracer(export_ok=False), _configured_tracer(raises=OSError("collector down"))],
    ids=["unacknowledged", "raises"],
)
def test_failed_export_records_no_verdict_and_stays_armed(tracer: _StubTracer):
    """Failed or raising OTel span export halts loudly, writes no last_verdict, and keeps gate armed."""
    session_id = "sess-span-fail-check"
    hg.arm(session_id, claim_id="claim-fail-1", judged_text="Report prose.", judged_ref="ref-1")

    with pytest.raises(RuntimeError, match="span export failed"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-fail-1",
            verdict="PASS",
            reason="Reasoning holds from cited evidence.",
            tracer_mod=tracer,
        )
    assert hg.is_armed(session_id) is True
    assert "last_verdict" not in hg.get_state(session_id)


def test_cli_exits_non_zero_when_export_fails_and_stays_armed(monkeypatch, tmp_path: Path):
    """CLI exits non-zero and leaves gate armed when OTel export is unacknowledged."""
    session_id = "sess-cli-export-fail"
    hg.arm(session_id, claim_id="claim-cli-fail-1", judged_text="Report prose.")
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _configured_tracer(export_ok=False)
    )
    reason_file = tmp_path / "reason.txt"
    reason_file.write_text("Reasoning holds from cited evidence.", encoding="utf-8")

    rc = pcv.main(
        [
            "--claim",
            "claim-cli-fail-1",
            "--verdict",
            "PASS",
            "--reason-file",
            str(reason_file),
            "--session",
            session_id,
        ]
    )
    assert rc != 0
    assert hg.is_armed(session_id) is True


def test_unconfigured_tracing_records_no_verdict():
    """Unconfigured OTel tracing raises RuntimeError and keeps gate armed."""
    session_id = "sess-unconf-check"
    hg.arm(session_id, claim_id="claim-unconf-1", judged_text="Report prose.")
    tracer = _StubTracer(config=None)

    with pytest.raises(RuntimeError, match="tracing is not configured"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-unconf-1",
            verdict="PASS",
            reason="Reasoning holds from cited evidence.",
            tracer_mod=tracer,
        )
    assert tracer.exported == []
    assert hg.is_armed(session_id) is True


def test_verdict_accepts_judged_file_to_verify_and_record_pass(tmp_path: Path):
    """verdict.py / record_verdict accepts --judged-file <path> and hashes it into the span."""
    tracer = _configured_tracer()
    session_id = "sess-judged-file-test"
    claim_id = "report-from-file"

    report_content = (
        "# Specimen Handback Report\n\n"
        "The hotfix was verified on dev with exit code 0 across all targeted tests.\n"
    )
    judged_file = tmp_path / "report.md"
    judged_file.write_text(report_content, encoding="utf-8")

    reason = (
        "The report cites direct execution output confirming exit code 0; the conclusion holds."
    )

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=reason,
        tracer_mod=tracer,
        judged_file=str(judged_file),
    )
    assert res["ok"] is True
    assert res["verdict"] == "PASS"
    assert res["verification_id"].startswith("verdict-")

    reason_file = tmp_path / "reason.txt"
    reason_file.write_text(reason, encoding="utf-8")
    with patch.object(pcv, "_import_claude_code_tracer", return_value=tracer):
        cli_rc = pcv.main(
            [
                "--claim",
                claim_id,
                "--verdict",
                "PASS",
                "--reason-file",
                str(reason_file),
                "--session",
                session_id,
                "--judged-file",
                str(judged_file),
            ]
        )
        assert cli_rc == 0


def test_verdict_resolves_session_from_gate_state_when_unspecified(tmp_path, monkeypatch):
    """AC2 (#3543, #2798): verdict.py resolves session ID across subshell invocations from gate state."""
    gate_dir = tmp_path / "subshell_gate"
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(gate_dir))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("SESSION_ID", raising=False)

    session_id = "subshell-session-abc"
    claim_id = "claim-subshell-123"

    hg.arm(
        session_id=session_id,
        claim_id=claim_id,
        judged_text="Result text",
        judged_ref=claim_id,
    )
    assert hg.is_armed(session_id) is True

    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    # When --session is not passed, resolve_session_id should find session_id from state
    resolved = pcv.resolve_session_id("", claim_id)
    assert resolved == session_id

    # And main() should resolve the session and record the verdict
    tracer = _configured_tracer()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    reason_file = tmp_path / "reason.txt"
    reason_file.write_text(
        "The report omits evidence for its main conclusion; revise to show supporting checks.",
        encoding="utf-8",
    )

    code = pcv.main(
        [
            "--claim",
            claim_id,
            "--verdict",
            "REVISE",
            "--reason-file",
            str(reason_file),
        ]
    )
    assert code == 0
    assert hg.is_armed(session_id) is False
    assert hg.get_state(session_id)["last_verdict"]["verdict"] == "REVISE"


def test_verdict_reports_clear_diagnostic_when_no_session_or_state(tmp_path, monkeypatch, capsys):
    """AC2 (#3543, #2798): verdict.py reports a clear diagnostic when neither --session nor session state is available."""
    gate_dir = tmp_path / "empty_gate"
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(gate_dir))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)

    code = pcv.main(
        [
            "--claim",
            "claim-no-state",
            "--verdict",
            "REVISE",
            "--reason",
            "missing evidence for the reported claim",
        ]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "no session id" in err
    assert "no session state available" in err


def test_subagent_verdict_span_uses_root_phoenix_session_id_and_subagent_active_trace(monkeypatch):
    """When record_verdict is called inside a subagent session, _export_tool_span loads the
    subagent's own state file (for current_trace) and exports the span under the root
    phoenix_session_id with agent_id and parent_session_id."""
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    tracer = _configured_tracer()
    sub_session = "subagent-verdict-sess"
    root_session = "root-verdict-sess"
    sub_trace_id = "a" * 32
    sub_root_span_id = "b" * 16

    state_map = {
        sub_session: {
            "session_id": sub_session,
            "phoenix_session_id": root_session,
            "parent_session_id": root_session,
            "current_trace": {
                "trace_id": sub_trace_id,
                "root_span_id": sub_root_span_id,
            },
        }
    }
    tracer._load_state = lambda sid: state_map.get(sid, {})
    tracer._resolve_agent_and_parent_ids = lambda state, data=None, session_key="session_id": (
        state.get("phoenix_session_id") or state.get("session_id"),
        state.get("session_id")
        if state.get("phoenix_session_id") != state.get("session_id")
        else "",
        state.get("parent_session_id"),
    )

    exported_calls: list[dict[str, Any]] = []

    def capture_export(*, config, session_id, username, span_records, **kw):
        exported_calls.append(
            {
                "session_id": session_id,
                "spans": span_records,
                "kwargs": kw,
            }
        )
        return True

    tracer._build_and_export_spans = capture_export

    claim_id = "claim-subagent-1"
    hg.arm(
        session_id=sub_session,
        claim_id=claim_id,
        judged_text="report",
        judged_ref=claim_id,
    )
    reason = "The report's second inference leaves out a necessary condition; revise to address it."

    res = pcv.record_verdict(
        session_id=sub_session,
        claim_id=claim_id,
        verdict="REVISE",
        reason=reason,
        tracer_mod=tracer,
    )
    assert res["ok"] is True
    assert len(exported_calls) == 1
    call = exported_calls[0]
    assert call["session_id"] == root_session
    assert call["kwargs"].get("agent_id") == sub_session
    assert call["kwargs"].get("parent_session_id") == root_session
    span = call["spans"][0]
    assert span["trace_id_hex"] == sub_trace_id
    assert span["parent_span_id_hex"] == sub_root_span_id


def test_judged_file_rejects_disarmed_foreign_and_mismatched_claims_while_allowing_task_revise_pass(
    tmp_path: Path,
):
    """--judged-file blocks replay of disarmed, foreign-slot, mismatched, or unarmed gate claims, while task REVISE->PASS succeeds."""
    tracer = _configured_tracer()
    session_id = "sess-judged-guards"
    valid_report = "Direct observation (`x=1`) establishes that the target invariant holds.\n"
    other_file = tmp_path / "other.md"
    other_file.write_text(valid_report.replace("x=1", "x=2"), encoding="utf-8")
    same_file = tmp_path / "same.md"
    same_file.write_text(valid_report, encoding="utf-8")

    def _pass_reason(cid: str) -> str:
        return f"PASS {cid}: the observation supports the stated answer directly."

    # 1. Already-disarmed gate claim cannot be masked or re-recorded via --judged-file
    hg.arm(session_id, claim_id="claim-11112222", judged_text=valid_report)
    pcv.record_verdict(
        session_id=session_id,
        claim_id="claim-11112222",
        verdict="REVISE",
        reason="Missing supporting check for the main conclusion; revise.",
        tracer_mod=tracer,
    )
    with pytest.raises(ValueError, match="already disarmed|not armed"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-11112222",
            verdict="PASS",
            reason=_pass_reason("claim-11112222"),
            tracer_mod=tracer,
            judged_file=str(same_file),
        )

    # 2. Foreign-slot claim cannot be consumed via --judged-file from another agent or omitted --agent
    hg.arm(
        session_id,
        claim_id="claim-33334444",
        judged_text=valid_report,
        agent_id="sub-b",
    )
    with pytest.raises(ValueError, match="armed for.*sub-b|not.*sub-a|foreign|other agent"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-33334444",
            verdict="PASS",
            reason=_pass_reason("claim-33334444"),
            tracer_mod=tracer,
            judged_file=str(same_file),
            agent_id="sub-a",
        )
    assert hg.is_armed(session_id, agent_id="sub-b") is True

    # 3. Substituting a different file SHA against stored .judged.txt in the owning slot is refused
    with pytest.raises(ValueError, match="mismatch|does not match"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-33334444",
            verdict="PASS",
            reason=_pass_reason("claim-33334444"),
            tracer_mod=tracer,
            judged_file=str(other_file),
            agent_id="sub-b",
        )

    # 4. Unarmed gate-minted claim-<8hex> ID cannot bypass arming via --judged-file
    with pytest.raises(ValueError, match="currently armed|not armed|unknown"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-deadbeef",
            verdict="PASS",
            reason=_pass_reason("claim-deadbeef"),
            tracer_mod=tracer,
            judged_file=str(same_file),
        )

    # 5. Out-of-band task_id and report-* labels MUST still allow REVISE -> PASS via --judged-file
    rev_task = pcv.record_verdict(
        session_id=session_id,
        claim_id="task_a1b2c3d4",
        verdict="REVISE",
        reason="Expand evidence for the task completion claim.",
        tracer_mod=tracer,
        judged_file=str(other_file),
    )
    assert rev_task["ok"] is True
    pass_task = pcv.record_verdict(
        session_id=session_id,
        claim_id="task_a1b2c3d4",
        verdict="PASS",
        reason=_pass_reason("task_a1b2c3d4"),
        tracer_mod=tracer,
        judged_file=str(same_file),
    )
    assert pass_task["ok"] is True

    rev_rep = pcv.record_verdict(
        session_id=session_id,
        claim_id="report-out-of-band",
        verdict="REVISE",
        reason="Expand evidence for the out-of-band report.",
        tracer_mod=tracer,
        judged_file=str(other_file),
    )
    assert rev_rep["ok"] is True
    pass_rep = pcv.record_verdict(
        session_id=session_id,
        claim_id="report-out-of-band",
        verdict="PASS",
        reason=_pass_reason("report-out-of-band"),
        tracer_mod=tracer,
        judged_file=str(same_file),
    )
    assert pass_rep["ok"] is True


def test_cli_agent_flag_binds_slot_and_rejects_mismatch(tmp_path: Path, monkeypatch, capsys):
    """CLI --agent/--recipient disarms strictly the targeted slot and refuses foreign --judged-file."""
    tracer = _configured_tracer()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    session_id = "sess-cli-agent"
    valid_report = "Direct observation (`v=1`) establishes the claim."
    hg.arm(
        session_id,
        claim_id="claim-a1b2c3d4",
        judged_text=valid_report,
        agent_id="sub-x",
    )
    reason_file = tmp_path / "reason.txt"
    reason_file.write_text(
        "PASS claim-a1b2c3d4: the cited observation supports the conclusion directly.\n",
        encoding="utf-8",
    )
    wrong_file = tmp_path / "wrong.md"
    wrong_file.write_text(valid_report.replace("v=1", "v=9"), encoding="utf-8")

    # Wrong --judged-file exits non-zero and leaves slot armed
    rc_bad = pcv.main(
        [
            "--claim",
            "claim-a1b2c3d4",
            "--verdict",
            "PASS",
            "--reason-file",
            str(reason_file),
            "--session",
            session_id,
            "--agent",
            "sub-x",
            "--judged-file",
            str(wrong_file),
        ]
    )
    assert rc_bad == 1
    assert "mismatch" in capsys.readouterr().err.lower()
    assert hg.is_armed(session_id, agent_id="sub-x") is True

    # Correct --recipient (--agent alias) succeeds and disarms sub-x slot
    rc_ok = pcv.main(
        [
            "--claim",
            "claim-a1b2c3d4",
            "--verdict",
            "PASS",
            "--reason-file",
            str(reason_file),
            "--session",
            session_id,
            "--recipient",
            "sub-x",
        ]
    )
    assert rc_ok == 0
    assert hg.is_armed(session_id, agent_id="sub-x") is False


def test_subagent_agent_flag_overrides_root_tracer_state_attribution(monkeypatch):
    """--agent attribution stamps recipient_agent_id and export agent_id even when root tracer state exists."""
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    tracer = _configured_tracer()
    root_session = "root-attr-sess"
    sub_agent = "sub-x"

    # Simulate claude_code_tracer where _load_state("sub-x") is empty and root state populates
    # resolved_agent_id = root_session (claude_code_tracer.py:628).
    tracer._load_state = lambda sid: (
        {"session_id": root_session, "phoenix_session_id": root_session}
        if sid == root_session
        else {}
    )
    tracer._resolve_agent_and_parent_ids = lambda state, data=None, session_key="session_id": (
        state.get("phoenix_session_id") or state.get("session_id"),
        state.get("session_id"),
        state.get("parent_session_id"),
    )

    exported_calls: list[dict[str, Any]] = []

    def capture_export(*, config, session_id, username, span_records, **kw):
        exported_calls.append({"session_id": session_id, "spans": span_records, "kwargs": kw})
        return True

    tracer._build_and_export_spans = capture_export

    claim_id = "claim-sub-attr"
    hg.arm(
        session_id=root_session,
        claim_id=claim_id,
        judged_text="report",
        judged_ref=claim_id,
        agent_id=sub_agent,
    )
    reason = "The report does not justify the claimed condition; send back for revision."
    res = pcv.record_verdict(
        session_id=root_session,
        claim_id=claim_id,
        verdict="REVISE",
        reason=reason,
        tracer_mod=tracer,
        agent_id=sub_agent,
    )
    assert res["ok"] is True
    assert len(exported_calls) == 1
    call = exported_calls[0]
    assert call["session_id"] == root_session
    assert call["kwargs"].get("agent_id") == sub_agent
    assert call["kwargs"].get("parent_session_id") == root_session
    assert call["spans"][0]["attributes"].get("premise_check.recipient_agent_id") == sub_agent


def test_resolve_session_id_raises_on_corrupt_slot_json(monkeypatch):
    """resolve_session_id fails loudly instead of silently skipping corrupt slot state JSON."""
    for var in (
        "AOPS_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "SESSION_ID",
        "ANTIGRAVITY_SESSION_ID",
        "GEMINI_SESSION_ID",
        "CLAUDE_ENV_FILE",
    ):
        monkeypatch.delenv(var, raising=False)
    corrupt_file = hg._state_dir() / "sess-corrupt-resolve.json"
    corrupt_file.write_text("{corrupt json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        pcv.resolve_session_id("", "claim-any")
