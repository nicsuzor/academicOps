#!/usr/bin/env python3
"""Structural parser for the report's ``argdown`` block and the checker's keyed reason.

The grammar is closed and defined by the premise-check skill:
``references/report-form.md`` (the block) and ``references/checker-reason.md``
(the keyed lines, whose keys ``vocabulary.toml`` names). Everything here is a
format or presence check over that grammar -- the YAML frontmatter, line shapes,
ids, numbers, and matches against the closed vocabularies in
``references/vocabulary.toml``. Nothing here classifies what a line means.

The vocabulary is read from the skill's ``vocabulary.toml`` at runtime; this
module keeps no copy of it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# A premise's basis separator, and the no-claim separator in a reason:
# ``--`` as committed, ``—`` as typed live.
_DASH = r"(?:--|—)"
_SEPARATOR = re.compile(rf"\s{_DASH}\s")
_FENCE_OPEN = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})\s*argdown\s*$", re.IGNORECASE)
_FRONTMATTER_FENCE = "==="
_NUMBERED = re.compile(r"^\((?P<n>\d+)\)\s*(?P<text>.*)$")
# Argdown takes an inference line only in ASCII: ``-- ... --``.
_INFERENCE = re.compile(r"^--\s.*\s--$|^--\s--$")
_TRAILING_MARKERS = re.compile(r"(?:\s*\^[A-Za-z]+)+\s*$")
_LINE_REF = re.compile(r"\((?P<n>\d+)\)")
_ARROW = re.compile(r"←|<-")
_VALID_ENTRY = re.compile(r"^\((?P<n>\d+)\)\s+(?P<word>holds|fails)\b(?P<rest>.*)$")
_ANSWERED_LINE = re.compile(r"^(?P<id>[^\s:]+):?\s*(?:←|<-)\s*\((?P<n>\d+)\)\s*$")
_ANSWERED_NONE = re.compile(r"^(?P<id>[^\s:]+):?\s+unanswered\s*$")
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
    reason_keys: tuple[str, ...]
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
        reason_keys=tuple(str(k) for k in data["reason_keys"]),
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
# The argdown block
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
    # ask id -> the line that answers it, None for ``none``, or the raw value
    # when it is neither.
    answers: dict[str, int | str | None] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)

    def weakest(self) -> Premise | None:
        if not self.premises:
            return None
        return min(self.premises, key=lambda p: p.rank)


def extract_block(text: str | None) -> str | None:
    """Body of the last ```argdown fenced block in ``text``, or None."""
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


def _split_frontmatter(lines: list[str]) -> tuple[str | None, list[str]] | None:
    """(YAML text or None, body lines); None when a frontmatter fence is unclosed."""
    start = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if start is None or lines[start].strip() != _FRONTMATTER_FENCE:
        return None, lines
    for end in range(start + 1, len(lines)):
        if lines[end].strip() == _FRONTMATTER_FENCE:
            return "\n".join(lines[start + 1 : end]), lines[end + 1 :]
    return None


def _answer_value(value: Any) -> int | str | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value).strip()
    if text.lower() == "none":
        return None
    return int(text) if text.isdigit() else text


def parse_block(block: str, vocab: Vocabulary) -> Argument | None:
    """Parse an argdown block; None when its YAML frontmatter fails to parse."""
    split = _split_frontmatter(block.splitlines())
    if split is None:
        return None
    frontmatter, body = split
    arg = Argument()
    if frontmatter is not None:
        try:
            data = yaml.safe_load(frontmatter)
        except yaml.YAMLError:
            return None
        data = {} if data is None else data
        if not isinstance(data, dict):
            return None
        sections = {k: data.get(k) or {} for k in ("asks", "answers", "notes")}
        if not all(isinstance(v, dict) for v in sections.values()):
            return None
        arg.asks = [str(k) for k in sections["asks"]]
        arg.answers = {str(k): _answer_value(v) for k, v in sections["answers"].items()}
        arg.notes = {str(k): str(v) for k, v in sections["notes"].items()}

    after_inference: Inference | None = None
    for line in (ln.strip() for ln in body):
        if not line:
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
    return arg


_NULL_FORM_RE = re.compile(
    r"^(?:===\s*\n)?\s*asks:\s*none\s*(?:\n===)?\s*\n\s*\[no\s+claim\]\s*$",
    re.IGNORECASE,
)


def is_null_form(block_text: str | None) -> bool:
    """True when a fenced argdown block is the null form declaring no claim."""
    if not block_text or not block_text.strip():
        return False
    return bool(_NULL_FORM_RE.match(block_text.strip()))


def clean_ansi(text: str, file_path: str | None = None) -> str:
    """Strip ANSI escape sequences from parser output and normalize paths."""
    clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text).strip()
    if file_path:
        clean = clean.replace(file_path, "<argdown>")
    clean = re.sub(rf"{re.escape(tempfile.gettempdir())}/[^\s]+\.argdown", "<argdown>", clean)
    return re.sub(r"/tmp/[^\s]+\.argdown", "<argdown>", clean)


def resolve_argdown_bin(parser_bin: str | None = None) -> str:
    """Resolve argdown parser binary across explicit arg, AOPS_ARGDOWN_BIN, repo/user node_modules, and PATH."""
    if parser_bin:
        return parser_bin
    env_bin = os.environ.get("AOPS_ARGDOWN_BIN")
    if env_bin and os.path.isfile(env_bin) and os.access(env_bin, os.X_OK):
        return env_bin

    candidates: list[Path] = []
    cwd = Path.cwd()
    candidates.append(cwd / "node_modules" / ".bin" / "argdown")
    repo_root = Path(__file__).resolve().parents[3]
    candidates.append(repo_root / "node_modules" / ".bin" / "argdown")
    home = Path.home()
    candidates.append(home / "node_modules" / ".bin" / "argdown")
    candidates.append(home / "ida" / "node_modules" / ".bin" / "argdown")
    candidates.append(home / ".config" / "yarn" / "global" / "node_modules" / ".bin" / "argdown")
    candidates.append(home / ".npm-global" / "bin" / "argdown")

    for cand in candidates:
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)

    path_bin = shutil.which("argdown")
    if path_bin:
        return path_bin

    raise RuntimeError("argdown parser binary not found on PATH")


def sanitise_argdown_text(text: str) -> str:
    """Prevent markdown punctuation (*, _) in premise-check blocks from triggering false-positive @argdown/cli syntax rejections, and ensure frontmatter has required empty line separation."""
    m = re.match(r"^(===\s*\n.*?\n===\s*\n)(.*)$", text, re.DOTALL)
    if m:
        fm, body = m.group(1), m.group(2)
        fm = fm.rstrip("\n") + "\n\n"
        body = body.lstrip("\n")
    else:
        fm, body = "", text

    # Escape unescaped * in argdown body
    body = re.sub(r"(?<!\\)\*", r"\*", body)
    # Escape unescaped _ in argdown body, except when part of relation '_>'
    body = re.sub(r"(?<!\\)_(?!>)", r"\_", body)
    return fm + body


def check_argdown_block(
    block_text: str,
    parser_bin: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Parse block with @argdown/cli and run machine checks: orphan statements and misaimed undercuts.

    Checks:
    1. Argdown syntax validity (clean exit and JSON AST from parser).
    2. Undercut check: any undercut (_>) must target an inference (toType == 'inference').
    3. Orphan statement check: statements must have relations or argument membership.

    Returns:
        (valid: bool, reason_or_error: str, ast: dict | None)
    """
    cmd = resolve_argdown_bin(parser_bin)
    text_to_parse = sanitise_argdown_text(block_text)

    with tempfile.NamedTemporaryFile("w", suffix=".argdown", delete=False) as f:
        f.write(text_to_parse)
        f.flush()
        f_path = Path(f.name)
    try:
        res = subprocess.run(
            [cmd, "json", str(f_path), "--stdout", "--logParserErrors", "true"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        try:
            f_path.unlink()
        except OSError:
            pass

    if res.returncode != 0:
        err = clean_ansi(res.stderr or res.stdout, str(f_path))
        if (
            "Argdown syntax error" in err
            or "Invalid Argdown syntax detected" in err
            or "SyntaxError" in err
        ):
            return False, f"Argdown syntax error:\n{err}", None
        raise RuntimeError(f"Argdown parser failed (exit {res.returncode}):\n{err}")

    idx = res.stdout.rfind("}")
    if idx == -1:
        raise RuntimeError("Argdown parser error: no JSON output from parser")
    try:
        data = json.loads(res.stdout[: idx + 1])
    except Exception as exc:
        raise RuntimeError(f"Argdown parser error decoding AST: {exc}") from exc

    stmts = data.get("statements", {})
    rels = data.get("relations", [])

    # Check 1: Undercut not aimed at an inference
    for r in rels:
        if r.get("relationType") == "undercut":
            if r.get("toType") != "inference":
                target = r.get("to")
                target_type = r.get("toType")
                src = r.get("from")
                return (
                    False,
                    f"Argdown argument invalid: undercut from '{src}' targets {target_type} '{target}' instead of an inference",
                    data,
                )

    # Check 2: Orphan statement (unconnected statement with no relation and no argument membership)
    connected_statements: set[str] = set()
    for r in rels:
        if r.get("from"):
            connected_statements.add(r.get("from"))
        if r.get("to"):
            connected_statements.add(r.get("to"))
    for title, stmt in stmts.items():
        if stmt.get("relations"):
            connected_statements.add(title)
        if (
            stmt.get("isUsedAsPremise")
            or stmt.get("isUsedAsMainConclusion")
            or stmt.get("isUsedAsIntermediaryConclusion")
        ):
            connected_statements.add(title)
        for m in stmt.get("members", []):
            role = m.get("role")
            if role in (
                "premise",
                "main-conclusion",
                "conclusion",
                "intermediary-conclusion",
                "relation-statement",
            ):
                connected_statements.add(title)
            if m.get("argumentTitle"):
                connected_statements.add(title)

    for title, stmt in stmts.items():
        if title not in connected_statements:
            text = next((m.get("text") for m in stmt.get("members", []) if m.get("text")), title)
            return (
                False,
                f"Argdown argument invalid: orphan statement '{title}' ('{text}') has no relations or argument membership",
                data,
            )

    return True, "", data


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

    def answered(self) -> list[tuple[str, int | None] | None]:
        """Each Answered entry as (ask id, line) or (ask id, None) for unanswered.

        None marks an entry in neither form.
        """
        out: list[tuple[str, int | None] | None] = []
        for entry in self.get("Answered"):
            if m := _ANSWERED_LINE.match(entry.strip()):
                out.append((m.group("id"), int(m.group("n"))))
            elif m := _ANSWERED_NONE.match(entry.strip()):
                out.append((m.group("id"), None))
            else:
                out.append(None)
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


def parse_reason(text: str, vocab: Vocabulary) -> Reason:
    keys = "|".join(re.escape(k) for k in vocab.reason_keys)
    line_re = re.compile(rf"^\s*(?P<key>{keys})\s*:\s?(?P<value>.*)$")
    reason = Reason()
    for line in (text or "").splitlines():
        if m := line_re.match(line):
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


def pass_failures(
    reason: Reason,
    block: Argument | None,
    vocab: Vocabulary,
    is_null: bool = False,
) -> list[str]:
    """Every check a PASS reason fails, per the skill's "What the recorder refuses"."""
    if reason.no_claim and set(reason.entries) == {"Judged"}:
        if block is not None and not is_null:
            return [
                "a no-claim reason, but the judged text has an argdown block: "
                "judge the block with the full reason"
            ]
        return []

    failures: list[str] = []
    missing = [k for k in vocab.reason_keys if not reason.get(k)]
    if missing:
        failures.append(f"missing keyed lines: {', '.join(missing)}")
    for key in ("Judged", "Supported"):
        count = len(reason.get(key))
        if count > 1:
            failures.append(f"{key} must appear exactly once; found {count}")

    judged_asks = reason.judged_asks
    if block is not None:
        if sorted(set(judged_asks)) != sorted(set(block.asks)):
            failures.append(
                f"Judged ask ids {sorted(set(judged_asks))} do not equal the block's "
                f"asks {sorted(set(block.asks))}"
            )
    ask_ids = block.asks if block is not None else judged_asks
    if not ask_ids:
        failures.append(
            "no ask ids: the block's frontmatter has no asks and Judged names none"
            if block is not None
            else "no ask ids: Judged names none"
        )
    answered = reason.answered()
    malformed_answers = [
        e for e, a in zip(reason.get("Answered"), answered, strict=True) if a is None
    ]
    if malformed_answers:
        failures.append(
            "Answered entries not in the form '<ask id> ← (n)' or '<ask id> unanswered': "
            + "; ".join(repr(e) for e in malformed_answers)
        )
    if block is not None:
        named = {a[1] for a in answered if a and a[1] is not None}
        absent = sorted(named - set(block.lines))
        if absent:
            failures.append(
                f"Answered names lines not in the block ({', '.join(map(str, absent))})"
            )
    if block is not None:
        bad = sorted(str(v) for v in block.answers.values() if isinstance(v, str))
        if bad:
            failures.append(f"the block's answers are not a line number or none: {', '.join(bad)}")
        named_by_block = {v for v in block.answers.values() if isinstance(v, int)}
        missing_lines = sorted(named_by_block - set(block.lines))
        if missing_lines:
            failures.append(
                "the block's answers name lines not in the block "
                f"({', '.join(map(str, missing_lines))})"
            )
    answered_ids = {a[0] for a in answered if a}
    unanswered = [a for a in ask_ids if a not in answered_ids]
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
        orphans = [inf.text for inf in block.inferences if inf.conclusion is None]
        if orphans:
            failures.append(
                "inference line with no conclusion line after it: "
                + "; ".join(repr(t) for t in orphans)
            )
        if len(reason.get("Valid")) != len(block.inferences):
            failures.append(
                f"Valid has {len(reason.get('Valid'))} entries for "
                f"{len(block.inferences)} inference lines"
            )
        elif not orphans:
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
        failures.append(
            "the judged text has no argdown block that parses: PASS needs 'Waived: block -- ...'"
        )

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
    for key in vocab.reason_keys:
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
