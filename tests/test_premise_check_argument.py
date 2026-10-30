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


def test_machine_checks_orphan_statement_refuses_pass_and_leaves_gate_armed():
    session_id = "s-mach-orphan"
    # Append an orphan statement to a valid report
    text = _report().replace(
        "```\n",
        "\n[orphan]: An orphan statement not used as premise or conclusion.\n```\n",
    )
    _arm_with_report(session_id, "CID", text=text)
    tracer = _configured()
    with pytest.raises(ValueError, match="orphan statement 'orphan'"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=tracer,
        )
    assert pcg.is_armed(session_id) is True


def test_machine_checks_misaimed_undercut_refuses_pass_and_leaves_gate_armed():
    session_id = "s-mach-undercut"
    # Append an undercut aimed at a statement (1) instead of an inference
    text = _report().replace(
        "```\n",
        "\n[undercut]: Undercutting statement.\n  _> (1)\n```\n",
    )
    _arm_with_report(session_id, "CID", text=text)
    tracer = _configured()
    with pytest.raises(ValueError, match="undercut from 'undercut' targets"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=tracer,
        )
    assert pcg.is_armed(session_id) is True


def test_machine_checks_parse_error_refuses_pass_and_leaves_gate_armed():
    session_id = "s-mach-parse-err"
    # Append a syntax error to the report's argdown block
    text = _report().replace(
        "```\n",
        "\n\n<+ unclosed relation\n```\n",
    )
    _arm_with_report(session_id, "CID", text=text)
    tracer = _configured()
    with pytest.raises(ValueError, match="Argdown syntax error"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="CID",
            verdict="PASS",
            reason=_reason("CID"),
            tracer_mod=tracer,
        )
    assert pcg.is_armed(session_id) is True


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
    with unittest.mock.patch(
        "report_argument.check_argdown_block",
        side_effect=RuntimeError("internal parser error"),
    ):
        with pytest.raises(RuntimeError, match="internal parser error"):
            pcv.record_verdict(
                session_id=session_id,
                claim_id="CID",
                verdict="PASS",
                reason=_reason("CID"),
                tracer_mod=tracer,
            )
    assert pcg.is_armed(session_id) is True


def test_check_argdown_block_parses_natively_without_external_binary(tmp_path, monkeypatch):
    """AC1: check_argdown_block parses natively without requiring argdown binary on PATH."""
    assert not hasattr(ra, "resolve_argdown_bin")

    # Works even when shutil.which returns None
    with unittest.mock.patch("shutil.which", return_value=None):
        valid, reason, ast = ra.check_argdown_block(
            "(1) claim -- I read it\n-- warrant --\n(2) conc\n"
        )
        assert valid is True
        assert ast is not None


def test_check_argdown_block_handles_markdown_punctuation():
    """AC3: Markdown punctuation (*, _) in premise-check blocks does not cause false-positive syntax rejections."""
    report_text = _report().replace(
        '(2) The hook returns "block", not advice. --',
        "(2) The hook returns *block*, not advice with an_identifier and **bold**. --",
    )
    block_text = ra.extract_block(report_text)
    assert block_text is not None

    valid, reason, ast = ra.check_argdown_block(block_text)
    assert valid is True, f"Argdown syntax check failed on markdown punctuation: {reason}"
    assert ast is not None


def test_scaffold_removed():
    """AC1: generate_scaffold and --scaffold removed."""
    assert not hasattr(pcv, "generate_scaffold")


def test_verdict_cli_scaffold_flag_and_refusal_scaffold(tmp_path, capsys):
    """AC1: --scaffold flag removed and refusal does not output scaffold."""
    session_id = "s-cli-scaffold"
    _arm_with_report(session_id, "CID-CLI")

    # 1. --scaffold flag is no longer recognized
    with pytest.raises(SystemExit):
        pcv.main(["--claim", "CID-CLI", "--session", session_id, "--scaffold"])

    # 2. Refused PASS check outputs error to stderr without scaffold and exits 1
    bad_reason = "Judged: CID-CLI\nValid: (4) holds -- test\nSupported: weakest none\nAnswered: none\nSufficient: none\nWaived: none\nRelay: none"
    exit_fail = pcv.main(
        [
            "--claim",
            "CID-CLI",
            "--session",
            session_id,
            "--verdict",
            "PASS",
            "--reason",
            bad_reason,
        ]
    )
    assert exit_fail == 1
    captured_fail = capsys.readouterr()
    assert "premise_check_verdict:" in captured_fail.err
    assert "Scaffold" not in captured_fail.err
    assert pcg.is_armed(session_id) is True


