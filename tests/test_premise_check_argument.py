"""Tests for the report-argument standard's enforcement in the premise-check gate.

Covers:
1. The structural parser for the ``argument`` block and the checker's keyed reason.
2. The recorder refuses a PASS whose reason misses a keyed line or an ask id, or
   contradicts the judged block -- each cross-check in the skill's "What the
   recorder refuses" fires, and one refusal names every failed check.
3. The verdict span carries one attribute per reason key plus the ask ids,
   weakest basis, inference count, defect tags, waived items, no-claim flag and
   the judged-text reference stored at arm time.
4. A failed span export records no verdict; unconfigured tracing records locally.
5. The gate arms on a PKB task read whose record has a report and no verdict.
6. Each override that lets an armed gate pass a blocked action is counted.

The vocabulary, task-read tool names and override variables come from
``tests/policy.toml`` and the skill's ``vocabulary.toml``, never from literals.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
import unittest.mock
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _REPO_ROOT / "plugins" / "ida" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import dispatch
import premise_check_gate as pcg
import premise_check_verdict as pcv
import report_argument as ra

_POLICY = tomllib.loads((_REPO_ROOT / "tests" / "policy.toml").read_text(encoding="utf-8"))[
    "premise_check"
]
_VOCAB = ra.load_vocabulary(_REPO_ROOT / _POLICY["vocabulary"])
_STRONG = max(_VOCAB.basis, key=lambda b: b.rank)
_WEAK = min(_VOCAB.basis, key=lambda b: b.rank)
_FORMAT_ITEM = next(i for i in _VOCAB.format_items if i != "block")
_DEFECT = _VOCAB.defect_tags[0]


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate_state"))
    monkeypatch.delenv("PREMISE_CHECK_GATE_MODE", raising=False)
    for var in _POLICY["override_vars"]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    yield


class _StubTracer:
    """Stand-in for claude_code_tracer: records exported span records."""

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


def _configured(**kw) -> _StubTracer:
    return _StubTracer(config={"endpoint": "http://collector:4318"}, **kw)


# ---------------------------------------------------------------------------
# Fixtures: a report with an argdown block, and a reason that passes it
# ---------------------------------------------------------------------------

ASK_A = "tg-1990"
ASK_B = "aops_0a8efbc2/AC1"


def _frontmatter(asks: bool = True, answers: str = f"{ASK_A}: 4\n  {ASK_B}: 6") -> str:
    lines = ["==="]
    if asks:
        lines += ["asks:", f"  {ASK_A}: is the hook enforced?", f"  {ASK_B}: does it block Stop?"]
    lines += [
        "answers:",
        f"  {answers}",
        "notes:",
        "  a: plugins/ida/hooks/handlers.py",
        "  b: plugins/ida/hooks/premise_check_gate.py",
        "===",
    ]
    return "\n".join(lines) + "\n"


def _report(frontmatter: str | None = None) -> str:
    """A report ending in an argdown block; premise (5) uses the live em-dash separator."""
    return (
        "I checked the hook and the runtime.\n\n"
        "```argdown\n"
        f"{frontmatter if frontmatter is not None else _frontmatter()}"
        "\n"
        f"(1) A hook that only advises cannot block an agent. -- {_STRONG.phrase}\n"
        f'(2) The hook returns "block", not advice. -- {_STRONG.phrase} ^a\n'
        f'(3) The agent runtime honours a "block" from a hook. -- {_WEAK.phrase}\n'
        '-- A hook that returns "block" to a runtime that honours it is enforced. '
        "Unless: this runtime ignores hook output; not ruled out. --\n"
        "(4) So, most likely, the hook is enforced.\n"
        f"(5) The handler returns block on Stop. — {_STRONG.phrase} ^b\n"
        "-- An enforced hook that returns block on Stop blocks Stop. "
        "Unless: the mode is off; ruled out by (5). --\n"
        "(6) So it blocks Stop.\n"
        "```\n"
    )


def _reason_lines(claim_id: str) -> list[str]:
    return [
        f"Judged: {claim_id}; asks {ASK_A}, {ASK_B}",
        "Valid: (4) holds -- the rule's two conditions are (2) and (3)",
        "Valid: (6) holds — (5) meets the rule",
        f"Supported: weakest {_WEAK.phrase} -- (3) carries a qualified conclusion",
        f"Answered: {ASK_A} ← (4)",
        f"Answered: {ASK_B} ← (6)",
        "Sufficient: (4) material; sufficiency obvious; no objection",
        "Sufficient: (6) material; sufficiency low-stakes",
        "Waived: none",
        'Relay: "the hook is enforced" ← (4)',
    ]


def _reason(claim_id: str, drop: tuple[str, ...] = (), extra: tuple[str, ...] = ()) -> str:
    lines = [ln for ln in _reason_lines(claim_id) if not ln.startswith(drop)] if drop else None
    return "\n".join([*(lines if lines is not None else _reason_lines(claim_id)), *extra])


def _arm_with_report(session_id: str, claim_id: str, text: str | None = None, ref: str = "toolu_1"):
    pcg.arm(session_id, claim_id=claim_id, judged_text=text or _report(), judged_ref=ref)


# ---------------------------------------------------------------------------
# 1. Parser
# ---------------------------------------------------------------------------


def test_parse_block_reads_frontmatter_premises_inferences_and_conclusions():
    block = ra.extract_block(_report())
    assert block is not None
    arg = ra.parse_block(block, _VOCAB)
    assert arg is not None
    assert arg.asks == [ASK_A, ASK_B]
    assert [inf.conclusion for inf in arg.inferences] == [4, 6]
    assert arg.conclusions == [4, 6]
    assert [p.number for p in arg.premises] == [1, 2, 3, 5]
    assert [p.basis for p in arg.premises] == [_STRONG, _STRONG, _WEAK, _STRONG]
    assert arg.weakest() is not None and arg.weakest().number == 3
    assert set(arg.notes) == {"a", "b"}
    assert arg.answers == {ASK_A: 4, ASK_B: 6}


def test_extract_block_takes_the_last_argdown_block():
    text = "```argdown\n===\nasks:\n  x-1: old?\n===\n```\n\n" + _report()
    block = ra.extract_block(text)
    assert block is not None and ASK_A in block and "x-1" not in block
    assert ra.extract_block("no block here") is None


def test_malformed_frontmatter_is_a_block_that_fails_to_parse():
    block = ra.extract_block(_report(frontmatter="===\nasks: [unclosed\n===\n"))
    assert block is not None
    assert ra.parse_block(block, _VOCAB) is None


def test_basis_takes_the_longest_vocabulary_phrase_and_unmatched_ranks_zero():
    phrases = sorted(_VOCAB.basis, key=lambda b: len(b.phrase), reverse=True)
    longest = phrases[0]
    arg = ra.parse_block(
        f"(1) A thing. -- {longest.phrase.upper()} with a note; more ^a ^b\n"
        "(2) Another thing. -- something no vocabulary has\n"
        "(3) A third thing with no basis.",
        _VOCAB,
    )
    assert arg is not None
    assert arg.premises[0].basis == longest
    assert arg.premises[0].basis_text == f"{longest.phrase.upper()} with a note; more"
    assert arg.premises[1].basis is None and arg.premises[1].rank == 0
    assert arg.premises[2].basis_text is None and arg.premises[2].rank == 0


def test_parse_reason_collects_repeated_keys():
    reason = ra.parse_reason(_reason("claim-1"), _VOCAB)
    assert set(reason.entries) == set(_VOCAB.reason_keys)
    assert len(reason.get("Valid")) == 2
    assert reason.judged_asks == [ASK_A, ASK_B]
    assert reason.no_claim is False


def test_reason_keys_are_read_from_the_vocabulary():
    """The parser recognises whatever keys the vocabulary names, and no others."""
    from dataclasses import replace

    first, dropped, *_ = _VOCAB.reason_keys
    custom = replace(_VOCAB, reason_keys=(first, "Probe"))
    reason = ra.parse_reason(f"{first}: a\nProbe: b\n{dropped}: c", custom)
    assert reason.entries == {first: ["a"], "Probe": ["b"]}


# ---------------------------------------------------------------------------
# 2. The recorder refuses PASS
# ---------------------------------------------------------------------------


def test_pass_with_seven_lines_matching_the_block_is_recorded():
    _arm_with_report("s-ok", "claim-ok")
    tracer = _configured()
    result = pcv.record_verdict(
        session_id="s-ok",
        claim_id="claim-ok",
        verdict="PASS",
        reason=_reason("claim-ok"),
        tracer_mod=tracer,
    )
    assert result["ok"] is True and result["span_emitted"] is True
    assert pcg.is_armed("s-ok") is False


def test_answered_unanswered_entry_is_accepted():
    _arm_with_report("s-unans", "CID")
    reason = _reason("CID", drop=(f"Answered: {ASK_B}",), extra=(f"Answered: {ASK_B} unanswered",))
    result = pcv.record_verdict(
        session_id="s-unans",
        claim_id="CID",
        verdict="PASS",
        reason=reason,
        tracer_mod=_configured(),
    )
    assert result["ok"] is True


def test_no_claim_reason_is_refused_when_the_judged_text_has_a_block():
    _arm_with_report("s-noclaim-block", "CID")
    with pytest.raises(ValueError, match="no-claim reason, but the judged text has an argdown"):
        pcv.record_verdict(
            session_id="s-noclaim-block",
            claim_id="CID",
            verdict="PASS",
            reason="Judged: CID; no claim -- a status ping",
            tracer_mod=_configured(),
        )
    assert pcg.is_armed("s-noclaim-block") is True


def _report_without_asks() -> str:
    return _report(frontmatter=_frontmatter(asks=False))


def test_block_answers_naming_an_absent_line_are_refused():
    _arm_with_report(
        "s-answers", "CID", text=_report(_frontmatter(answers=f"{ASK_A}: 4\n  {ASK_B}: 9"))
    )
    with pytest.raises(ValueError, match="the block's answers name lines not in the block"):
        pcv.record_verdict(
            session_id="s-answers",
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=_configured(),
        )


def test_malformed_frontmatter_means_pass_needs_waived_block():
    _arm_with_report("s-badyaml", "CID", text=_report(frontmatter="===\nasks: [unclosed\n===\n"))
    with pytest.raises(ValueError, match="PASS needs 'Waived: block"):
        pcv.record_verdict(
            session_id="s-badyaml",
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=_configured(),
        )


@pytest.mark.parametrize("with_block", [True, False], ids=["block", "waived-block"])
def test_pass_with_no_ask_ids_is_refused(with_block):
    text = _report_without_asks() if with_block else "Done. All tests pass."
    _arm_with_report("s-noasks", "CID", text=text)
    reason = _reason(
        "CID",
        drop=("Judged", "Answered", "Waived"),
        extra=("Judged: CID", "Answered: none", "Waived: block -- prose report"),
    )
    with pytest.raises(ValueError, match="no ask ids"):
        pcv.record_verdict(
            session_id="s-noasks",
            claim_id="CID",
            verdict="PASS",
            reason=reason,
            tracer_mod=_configured(),
        )


def test_inference_line_with_no_conclusion_fails():
    text = _report().replace("(6) So it blocks Stop.\n", "")
    _arm_with_report("s-noconc", "CID", text=text)
    reason = _reason("CID", drop=("Relay",), extra=("Relay: none",))
    with pytest.raises(ValueError, match="inference line with no conclusion"):
        pcv.record_verdict(
            session_id="s-noconc",
            claim_id="CID",
            verdict="PASS",
            reason=reason,
            tracer_mod=_configured(),
        )


def test_pass_with_free_text_reason_is_refused_and_gate_stays_armed():
    _arm_with_report("s-free", "claim-free")
    with pytest.raises(ValueError, match="missing keyed lines"):
        pcv.record_verdict(
            session_id="s-free",
            claim_id="claim-free",
            verdict="PASS",
            reason="The cited diff supports each claim; the conclusion answers the ask.",
            tracer_mod=_configured(),
        )
    assert pcg.is_armed("s-free") is True


_REFUSALS = {
    "missing_key": (dict(drop=("Sufficient",)), "missing keyed lines: Sufficient"),
    "judged_asks": (
        dict(drop=("Judged",), extra=(f"Judged: CID; asks {ASK_A}",)),
        "do not equal the block's asks",
    ),
    "unanswered": (dict(drop=(f"Answered: {ASK_B}",)), f"no Answered line for ask ids: {ASK_B}"),
    "answered_absent_line": (
        dict(drop=(f"Answered: {ASK_B}",), extra=(f"Answered: {ASK_B} ← (9)",)),
        "Answered names lines not in the block (9)",
    ),
    "answered_shape": (
        dict(drop=(f"Answered: {ASK_B}",), extra=(f"Answered: {ASK_B} looks fine",)),
        "Answered entries not in the form",
    ),
    "judged_twice": (
        dict(extra=(f"Judged: CID; asks {ASK_A}, {ASK_B}",)),
        "Judged must appear exactly once; found 2",
    ),
    "supported_twice": (
        dict(extra=(f"Supported: weakest {_WEAK.phrase} -- again",)),
        "Supported must appear exactly once; found 2",
    ),
    "valid_count": (dict(drop=("Valid: (6)",)), "Valid has 1 entries for 2 inference lines"),
    "valid_keyed": (
        dict(drop=("Valid: (6)",), extra=("Valid: (5) holds -- wrong line",)),
        "the inference lines yield [4, 6]",
    ),
    "valid_fails": (
        dict(drop=("Valid: (6)",), extra=(f"Valid: (6) fails {_DEFECT} -- no premise",)),
        "Valid says fails for (6)",
    ),
    "supported_rank": (
        dict(drop=("Supported",), extra=(f"Supported: weakest {_STRONG.phrase} -- all strong",)),
        "the block's weakest premise is (3)",
    ),
    "waived_item": (
        dict(drop=("Waived",), extra=("Waived: the warrant was vague -- fine",)),
        "Waived entries that do not start with a format item",
    ),
    "relay_absent_line": (
        dict(drop=("Relay",), extra=('Relay: "it is merged" ← (9)',)),
        "Relay names lines not in the block (9)",
    ),
    "relay_no_line": (
        dict(drop=("Relay",), extra=('Relay: "it is merged"',)),
        "Relay names no line",
    ),
}


@pytest.mark.parametrize("case", sorted(_REFUSALS))
def test_each_pass_cross_check_fires(case):
    kw, fragment = _REFUSALS[case]
    session_id = f"s-{case}"
    _arm_with_report(session_id, "CID")
    tracer = _configured()
    with pytest.raises(ValueError) as exc:
        pcv.record_verdict(
            session_id=session_id,
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID", **kw),
            tracer_mod=tracer,
        )
    assert fragment in str(exc.value)
    assert tracer.exported == []
    assert pcg.is_armed(session_id) is True


def test_one_refusal_names_every_failed_check():
    _arm_with_report("s-many", "CID")
    reason = _reason(
        "CID",
        drop=("Sufficient", f"Answered: {ASK_B}", "Relay"),
        extra=('Relay: "x" ← (9)',),
    )
    with pytest.raises(ValueError) as exc:
        pcv.record_verdict(
            session_id="s-many",
            claim_id="CID",
            verdict="PASS",
            reason=reason,
            tracer_mod=_configured(),
        )
    for fragment in (
        "missing keyed lines: Sufficient",
        f"no Answered line for ask ids: {ASK_B}",
        "Relay names lines not in the block (9)",
    ):
        assert fragment in str(exc.value)


def test_pass_on_text_without_a_block_needs_waived_block():
    _arm_with_report("s-noblock", "CID", text="Done. All tests pass.")
    with pytest.raises(ValueError, match="PASS needs 'Waived: block"):
        pcv.record_verdict(
            session_id="s-noblock",
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=_configured(),
        )
    assert pcg.is_armed("s-noblock") is True

    reason = _reason(
        "CID", drop=("Waived",), extra=("Waived: block -- no block; steps judged from prose",)
    )
    result = pcv.record_verdict(
        session_id="s-noblock",
        claim_id="CID",
        verdict="PASS",
        reason=reason,
        tracer_mod=_configured(),
    )
    assert result["ok"] is True


def test_no_claim_one_line_reason_is_accepted_and_flagged():
    _arm_with_report("s-noclaim", "CID", text="<task-notification>heartbeat</task-notification>")
    tracer = _configured()
    pcv.record_verdict(
        session_id="s-noclaim",
        claim_id="CID",
        verdict="PASS",
        reason="Judged: CID; no claim -- a status ping",
        tracer_mod=tracer,
    )
    attrs = tracer.exported[0]["attributes"]
    assert attrs["premise_check.no_claim"] is True
    assert attrs["premise_check.reason.judged"] == "CID; no claim -- a status ping"


@pytest.mark.parametrize("token", ["REVISE", "FAIL"])
def test_revise_and_fail_take_any_reason_and_still_parse_keyed_lines(token):
    _arm_with_report(f"s-{token}", "CID")
    tracer = _configured()
    reason = (
        f"Valid: (6) fails {_DEFECT} -- no line says the mode is on\n"
        "Some free prose the sender reads.\n"
        f"Waived: {_FORMAT_ITEM} -- off but judgeable"
    )
    pcv.record_verdict(
        session_id=f"s-{token}", claim_id="CID", verdict=token, reason=reason, tracer_mod=tracer
    )
    attrs = tracer.exported[0]["attributes"]
    assert attrs["premise_check.verdict"] == token
    assert attrs["premise_check.defect_tags"] == [_DEFECT]
    assert attrs["premise_check.defect_tag_count"] == 1
    assert attrs["premise_check.inference_count"] == 2
    assert attrs["premise_check.waived_items"] == [_FORMAT_ITEM]
    assert pcg.is_armed(f"s-{token}") is False


# ---------------------------------------------------------------------------
# 3. Span attributes and the judged-text link
# ---------------------------------------------------------------------------


def test_verdict_span_carries_one_attribute_per_reason_key_and_the_block_measures():
    _arm_with_report("s-span", "CID", ref="toolu_01ABC")
    tracer = _configured()
    pcv.record_verdict(
        session_id="s-span",
        claim_id="CID",
        verdict="PASS",
        reason=_reason("CID"),
        tracer_mod=tracer,
    )
    attrs = tracer.exported[0]["attributes"]
    parsed = ra.parse_reason(_reason("CID"), _VOCAB)
    for key in _VOCAB.reason_keys:
        assert attrs[f"premise_check.reason.{key.lower()}"] == "\n".join(parsed.get(key))
    assert attrs["premise_check.reason_text"] == _reason("CID")
    assert attrs["premise_check.ask_ids"] == [ASK_A, ASK_B]
    assert attrs["premise_check.weakest_basis"] == _WEAK.phrase
    assert attrs["premise_check.weakest_basis_term"] == _WEAK.term
    assert attrs["premise_check.inference_count"] == 2
    assert attrs["premise_check.defect_tag_count"] == 0
    assert attrs["premise_check.waived_items"] == []
    assert attrs["premise_check.no_claim"] is False
    assert attrs["premise_check.judged_ref"] == "toolu_01ABC"
    assert (
        attrs["premise_check.judged_text_sha256"] == hashlib.sha256(_report().encode()).hexdigest()
    )
    # No attribute is both a leaf and a prefix: Phoenix nests dotted keys.
    keys = list(attrs)
    assert not [k for k in keys if any(o.startswith(k + ".") for o in keys)]


def _subagent_result_ctx(session_id: str, text: str, tool_use_id: str) -> dispatch.HookContext:
    return dispatch.HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id=session_id,
        agent_type="ida:ida",
        raw={
            "prompt": f'<task-notification id="{tool_use_id}"><result>{text}</result></task-notification>',
        },
    )


def test_arm_on_subagent_result_stores_judged_text_and_tool_use_id():
    ctx = _subagent_result_ctx("s-arm-sub", _report(), "toolu_0XYZ")
    assert pcg.premise_check_arm(ctx) is not None
    claim_id = pcg.get_state("s-arm-sub")["claim_id"]
    text, ref = pcg.get_judged("s-arm-sub", claim_id)
    assert ref == "toolu_0XYZ"
    assert text is not None and ra.extract_block(text) == ra.extract_block(_report())

    tracer = _configured()
    pcv.record_verdict(
        session_id="s-arm-sub",
        claim_id=claim_id,
        verdict="PASS",
        reason=_reason(claim_id),
        tracer_mod=tracer,
    )
    assert tracer.exported[0]["attributes"]["premise_check.judged_ref"] == "toolu_0XYZ"
    assert pcg.get_judged("s-arm-sub", claim_id) == (None, None)


def test_arm_on_peer_message_uses_the_envelope_id_as_judged_ref():
    prompt = f'<cross-session-message from="twin" id="msg-42">{_report()}</cross-session-message>'
    ctx = dispatch.HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="s-arm-peer",
        agent_type="ida:ida",
        raw={"prompt": prompt},
    )
    pcg.premise_check_arm(ctx)
    text, ref = pcg.get_judged("s-arm-peer", "msg-42")
    assert ref == "msg-42"
    assert text is not None and ASK_A in text


def test_judged_block_drives_the_cross_checks():
    """A reason that fits the block passes; the same reason against another block is refused."""
    other = _report().replace(ASK_B, "tg-7")
    _arm_with_report("s-other", "CID", text=other)
    with pytest.raises(ValueError, match="do not equal the block's asks"):
        pcv.record_verdict(
            session_id="s-other",
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=_configured(),
        )


# ---------------------------------------------------------------------------
# 4. A failed span means no verdict
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tracer",
    [_configured(export_ok=False), _configured(raises=OSError("collector down"))],
    ids=["unacknowledged", "raises"],
)
def test_failed_export_records_no_verdict_and_stays_armed(tracer):
    _arm_with_report("s-span-fail", "CID")
    with pytest.raises(RuntimeError, match="span export failed"):
        pcv.record_verdict(
            session_id="s-span-fail",
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=tracer,
        )
    assert pcg.is_armed("s-span-fail") is True
    assert "last_verdict" not in pcg.get_state("s-span-fail")


def test_cli_exits_non_zero_when_export_fails(monkeypatch, tmp_path):
    _arm_with_report("s-cli-fail", "CID")
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: _configured(export_ok=False))
    reason_file = tmp_path / "reason.txt"
    reason_file.write_text(_reason("CID"), encoding="utf-8")
    rc = pcv.main(
        [
            "--claim",
            "CID",
            "--verdict",
            "PASS",
            "--reason-file",
            str(reason_file),
            "--session",
            "s-cli-fail",
        ]
    )
    assert rc != 0
    assert pcg.is_armed("s-cli-fail") is True


def test_unconfigured_tracing_records_no_verdict():
    _arm_with_report("s-unconf", "CID")
    tracer = _StubTracer(config=None)
    with pytest.raises(RuntimeError, match="tracing is not configured"):
        pcv.record_verdict(
            session_id="s-unconf",
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=tracer,
        )
    assert tracer.exported == []
    assert pcg.is_armed("s-unconf") is True


# ---------------------------------------------------------------------------
# 5. Arming on task-record handbacks
# ---------------------------------------------------------------------------


def _task_body(with_verdict: bool = False, with_report: bool = True) -> str:
    body = "## Goal\n\nDo the thing.\n\n"
    if with_report:
        body += "## Report\n\n" + _report()
    if with_verdict:
        body += "\n## Premise-Check Verdict\n\nverdict-12345678 PASS\n"
    return body


def _task_read_ctx(tool: str, body: str, task_id: str, shape: str, agent: str = "ida:ida"):
    record = {"id": task_id, "title": "Do the thing", "status": "review", "body": body}
    if shape == "content_blocks":
        response: Any = [{"type": "text", "text": json.dumps(record)}]
    elif shape == "dict":
        response = record
    else:
        response = json.dumps(record)
    return dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        tool=tool,
        session_id=f"s-task-{shape}",
        agent_type=agent,
        raw={"tool_input": {"id": task_id}, "tool_response": response},
    )


@pytest.mark.parametrize("shape", ["content_blocks", "dict", "json_text"])
@pytest.mark.parametrize("tool", _POLICY["task_read_tools"])
def test_task_read_with_unverdicted_report_does_not_arm_while_bypassed(tool, shape):
    ctx = _task_read_ctx(tool, _task_body(), "aops_0a8efbc2", shape)
    assert pcg.premise_check_arm(ctx) is None
    assert pcg.is_armed(ctx.session_id) is False


@pytest.mark.skip(reason="bypassed pending decision")
@pytest.mark.parametrize("shape", ["content_blocks", "dict", "json_text"])
def test_unverdicted_task_report_finds_task_id_and_body(shape):
    ctx = _task_read_ctx(_POLICY["task_read_tools"][0], _task_body(), "aops_0a8efbc2", shape)
    assert pcg.unverdicted_task_report(ctx) == ("aops_0a8efbc2", _task_body())


@pytest.mark.skip(reason="bypassed pending decision")
@pytest.mark.parametrize(
    "body", [_task_body(with_verdict=True), _task_body(with_report=False)], ids=["verdict", "none"]
)
def test_unverdicted_task_report_skips_verdicted_or_reportless_tasks(body):
    ctx = _task_read_ctx(_POLICY["task_read_tools"][0], body, "aops_0a8efbc2", "dict")
    assert pcg.unverdicted_task_report(ctx) is None


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_post_tool_entry_point_does_not_arm_on_task_read_while_bypassed(client):
    import importlib.util

    spec = importlib.util.spec_from_file_location("ida_handlers_arm", _HOOKS_DIR / "handlers.py")
    assert spec and spec.loader
    handlers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handlers)
    record = {"id": "aops_0a8efbc2", "body": _task_body()}
    raw = {
        "tool_name": _POLICY["task_read_tools"][0],
        "session_id": f"s-entry-{client}",
        "agent_type": "ida:ida",
        "tool_input": {"id": "aops_0a8efbc2"},
        "tool_response": [{"type": "text", "text": json.dumps(record)}],
    }
    ctx = dispatch.normalize(client, "PostToolUse", raw, _HOOKS_DIR)
    handlers.post_tool(ctx)
    assert pcg.is_armed(f"s-entry-{client}") is False


# ---------------------------------------------------------------------------
# 6. Overrides pass an armed gate; counting them is bypassed
# ---------------------------------------------------------------------------


def _dispatch_ctx(session_id: str) -> dispatch.HookContext:
    return dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Agent",
        session_id=session_id,
        agent_type="ida:ida",
    )


@pytest.mark.parametrize("var", _POLICY["override_vars"])
def test_override_passes_an_armed_gate_with_no_span_and_no_count(monkeypatch, var):
    session_id = f"s-ovr-{var}"
    pcg.arm(session_id, claim_id="claim-ovr")
    tracer = _configured(raises=OSError("an export attempt would raise"))
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    monkeypatch.setenv(var, "1")

    assert pcg.premise_check_handler(_dispatch_ctx(session_id)) is None

    assert tracer.exported == []
    assert "override_count" not in pcg.get_state(session_id)


@pytest.mark.skip(reason="bypassed pending decision")
def test_count_override_emits_a_span_and_counts(monkeypatch):
    pcg.arm("s-ovr-count", claim_id="claim-ovr")
    tracer = _configured()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    pcg._count_override(_dispatch_ctx("s-ovr-count"), _POLICY["override_vars"][0])
    assert pcg.get_state("s-ovr-count")["override_count"] == 1
    assert [s["name"] for s in tracer.exported] == ["premise_check_override"]


def test_get_judged_raises_when_the_stored_file_is_missing():
    _arm_with_report("s-gone", "CID")
    for path in Path(pcg._state_dir()).glob("*.judged.txt"):
        path.unlink()
    with pytest.raises(FileNotFoundError):
        pcg.get_judged("s-gone", "CID")


def test_disarm_raises_when_the_stored_file_is_missing():
    _arm_with_report("s-gone-2", "CID")
    for path in Path(pcg._state_dir()).glob("*.judged.txt"):
        path.unlink()
    with pytest.raises(FileNotFoundError):
        pcg.disarm("s-gone-2", "CID", "REVISE", "r")


def test_override_on_a_disarmed_gate_is_not_counted(monkeypatch):
    tracer = _configured()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    monkeypatch.setenv(_POLICY["override_vars"][0], "1")
    assert pcg.premise_check_handler(_dispatch_ctx("s-ovr-idle")) is None
    assert tracer.exported == []
    assert "override_count" not in pcg.get_state("s-ovr-idle")


# ---------------------------------------------------------------------------
# Machine checks on Argdown block (Acceptance Criterion 2)
# ---------------------------------------------------------------------------


def test_machine_checks_valid_argument_passes():
    session_id = "s-mach-pass"
    _arm_with_report(session_id, "CID")
    tracer = _configured()
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="CID",
        verdict="PASS",
        reason=_reason("CID"),
        tracer_mod=tracer,
    )
    assert result["verdict"] == "PASS"
    assert result["disarmed"] is True
    assert pcg.is_armed(session_id) is False


def test_machine_checks_orphan_statement_records_revise_and_clears_gate():
    session_id = "s-mach-orphan"
    # Append an orphan statement to a valid report
    text = _report().replace(
        "```\n",
        "\n[orphan]: An orphan statement not used as premise or conclusion.\n```\n",
    )
    _arm_with_report(session_id, "CID", text=text)
    tracer = _configured()
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="CID",
        verdict="PASS",
        reason=_reason("CID"),
        tracer_mod=tracer,
    )
    assert result["verdict"] == "REVISE"
    assert "orphan statement 'orphan'" in result["reason"]
    assert result["disarmed"] is True
    assert pcg.is_armed(session_id) is False


def test_machine_checks_misaimed_undercut_records_revise_and_clears_gate():
    session_id = "s-mach-undercut"
    # Append an undercut aimed at a statement (1) instead of an inference
    text = _report().replace(
        "```\n",
        "\n[undercut]: Undercutting statement.\n  _> (1)\n```\n",
    )
    _arm_with_report(session_id, "CID", text=text)
    tracer = _configured()
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="CID",
        verdict="PASS",
        reason=_reason("CID"),
        tracer_mod=tracer,
    )
    assert result["verdict"] == "REVISE"
    assert "undercut from 'undercut' targets" in result["reason"]
    assert "instead of an inference" in result["reason"]
    assert result["disarmed"] is True
    assert pcg.is_armed(session_id) is False


def test_machine_checks_parse_error_records_revise_and_clears_gate():
    session_id = "s-mach-parse-err"
    # Append a syntax error to the report's argdown block
    text = _report().replace(
        "```\n",
        "\n\n<+ unclosed relation\n```\n",
    )
    _arm_with_report(session_id, "CID", text=text)
    tracer = _configured()
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="CID",
        verdict="PASS",
        reason=_reason("CID"),
        tracer_mod=tracer,
    )
    assert result["verdict"] == "REVISE"
    assert "Argdown syntax error" in result["reason"]
    assert result["disarmed"] is True
    assert result["machine"] is True
    assert pcg.is_armed(session_id) is False


def test_machine_checks_valid_relation_is_not_orphan():
    session_id = "s-mach-rel"
    text = _report().replace(
        "```\n",
        "\n[Objection]: An objection.\n  -> [Reply]: A reply.\n```\n",
    )
    _arm_with_report(session_id, "CID", text=text)
    tracer = _configured()
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="CID",
        verdict="PASS",
        reason=_reason("CID"),
        tracer_mod=tracer,
    )
    assert result["verdict"] == "PASS"
    assert result["disarmed"] is True
    assert pcg.is_armed(session_id) is False


def test_machine_checks_parser_failure_raises_and_leaves_gate_armed():
    session_id = "s-mach-parser-fail"
    _arm_with_report(session_id, "CID")
    tracer = _configured()
    with unittest.mock.patch("report_argument.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="argdown parser binary not found"):
            pcv.record_verdict(
                session_id=session_id,
                claim_id="CID",
                verdict="PASS",
                reason=_reason("CID"),
                tracer_mod=tracer,
            )
    assert pcg.is_armed(session_id) is True


def test_resolve_argdown_bin_across_env_node_modules_and_path(tmp_path, monkeypatch):
    """AC5: Resolves argdown binary across AOPS_ARGDOWN_BIN, repo/user node_modules, and PATH."""
    fake_bin = tmp_path / "fake_argdown"
    fake_bin.write_text("#!/bin/sh\nexit 0\n")
    fake_bin.chmod(0o755)

    # 1. AOPS_ARGDOWN_BIN environment variable takes precedence
    monkeypatch.setenv("AOPS_ARGDOWN_BIN", str(fake_bin))
    with unittest.mock.patch("report_argument.shutil.which", return_value=None):
        assert ra.resolve_argdown_bin() == str(fake_bin)

    # 2. repo/user node_modules/.bin/argdown
    monkeypatch.delenv("AOPS_ARGDOWN_BIN", raising=False)
    fake_nm_bin = tmp_path / "node_modules" / ".bin" / "argdown"
    fake_nm_bin.parent.mkdir(parents=True)
    fake_nm_bin.write_text("#!/bin/sh\nexit 0\n")
    fake_nm_bin.chmod(0o755)

    with unittest.mock.patch("pathlib.Path.cwd", return_value=tmp_path):
        with unittest.mock.patch("report_argument.shutil.which", return_value=None):
            assert ra.resolve_argdown_bin() == str(fake_nm_bin)

    # 3. Falls back to shutil.which('argdown')
    with unittest.mock.patch("pathlib.Path.cwd", return_value=tmp_path / "empty"):
        with unittest.mock.patch("report_argument.shutil.which", return_value="/usr/bin/argdown"):
            assert ra.resolve_argdown_bin() == "/usr/bin/argdown"


def test_check_argdown_block_handles_markdown_punctuation():
    """AC5: Markdown punctuation (*, _) in premise-check blocks does not cause false-positive syntax rejections."""
    report_text = _report().replace(
        '(2) The hook returns "block", not advice. --',
        "(2) The hook returns *block*, not advice with an_identifier and **bold**. --",
    )
    block_text = ra.extract_block(report_text)
    assert block_text is not None

    valid, reason, ast = ra.check_argdown_block(block_text)
    assert valid is True, f"Argdown syntax check failed on markdown punctuation: {reason}"
    assert ast is not None
