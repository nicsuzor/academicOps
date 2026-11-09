#!/usr/bin/env python3
"""Audit premise-check and hearsay gate telemetry across agent harnesses from Phoenix.

Automates the deterministic data assembly, census aggregation, dossier sampling,
single-session logging, and mechanical confusion-matrix tallying for premise-check
audits across execution harnesses (such as claude-code and agy).

Qualitative evaluation of logical defects, argument validity, and ground-truth
classification is strictly non-mechanical and performed by agents or human auditors
using assembled dossiers.

Commands:
  census:    Aggregate macro population statistics across harnesses over a time window.
  dossier:   Assemble candidate records for agentic qualitative review (Markdown/JSON/annotations template).
  log:       Extract a single session's complete premise-check log and recorder refusals.
  tally:     Deterministically tally agent-evaluated annotations into confusion matrices and comparative tables.

Configuration:
  --base-url or $PHOENIX_MCP_URL (HTTP root, e.g. http://localhost:6006)
  --project  or $PHOENIX_MCP_PROJECT (Phoenix project name or ID, default: academicOps)
  --from-file for offline execution from saved span payloads

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Resolve local sibling imports in session-trace/scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phoenix_token_cost import (  # noqa: E402
    BASE_URL_ENV_VAR,
    PROJECT_ENV_VAR,
    ConfigError,
    _extract_jsonrpc_payload,
    _mcp_headers,
    _mcp_init_session,
    iso,
    parse_tz,
    parse_when,
    resolve_base_url,
    resolve_project,
)

EXIT_OK = 0
EXIT_EMPTY = 1
EXIT_CONFIG = 2

Span = dict[str, Any]


# --- Attribute and Metadata Helpers ------------------------------------------


def attr(span: Span, key: str) -> Any:
    """Retrieve span attribute by dotted path or flat key."""
    attributes = span.get("attributes") or {}
    if key in attributes:
        return attributes[key]
    node: Any = attributes
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def session_of(span: Span) -> str:
    """Session ID of span."""
    return str(
        attr(span, "session.id")
        or span.get("session_id")
        or (span.get("context") or {}).get("session_id")
        or ""
    )


def span_id_of(span: Span) -> str:
    """Span ID hex."""
    return str((span.get("context") or {}).get("span_id") or span.get("span_id") or "")


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def start_time_of(span: Span) -> str:
    raw = span.get("start_time")
    if not raw:
        return ""
    dt = parse_time(raw)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else str(raw)[:19]


def classify_harness(span: Span) -> str:
    """Classify execution harness deterministically from serialized aops.surface attribute.

    Returns 'claude-code', 'agy', or 'unknown'. Does not guess using host or cwd heuristics.
    """
    surface = attr(span, "aops.surface")
    if surface in ("claude-code", "agy"):
        return str(surface)
    if surface == "claude":
        return "claude-code"
    return "unknown"


def parse_premise_check_attr(span: Span) -> dict[str, Any]:
    """Parse premise_check dictionary from nested or flat dot-delimited span attributes."""
    val = attr(span, "premise_check")
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Handle flat dot-prefixed attributes from Phoenix store (e.g. 'premise_check.verdict')
    attributes = span.get("attributes") or {}
    prefix = "premise_check."
    flat_pc: dict[str, Any] = {}
    for k, v in attributes.items():
        if k.startswith(prefix):
            flat_pc[k[len(prefix) :]] = v

    if flat_pc:
        return flat_pc

    return {}


# --- Census Aggregation ------------------------------------------------------


@dataclass
class CensusStats:
    total_verdicts: int = 0
    sessions: set[str] = field(default_factory=set)
    armed_hearsay_spans: int = 0
    armed_sessions: set[str] = field(default_factory=set)
    overrides: int = 0
    refusals: int = 0
    refusal_sessions: set[str] = field(default_factory=set)

    pass_count: int = 0
    waived_format_items: int = 0
    revise_count: int = 0
    revise_format_only: int = 0
    revise_defect_tagged: int = 0
    revise_no_claim: int = 0
    fail_count: int = 0
    fail_defect_tagged: int = 0
    fail_untagged: int = 0

    defect_tags: Counter[str] = field(default_factory=Counter)
    waived_categories: Counter[str] = field(default_factory=Counter)


def aggregate_census(
    spans: list[Span],
    exclude_sessions: set[str] | None = None,
) -> dict[str, CensusStats]:
    """Aggregate premise-check telemetry into claude-code, agy, unknown, and combined stats."""
    exclude = exclude_sessions or set()
    stats: dict[str, CensusStats] = {
        "claude-code": CensusStats(),
        "agy": CensusStats(),
        "unknown": CensusStats(),
        "combined": CensusStats(),
    }

    for span in spans:
        sid = session_of(span)
        if any(sid.startswith(ex) for ex in exclude):
            continue

        harness = classify_harness(span)
        if harness not in ("claude-code", "agy", "unknown"):
            harness = "unknown"

        targets = (stats[harness], stats["combined"])
        name = span.get("name")
        output_val = str(attr(span, "output.value") or "")

        # 1. Hearsay check spans
        if name == "hearsay_check":
            for target in targets:
                target.armed_hearsay_spans += 1
                if sid:
                    target.armed_sessions.add(sid)

        # 2. Premise check override spans
        elif name == "premise_check_override":
            for target in targets:
                target.overrides += 1

        # 3. Refused / unrecorded attempts
        elif (
            span.get("span_kind") == "TOOL"
            and name != "premise_check_verdict"
            and (
                "premise_check_verdict:" in output_val
                or "span_emitted_: false" in output_val
                or "span_emitted__: false" in output_val
            )
        ):
            for target in targets:
                target.refusals += 1
                if sid:
                    target.refusal_sessions.add(sid)

        # 4. Recorded verdict spans
        elif name == "premise_check_verdict":
            pc = parse_premise_check_attr(span)
            verdict = str(pc.get("verdict") or "").upper()
            tags = [t if t.startswith("#") else f"#{t}" for t in pc.get("defect_tags") or [] if t]
            waived = pc.get("waived_items") or []
            no_claim = bool(pc.get("no_claim"))

            for target in targets:
                target.total_verdicts += 1
                if sid:
                    target.sessions.add(sid)

                if verdict == "PASS":
                    target.pass_count += 1
                    target.waived_format_items += len(waived)
                    for w in waived:
                        target.waived_categories[w] += 1
                elif verdict == "REVISE":
                    target.revise_count += 1
                    if tags:
                        target.revise_defect_tagged += 1
                        for t in tags:
                            target.defect_tags[t] += 1
                    elif no_claim:
                        target.revise_no_claim += 1
                    else:
                        target.revise_format_only += 1
                elif verdict == "FAIL":
                    target.fail_count += 1
                    if tags:
                        target.fail_defect_tagged += 1
                        for t in tags:
                            target.defect_tags[t] += 1
                    else:
                        target.fail_untagged += 1

    return stats


def render_census_markdown(stats: dict[str, CensusStats]) -> str:
    """Render census statistics as a GitHub-flavored Markdown comparative table."""
    c = stats["claude-code"]
    a = stats["agy"]
    u = stats.get("unknown", CensusStats())
    comb = stats["combined"]

    def pct(num: int, den: int) -> str:
        if not den:
            return "0.00%"
        return f"{(num / den) * 100:.2f}%"

    def ratio_str(v_a: int | float, v_c: int | float) -> str:
        if v_c == 0:
            return "n/a"
        r = v_a / v_c
        return f"{r:.2f}x"

    has_unknown = bool(
        u.total_verdicts > 0 or u.armed_hearsay_spans > 0 or u.overrides > 0 or u.refusals > 0
    )

    c_sess_len = len(c.sessions) or 1
    a_sess_len = len(a.sessions) or 1
    u_sess_len = len(u.sessions) or 1
    comb_sess_len = len(comb.sessions) or 1

    c_mean_v = c.total_verdicts / c_sess_len
    a_mean_v = a.total_verdicts / a_sess_len
    u_mean_v = u.total_verdicts / u_sess_len
    comb_mean_v = comb.total_verdicts / comb_sess_len

    c_tagged = c.revise_defect_tagged + c.fail_defect_tagged
    a_tagged = a.revise_defect_tagged + a.fail_defect_tagged
    u_tagged = u.revise_defect_tagged + u.fail_defect_tagged
    comb_tagged = comb.revise_defect_tagged + comb.fail_defect_tagged

    if has_unknown:
        lines: list[str] = [
            "| Metric | `claude-code` | `agy` | `unknown` | Combined / Comparative |",
            "| :--- | :--- | :--- | :--- | :--- |",
            f"| **Total Recorded Verdict Spans** | **{c.total_verdicts}** | **{a.total_verdicts}** | **{u.total_verdicts}** | **{comb.total_verdicts}** total (`{ratio_str(a.total_verdicts, c.total_verdicts)}` in `agy`) |",
            f"| **Distinct Sessions with Verdicts** | **{len(c.sessions)}** | **{len(a.sessions)}** | **{len(u.sessions)}** | **{len(comb.sessions)}** (`{ratio_str(len(a.sessions), len(c.sessions))}` in `agy`) |",
            f"| **Mean Verdicts per Session** | **{c_mean_v:.2f}** | **{a_mean_v:.2f}** | **{u_mean_v:.2f}** | **{comb_mean_v:.2f}** |",
            f"| **Armed `hearsay_check` Spans** | **{c.armed_hearsay_spans}** ({len(c.armed_sessions)} sess) | **{a.armed_hearsay_spans}** ({len(a.armed_sessions)} sess) | **{u.armed_hearsay_spans}** ({len(u.armed_sessions)} sess) | **{comb.armed_hearsay_spans}** spans |",
            f"| **Administrative Overrides (`premise_check_override`)** | **{c.overrides}** | **{a.overrides}** | **{u.overrides}** | **{comb.overrides}** overrides |",
            f"| **Traced Pre-Verdict Recorder Refusals** | **{c.refusals}** ({len(c.refusal_sessions)} sess) | **{a.refusals}** ({len(a.refusal_sessions)} sess) | **{u.refusals}** ({len(u.refusal_sessions)} sess) | **{comb.refusals}** refusals |",
            f"| **`PASS` Verdicts** | **{c.pass_count} ({pct(c.pass_count, c.total_verdicts)})** | **{a.pass_count} ({pct(a.pass_count, a.total_verdicts)})** | **{u.pass_count} ({pct(u.pass_count, u.total_verdicts)})** | **{comb.pass_count} ({pct(comb.pass_count, comb.total_verdicts)})** |",
            f"| **Waived Format Items on `PASS`** | **{c.waived_format_items}** | **{a.waived_format_items}** | **{u.waived_format_items}** | **{comb.waived_format_items}** waived format slips |",
            f"| **`REVISE` Verdicts** | **{c.revise_count} ({pct(c.revise_count, c.total_verdicts)})** | **{a.revise_count} ({pct(a.revise_count, a.total_verdicts)})** | **{u.revise_count} ({pct(u.revise_count, u.total_verdicts)})** | **{comb.revise_count} ({pct(comb.revise_count, comb.total_verdicts)})** |",
            f"| — *Format-Only `REVISE`* | **{c.revise_format_only}** ({pct(c.revise_format_only, c.revise_count)}) | **{a.revise_format_only}** ({pct(a.revise_format_only, a.revise_count)}) | **{u.revise_format_only}** ({pct(u.revise_format_only, u.revise_count)}) | **{comb.revise_format_only}** ({pct(comb.revise_format_only, comb.revise_count)}) |",
            f"| — *Defect-Tagged `REVISE`* | **{c.revise_defect_tagged}** ({pct(c.revise_defect_tagged, c.revise_count)}) | **{a.revise_defect_tagged}** ({pct(a.revise_defect_tagged, a.revise_count)}) | **{u.revise_defect_tagged}** ({pct(u.revise_defect_tagged, u.revise_count)}) | **{comb.revise_defect_tagged}** ({pct(comb.revise_defect_tagged, comb.revise_count)}) |",
            f"| — *`no_claim` `REVISE`* | **{c.revise_no_claim}** ({pct(c.revise_no_claim, c.revise_count)}) | **{a.revise_no_claim}** ({pct(a.revise_no_claim, a.revise_count)}) | **{u.revise_no_claim}** ({pct(u.revise_no_claim, u.revise_count)}) | **{comb.revise_no_claim}** ({pct(comb.revise_no_claim, comb.revise_count)}) |",
            f"| **`FAIL` Verdicts** | **{c.fail_count} ({pct(c.fail_count, c.total_verdicts)})** | **{a.fail_count} ({pct(a.fail_count, a.total_verdicts)})** | **{u.fail_count} ({pct(u.fail_count, u.total_verdicts)})** | **{comb.fail_count} ({pct(comb.fail_count, comb.total_verdicts)})** |",
            f"| **Total Defect-Tagged Spans (`REVISE` + `FAIL`)** | **{c_tagged} ({pct(c_tagged, c.total_verdicts)})** | **{a_tagged} ({pct(a_tagged, a.total_verdicts)})** | **{u_tagged} ({pct(u_tagged, u.total_verdicts)})** | **{comb_tagged} ({pct(comb_tagged, comb.total_verdicts)})** gross |",
        ]

        all_tags = sorted(
            set(c.defect_tags.keys()) | set(a.defect_tags.keys()) | set(u.defect_tags.keys())
        )
        if all_tags:
            lines.extend(
                [
                    "",
                    "### Defect Tags Distribution",
                    "",
                    "| Defect Tag | `claude-code` | `agy` | `unknown` | Combined |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for tag in all_tags:
                lines.append(
                    f"| `{tag}` | {c.defect_tags[tag]} | {a.defect_tags[tag]} | {u.defect_tags[tag]} | {comb.defect_tags[tag]} |"
                )
    else:
        lines = [
            "| Metric | `claude-code` | `agy` | Combined / Comparative |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Total Recorded Verdict Spans** | **{c.total_verdicts}** | **{a.total_verdicts}** | **{comb.total_verdicts}** total (`{ratio_str(a.total_verdicts, c.total_verdicts)}` in `agy`) |",
            f"| **Distinct Sessions with Verdicts** | **{len(c.sessions)}** | **{len(a.sessions)}** | **{len(comb.sessions)}** (`{ratio_str(len(a.sessions), len(c.sessions))}` in `agy`) |",
            f"| **Mean Verdicts per Session** | **{c_mean_v:.2f}** | **{a_mean_v:.2f}** | **{comb_mean_v:.2f}** |",
            f"| **Armed `hearsay_check` Spans** | **{c.armed_hearsay_spans}** ({len(c.armed_sessions)} sess) | **{a.armed_hearsay_spans}** ({len(a.armed_sessions)} sess) | **{comb.armed_hearsay_spans}** spans |",
            f"| **Administrative Overrides (`premise_check_override`)** | **{c.overrides}** | **{a.overrides}** | **{comb.overrides}** overrides |",
            f"| **Traced Pre-Verdict Recorder Refusals** | **{c.refusals}** ({len(c.refusal_sessions)} sess) | **{a.refusals}** ({len(a.refusal_sessions)} sess) | **{comb.refusals}** refusals |",
            f"| **`PASS` Verdicts** | **{c.pass_count} ({pct(c.pass_count, c.total_verdicts)})** | **{a.pass_count} ({pct(a.pass_count, a.total_verdicts)})** | **{comb.pass_count} ({pct(comb.pass_count, comb.total_verdicts)})** |",
            f"| **Waived Format Items on `PASS`** | **{c.waived_format_items}** | **{a.waived_format_items}** | **{comb.waived_format_items}** waived format slips |",
            f"| **`REVISE` Verdicts** | **{c.revise_count} ({pct(c.revise_count, c.total_verdicts)})** | **{a.revise_count} ({pct(a.revise_count, a.total_verdicts)})** | **{comb.revise_count} ({pct(comb.revise_count, comb.total_verdicts)})** |",
            f"| — *Format-Only `REVISE`* | **{c.revise_format_only}** ({pct(c.revise_format_only, c.revise_count)}) | **{a.revise_format_only}** ({pct(a.revise_format_only, a.revise_count)}) | **{comb.revise_format_only}** ({pct(comb.revise_format_only, comb.revise_count)}) |",
            f"| — *Defect-Tagged `REVISE`* | **{c.revise_defect_tagged}** ({pct(c.revise_defect_tagged, c.revise_count)}) | **{a.revise_defect_tagged}** ({pct(a.revise_defect_tagged, a.revise_count)}) | **{comb.revise_defect_tagged}** ({pct(comb.revise_defect_tagged, comb.revise_count)}) |",
            f"| — *`no_claim` `REVISE`* | **{c.revise_no_claim}** ({pct(c.revise_no_claim, c.revise_count)}) | **{a.revise_no_claim}** ({pct(a.revise_no_claim, a.revise_count)}) | **{comb.revise_no_claim}** ({pct(comb.revise_no_claim, comb.revise_count)}) |",
            f"| **`FAIL` Verdicts** | **{c.fail_count} ({pct(c.fail_count, c.total_verdicts)})** | **{a.fail_count} ({pct(a.fail_count, a.total_verdicts)})** | **{comb.fail_count} ({pct(comb.fail_count, comb.total_verdicts)})** |",
            f"| **Total Defect-Tagged Spans (`REVISE` + `FAIL`)** | **{c_tagged} ({pct(c_tagged, c.total_verdicts)})** | **{a_tagged} ({pct(a_tagged, a.total_verdicts)})** | **{comb_tagged} ({pct(comb_tagged, comb.total_verdicts)})** gross |",
        ]

        all_tags = sorted(set(c.defect_tags.keys()) | set(a.defect_tags.keys()))
        if all_tags:
            lines.extend(
                [
                    "",
                    "### Defect Tags Distribution",
                    "",
                    "| Defect Tag | `claude-code` | `agy` | Combined |",
                    "| :--- | :--- | :--- | :--- |",
                ]
            )
            for tag in all_tags:
                lines.append(
                    f"| `{tag}` | {c.defect_tags[tag]} | {a.defect_tags[tag]} | {comb.defect_tags[tag]} |"
                )

    return "\n".join(lines)


# --- Candidate Dossier Assembly ----------------------------------------------


@dataclass
class DossierRecord:
    span_id: str
    session_id: str
    start_time: str
    harness: str
    host: str
    cwd: str
    verdict: str
    verification_id: str
    claim_id: str
    ask_ids: list[str]
    defect_tags: list[str]
    waived_items: list[str]
    weakest_basis: str
    has_block: bool
    no_claim: bool
    judged_text_sha256: str
    reason_text: str


def extract_dossier_records(
    spans: list[Span],
    harness_filter: str = "all",
    verdict_filter: str = "all",
    tagged_only: bool = False,
    exclude_sessions: set[str] | None = None,
    limit: int | None = None,
) -> list[DossierRecord]:
    """Extract structured dossier records for agentic qualitative review."""
    exclude = exclude_sessions or set()
    records: list[DossierRecord] = []

    for span in spans:
        if span.get("name") != "premise_check_verdict":
            continue

        sid = session_of(span)
        if any(sid.startswith(ex) for ex in exclude):
            continue

        harness = classify_harness(span)
        if harness_filter != "all" and harness != harness_filter:
            continue

        pc = parse_premise_check_attr(span)
        verdict = str(pc.get("verdict") or "").upper()
        if verdict_filter != "all" and verdict != verdict_filter.upper():
            continue

        tags = [t if t.startswith("#") else f"#{t}" for t in pc.get("defect_tags") or [] if t]
        if tagged_only and not tags:
            continue

        records.append(
            DossierRecord(
                span_id=span_id_of(span),
                session_id=sid,
                start_time=start_time_of(span),
                harness=harness,
                host=str(attr(span, "host.name") or ""),
                cwd=str(attr(span, "cwd") or ""),
                verdict=verdict,
                verification_id=str(pc.get("verification_id") or ""),
                claim_id=str(pc.get("claim_id") or ""),
                ask_ids=[str(a) for a in pc.get("ask_ids") or []],
                defect_tags=tags,
                waived_items=[str(w) for w in pc.get("waived_items") or []],
                weakest_basis=str(pc.get("weakest_basis") or ""),
                has_block=bool(pc.get("has_block")),
                no_claim=bool(pc.get("no_claim")),
                judged_text_sha256=str(pc.get("judged_text_sha256") or ""),
                reason_text=str(pc.get("reason_text") or ""),
            )
        )

        if limit and len(records) >= limit:
            break

    return records


def render_dossier_markdown(records: list[DossierRecord]) -> str:
    """Render dossier records for human or agent qualitative inspection."""
    out: list[str] = [
        f"# Premise-Check Candidate Review Dossier ({len(records)} records)",
        "",
        "Extracted for qualitative evaluation of logical defects, argument validity,",
        "and ground-truth classification. Read each record's claim, ask, basis, and reason",
        "to judge whether rejections represent genuine substantive catches or disguised syntax/plumbing,",
        "and whether PASS verdicts represent rigorous verification or rubber stamps.",
        "",
    ]

    for i, r in enumerate(records, 1):
        out.append(f"### {i}. {r.verdict} · `{r.claim_id or 'no-claim-id'}` ({r.harness})")
        out.append(f"- **Span ID:** `{r.span_id}`")
        out.append(f"- **Session ID:** `{r.session_id}`")
        out.append(f"- **Timestamp:** {r.start_time}")
        out.append(f"- **Verification ID:** `{r.verification_id or '-'}`")
        out.append(f"- **Ask IDs:** {', '.join(f'`{a}`' for a in r.ask_ids) or '-'}")
        out.append(f"- **Defect Tags:** {', '.join(f'`{t}`' for t in r.defect_tags) or '-'}")
        out.append(f"- **Waived Items:** {', '.join(f'`{w}`' for w in r.waived_items) or '-'}")
        out.append(f"- **Weakest Basis:** {r.weakest_basis or '-'}")
        out.append(f"- **Block Parsed:** {'yes' if r.has_block else 'no'}")
        out.append(f"- **Judged Text SHA256:** `{r.judged_text_sha256 or '-'}`")
        out.append("")
        out.append("```text")
        out.append(r.reason_text.strip() or "(no reason text recorded)")
        out.append("```")
        out.append("")

    return "\n".join(out)


def render_dossier_annotations_template(records: list[DossierRecord]) -> dict[str, Any]:
    """Generate empty annotations schema for agentic qualitative classification."""
    evals: list[dict[str, Any]] = []
    for r in records:
        evals.append(
            {
                "span_id": r.span_id,
                "session_id": r.session_id,
                "harness": r.harness,
                "verdict": r.verdict,
                "recorded_defect_tags": r.defect_tags,
                "claim_id": r.claim_id,
                "evaluation": {
                    # Valid categories to be evaluated agentically:
                    # "substantive": genuine catch of logical, epistemic, or rule defect
                    # "structural_bar": missing inference bar (-- ... --) or orphan conclusion
                    # "format_plumbing": disguised formatting, frontmatter parse slip, or un-nulled brief
                    # "synthetic_test": test suite / verification execution rather than operational session
                    "defect_classification": None,
                    "is_substantive": None,  # true/false
                    "is_rubber_stamp": None,  # for PASS: true if accepted secondary report without primary check
                    "is_synthetic_test": None,  # true if qualitative evaluator identifies test fixture
                    "notes": "",
                },
            }
        )

    return {
        "version": "1.0",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_records": len(records),
        "evaluations": evals,
    }


# --- Single-Session Premise-Check Log ----------------------------------------


def render_session_log(
    session_id: str,
    spans: list[Span],
) -> str:
    """Render structured premise-check log table and recorder refusals for a single session."""
    target_spans = [s for s in spans if session_of(s).startswith(session_id)]
    v_spans: list[Span] = [s for s in target_spans if s.get("name") == "premise_check_verdict"]
    v_spans.sort(key=lambda s: str(s.get("start_time") or ""))

    r_spans: list[Span] = []
    for s in target_spans:
        if s.get("span_kind") != "TOOL" or s.get("name") == "premise_check_verdict":
            continue
        out_val = str(attr(s, "output.value") or "")
        if (
            "premise_check_verdict:" in out_val
            or "span_emitted_: false" in out_val
            or "span_emitted__: false" in out_val
        ):
            r_spans.append(s)
    r_spans.sort(key=lambda s: str(s.get("start_time") or ""))

    counts: Counter[str] = Counter()
    rows: list[tuple[str, str, str, str, dict[str, Any]]] = []
    for s in v_spans:
        pc = parse_premise_check_attr(s)
        verdict = str(pc.get("verdict") or "?")
        counts[verdict] += 1
        rows.append(
            (
                span_id_of(s),
                start_time_of(s),
                str(attr(s, "host.name") or ""),
                str(attr(s, "cwd") or ""),
                pc,
            )
        )

    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"
    places = sorted({f"{r[2]}:{r[3]}" for r in rows if r[2] or r[3]})

    out: list[str] = [
        f"# Premise-check log: session `{session_id}`",
        "",
        "Assembled mechanically from Phoenix: every `premise_check_verdict` span in the session,",
        "and every traced tool output that shows the recorder refusing or failing. Reasons are verbatim.",
        "",
        f"- **Recorded verdicts:** {len(rows)} ({summary})",
        f"- **Refused or unrecorded attempts:** {len(r_spans)}",
    ]
    if rows:
        out.append(f"- **Window:** {rows[0][1]} to {rows[-1][1]}")
    if places:
        out.append(f"- **Recorded on (host:cwd):** {', '.join(f'`{p}`' for p in places)}")

    out.extend(
        [
            "",
            "## Verdicts",
            "",
            "| # | Time (UTC) | Verdict | Verification | Claim | Asks | Weakest basis | Defect tags | Waived | Block parsed | Span |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    for i, (span, ts, _host, _cwd, p) in enumerate(rows, 1):
        asks = ", ".join(p.get("ask_ids") or []) or "-"
        dtags = ", ".join(p.get("defect_tags") or []) or "-"
        witems = ", ".join(p.get("waived_items") or []) or "-"
        has_b = "yes" if p.get("has_block") else "no"
        time_part = ts[11:] if len(ts) >= 19 else ts
        out.append(
            f"| {i} | {time_part} | {p.get('verdict', '?')} | `{p.get('verification_id', '')}` | `{p.get('claim_id', '')}` | {asks} | {p.get('weakest_basis') or '-'} | {dtags} | {witems} | {has_b} | `{span}` |"
        )

    for i, (span, ts, _host, _cwd, p) in enumerate(rows, 1):
        verdict = p.get("verdict", "?")
        verif = p.get("verification_id", "")
        claim = p.get("claim_id", "")
        sha = p.get("judged_text_sha256", "")
        no_claim_str = " · no claim" if p.get("no_claim") else ""
        out.extend(
            [
                "",
                f"### {i}. {verdict} · `{verif}` on `{claim}`",
                "",
                f"{ts} · span `{span}` · judged text sha256 `{sha}`{no_claim_str}",
                "",
                "```text",
                (p.get("reason_text") or "").strip(),
                "```",
            ]
        )

    out.extend(["", "## Refused or unrecorded attempts", ""])
    if not r_spans:
        out.append("None traced.")
    else:
        for s in r_spans:
            s_name = s.get("name") or "tool"
            s_span = span_id_of(s)
            s_ts = start_time_of(s)
            raw_out = str(attr(s, "output.value") or "")
            try:
                parsed_out = json.loads(raw_out)
                if isinstance(parsed_out, dict):
                    raw_out = "\n".join(str(parsed_out.get(k) or "") for k in ("stdout", "stderr"))
            except Exception:
                pass
            keep: list[str] = []
            on = False
            for line in raw_out.splitlines():
                if "premise_check_verdict:" in line or re.search(r"span_emitted\W+false", line):
                    keep.append(line)
                    on = True
                elif on and line.startswith("- "):
                    keep.append(line)
                else:
                    on = False
            out.extend(
                [
                    f"### {s_ts} · `{s_name}` span `{s_span}`",
                    "",
                    "```text",
                    "\n".join(keep[:40]) or "(refusal output)",
                    "```",
                    "",
                ]
            )

    out.extend(
        [
            "## Limits",
            "",
            "- The judged report itself is not in this log. Each verdict names it by claim id and sha256.",
            "- Subagents share session id, so the log does not partition agents within a single session tree.",
            "- Refusals are recorded only when tool output was captured in Phoenix.",
        ]
    )
    return "\n".join(out) + "\n"


# --- Mechanical Tally and Confusion Matrix -----------------------------------


@dataclass
class TallyMetrics:
    total_evaluations: int = 0
    operational_evaluations: int = 0
    synthetic_test_evaluations: int = 0

    bucket_1_substantive: int = 0
    bucket_2_structural_bar: int = 0
    bucket_3_format_plumbing: int = 0

    total_rejections: int = 0
    substantive_rejections: int = 0

    total_passes: int = 0
    rigorous_passes: int = 0
    rubber_stamp_passes: int = 0


def tally_annotations(annotations_payload: dict[str, Any]) -> dict[str, TallyMetrics]:
    """Compute confusion matrices and accuracy metrics from agent-evaluated annotations.

    Fails fast (raising ConfigError) if an evaluation entry is missing required fields or carries
    unrecognized verdicts or classifications, preventing silent fallback misclassification.
    """
    evals = annotations_payload.get("evaluations", [])
    metrics: dict[str, TallyMetrics] = {
        "claude-code": TallyMetrics(),
        "agy": TallyMetrics(),
        "unknown": TallyMetrics(),
        "combined": TallyMetrics(),
    }

    for item in evals:
        entry_id = str(item.get("claim_id") or item.get("span_id") or "unknown-entry")
        harness = item.get("harness")
        if harness not in ("claude-code", "agy", "unknown"):
            harness = "unknown"

        ev = item.get("evaluation")
        if not isinstance(ev, dict):
            raise ConfigError(
                f"Entry '{entry_id}' is missing required 'evaluation' object in annotations"
            )

        raw_verdict = item.get("verdict")
        verdict = str(raw_verdict or "").upper()
        if verdict not in ("PASS", "REVISE", "FAIL"):
            raise ConfigError(f"Entry '{entry_id}' has unrecognized verdict: {raw_verdict!r}")

        is_synth = bool(item.get("is_synthetic_test") or ev.get("is_synthetic_test"))
        cat = str(ev.get("defect_classification") or "").strip().lower()
        is_sub = ev.get("is_substantive")
        is_rubber = ev.get("is_rubber_stamp")

        targets = (metrics[harness], metrics["combined"])

        for t in targets:
            t.total_evaluations += 1
            if is_synth or cat == "synthetic_test":
                t.synthetic_test_evaluations += 1
                continue
            t.operational_evaluations += 1

            if verdict in ("REVISE", "FAIL"):
                t.total_rejections += 1

                # Classify into 3 buckets without silent fallbacks
                if cat == "substantive" or (is_sub is True and not cat):
                    t.bucket_1_substantive += 1
                    t.substantive_rejections += 1
                elif cat == "structural_bar":
                    t.bucket_2_structural_bar += 1
                elif cat in ("format_plumbing", "format", "plumbing") or (
                    is_sub is False and not cat
                ):
                    t.bucket_3_format_plumbing += 1
                elif is_sub is True:
                    t.bucket_1_substantive += 1
                    t.substantive_rejections += 1
                else:
                    raise ConfigError(
                        f"Entry '{entry_id}' has missing or unrecognized defect classification for {verdict}: "
                        f"defect_classification={ev.get('defect_classification')!r}, is_substantive={is_sub!r}"
                    )

            elif verdict == "PASS":
                t.total_passes += 1
                if is_rubber is True:
                    t.rubber_stamp_passes += 1
                elif is_rubber is False:
                    t.rigorous_passes += 1
                else:
                    raise ConfigError(
                        f"Entry '{entry_id}' has missing or non-boolean is_rubber_stamp for PASS: "
                        f"is_rubber_stamp={is_rubber!r}"
                    )

    return metrics


def render_tally_markdown(metrics: dict[str, TallyMetrics]) -> str:
    """Render tally results as Markdown tables matching audit standards."""
    c = metrics["claude-code"]
    a = metrics["agy"]
    u = metrics.get("unknown", TallyMetrics())
    comb = metrics["combined"]

    def pct(num: int, den: int) -> str:
        if not den:
            return "0.00%"
        return f"{(num / den) * 100:.2f}%"

    has_unknown = u.total_evaluations > 0

    if has_unknown:
        out: list[str] = [
            "## Defect-Tagged Rejections Classification Audit",
            "",
            "| Defect-Tag Classification Bucket | `claude-code` | `agy` | `unknown` | Combined / Comparative |",
            "| :--- | :--- | :--- | :--- | :--- |",
            f"| **Gross Evaluations** | **{c.total_evaluations}** | **{a.total_evaluations}** | **{u.total_evaluations}** | **{comb.total_evaluations}** |",
            f"| **Synthetic Test / CLI Harnesses** | **{c.synthetic_test_evaluations}** ({pct(c.synthetic_test_evaluations, c.total_evaluations)}) | **{a.synthetic_test_evaluations}** ({pct(a.synthetic_test_evaluations, a.total_evaluations)}) | **{u.synthetic_test_evaluations}** ({pct(u.synthetic_test_evaluations, u.total_evaluations)}) | **{comb.synthetic_test_evaluations}** excluded |",
            f"| **Bucket 1: Substantive Logical, Epistemic, & Rule Catches** | **{c.bucket_1_substantive} / {c.total_rejections} ({pct(c.bucket_1_substantive, c.total_rejections)})** | **{a.bucket_1_substantive} / {a.total_rejections} ({pct(a.bucket_1_substantive, a.total_rejections)})** | **{u.bucket_1_substantive} / {u.total_rejections} ({pct(u.bucket_1_substantive, u.total_rejections)})** | **{comb.bucket_1_substantive} / {comb.total_rejections} ({pct(comb.bucket_1_substantive, comb.total_rejections)})** |",
            f"| **Bucket 2: Structural Missing-Warrant Bar / Orphan Conclusions** | **{c.bucket_2_structural_bar} / {c.total_rejections} ({pct(c.bucket_2_structural_bar, c.total_rejections)})** | **{a.bucket_2_structural_bar} / {a.total_rejections} ({pct(a.bucket_2_structural_bar, a.total_rejections)})** | **{u.bucket_2_structural_bar} / {u.total_rejections} ({pct(u.bucket_2_structural_bar, u.total_rejections)})** | **{comb.bucket_2_structural_bar} / {comb.total_rejections} ({pct(comb.bucket_2_structural_bar, comb.total_rejections)})** |",
            f"| **Bucket 3: Disguised Mechanical, Parser, & Plumbing Rejections** | **{c.bucket_3_format_plumbing} / {c.total_rejections} ({pct(c.bucket_3_format_plumbing, c.total_rejections)})** | **{a.bucket_3_format_plumbing} / {a.total_rejections} ({pct(a.bucket_3_format_plumbing, a.total_rejections)})** | **{u.bucket_3_format_plumbing} / {u.total_rejections} ({pct(u.bucket_3_format_plumbing, u.total_rejections)})** | **{comb.bucket_3_format_plumbing} / {comb.total_rejections} ({pct(comb.bucket_3_format_plumbing, comb.total_rejections)})** |",
            "",
            "## Substantive PASS Rigor vs Rubber-Stamp False Negatives",
            "",
            "| Metric | `claude-code` | `agy` | `unknown` | Combined / Comparative |",
            "| :--- | :--- | :--- | :--- | :--- |",
            f"| **Total PASS Verdicts Evaluated** | **{c.total_passes}** | **{a.total_passes}** | **{u.total_passes}** | **{comb.total_passes}** |",
            f"| **Rigorous Primary Verification (True Negative)** | **{c.rigorous_passes} ({pct(c.rigorous_passes, c.total_passes)})** | **{a.rigorous_passes} ({pct(a.rigorous_passes, a.total_passes)})** | **{u.rigorous_passes} ({pct(u.rigorous_passes, u.total_passes)})** | **{comb.rigorous_passes} ({pct(comb.rigorous_passes, comb.total_passes)})** |",
            f"| **False-Negative Rubber Stamps** | **{c.rubber_stamp_passes} ({pct(c.rubber_stamp_passes, c.total_passes)})** | **{a.rubber_stamp_passes} ({pct(a.rubber_stamp_passes, a.total_passes)})** | **{u.rubber_stamp_passes} ({pct(u.rubber_stamp_passes, u.total_passes)})** | **{comb.rubber_stamp_passes} ({pct(comb.rubber_stamp_passes, comb.total_passes)})** |",
        ]
    else:
        out = [
            "## Defect-Tagged Rejections Classification Audit",
            "",
            "| Defect-Tag Classification Bucket | `claude-code` | `agy` | Combined / Comparative |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Gross Evaluations** | **{c.total_evaluations}** | **{a.total_evaluations}** | **{comb.total_evaluations}** |",
            f"| **Synthetic Test / CLI Harnesses** | **{c.synthetic_test_evaluations}** ({pct(c.synthetic_test_evaluations, c.total_evaluations)}) | **{a.synthetic_test_evaluations}** ({pct(a.synthetic_test_evaluations, a.total_evaluations)}) | **{comb.synthetic_test_evaluations}** excluded |",
            f"| **Bucket 1: Substantive Logical, Epistemic, & Rule Catches** | **{c.bucket_1_substantive} / {c.total_rejections} ({pct(c.bucket_1_substantive, c.total_rejections)})** | **{a.bucket_1_substantive} / {a.total_rejections} ({pct(a.bucket_1_substantive, a.total_rejections)})** | **{comb.bucket_1_substantive} / {comb.total_rejections} ({pct(comb.bucket_1_substantive, comb.total_rejections)})** |",
            f"| **Bucket 2: Structural Missing-Warrant Bar / Orphan Conclusions** | **{c.bucket_2_structural_bar} / {c.total_rejections} ({pct(c.bucket_2_structural_bar, c.total_rejections)})** | **{a.bucket_2_structural_bar} / {a.total_rejections} ({pct(a.bucket_2_structural_bar, a.total_rejections)})** | **{comb.bucket_2_structural_bar} / {comb.total_rejections} ({pct(comb.bucket_2_structural_bar, comb.total_rejections)})** |",
            f"| **Bucket 3: Disguised Mechanical, Parser, & Plumbing Rejections** | **{c.bucket_3_format_plumbing} / {c.total_rejections} ({pct(c.bucket_3_format_plumbing, c.total_rejections)})** | **{a.bucket_3_format_plumbing} / {a.total_rejections} ({pct(a.bucket_3_format_plumbing, a.total_rejections)})** | **{comb.bucket_3_format_plumbing} / {comb.total_rejections} ({pct(comb.bucket_3_format_plumbing, comb.total_rejections)})** |",
            "",
            "## Substantive PASS Rigor vs Rubber-Stamp False Negatives",
            "",
            "| Metric | `claude-code` | `agy` | Combined / Comparative |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Total PASS Verdicts Evaluated** | **{c.total_passes}** | **{a.total_passes}** | **{comb.total_passes}** |",
            f"| **Rigorous Primary Verification (True Negative)** | **{c.rigorous_passes} ({pct(c.rigorous_passes, c.total_passes)})** | **{a.rigorous_passes} ({pct(a.rigorous_passes, a.total_passes)})** | **{comb.rigorous_passes} ({pct(comb.rigorous_passes, comb.total_passes)})** |",
            f"| **False-Negative Rubber Stamps** | **{c.rubber_stamp_passes} ({pct(c.rubber_stamp_passes, c.total_passes)})** | **{a.rubber_stamp_passes} ({pct(a.rubber_stamp_passes, a.total_passes)})** | **{comb.rubber_stamp_passes} ({pct(comb.rubber_stamp_passes, comb.total_passes)})** |",
        ]

    return "\n".join(out)


# --- CLI Routing -------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common connection options
    conn = argparse.ArgumentParser(add_help=False)
    conn.add_argument("--base-url", help=f"Phoenix HTTP root or ${BASE_URL_ENV_VAR}")
    conn.add_argument("--project", help=f"Phoenix project or ${PROJECT_ENV_VAR}")
    conn.add_argument("--from-file", type=Path, help="Load spans from saved JSON file")
    conn.add_argument("--save-spans", type=Path, help="Save fetched spans to JSON file")
    conn.add_argument(
        "--days",
        type=int,
        default=7,
        help="Window size in days (default: 7, overridden by --since)",
    )
    conn.add_argument("--since", help="Start time (ISO or YYYY-MM-DD [HH:MM])")
    conn.add_argument("--until", help="End time (default: now)")
    conn.add_argument("--tz", default="+00:00", help="Timezone offset (default: +00:00)")
    conn.add_argument("--session", help="Filter by session ID prefix")
    conn.add_argument(
        "--exclude-sessions",
        help="Comma-separated session prefixes to exclude (e.g. audit family)",
    )

    # 1. Census
    p_census = subparsers.add_parser(
        "census", parents=[conn], help="Macro population census across harnesses"
    )
    p_census.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")

    # 2. Dossier
    p_dossier = subparsers.add_parser(
        "dossier", parents=[conn], help="Extract review dossier for agentic evaluation"
    )
    p_dossier.add_argument(
        "--harness",
        choices=["all", "claude-code", "agy"],
        default="all",
        help="Filter by harness",
    )
    p_dossier.add_argument(
        "--verdict",
        choices=["all", "PASS", "REVISE", "FAIL"],
        default="all",
        help="Filter by verdict",
    )
    p_dossier.add_argument(
        "--tagged-only", action="store_true", help="Include only defect-tagged spans"
    )
    p_dossier.add_argument(
        "--sample", "--limit", type=int, dest="sample", help="Max records to include"
    )
    p_dossier.add_argument(
        "--format",
        choices=["markdown", "json", "annotations"],
        default="markdown",
        help="Output format",
    )
    p_dossier.add_argument("--out", type=Path, help="Write output to file")

    # 3. Log
    p_log = subparsers.add_parser("log", parents=[conn], help="Single-session premise-check log")
    p_log.add_argument("--out", type=Path, help="Write output to file")

    # 4. Tally
    p_tally = subparsers.add_parser(
        "tally", help="Tally agent-evaluated annotations into confusion matrix"
    )
    p_tally.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="Path to agent-evaluated annotations JSON",
    )
    p_tally.add_argument("--json", action="store_true", help="Output JSON")

    return parser


def query_phoenix_sql(mcp_url: str, session_id: str, sql: str) -> dict[str, Any]:
    """Execute read-only SQL via Phoenix MCP executeSql tool."""
    code = f'return await call_tool("executeSql", {{"sql": {json.dumps(sql)}}})'
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "phoenix_execute", "arguments": {"code": code}},
    }
    req = urllib.request.Request(
        mcp_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_mcp_headers(session_id),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise ConfigError(f"HTTP {exc.code} from {mcp_url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ConfigError(f"cannot reach {mcp_url}: {exc.reason}") from exc

    rpc = _extract_jsonrpc_payload(raw, mcp_url)
    if "error" in rpc:
        raise ConfigError(f"Phoenix MCP error: {rpc['error']}")
    result = rpc.get("result") or {}
    content = result.get("content") or []
    text = "".join(item.get("text", "") for item in content if isinstance(item, dict)).strip()
    if result.get("isError"):
        raise ConfigError(f"Phoenix executeSql failed: {text}")
    try:
        data = json.loads(text) if text else {}
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Phoenix executeSql returned non-JSON: {text[:400]}") from exc

    if "error" in data:
        err = data["error"]
        raise ConfigError(f"Phoenix SQL execution error: {err}")
    return data


def page_spans_sql(
    base_url: str,
    project_name: str,
    since_iso: str,
    until_iso: str,
    session_id_filter: str | None = None,
) -> list[Span]:
    """Exhaustively page premise-check and hearsay telemetry via executeSql keyset pagination.

    Pages to complete exhaustion using `s.id > last_id ORDER BY s.id ASC`. Halts loudly
    if `row_count_is_partial` remains True on an empty page or if a query fails.
    """
    mcp_session_id = _mcp_init_session(base_url)
    last_id = 0
    all_spans: list[Span] = []

    session_clause = ""
    if session_id_filter:
        safe_sid = session_id_filter.replace("'", "''")
        session_clause = (
            f"AND ((s.attributes ->> '$.session.id') LIKE '{safe_sid}%' "
            f"OR (s.attributes ->> '$.session_id') LIKE '{safe_sid}%') "
        )

    while True:
        sql = f"""
        SELECT s.id, s.span_id, t.trace_id, s.name, s.start_time, s.span_kind, s.attributes
        FROM spans s
        JOIN traces t ON t.id = s.trace_rowid
        JOIN projects p ON p.id = t.project_rowid
        WHERE p.name = '{project_name.replace("'", "''")}'
          AND s.start_time >= '{since_iso}'
          AND s.start_time <= '{until_iso}'
          {session_clause}
          AND (
            s.name IN ('premise_check_verdict', 'hearsay_check', 'premise_check_override')
            OR (
              s.span_kind = 'TOOL' AND s.name != 'premise_check_verdict' AND (
                (s.attributes ->> '$.output.value') LIKE '%premise_check_verdict:%'
                OR (s.attributes ->> '$.output.value') LIKE '%span_emitted%false%'
              )
            )
          )
          AND s.id > {last_id}
        ORDER BY s.id ASC
        """
        data = query_phoenix_sql(base_url, mcp_session_id, sql)
        rows = data.get("rows", [])
        is_partial = bool(data.get("row_count_is_partial"))

        if not rows:
            if is_partial:
                raise ConfigError(
                    f"Phoenix query truncated unexpectedly: row_count_is_partial is True but 0 rows returned at id > {last_id}"
                )
            break

        for r in rows:
            attrs = json.loads(r[6]) if isinstance(r[6], str) else (r[6] or {})
            span: Span = {
                "name": r[3],
                "span_kind": r[5],
                "start_time": r[4],
                "context": {
                    "span_id": r[1],
                    "trace_id": r[2],
                },
                "attributes": attrs,
            }
            all_spans.append(span)

        last_id = rows[-1][0]
        if not is_partial:
            break

    return all_spans


def load_spans(args: argparse.Namespace) -> list[Span]:
    """Load spans from file or Phoenix executeSql keyset pagination."""
    if getattr(args, "from_file", None):
        path: Path = args.from_file
        raw = json.loads(path.read_text(encoding="utf-8"))
        spans = raw.get("data", []) if isinstance(raw, dict) and "data" in raw else raw
        if isinstance(raw, dict) and "tools" in raw:
            # Bundle produced by --save-spans
            spans = raw.get("tools", [])
        if not isinstance(spans, list):
            raise ConfigError(f"{path}: expected JSON list or object with data/tools")
        return spans

    base_url = resolve_base_url(args.base_url)
    _project_id, project_name = resolve_project(base_url, args.project)

    tz = parse_tz(args.tz)
    days = getattr(args, "days", 7) or 7
    since_dt = (
        parse_when(args.since, tz) if args.since else (datetime.now(UTC) - timedelta(days=days))
    )
    until_dt = parse_when(args.until, tz) if args.until else datetime.now(UTC)

    # Exhaustive keyset pagination via executeSql
    all_spans = page_spans_sql(
        base_url,
        project_name,
        iso(since_dt),
        iso(until_dt),
        session_id_filter=args.session,
    )

    if getattr(args, "save_spans", None):
        args.save_spans.write_text(
            json.dumps(
                {
                    "project": project_name,
                    "window": [iso(since_dt), iso(until_dt)],
                    "tools": all_spans,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return all_spans


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        # Tally command runs on local annotation file without Phoenix spans
        if args.command == "tally":
            path: Path = args.annotations
            if not path.is_file():
                raise ConfigError(f"annotations file not found: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            metrics = tally_annotations(payload)
            if args.json:
                print(
                    json.dumps(
                        {k: asdict(v) for k, v in metrics.items()},
                        indent=2,
                    )
                )
            else:
                print(render_tally_markdown(metrics))
            return EXIT_OK

        spans = load_spans(args)
        if not spans:
            print("no spans retrieved for specified parameters", file=sys.stderr)
            return EXIT_EMPTY

        exclude_sessions = {
            s.strip() for s in (args.exclude_sessions or "").split(",") if s.strip()
        }
        if args.session:
            spans = [s for s in spans if session_of(s).startswith(args.session)]

        if args.command == "census":
            stats = aggregate_census(spans, exclude_sessions=exclude_sessions)
            if args.json:
                res: dict[str, Any] = {}
                for k, v in stats.items():
                    d = asdict(v)
                    d["sessions"] = sorted(v.sessions)
                    d["armed_sessions"] = sorted(v.armed_sessions)
                    d["refusal_sessions"] = sorted(v.refusal_sessions)
                    d["defect_tags"] = dict(v.defect_tags)
                    d["waived_categories"] = dict(v.waived_categories)
                    res[k] = d
                print(json.dumps(res, indent=2))
            else:
                print(render_census_markdown(stats))
            return EXIT_OK

        if args.command == "dossier":
            records = extract_dossier_records(
                spans,
                harness_filter=args.harness,
                verdict_filter=args.verdict,
                tagged_only=args.tagged_only,
                exclude_sessions=exclude_sessions,
                limit=args.sample,
            )
            if args.format == "json":
                out_text = json.dumps([asdict(r) for r in records], indent=2)
            elif args.format == "annotations":
                out_text = json.dumps(render_dossier_annotations_template(records), indent=2)
            else:
                out_text = render_dossier_markdown(records)

            if args.out:
                args.out.write_text(out_text, encoding="utf-8")
                print(f"wrote {len(records)} records to {args.out}")
            else:
                print(out_text)
            return EXIT_OK

        if args.command == "log":
            if not args.session:
                raise ConfigError("log command requires --session <session-id>")
            rendered = render_session_log(args.session, spans)
            if args.out:
                args.out.write_text(rendered, encoding="utf-8")
                print(f"wrote premise-check log to {args.out}")
            else:
                print(rendered)
            return EXIT_OK

        return EXIT_OK

    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
