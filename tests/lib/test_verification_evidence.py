#!/usr/bin/env python3
"""Unit tests for the completion-claim evidence contract (epic aops-262def9f WI2).

Deterministic contract checks only — the gate wiring lives in
tests/hooks/test_completion_claim_evidence.py and the tool boundary in
tests/polecat/test_pkb_bridge.py.
"""

import sys
from pathlib import Path

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

import pytest  # noqa: E402
from lib.verification_evidence import (  # noqa: E402
    detect_completion_claim,
    extract_evidence,
    parse_evidence_trailers,
    parse_verifier_verdict,
    validate_completion_evidence,
)

GOOD_EVIDENCE = {
    "verified_by": "marsha (subagent 9f3e3217)",
    "verified_sha": "51ed2fff",
    "findings": "no defects found via pytest tests/hooks + read of definitions.py:294-398",
}


# --- Trailer parsing ---


def test_parse_trailers_full_block():
    text = (
        "Shipped the thing.\n\n"
        "Verified-By: rbg\n"
        "Verified-SHA: 51ed2fff1234\n"
        "Findings: sentinel regex too narrow at custom_conditions.py:15\n"
    )
    assert parse_evidence_trailers(text) == {
        "verified_by": "rbg",
        "verified_sha": "51ed2fff1234",
        "findings": "sentinel regex too narrow at custom_conditions.py:15",
    }


def test_parse_trailers_folded_findings():
    text = (
        "Findings: no defects found via pytest tests/hooks\n  + manual read of engine.py:410-486\n"
    )
    trailers = parse_evidence_trailers(text)
    assert trailers["findings"] == (
        "no defects found via pytest tests/hooks + manual read of engine.py:410-486"
    )


def test_parse_trailers_absent():
    assert parse_evidence_trailers("just a summary, nothing attached") == {}
    assert parse_evidence_trailers(None) == {}


def test_extract_evidence_explicit_fields_win_over_trailers():
    tool_input = {
        "summary": "Verified-By: someone-else\nVerified-SHA: deadbeef\nFindings: x.py:1 off-by-one",
        "verified_by": "marsha",
    }
    evidence = extract_evidence(tool_input)
    assert evidence["verified_by"] == "marsha"
    assert evidence["verified_sha"] == "deadbeef"


# --- Structural validation ---


def test_conformant_evidence_has_no_problems():
    assert validate_completion_evidence(GOOD_EVIDENCE) == []


def test_findings_with_file_line_accepted():
    evidence = dict(GOOD_EVIDENCE, findings="off-by-one in engine.py:593; fixed in review")
    assert validate_completion_evidence(evidence) == []


@pytest.mark.parametrize(
    "findings",
    [
        "clean",
        "verified",
        "LGTM",
        "looks good, all checks green",
        "no issues",  # null result WITHOUT a named method
    ],
)
def test_attestation_only_findings_rejected(findings):
    evidence = dict(GOOD_EVIDENCE, findings=findings)
    problems = validate_completion_evidence(evidence)
    assert any("attestation-only" in p for p in problems), problems


@pytest.mark.parametrize("identity", ["self", "me", "producer", "SAME", "worker"])
def test_self_identities_rejected(identity):
    evidence = dict(GOOD_EVIDENCE, verified_by=identity)
    problems = validate_completion_evidence(evidence)
    assert any("independent reviewer" in p for p in problems), problems


def test_reviewer_equal_to_producer_rejected():
    evidence = dict(GOOD_EVIDENCE, verified_by="botnicbot")
    problems = validate_completion_evidence(evidence, producer="botnicbot")
    assert any("producer" in p for p in problems), problems


@pytest.mark.parametrize("sha", ["latest", "the head", "abc123", "g1234567"])
def test_non_sha_artifact_identifiers_rejected(sha):
    evidence = dict(GOOD_EVIDENCE, verified_sha=sha)
    problems = validate_completion_evidence(evidence)
    assert any("Verified-SHA" in p for p in problems), problems


def test_missing_fields_each_named():
    problems = validate_completion_evidence({})
    joined = "\n".join(problems)
    assert "Verified-By" in joined
    assert "Verified-SHA" in joined
    assert "Findings" in joined


# --- Completion-claim detection ---


@pytest.mark.parametrize(
    ("tool_name", "tool_input", "expected"),
    [
        ("release_task", {"id": "t1", "status": "merge_ready"}, ("t1", "merge_ready")),
        ("mcp__pkb__release_task", {"id": "t1", "status": "done"}, ("t1", "done")),
        ("complete_task", {"id": "t2"}, ("t2", "done")),
        (
            "mcp__plugin_aops-core_pkb__update_task",
            {"id": "t3", "updates": {"status": "done"}},
            ("t3", "done"),
        ),
        ("update_task", {"id": "t3", "status": "merge_ready"}, ("t3", "merge_ready")),
        # Non-claims:
        ("release_task", {"id": "t1", "status": "blocked"}, None),
        ("update_task", {"id": "t3", "status": "in_progress"}, None),
        ("claim_task", {"id": "t4"}, None),
        ("get_task", {"id": "t5"}, None),
    ],
)
def test_detect_completion_claim(tool_name, tool_input, expected):
    assert detect_completion_claim(tool_name, tool_input) == expected


# --- Verifier verdict parsing (WI3) ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("**Verdict:** PASS\n\nran the suite", "PASS"),
        ("Verdict: fail — broke at x.py:3", "FAIL"),
        ("verdict - REVISE", "REVISE"),
        ("Everything came back green, nothing conclusive to report.", None),
        ("I believe the tests pass now.", None),  # lowercase prose is not a verdict
        ("Final check: PASS", "PASS"),  # bare uppercase token counts
        ("", None),
        (None, None),
    ],
)
def test_parse_verifier_verdict(text, expected):
    assert parse_verifier_verdict(text) == expected