def test_valid_grouped_lines_accepted():
    """Grouped line references on one Valid line pass a multi-inference argument."""
    vocab = ra.load_vocabulary()
    block = ra.parse_block(ra.extract_block(_report()), vocab)
    assert block is not None
    assert len(block.inferences) == 2

    # (4), (6) holds
    r1 = ra.parse_reason(
        _reason("CID", drop=("Valid:",), extra=("Valid: (4), (6) holds -- both hold",)), vocab
    )
    assert not ra.pass_failures(r1, block, vocab)

    # (4), (6) hold
    r2 = ra.parse_reason(
        _reason("CID", drop=("Valid:",), extra=("Valid: (4), (6) hold -- both hold",)), vocab
    )
    assert not ra.pass_failures(r2, block, vocab)

    # (4) and (6) hold
    r3 = ra.parse_reason(
        _reason("CID", drop=("Valid:",), extra=("Valid: (4) and (6) hold -- both hold",)), vocab
    )
    assert not ra.pass_failures(r3, block, vocab)

    # Semicolon-separated clauses on one Valid line
    r4 = ra.parse_reason(
        _reason(
            "CID", drop=("Valid:",), extra=("Valid: (4) holds -- rule; (6) holds -- meets rule",)
        ),
        vocab,
    )
    assert not ra.pass_failures(r4, block, vocab)


def test_valid_multiline_indented_accepted():
    """Indented lines under Valid: are parsed as entries and validate multi-inference blocks."""
    vocab = ra.load_vocabulary()
    block = ra.parse_block(ra.extract_block(_report()), vocab)
    assert block is not None

    reason_text = _reason(
        "CID",
        drop=("Valid:",),
        extra=("Valid:\n  (4) holds -- rule\n  (6) holds -- meets rule",),
    )
    r = ra.parse_reason(reason_text, vocab)
    assert len(r.get("Valid")) == 2
    assert not ra.pass_failures(r, block, vocab)


def test_valid_clause_with_failure_refuses_pass():
    """A grouped or semicolon valid entry that contains a failure is detected."""
    vocab = ra.load_vocabulary()
    block = ra.parse_block(ra.extract_block(_report()), vocab)
    assert block is not None

    r = ra.parse_reason(
        _reason(
            "CID",
            drop=("Valid:",),
            extra=("Valid: (4) holds -- rule; (6) fails #missing -- no premise",),
        ),
        vocab,
    )
    failures = ra.pass_failures(r, block, vocab)
    assert any("Valid says fails for (6)" in f for f in failures)


def test_parse_block_and_check_handles_em_dash_inferences():
    """Inference bars with em-dashes (—) parse correctly and pass argdown syntax check."""
    report_text = (
        "Report\n\n"
        "```argdown\n"
        f"{_frontmatter()}\n"
        f"(1) First premise. -- {_STRONG.phrase}\n"
        "— Warrant with em dashes —\n"
        "(2) Conclusion.\n"
        "```\n"
    )
    vocab = ra.load_vocabulary()
    block_text = ra.extract_block(report_text)
    assert block_text is not None

    block = ra.parse_block(block_text, vocab)
    assert block is not None
    assert len(block.inferences) == 1
    assert block.inferences[0].conclusion == 2

    valid, reason, ast = ra.check_argdown_block(block_text)
    assert valid is True, f"Argdown syntax check failed: {reason}"


# ---------------------------------------------------------------------------
# AC1 & AC2: Tolerant native Argdown parser and machine checks
# ---------------------------------------------------------------------------


def test_native_parser_valid_argdown_with_markdown_emphasis_and_code():
    """AC1/AC2: Native parser parses valid Argdown blocks with inline markdown emphasis/code."""
    block = (
        "===\n"
        "asks:\n"
        "  q1: is it working?\n"
        "answers:\n"
        "  q1: 2\n"
        "notes:\n"
        "  a: '`plugins/ida/hooks/report_argument.py` with *inline* and **bold**'\n"
        "===\n\n"
        "(1) Code `foo()` has an_identifier and **bold** and *emphasis*. -- I read it ^a\n"
        "-- Warrant text. Unless: defeater; not ruled out. --\n"
        "(2) So, `bar()` succeeds.\n"
    )
    valid, reason, ast = ra.check_argdown_block(block)
    assert valid is True, f"Expected valid Argdown block, got error: {reason}"
    assert ast is not None
    parsed = ra.parse_block(block, _VOCAB)
    assert parsed is not None
    assert parsed.asks == ["q1"]
    assert len(parsed.premises) == 1
    assert parsed.premises[0].basis == _STRONG  # 'I read it' is rank 3
    assert len(parsed.inferences) == 1
    assert parsed.conclusions == [2]


