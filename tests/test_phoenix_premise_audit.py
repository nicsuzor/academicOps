"""Tests for phoenix_premise_audit.py: census, dossier, log, and tally."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "plugins/ida/skills/session-trace/scripts"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location(
    "phoenix_premise_audit", SCRIPTS / "phoenix_premise_audit.py"
)
assert _spec is not None and _spec.loader is not None
ppa = importlib.util.module_from_spec(_spec)
sys.modules["phoenix_premise_audit"] = ppa
_spec.loader.exec_module(ppa)


def make_span(
    name: str,
    span_id: str,
    session_id: str,
    start_time: str = "2026-11-05T12:00:00Z",
    span_kind: str = "TOOL",
    surface: str | None = None,
    host: str = "host-1",
    cwd: str = "/workspace",
    agent: str = "agent-1",
    output_val: str = "",
    premise_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "session.id": session_id,
        "host.name": host,
        "cwd": cwd,
        "agent.name": agent,
    }
    if surface:
        attrs["aops.surface"] = surface
    if output_val:
        attrs["output.value"] = output_val
    if premise_check is not None:
        attrs["premise_check"] = premise_check

    return {
        "name": name,
        "span_kind": span_kind,
        "context": {"span_id": span_id, "trace_id": "a" * 32},
        "start_time": start_time,
        "attributes": attrs,
    }


def make_verdict_span(
    span_id: str,
    session_id: str,
    verdict: str,
    surface: str = "claude-code",
    claim_id: str = "claim-101",
    ask_ids: list[str] | None = None,
    defect_tags: list[str] | None = None,
    waived_items: list[str] | None = None,
    weakest_basis: str = "primary",
    reason_text: str = "Valid: (1) holds -- ok\nSupported: (1) ok",
    cwd: str = "/home/user/project",
) -> dict[str, Any]:
    pc = {
        "verdict": verdict,
        "verification_id": f"verif-{span_id}",
        "claim_id": claim_id,
        "ask_ids": ask_ids or ["ask-1"],
        "defect_tags": defect_tags or [],
        "waived_items": waived_items or [],
        "weakest_basis": weakest_basis,
        "has_block": True,
        "no_claim": False,
        "judged_text_sha256": "abcdef123456",
        "reason_text": reason_text,
    }
    return make_span(
        name="premise_check_verdict",
        span_id=span_id,
        session_id=session_id,
        surface=surface,
        cwd=cwd,
        premise_check=pc,
    )


# --- Tests -------------------------------------------------------------------


def test_harness_classification():
    # Explicit aops.surface attribute
    s1 = make_span("tool", "1", "s1", surface="claude-code")
    assert ppa.classify_harness(s1) == "claude-code"

    s2 = make_span("tool", "2", "s2", surface="agy")
    assert ppa.classify_harness(s2) == "agy"

    s3 = make_span("tool", "3", "s3", surface="claude")
    assert ppa.classify_harness(s3) == "claude-code"

    # Fallback to cwd/host heuristics when surface is missing
    s4 = make_span("tool", "4", "s4", cwd="/home/user/.gemini/antigravity-cli/worktrees/wt1")
    assert ppa.classify_harness(s4) == "agy"

    s5 = make_span("tool", "5", "s5", cwd="/home/user/project")
    assert ppa.classify_harness(s5) == "claude-code"


def test_census_aggregation_across_harnesses():
    spans = [
        # claude-code: 2 sessions
        # sess_c1: 1 PASS (with waived format), 1 REVISE (#conflict)
        make_verdict_span(
            "c1", "sess_c1", "PASS", surface="claude-code", waived_items=["numbering"]
        ),
        make_verdict_span(
            "c2", "sess_c1", "REVISE", surface="claude-code", defect_tags=["#conflict"]
        ),
        # sess_c2: 1 PASS
        make_verdict_span("c3", "sess_c2", "PASS", surface="claude-code"),
        # hearsay check & refusal for claude-code
        make_span("hearsay_check", "c4", "sess_c1", surface="claude-code"),
        make_span(
            "Bash",
            "c5",
            "sess_c1",
            surface="claude-code",
            output_val="premise_check_verdict: refused missing ask",
        ),
        # agy: 1 session
        # sess_a1: 1 PASS, 1 REVISE (format-only), 1 FAIL (#insufficient-for-stakes)
        make_verdict_span("a1", "sess_a1", "PASS", surface="agy"),
        make_verdict_span("a2", "sess_a1", "REVISE", surface="agy"),  # format-only (no tags)
        make_verdict_span(
            "a3", "sess_a1", "FAIL", surface="agy", defect_tags=["#insufficient-for-stakes"]
        ),
        make_span("premise_check_override", "a4", "sess_a1", surface="agy"),
        # Excluded session
        make_verdict_span("e1", "exclude_me_sess", "PASS", surface="claude-code"),
    ]

    stats = ppa.aggregate_census(spans, exclude_sessions={"exclude_me"})

    c = stats["claude-code"]
    assert c.total_verdicts == 3
    assert len(c.sessions) == 2
    assert c.pass_count == 2
    assert c.waived_format_items == 1
    assert c.revise_count == 1
    assert c.revise_defect_tagged == 1
    assert c.armed_hearsay_spans == 1
    assert c.refusals == 1
    assert c.defect_tags["#conflict"] == 1

    a = stats["agy"]
    assert a.total_verdicts == 3
    assert len(a.sessions) == 1
    assert a.pass_count == 1
    assert a.revise_count == 1
    assert a.revise_format_only == 1
    assert a.fail_count == 1
    assert a.fail_defect_tagged == 1
    assert a.overrides == 1
    assert a.defect_tags["#insufficient-for-stakes"] == 1

    comb = stats["combined"]
    assert comb.total_verdicts == 6
    assert len(comb.sessions) == 3
    assert comb.pass_count == 3
    assert comb.revise_count == 2
    assert comb.fail_count == 1

    md = ppa.render_census_markdown(stats)
    assert "| Metric | `claude-code` | `agy` | Combined / Comparative |" in md
    assert "**Total Recorded Verdict Spans**" in md
    assert "`#conflict`" in md
    assert "`#insufficient-for-stakes`" in md


def test_extract_dossier_records_and_annotations():
    spans = [
        make_verdict_span(
            "s1", "sess_1", "REVISE", surface="claude-code", defect_tags=["#undercut"]
        ),
        make_verdict_span("s2", "sess_2", "PASS", surface="agy"),
    ]

    records = ppa.extract_dossier_records(spans, harness_filter="all", verdict_filter="all")
    assert len(records) == 2

    # Filter by tagged only
    tagged_records = ppa.extract_dossier_records(spans, tagged_only=True)
    assert len(tagged_records) == 1
    assert tagged_records[0].span_id == "s1"
    assert tagged_records[0].defect_tags == ["#undercut"]

    # Filter by harness
    agy_records = ppa.extract_dossier_records(spans, harness_filter="agy")
    assert len(agy_records) == 1
    assert agy_records[0].span_id == "s2"

    # Markdown format
    md = ppa.render_dossier_markdown(records)
    assert "# Premise-Check Candidate Review Dossier (2 records)" in md
    assert "`#undercut`" in md

    # Annotations template format
    tmpl = ppa.render_dossier_annotations_template(records)
    assert tmpl["total_records"] == 2
    eval0 = tmpl["evaluations"][0]
    assert eval0["span_id"] == "s1"
    assert eval0["evaluation"]["defect_classification"] is None
    assert eval0["evaluation"]["is_substantive"] is None
    assert eval0["evaluation"]["is_synthetic_test"] is None


def test_render_session_log():
    spans = [
        make_verdict_span(
            "v1",
            "sess_log_1",
            "PASS",
            claim_id="claim-1",
            ask_ids=["ask-1"],
            weakest_basis="primary",
            reason_text="Valid: (1) holds\nSupported: (1) ok",
        ),
        make_verdict_span(
            "v2",
            "sess_log_1",
            "REVISE",
            claim_id="claim-2",
            defect_tags=["#missing"],
            reason_text="Valid: (1) fails #missing",
        ),
        make_span(
            "Bash",
            "r1",
            "sess_log_1",
            output_val="premise_check_verdict: refused missing ask\n- ask-2 not answered",
        ),
    ]

    log_md = ppa.render_session_log("sess_log_1", spans)
    assert "# Premise-check log: session `sess_log_1`" in log_md
    assert "- **Recorded verdicts:** 2 (PASS 1, REVISE 1)" in log_md
    assert "- **Refused or unrecorded attempts:** 1" in log_md
    assert "### 1. PASS · `verif-v1` on `claim-1`" in log_md
    assert "### 2. REVISE · `verif-v2` on `claim-2`" in log_md
    assert "## Refused or unrecorded attempts" in log_md
    assert "premise_check_verdict: refused missing ask" in log_md


def test_tally_annotations_confusion_matrix():
    payload = {
        "version": "1.0",
        "evaluations": [
            # Claude-code:
            # 1 substantive catch (Bucket 1)
            {
                "span_id": "c_rev_1",
                "harness": "claude-code",
                "verdict": "REVISE",
                "is_synthetic_test": False,
                "evaluation": {"defect_classification": "substantive", "is_substantive": True},
            },
            # 1 structural bar catch (Bucket 2)
            {
                "span_id": "c_rev_2",
                "harness": "claude-code",
                "verdict": "REVISE",
                "is_synthetic_test": False,
                "evaluation": {"defect_classification": "structural_bar"},
            },
            # 1 disguised plumbing/syntax (Bucket 3)
            {
                "span_id": "c_rev_3",
                "harness": "claude-code",
                "verdict": "REVISE",
                "is_synthetic_test": False,
                "evaluation": {"defect_classification": "format_plumbing"},
            },
            # 1 synthetic test (excluded from operational metrics)
            {
                "span_id": "c_synth",
                "harness": "claude-code",
                "verdict": "REVISE",
                "is_synthetic_test": True,
                "evaluation": {"defect_classification": "synthetic_test"},
            },
            # 2 PASS verdicts: 1 rigorous, 1 rubber stamp
            {
                "span_id": "c_pass_1",
                "harness": "claude-code",
                "verdict": "PASS",
                "is_synthetic_test": False,
                "evaluation": {"is_rubber_stamp": False},
            },
            {
                "span_id": "c_pass_2",
                "harness": "claude-code",
                "verdict": "PASS",
                "is_synthetic_test": False,
                "evaluation": {"is_rubber_stamp": True},
            },
            # Agy:
            # 1 substantive catch (Bucket 1)
            {
                "span_id": "a_rev_1",
                "harness": "agy",
                "verdict": "REVISE",
                "is_synthetic_test": False,
                "evaluation": {"defect_classification": "substantive"},
            },
            # 2 format/plumbing slips (Bucket 3)
            {
                "span_id": "a_rev_2",
                "harness": "agy",
                "verdict": "REVISE",
                "is_synthetic_test": False,
                "evaluation": {"defect_classification": "format_plumbing"},
            },
            {
                "span_id": "a_rev_3",
                "harness": "agy",
                "verdict": "REVISE",
                "is_synthetic_test": False,
                "evaluation": {"defect_classification": "format_plumbing"},
            },
            # 1 PASS: rigorous
            {
                "span_id": "a_pass_1",
                "harness": "agy",
                "verdict": "PASS",
                "is_synthetic_test": False,
                "evaluation": {"is_rubber_stamp": False},
            },
        ],
    }

    metrics = ppa.tally_annotations(payload)

    c = metrics["claude-code"]
    assert c.total_evaluations == 6
    assert c.synthetic_test_evaluations == 1
    assert c.operational_evaluations == 5
    assert c.total_rejections == 3
    assert c.bucket_1_substantive == 1
    assert c.bucket_2_structural_bar == 1
    assert c.bucket_3_format_plumbing == 1
    assert c.total_passes == 2
    assert c.rigorous_passes == 1
    assert c.rubber_stamp_passes == 1

    a = metrics["agy"]
    assert a.total_evaluations == 4
    assert a.operational_evaluations == 4
    assert a.total_rejections == 3
    assert a.bucket_1_substantive == 1
    assert a.bucket_2_structural_bar == 0
    assert a.bucket_3_format_plumbing == 2
    assert a.total_passes == 1
    assert a.rigorous_passes == 1
    assert a.rubber_stamp_passes == 0

    md = ppa.render_tally_markdown(metrics)
    assert "## Defect-Tagged Rejections Classification Audit" in md
    assert "Bucket 1: Substantive Logical, Epistemic, & Rule Catches" in md
    assert "## Substantive PASS Rigor vs Rubber-Stamp False Negatives" in md


def test_cli_census_and_dossier_from_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    spans = [
        make_verdict_span("v1", "s1", "PASS", surface="claude-code"),
        make_verdict_span("v2", "s1", "REVISE", surface="claude-code", defect_tags=["#conflict"]),
        make_verdict_span("v3", "s2", "PASS", surface="agy"),
    ]
    spans_file = tmp_path / "test_spans.json"
    spans_file.write_text(json.dumps(spans))

    # Test census CLI with JSON output
    ret = ppa.main(["census", "--from-file", str(spans_file), "--json"])
    assert ret == 0
    out, _ = capsys.readouterr()
    census_data = json.loads(out)
    assert census_data["combined"]["total_verdicts"] == 3
    assert census_data["claude-code"]["total_verdicts"] == 2
    assert census_data["agy"]["total_verdicts"] == 1

    # Test dossier CLI outputting annotations template to file
    ann_file = tmp_path / "annotations.json"
    ret = ppa.main(
        [
            "dossier",
            "--from-file",
            str(spans_file),
            "--format",
            "annotations",
            "--out",
            str(ann_file),
        ]
    )
    assert ret == 0
    assert ann_file.is_file()
    ann_data = json.loads(ann_file.read_text())
    assert ann_data["total_records"] == 3

    # Test tally CLI on annotated template
    # Fill in an evaluation
    ann_data["evaluations"][1]["evaluation"]["defect_classification"] = "substantive"
    ann_file.write_text(json.dumps(ann_data))

    capsys.readouterr()  # Clear previous output
    ret = ppa.main(["tally", "--annotations", str(ann_file), "--json"])
    assert ret == 0
    out, _ = capsys.readouterr()
    tally_data = json.loads(out)
    assert tally_data["claude-code"]["bucket_1_substantive"] == 1
