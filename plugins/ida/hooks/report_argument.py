#!/usr/bin/env python3
"""Structural parser for the report ``argument`` block and the checker's keyed reason.

The grammar is closed and defined by the premise-check skill:
``references/report-form.md`` (the block) and ``references/checker-reason.md``
(the seven keyed lines). Everything here is a format or presence check over that
grammar -- line shapes, ids, numbers, and matches against the closed vocabularies
in ``references/vocabulary.toml``. Nothing here classifies what a line means.

The vocabulary is read from the skill's ``vocabulary.toml`` at runtime; this
module keeps no copy of it.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The seven keys of the checker's reason, in the order the skill lists them.
REASON_KEYS: tuple[str, ...] = (
    "Judged",
    "Valid",
    "Supported",
    "Answered",
    "Sufficient",
    "Waived",
    "Relay",
)

# A separator / inference marker: ``--`` as committed, ``—`` as typed live.
_DASH = r"(?:--|—)"
_SEPARATOR = re.compile(rf"\s{_DASH}\s")
_FENCE_OPEN = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})\s*argument\s*$")
_ASK = re.compile(r"^Asked\s*\((?P<id>[^)\s]+)\)\s*:\s*(?P<words>.*)$")
_NUMBERED = re.compile(r"^\((?P<n>\d+)\)\s*(?P<text>.*)$")
_INFERENCE = re.compile(rf"^{_DASH}\s.*\s{_DASH}$|^{_DASH}\s{_DASH}$")
_ENDNOTE = re.compile(r"^\[(?P<key>[A-Za-z0-9]+)\]\s+(?P<pointer>.+)$")
_ANSWERS = re.compile(r"^Answers\s*:\s*(?P<rest>.*)$")
_TRAILING_MARKERS = re.compile(r"(?:\s*\[[A-Za-z0-9]+\])+\s*$")
_REASON_LINE = re.compile(rf"^\s*(?P<key>{'|'.join(REASON_KEYS)})\s*:\s?(?P<value>.*)$")
_LINE_REF = re.compile(r"\((?P<n>\d+)\)")
_ARROW = re.compile(r"←|<-")
_VALID_ENTRY = re.compile(r"^\((?P<n>\d+)\)\s+(?P<word>holds|fails)\b(?P<rest>.*)$")
_TAG = re.compile(r"#[A-Za-z0-9_-]+")
_JUDGED_ASKS = re.compile(r";\s*asks?\b\s*(?P<asks>.*)$")
_JUDGED_NO_CLAIM = re.compile(rf";\s*no claim\b(?:\s*{_DASH}\s*(?P<what>.*))?\s*$")


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Basis:
    phrase: str
    term: str
    rank: int


@dataclass(frozen=True)
class Vocabulary:
    basis: tuple[Basis, ...]
    format_items: tuple[str, ...]
    defect_tags: tuple[str, ...]
    path: Path


def vocabulary_path(plugin_dir: Path | None = None) -> Path:
    """Path of the skill's vocabulary file inside the plugin.

    The hooks directory and the skills directory are siblings in the source
    tree (``plugins/ida/``) and in every built plugin (``dist/ida-<client>/``).
    """
    base = plugin_dir or Path(__file__).resolve().parent.parent
    return base / "skills" / "premise-check" / "references" / "vocabulary.toml"


def load_vocabulary(path: Path | None = None) -> Vocabulary:
    """Read the closed vocabularies. A missing or malformed file raises."""
    target = path or vocabulary_path()
    data = tomllib.loads(target.read_text(encoding="utf-8"))
    basis = tuple(
        Basis(phrase=str(b["phrase"]), term=str(b["term"]), rank=int(b["rank"]))
        for b in data["basis"]
    )
    return Vocabulary(
        basis=basis,
        format_items=tuple(str(x) for x in data["format_items"]),
        defect_tags=tuple(str(x) for x in data["defect_tags"]),
        path=target,
    )


def _starts_with_phrase(text: str, phrase: str) -> bool:
    low, p = text.lower(), phrase.lower()
    if not low.startswith(p):
        return False
    return len(low) == len(p) or not low[len(p)].isalnum()


def match_basis(text: str, vocab: Vocabulary) -> Basis | None:
    """The longest vocabulary phrase ``text`` starts with, case-insensitively."""
    for b in sorted(vocab.basis, key=lambda b: len(b.phrase), reverse=True):
        if _starts_with_phrase(text.strip(), b.phrase):
            return b
    return None


def match_format_item(text: str, vocab: Vocabulary) -> str | None:
    for item in sorted(vocab.format_items, key=len, reverse=True):
        if _starts_with_phrase(text.strip(), item):
            return item
    return None


# ---------------------------------------------------------------------------
# The argument block
# ---------------------------------------------------------------------------


@dataclass
class Premise:
    number: int
    text: str
    basis_text: str | None
    basis: Basis | None

    @property
    def rank(self) -> int:
        return self.basis.rank if self.basis else 0


@dataclass
class Inference:
    text: str
    conclusion: int | None


@dataclass
class Argument:
    asks: list[str] = field(default_factory=list)
    lines: dict[int, str] = field(default_factory=dict)
    premises: list[Premise] = field(default_factory=list)
    inferences: list[Inference] = field(default_factory=list)
    conclusions: list[int] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    endnotes: dict[str, str] = field(default_factory=dict)

    def weakest(self) -> Premise | None:
        if not self.premises:
            return None
        return min(self.premises, key=lambda p: p.rank)


def extract_block(text: str | None) -> str | None:
    """Body of the last ```argument fenced block in ``text``, or None."""
    if not text:
        return None
    lines = text.splitlines()
    found: str | None = None
    i = 0
    while i < len(lines):
        m = _FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group("fence")
        close = re.compile(rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$")
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not close.match(lines[j]):
            body.append(lines[j])
            j += 1
        if j < len(lines):
            found = "\n".join(body)
        i = j + 1
    return found


def _premise_basis(text: str) -> str | None:
    seps = list(_SEPARATOR.finditer(text))
    if not seps:
        return None
    tail = text[seps[-1].end() :]
    return _TRAILING_MARKERS.sub("", tail).strip()


def parse_block(block: str, vocab: Vocabulary) -> Argument:
    arg = Argument()
    raw = [ln.strip() for ln in block.splitlines()]
    after_inference: Inference | None = None
    for line in raw:
        if not line:
            continue
        if m := _ASK.match(line):
            arg.asks.append(m.group("id"))
            after_inference = None
            continue
        if _INFERENCE.match(line):
            after_inference = Inference(text=line, conclusion=None)
            arg.inferences.append(after_inference)
            continue
        if m := _NUMBERED.match(line):
            n = int(m.group("n"))
            arg.lines[n] = m.group("text")
            if after_inference is not None:
                after_inference.conclusion = n
                arg.conclusions.append(n)
            else:
                basis_text = _premise_basis(m.group("text"))
                basis = match_basis(basis_text, vocab) if basis_text else None
                arg.premises.append(Premise(n, m.group("text"), basis_text, basis))
            after_inference = None
            continue
        after_inference = None
        if m := _ANSWERS.match(line):
            arg.answers.extend(p.strip() for p in m.group("rest").split(";") if p.strip())
            continue
        if m := _ENDNOTE.match(line):
            arg.endnotes[m.group("key")] = m.group("pointer")
    return arg


# ---------------------------------------------------------------------------
# The checker's reason
# ---------------------------------------------------------------------------


@dataclass
class Reason:
    entries: dict[str, list[str]] = field(default_factory=dict)

    def get(self, key: str) -> list[str]:
        return self.entries.get(key, [])

    @property
    def judged_asks(self) -> list[str]:
        ids: list[str] = []
        for entry in self.get("Judged"):
            if m := _JUDGED_ASKS.search(entry):
                ids.extend(t for t in re.split(r"[,\s]+", m.group("asks")) if t)
        return ids

    @property
    def no_claim(self) -> bool:
        judged = self.get("Judged")
        return len(judged) == 1 and bool(_JUDGED_NO_CLAIM.search(judged[0]))

    def answered_ids(self) -> list[str]:
        out: list[str] = []
        for entry in self.get("Answered"):
            token = entry.strip().split()[0] if entry.strip() else ""
            out.append(token.rstrip(":,;"))
        return out

    def valid_entries(self) -> list[re.Match[str] | None]:
        return [_VALID_ENTRY.match(e.strip()) for e in self.get("Valid")]

    def defect_tags(self, vocab: Vocabulary) -> list[str]:
        tags: list[str] = []
        for m in self.valid_entries():
            if m and m.group("word") == "fails":
                rest = m.group("rest").strip()
                for tag in _TAG.findall(rest.split(" -- ")[0].split(" — ")[0]):
                    if tag in vocab.defect_tags:
                        tags.append(tag)
        return tags

    def waived_items(self, vocab: Vocabulary) -> list[str]:
        items: list[str] = []
        for entry in self.get("Waived"):
            item = match_format_item(entry, vocab)
            if item:
                items.append(item)
        return items

    def supported_basis(self, vocab: Vocabulary) -> Basis | None:
        entries = self.get("Supported")
        if not entries:
            return None
        text = re.sub(r"^\s*weakest\b\s*", "", entries[0], flags=re.IGNORECASE)
        return match_basis(text, vocab)


def parse_reason(text: str) -> Reason:
    reason = Reason()
    for line in (text or "").splitlines():
        if m := _REASON_LINE.match(line):
            reason.entries.setdefault(m.group("key"), []).append(m.group("value").strip())
    return reason


def _is_none(entry: str) -> bool:
    return entry.strip().lower() == "none"


def relay_refs(entry: str) -> list[int]:
    arrow = _ARROW.search(entry)
    if not arrow:
        return []
    return [int(n) for n in _LINE_REF.findall(entry[arrow.end() :])]


# ---------------------------------------------------------------------------
# What the recorder refuses for PASS
# ---------------------------------------------------------------------------


def pass_failures(reason: Reason, block: Argument | None, vocab: Vocabulary) -> list[str]:
    """Every check a PASS reason fails, per the skill's "What the recorder refuses"."""
    if reason.no_claim and set(reason.entries) == {"Judged"}:
        return []

    failures: list[str] = []
    missing = [k for k in REASON_KEYS if not reason.get(k)]
    if missing:
        failures.append(f"missing keyed lines: {', '.join(missing)}")

    judged_asks = reason.judged_asks
    if block is not None:
        if sorted(set(judged_asks)) != sorted(set(block.asks)):
            failures.append(
                f"Judged ask ids {sorted(set(judged_asks))} do not equal the block's "
                f"Asked ids {sorted(set(block.asks))}"
            )
    ask_ids = block.asks if block is not None else judged_asks
    answered = set(reason.answered_ids())
    unanswered = [a for a in ask_ids if a not in answered]
    if unanswered:
        failures.append(f"no Answered line for ask ids: {', '.join(unanswered)}")

    valid = reason.valid_entries()
    malformed = [e for e, m in zip(reason.get("Valid"), valid, strict=True) if m is None]
    if malformed:
        failures.append(
            "Valid entries not in the form '(n) holds|fails ...': "
            + "; ".join(repr(e) for e in malformed)
        )
    fails = [m.group("n") for m in valid if m and m.group("word") == "fails"]
    if fails:
        failures.append(f"Valid says fails for ({'), ('.join(fails)})")
    if block is not None:
        if len(reason.get("Valid")) != len(block.inferences):
            failures.append(
                f"Valid has {len(reason.get('Valid'))} entries for "
                f"{len(block.inferences)} inference lines"
            )
        elif all(inf.conclusion is not None for inf in block.inferences):
            keyed = sorted(int(m.group("n")) for m in valid if m)
            expected = sorted(int(inf.conclusion or 0) for inf in block.inferences)
            if keyed != expected:
                failures.append(
                    f"Valid is keyed by lines {keyed}; the inference lines yield {expected}"
                )

    if block is not None and block.premises and reason.get("Supported"):
        named = reason.supported_basis(vocab)
        lowest = min(p.rank for p in block.premises)
        if named is None:
            failures.append(
                f"Supported names no basis phrase from {vocab.path.name}: "
                f"{reason.get('Supported')[0]!r}"
            )
        elif named.rank != lowest:
            weakest = block.weakest()
            shown = weakest.basis.phrase if weakest and weakest.basis else "an unmatched basis"
            failures.append(
                f"Supported names {named.phrase!r} (rank {named.rank}); the block's weakest "
                f"premise is ({weakest.number if weakest else '?'}) {shown!r} (rank {lowest})"
            )

    bad_waived = [
        e for e in reason.get("Waived") if not _is_none(e) and match_format_item(e, vocab) is None
    ]
    if bad_waived:
        failures.append(
            "Waived entries that do not start with a format item "
            f"({', '.join(vocab.format_items)}): " + "; ".join(repr(e) for e in bad_waived)
        )
    if block is None and "block" not in reason.waived_items(vocab):
        failures.append("the judged text has no argument block: PASS needs 'Waived: block -- ...'")

    for entry in reason.get("Relay"):
        if _is_none(entry):
            continue
        refs = relay_refs(entry)
        if not refs:
            failures.append(f"Relay names no line: {entry!r}")
        elif block is not None:
            absent = [n for n in refs if n not in block.lines]
            if absent:
                failures.append(
                    f"Relay names lines not in the block ({', '.join(map(str, absent))}): {entry!r}"
                )
    return failures


# ---------------------------------------------------------------------------
# Span attributes
# ---------------------------------------------------------------------------


def span_attributes(reason: Reason, block: Argument | None, vocab: Vocabulary) -> dict[str, Any]:
    """Telemetry attributes for one verdict, all under ``premise_check.``.

    Ask ids, defect tags and waived items are string arrays, so span-store SQL
    can expand them with ``json_each``.
    """
    attrs: dict[str, Any] = {}
    for key in REASON_KEYS:
        entries = reason.get(key)
        if entries:
            attrs[f"premise_check.reason.{key.lower()}"] = "\n".join(entries)

    asks = block.asks if block is not None else reason.judged_asks
    attrs["premise_check.ask_ids"] = list(asks)
    attrs["premise_check.has_block"] = block is not None

    weakest_phrase, weakest_term = "", ""
    if block is not None and block.premises:
        weakest = block.weakest()
        if weakest is not None and weakest.basis is not None:
            weakest_phrase, weakest_term = weakest.basis.phrase, weakest.basis.term
        elif weakest is not None:
            weakest_phrase, weakest_term = weakest.basis_text or "", "unmatched"
    else:
        named = reason.supported_basis(vocab)
        if named is not None:
            weakest_phrase, weakest_term = named.phrase, named.term
    attrs["premise_check.weakest_basis"] = weakest_phrase
    attrs["premise_check.weakest_basis_term"] = weakest_term

    attrs["premise_check.inference_count"] = (
        len(block.inferences) if block is not None else len(reason.get("Valid"))
    )
    tags = reason.defect_tags(vocab)
    attrs["premise_check.defect_tags"] = tags
    attrs["premise_check.defect_tag_count"] = len(tags)
    attrs["premise_check.waived_items"] = reason.waived_items(vocab)
    attrs["premise_check.no_claim"] = reason.no_claim
    return attrs