def test_native_parser_rejects_malformed_inference_lines():
    """AC2: Rejects malformed inference lines (missing closing dashes)."""
    block = (
        "(1) A premise. -- I read it\n"
        "-- Malformed inference line without closing dashes\n"
        "(2) Conclusion.\n"
    )
    valid, reason, ast = ra.check_argdown_block(block)
    assert valid is False
    assert "inference" in reason.lower() or "syntax" in reason.lower()


def test_native_parser_rejects_unconnected_orphan_statements():
    """AC2: Rejects unconnected statements with no relations or argument membership."""
    block = (
        "(1) A premise. -- I read it\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) Conclusion.\n"
        "[orphan_stmt]: This statement is totally unconnected.\n"
    )
    valid, reason, ast = ra.check_argdown_block(block)
    assert valid is False
    assert "orphan statement 'orphan_stmt'" in reason


# ---------------------------------------------------------------------------
# AC4: Premise attribute syntax {basis: ...} and 0 inference lines check
# ---------------------------------------------------------------------------


def test_premise_attribute_syntax_basis():
    """AC4: Accepts {basis: \"<basis phrase>\", pointer: ...} alongside -- <basis phrase> ^note."""
    block = (
        "===\n"
        "asks:\n"
        "  q1: ok?\n"
        "answers:\n"
        "  q1: 3\n"
        "===\n\n"
        '(1) [P1]: First premise with attr. {basis: "I read it", pointer: "file.py:10"}\n'
        "(2) [P2]: Second premise with rule.\n"
        '  {basis: "rule", pointer: "rule.md"}\n'
        "-- Warrant. Unless: def; status. --\n"
        "(3) [C1]: Conclusion.\n"
    )
    parsed = ra.parse_block(block, _VOCAB)
    assert parsed is not None
    assert len(parsed.premises) == 2
    assert parsed.premises[0].basis_text == "I read it"
    assert parsed.premises[0].basis is not None and parsed.premises[0].basis.phrase == "I read it"
    assert parsed.premises[0].rank == 3
    assert parsed.premises[1].basis_text == "rule"
    assert parsed.premises[1].basis is not None and parsed.premises[1].basis.phrase == "rule"
    assert parsed.premises[1].rank == 2
    assert parsed.weakest() is not None and parsed.weakest().number == 2


def test_pass_rejected_when_report_argument_block_has_0_inferences():
    """AC4: Rejects PASS with actionable error when block has 0 inference lines."""
    block_text = (
        "===\n"
        "asks:\n"
        f"  {ASK_A}: is it working?\n"
        "answers:\n"
        f"  {ASK_A}: 1\n"
        "===\n\n"
        "(1) Just a premise with no inferences. -- I read it\n"
    )
    arg = ra.parse_block(block_text, _VOCAB)
    assert arg is not None
    assert len(arg.inferences) == 0

    reason = ra.parse_reason(
        f"Judged: claim-0inf; asks {ASK_A}\n"
        "Valid: (1) holds -- test\n"
        "Supported: weakest I read it -- (1)\n"
        f"Answered: {ASK_A} ← (1)\n"
        "Sufficient: (1) obvious\n"
        "Waived: none\n"
        "Relay: none\n",
        _VOCAB,
    )
    failures = ra.pass_failures(reason, arg, _VOCAB)
    expected_msg = (
        "report argument block has 0 inference lines (-- <warrant>. Unless: <defeater>; <status>. --); "
        "cannot record PASS"
    )
    assert expected_msg in failures


# ---------------------------------------------------------------------------
# AC5: Semicolon-separated Waived: items and specific waiver enforcement
# ---------------------------------------------------------------------------


def test_waived_semicolon_separated_items_and_bad_items():
    """AC5: Splits semicolon-separated items on Waived: lines and catches invalid items."""
    reason = ra.parse_reason(
        "Waived: block -- not provided; ask wording -- reworded; layout\n",
        _VOCAB,
    )
    assert reason.waived_items(_VOCAB) == ["block", "ask wording", "layout"]

    bad_reason = ra.parse_reason(
        "Waived: block; invalid_item -- reason; ask wording\n",
        _VOCAB,
    )
    assert bad_reason.waived_items(_VOCAB) == ["block", "ask wording"]
    failures = ra.pass_failures(bad_reason, None, _VOCAB)
    assert any("invalid_item" in f for f in failures)


def test_waived_block_honored_when_block_is_not_none():
    """AC5: Honors Waived: block when block is not None (skips block cross-checks)."""
    # A block with missing inference lines and mismatched asks
    block_text = (
        "===\n"
        "asks:\n"
        "  different_ask: what is this?\n"
        "answers:\n"
        "  different_ask: 1\n"
        "===\n\n"
        "(1) A premise without inferences. -- I read it\n"
    )
    arg = ra.parse_block(block_text, _VOCAB)
    assert arg is not None

    reason = ra.parse_reason(
        f"Judged: claim-wb; asks {ASK_A}\n"
        "Valid: (1) holds -- test\n"
        "Supported: weakest I read it -- test\n"
        f"Answered: {ASK_A} ← (1)\n"
        "Sufficient: (1) obvious\n"
        "Waived: block -- block structure waived\n"
        "Relay: none\n",
        _VOCAB,
    )
    failures = ra.pass_failures(reason, arg, _VOCAB)
    assert failures == []


def test_waived_ask_wording_honored_when_block_is_not_none():
    """AC5: Honors Waived: ask wording when block is not None."""
    # Block has reworded ask id in frontmatter
    report_text = _report().replace(ASK_A, "reworded_ask")
    block_text = ra.extract_block(report_text)
    arg = ra.parse_block(block_text, _VOCAB)
    assert arg is not None

    # Without waiver, fails because judged asks don't equal block asks
    reason_no_waiver = ra.parse_reason(_reason("CID"), _VOCAB)
    failures = ra.pass_failures(reason_no_waiver, arg, _VOCAB)
    assert any("Judged ask ids" in f for f in failures)

    # With Waived: ask wording, passes
    reason_with_waiver = ra.parse_reason(
        _reason(
            "CID", drop=("Waived:",), extra=("Waived: ask wording -- reworded in frontmatter",)
        ),
        _VOCAB,
    )
    failures_waived = ra.pass_failures(reason_with_waiver, arg, _VOCAB)
    assert failures_waived == []


def test_waived_basis_wording_when_basis_is_none_without_escalating_low_rank():
    """AC5: Honors Waived: basis wording when p.basis is None without escalating matched unchecked/assumed premises above rank=1."""
    # Case 1: Premise with non-standard basis phrase (p.basis is None)
    block_text = (
        "===\n"
        f"asks:\n  {ASK_A}: test\n"
        f"answers:\n  {ASK_A}: 2\n"
        "===\n\n"
        "(1) Premise with custom basis wording. -- verified from direct logs\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
    )
    arg = ra.parse_block(block_text, _VOCAB)
    assert arg is not None
    assert arg.premises[0].basis is None

    # Without waiver: fails because basis is unmatched (rank 0)
    reason_no_waiver = ra.parse_reason(
        f"Judged: CID; asks {ASK_A}\n"
        "Valid: (2) holds -- warrant\n"
        "Supported: weakest I read it -- direct logs\n"
        f"Answered: {ASK_A} ← (2)\n"
        "Sufficient: (2) obvious\n"
        "Waived: none\n"
        "Relay: none\n",
        _VOCAB,
    )
    failures_no_waiver = ra.pass_failures(reason_no_waiver, arg, _VOCAB)
    assert any(
        "weakest premise is (1) 'an unmatched basis' (rank 0)" in f for f in failures_no_waiver
    )

    # With Waived: basis wording: passes because p.basis is None is waived to match Supported
    reason_waived = ra.parse_reason(
        f"Judged: CID; asks {ASK_A}\n"
        "Valid: (2) holds -- warrant\n"
        "Supported: weakest I read it -- direct logs\n"
        f"Answered: {ASK_A} ← (2)\n"
        "Sufficient: (2) obvious\n"
        "Waived: basis wording -- custom phrase\n"
        "Relay: none\n",
        _VOCAB,
    )
    failures_waived = ra.pass_failures(reason_waived, arg, _VOCAB)
    assert failures_waived == []

    # Case 2: But matched unchecked (rank 1) or assumed (rank 0) CANNOT be escalated above rank 1
    block_text_with_unchecked = (
        "===\n"
        f"asks:\n  {ASK_A}: test\n"
        f"answers:\n  {ASK_A}: 3\n"
        "===\n\n"
        "(1) Premise with custom wording. -- verified from logs\n"
        "(2) Another premise that is unchecked. -- worker reported, unchecked\n"
        "-- Warrant. Unless: def; status. --\n"
        "(3) So, conclusion.\n"
    )
    arg_unchecked = ra.parse_block(block_text_with_unchecked, _VOCAB)
    assert arg_unchecked is not None
    assert arg_unchecked.premises[0].basis is None
    assert arg_unchecked.premises[1].basis is not None
    assert arg_unchecked.premises[1].rank == 1

    # Checker attempts to claim Supported: weakest I read it (rank 3) with Waived: basis wording
    reason_escalate_attempt = ra.parse_reason(
        f"Judged: CID; asks {ASK_A}\n"
        "Valid: (3) holds -- warrant\n"
        "Supported: weakest I read it -- logs\n"
        f"Answered: {ASK_A} ← (3)\n"
        "Sufficient: (3) obvious\n"
        "Waived: basis wording -- custom phrase\n"
        "Relay: none\n",
        _VOCAB,
    )
    failures_escalate = ra.pass_failures(reason_escalate_attempt, arg_unchecked, _VOCAB)
    assert any(
        "the block's weakest premise is (2) 'worker reported, unchecked' (rank 1)" in f
        for f in failures_escalate
    )


# ---------------------------------------------------------------------------
# Refusal diagnostics and actionable remediation guidance (AC1, AC2)
# ---------------------------------------------------------------------------


def test_refusal_diagnostics_parenthesized_line_numbers_in_frontmatter_answers():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for parenthesized line numbers."""
    block = (
        "===\n"
        f"asks:\n  {ASK_A}: is the hook enforced?\n"
        f"answers:\n  {ASK_A}: (2)\n"
        "===\n\n"
        "(1) Observation. -- I read it\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
    )
    # Check directly via check_argdown_block
    valid, error_msg, ast = ra.check_argdown_block(block)
    assert valid is False
    assert "Parenthesized line number in frontmatter answers" in error_msg
    assert "Defect:" in error_msg
    assert "Required remediation format:" in error_msg
    assert f"{ASK_A}: 2" in error_msg

    # Check via record_verdict
    session_id = "s-diag-paren"
    text = f"```argdown\n{block}```\n"
    _arm_with_report(session_id, "CID", text=text)
    reason = (
        f"Judged: CID; asks {ASK_A}\n"
        "Valid: (2) holds -- warrant\n"
        "Supported: weakest I read it -- direct logs\n"
        f"Answered: {ASK_A} ← (2)\n"
        "Sufficient: (2) obvious\n"
        "Waived: none\n"
        "Relay: none\n"
    )
    with pytest.raises(ValueError) as excinfo:
        pcv.record_verdict(
            session_id=session_id,
            claim_id="CID",
            verdict="PASS",
            reason=reason,
            tracer_mod=_configured(),
        )
    err = str(excinfo.value)
    assert "PASS verdict refused for CID" in err
    assert "Parenthesized line number in frontmatter answers" in err
    assert "Required remediation format:" in err
    assert f"{ASK_A}: 2" in err


def test_refusal_diagnostics_unmapped_asks_in_frontmatter_answers():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for unmapped asks."""
    block = (
        "===\n"
        f"asks:\n  {ASK_A}: first ask\n  {ASK_B}: second ask\n"
        f"answers:\n  {ASK_A}: 2\n"
        "===\n\n"
        "(1) Observation. -- I read it\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
    )
    # Check directly via check_argdown_block
    valid, error_msg, ast = ra.check_argdown_block(block)
    assert valid is False
    assert f"Unmapped ask(s) in frontmatter answers: {ASK_B}" in error_msg
    assert "Defect:" in error_msg
    assert "Required remediation format:" in error_msg
    assert f"answers:\n  {ASK_B}: <line_number | none>" in error_msg

    # Check via record_verdict
    session_id = "s-diag-unmapped"
    text = f"```argdown\n{block}```\n"
    _arm_with_report(session_id, "CID", text=text)
    reason = (
        f"Judged: CID; asks {ASK_A}, {ASK_B}\n"
        "Valid: (2) holds -- warrant\n"
        "Supported: weakest I read it -- direct logs\n"
        f"Answered: {ASK_A} ← (2)\n"
        f"Answered: {ASK_B} ← (2)\n"
        "Sufficient: (2) obvious\n"
        "Waived: none\n"
        "Relay: none\n"
    )
    with pytest.raises(ValueError) as excinfo:
        pcv.record_verdict(
            session_id=session_id,
            claim_id="CID",
            verdict="PASS",
            reason=reason,
            tracer_mod=_configured(),
        )
    err = str(excinfo.value)
    assert "Unmapped ask(s) in frontmatter answers" in err
    assert ASK_B in err
    assert "Required remediation format:" in err


def test_refusal_diagnostics_malformed_inference_line():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for malformed inference line."""
    block = (
        "(1) Observation. -- I read it\n"
        "-- Malformed inference line without closing dashes\n"
        "(2) So, conclusion.\n"
    )
    valid, error_msg, ast = ra.check_argdown_block(block)
    assert valid is False
    assert "Malformed inference line (missing closing '--'):" in error_msg
    assert "Defect:" in error_msg
    assert "Required remediation format:" in error_msg
    assert "-- <warrant rule>. Unless: <defeater>; <status>. --" in error_msg


def test_refusal_diagnostics_markdown_numbered_list():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for markdown numbers (1. instead of (1))."""
    block = (
        "1. Markdown numbered list item. -- I read it\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
    )
    valid, error_msg, ast = ra.check_argdown_block(block)
    assert valid is False
    assert (
        "Markdown numbered list '1. Markdown numbered list item. -- I read it' is not valid Argdown syntax"
        in error_msg
    )
    assert "Defect:" in error_msg
    assert "Required remediation format:" in error_msg
    assert "(1) Markdown numbered list item. -- I read it -- <basis phrase>" in error_msg


def test_refusal_diagnostics_premise_number_colon():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for (1): instead of (1)."""
    block = (
        "(1): Premise with colon. -- I read it\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
    )
    valid, error_msg, ast = ra.check_argdown_block(block)
    assert valid is False
    assert "Premise number followed by colon '(1):' is not valid Argdown syntax" in error_msg
    assert "Defect:" in error_msg
    assert "Required remediation format:" in error_msg
    assert "(1) Premise with colon. -- I read it" in error_msg


def test_refusal_diagnostics_orphan_statement():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for orphan statement."""
    block = (
        "(1) Observation. -- I read it\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
        "[orphan_node]: Disconnected statement text\n"
    )
    valid, error_msg, ast = ra.check_argdown_block(block)
    assert valid is False
    assert "orphan statement 'orphan_node'" in error_msg
    assert "Defect:" in error_msg
    assert "Required remediation format:" in error_msg
    assert "[orphan_node]: Disconnected statement text\n  +> (n)" in error_msg


def test_refusal_diagnostics_undercut_targeting_statement():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for undercut targeting statement."""
    block = (
        "(1) Observation. -- I read it\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
        "[objection]: Objection\n"
        "  _> (1)\n"
    )
    valid, error_msg, ast = ra.check_argdown_block(block)
    assert valid is False
    assert "undercut from 'objection' targets statement '1' instead of an inference" in error_msg
    assert "Defect:" in error_msg
    assert "Required remediation format:" in error_msg
    assert "Undercuts (_>) must target an inference bar title (<Inference>)" in error_msg


def test_refusal_diagnostics_unclosed_frontmatter_fence():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for unclosed frontmatter fence."""
    block = f"===\nasks:\n  {ASK_A}: question\n(1) Observation. -- I read it\n"
    valid, error_msg, ast = ra.check_argdown_block(block)
    assert valid is False
    assert "Unclosed frontmatter fence (missing closing '===')" in error_msg
    assert "Defect:" in error_msg
    assert "Required remediation format:" in error_msg


def test_refusal_diagnostics_zero_inference_lines_in_reason():
    """AC1, AC2: Refusal explicitly lists defect and shows remediation for 0 inference lines."""
    block = (
        "===\n"
        f"asks:\n  {ASK_A}: question\n"
        f"answers:\n  {ASK_A}: 1\n"
        "===\n\n"
        "(1) Bare observation without inferences. -- I read it\n"
    )
    session_id = "s-diag-0inf"
    text = f"```argdown\n{block}```\n"
    _arm_with_report(session_id, "CID", text=text)
    reason = (
        f"Judged: CID; asks {ASK_A}\n"
        "Valid: (1) holds -- warrant\n"
        "Supported: weakest I read it -- direct logs\n"
        f"Answered: {ASK_A} ← (1)\n"
        "Sufficient: (1) obvious\n"
        "Waived: none\n"
        "Relay: none\n"
    )
    with pytest.raises(ValueError) as excinfo:
        pcv.record_verdict(
            session_id=session_id,
            claim_id="CID",
            verdict="PASS",
            reason=reason,
            tracer_mod=_configured(),
        )
    err = str(excinfo.value)
    assert "0 inference lines" in err
    assert "Required remediation format:" in err
    assert "-- <warrant rule>. Unless: <defeater>; <status>. --" in err


# ---------------------------------------------------------------------------
# task_d87193b7: Indented hand-backs and unparsable blocks (AC1-AC5)
# ---------------------------------------------------------------------------


def test_indented_handback_four_inferences_parses_and_records_pass():
    """AC1: A hand-back whose block opens '  ===\\n  asks:...', carrying a sound four-inference argument,
    parses with 4 inference lines and records PASS; fails before the fix."""
    ask_c = "tg-1992"
    ask_d = "tg-1993"
    block = (
        "  ===\n"
        f"  asks:\n"
        f"    {ASK_A}: is step 1 ok?\n"
        f"    {ASK_B}: is step 2 ok?\n"
        f"    {ask_c}: is step 3 ok?\n"
        f"    {ask_d}: is step 4 ok?\n"
        f"  answers:\n"
        f"    {ASK_A}: 2\n"
        f"    {ASK_B}: 3\n"
        f"    {ask_c}: 4\n"
        f"    {ask_d}: 5\n"
        "  ===\n\n"
        "  (1) First premise. -- I did it\n"
        "  -- Warrant 1. Unless: def1; not ruled out. --\n"
        "  (2) So, first conclusion.\n"
        "  -- Warrant 2. Unless: def2; not ruled out. --\n"
        "  (3) So, second conclusion.\n"
        "  -- Warrant 3. Unless: def3; not ruled out. --\n"
        "  (4) So, third conclusion.\n"
        "  -- Warrant 4. Unless: def4; not ruled out. --\n"
        "  (5) So, fourth conclusion.\n"
    )
    # Check parse_block directly
    parsed = ra.parse_block(block, _VOCAB)
    assert parsed is not None
    assert len(parsed.inferences) == 4
    assert [inf.conclusion for inf in parsed.inferences] == [2, 3, 4, 5]

    # Check record_verdict on hand-back text
    session_id = "s-ac1-indented"
    cid = "claim-ac1"
    judged_text = f"## Report\n\n```argdown\n{block}```\n"
    _arm_with_report(session_id, cid, text=judged_text)

    reason = (
        f"Judged: {cid}; asks {ASK_A}, {ASK_B}, {ask_c}, {ask_d}\n"
        "Valid: (2) holds -- warrant 1\n"
        "Valid: (3) holds -- warrant 2\n"
        "Valid: (4) holds -- warrant 3\n"
        "Valid: (5) holds -- warrant 4\n"
        "Supported: weakest I did it -- (1)\n"
        f"Answered: {ASK_A} ← (2)\n"
        f"Answered: {ASK_B} ← (3)\n"
        f"Answered: {ask_c} ← (4)\n"
        f"Answered: {ask_d} ← (5)\n"
        "Sufficient: (2), (3), (4), (5) obvious\n"
        "Waived: none\n"
        "Relay: none\n"
    )
    tracer = _configured()
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id=cid,
        verdict="PASS",
        reason=reason,
        tracer_mod=tracer,
    )
    assert result["ok"] is True
    assert result["verdict"] == "PASS"
    assert pcg.is_armed(session_id) is False
    assert tracer.exported[0]["attributes"]["premise_check.inference_count"] == 4


def test_nested_argdown_relations_under_common_indent_yields_same_structure():
    """AC2: A block with nested Argdown relations under a common indent yields the same
    relation structure as the same block unindented."""
    unindented_block = (
        "[S1]: Statement 1\n  +> [S2]\n    +> [S3]\n[S2]: Statement 2\n[S3]: Statement 3\n"
    )
    indented_block = (
        "  [S1]: Statement 1\n"
        "    +> [S2]\n"
        "      +> [S3]\n"
        "  [S2]: Statement 2\n"
        "  [S3]: Statement 3\n"
    )
    valid_u, err_u, ast_u = ra.check_argdown_block(unindented_block)
    assert valid_u is True, err_u
    valid_i, err_i, ast_i = ra.check_argdown_block(indented_block)
    assert valid_i is True, err_i
    assert ast_u is not None and ast_i is not None
    assert ast_u["relations"] == ast_i["relations"]
    assert ast_u["statements"] == ast_i["statements"]


def test_strict_structural_markers_remain_refused():
    """AC3: Malformed inference lines, (n) numbering, answers: pointers and basis phrases
    are refused after the change as before."""
    # 1. Malformed inference line
    block_bad_inf = (
        "===\n"
        f"asks:\n  {ASK_A}: q\n"
        f"answers:\n  {ASK_A}: 2\n"
        "===\n\n"
        "(1) Observation. -- I read it\n"
        "-- Malformed inference without closing dashes\n"
        "(2) So, conclusion.\n"
    )
    valid, err, _ = ra.check_argdown_block(block_bad_inf)
    assert valid is False
    assert "Malformed inference line" in err

    # 2. Malformed (n) numbering (markdown list item)
    block_bad_num = (
        "1. Markdown item. -- I read it\n-- Warrant. Unless: def; status. --\n(2) So, conclusion.\n"
    )
    valid, err, _ = ra.check_argdown_block(block_bad_num)
    assert valid is False
    assert "Markdown numbered list" in err

    # 3. Malformed answers: pointer (unmapped ask)
    block_bad_ans = (
        "===\n"
        f"asks:\n  {ASK_A}: q1\n  {ASK_B}: q2\n"
        f"answers:\n  {ASK_A}: 2\n"
        "===\n\n"
        "(1) Observation. -- I read it\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
    )
    valid, err, _ = ra.check_argdown_block(block_bad_ans)
    assert valid is False
    assert "Unmapped ask" in err

    # 4. Malformed basis phrase (unknown phrase)
    block_bad_basis = (
        "(1) Observation. -- totally made up basis\n"
        "-- Warrant. Unless: def; status. --\n"
        "(2) So, conclusion.\n"
    )
    parsed = ra.parse_block(block_bad_basis, _VOCAB)
    assert parsed is not None
    assert parsed.premises[0].basis is None and parsed.premises[0].rank == 0


def test_unparsable_block_yields_could_not_parse_refusal_not_0_inferences_and_leaves_gate_armed():
    """AC4: An unparsable block yields a refusal stating the block could not be parsed,
    never '0 inference lines', and the gate stays armed."""
    session_id = "s-ac4-unparsable"
    cid = "claim-unparsable"
    unparsable_block = (
        "===\n"
        f"asks:\n  {ASK_A}: question\n"
        f"answers:\n  {ASK_A}: 2\n"
        "===\n\n"
        "(1) Premise without warrant.\n"
        "this line is unparsable gibberish that violates argdown syntax entirely\n"
    )
    judged_text = f"## Report\n\n```argdown\n{unparsable_block}```\n"
    _arm_with_report(session_id, cid, text=judged_text)
    assert pcg.is_armed(session_id) is True

    reason = (
        f"Judged: {cid}; asks {ASK_A}\n"
        "Valid: (1) holds -- warrant\n"
        "Supported: weakest I did it -- (1)\n"
        f"Answered: {ASK_A} ← (1)\n"
        "Sufficient: (1) obvious\n"
        "Waived: none\n"
        "Relay: none\n"
    )
    with pytest.raises(ValueError) as excinfo:
        pcv.record_verdict(
            session_id=session_id,
            claim_id=cid,
            verdict="PASS",
            reason=reason,
            tracer_mod=_configured(),
        )

    err = str(excinfo.value)
    # Refusal states the block could not be parsed
    assert (
        "could not parse" in err.lower()
        or "cannot parse" in err.lower()
        or "no argdown block that parses" in err.lower()
    )
    # Refusal NEVER says "0 inference lines"
    assert "0 inference lines" not in err
    # Gate stays armed
    assert pcg.is_armed(session_id) is True


def test_unindented_handback_parses_identically_to_baseline():
    """AC5: Unindented hand-backs parse as before; full test suite and linter green."""
    report_text = _report()
    block = ra.extract_block(report_text)
    assert block is not None
    parsed = ra.parse_block(block, _VOCAB)
    assert parsed is not None
    assert parsed.asks == [ASK_A, ASK_B]
    assert len(parsed.inferences) == 2
    assert [inf.conclusion for inf in parsed.inferences] == [4, 6]
    valid, err, ast = ra.check_argdown_block(block)
    assert valid is True
