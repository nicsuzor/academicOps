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

import re
import tempfile
import textwrap
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
# Argdown takes an inference line in ASCII (``-- ... --``) or typed live (``— ... —``).
_INFERENCE = re.compile(r"^(?:--|—)\s*.*\s*(?:--|—)$|^--\s--$")
_TRAILING_MARKERS = re.compile(r"(?:\s*\^[A-Za-z0-9_-]+)+\s*$")
_ATTR_BLOCK = re.compile(r"\{(?P<attrs>[^{}]+)\}\s*$")
_BASIS_ATTR = re.compile(r"\bbasis\s*:\s*(?:\"([^\"]+)\"|'([^']+)'|([^,}\n]+))")
_LINE_REF = re.compile(r"\((?P<n>\d+)\)")
_ARROW = re.compile(r"←|<-")
_VALID_ENTRY = re.compile(
    r"^\s*(?P<lines>(?:\(\d+\)(?:\s*(?:,|and)\s*)*)+)\s+(?P<word>holds?|fails?)\b(?P<rest>.*)$",
    re.IGNORECASE,
)


@dataclass
class ValidMatch:
    lines: tuple[int, ...]
    word: str
    rest: str
    raw: str
    clauses: tuple[ValidMatch, ...] = ()

    def group(self, key: str | int) -> str:
        if key in ("n", 1):
            return str(self.lines[0]) if self.lines else ""
        if key in ("word", 2):
            return self.word
        if key in ("rest", 3):
            return self.rest
        if key in ("lines", 4):
            return ", ".join(f"({n})" for n in self.lines)
        raise IndexError(f"unknown group {key}")


def _match_valid_part(part: str) -> ValidMatch | None:
    s = part.strip()
    if not s:
        return None
    clauses = [c.strip() for c in re.split(r";\s*(?=\(\d+\))", s) if c.strip()]
    if len(clauses) > 1:
        sub = [_match_valid_part(c) for c in clauses]
        if any(sm is None for sm in sub):
            return None
        all_lines: list[int] = []
        has_fail = False
        rests: list[str] = []
        for sm in sub:
            if sm is not None:
                all_lines.extend(sm.lines)
                if sm.word == "fails":
                    has_fail = True
                if sm.rest.strip():
                    rests.append(sm.rest.strip())
        return ValidMatch(
            lines=tuple(all_lines),
            word="fails" if has_fail else "holds",
            rest=" ; ".join(rests),
            raw=s,
            clauses=tuple(sm for sm in sub if sm is not None),
        )

    m = _VALID_ENTRY.match(s)
    if not m:
        return None
    raw_lines = _LINE_REF.findall(m.group("lines"))
    if not raw_lines:
        return None
    lines = tuple(int(n) for n in raw_lines)
    word_raw = m.group("word").lower()
    word = "holds" if word_raw.startswith("hold") else "fails"
    return ValidMatch(lines=lines, word=word, rest=m.group("rest"), raw=s)


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


def normalise_argdown_block(text: str) -> str:
    """Normalise meaning-free whitespace in an Argdown block.

    Strips CRLF endings, trailing whitespace on every line, and removes common
    leading indentation across the block while preserving relative indentation.
    """
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.splitlines()]
    dedented = textwrap.dedent("\n".join(lines))
    return dedented.strip("\n")


def extract_block(text: str | None) -> str | None:
    """Body of the last ```argdown fenced block in ``text``, or None."""
    if not text:
        return None
    text = textwrap.dedent(text)
    lines = text.splitlines()
    found: str | None = None
    i = 0
    while i < len(lines):
        m = _FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group("fence")
        close = re.compile(rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}(?:\s*|</[^>]+>)*\s*$")
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not close.match(lines[j]):
            body.append(lines[j])
            j += 1
        if j < len(lines):
            found = normalise_argdown_block("\n".join(body))
        i = j + 1
    return found


def _premise_basis(text: str) -> str | None:
    # 1. Attribute syntax {basis: ...}
    if m_attr := _ATTR_BLOCK.search(text):
        attrs = m_attr.group("attrs")
        if m_b := _BASIS_ATTR.search(attrs):
            val = m_b.group(1) or m_b.group(2) or m_b.group(3)
            if val:
                return val.strip()

    # 2. Leading separator on continuation line: -- or —
    stripped = text.strip()
    if stripped.startswith(("-- ", "— ")):
        tail = stripped[3:] if stripped.startswith("-- ") else stripped[2:]
        return _TRAILING_MARKERS.sub("", tail).strip()

    # 3. Separator -- or — syntax
    seps = list(_SEPARATOR.finditer(text))
    if not seps:
        return None
    tail = text[seps[-1].end() :]
    return _TRAILING_MARKERS.sub("", tail).strip()


def _split_frontmatter(lines: list[str]) -> tuple[str | None, list[str]] | None:
    """(YAML text or None, body lines); None when a frontmatter fence is unclosed."""
    start = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if start is None or lines[start].strip() != _FRONTMATTER_FENCE:
        return None, textwrap.dedent("\n".join(lines)).splitlines()
    for end in range(start + 1, len(lines)):
        if lines[end].strip() == _FRONTMATTER_FENCE:
            fm_text = textwrap.dedent("\n".join(lines[start + 1 : end])).strip("\n")
            body = textwrap.dedent("\n".join(lines[end + 1 :])).splitlines()
            return fm_text, body
    return None


def _answer_value(value: Any) -> int | str | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value).strip()
    if text.lower() == "none":
        return None
    return int(text) if text.isdigit() else text


def parse_block(block: str, vocab: Vocabulary) -> Argument | None:
    """Parse an argdown block; None when its YAML frontmatter fails to parse or syntax is invalid."""
    block = normalise_argdown_block(block)
    valid, _, _ = check_argdown_block(block)
    if not valid:
        return None
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

    # Collect logical lines in body, joining multi-line inference bars:
    body_lines: list[str] = []
    in_inference = False
    current_inf: list[str] = []
    for raw_ln in body:
        s = raw_ln.strip()
        if not in_inference:
            if raw_ln.startswith((" ", "\t")) and _premise_basis(s):
                body_lines.append(raw_ln)
            elif not raw_ln.startswith((" ", "\t")) and (
                (s.startswith("--") and not s.endswith("--") and len(s) > 2)
                or (s.startswith("—") and not s.endswith("—") and len(s) > 1)
            ):
                in_inference = True
                current_inf = [s]
            else:
                body_lines.append(raw_ln)
        else:
            current_inf.append(s)
            if s.endswith("--") or s.endswith("—"):
                in_inference = False
                body_lines.append(" ".join(current_inf))
                current_inf = []
    if current_inf:
        body_lines.append(" ".join(current_inf))

    after_inference: Inference | None = None
    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Indented continuation line under premise
        if line.startswith((" ", "\t")) and arg.premises and after_inference is None:
            if b_text := _premise_basis(stripped):
                if arg.premises[-1].basis_text is None:
                    arg.premises[-1].basis_text = b_text
                    arg.premises[-1].basis = match_basis(b_text, vocab)
            continue
        if _INFERENCE.match(stripped):
            after_inference = Inference(text=stripped, conclusion=None)
            arg.inferences.append(after_inference)
            continue
        if m := _NUMBERED.match(stripped):
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
    r"^(?:===\s*\n)?\s*asks:\s*none\s*(?:\n\s*===)?\s*\n\s*\[no\s+claim\]\s*$",
    re.IGNORECASE,
)


def is_null_form(block_text: str | None) -> bool:
    """True when a fenced argdown block is the null form declaring no claim."""
    if not block_text or not block_text.strip():
        return False
    norm = normalise_argdown_block(block_text)
    return bool(_NULL_FORM_RE.match(norm.strip()))


def clean_ansi(text: str, file_path: str | None = None) -> str:
    """Strip ANSI escape sequences from parser output and normalize paths."""
    clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text).strip()
    if file_path:
        clean = clean.replace(file_path, "<argdown>")
    clean = re.sub(rf"{re.escape(tempfile.gettempdir())}/[^\s]+\.argdown", "<argdown>", clean)
    return re.sub(r"/tmp/[^\s]+\.argdown", "<argdown>", clean)


def sanitise_argdown_text(text: str) -> str:
    """Pass-through for backward compatibility without regex pre-mutation."""
    return text


def check_argdown_block(
    block_text: str,
    parser_bin: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Parse and validate an Argdown block using a native tolerant parser.

    Checks:
    1. Argdown syntax validity (clean frontmatter, statements, inferences, relations).
    2. Undercut check: any undercut (_>) must target an inference (toType == 'inference').
    3. Orphan statement check: statements must have relations or argument membership.

    Returns:
        (valid: bool, reason_or_error: str, ast: dict | None)
    """
    if not block_text or not block_text.strip():
        return (
            False,
            "Argdown syntax error: empty block\n"
            "Defect: The ```argdown block contains no content.\n"
            "Required remediation format:\n"
            "```argdown\n"
            "===\n"
            "asks:\n"
            "  <ask_id>: <question or description>\n"
            "answers:\n"
            "  <ask_id>: <line_number | none>\n"
            "===\n\n"
            "(1) <empirical observation quoting deciding values>. -- <basis phrase> ^note\n"
            "-- <warrant rule>. Unless: <defeater>; <status>. --\n"
            "(2) So, <conclusion answering ask>.\n"
            "```",
            None,
        )

    block_text = normalise_argdown_block(block_text)
    lines = block_text.splitlines()

    # 1. Frontmatter check
    start = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    body_lines = textwrap.dedent("\n".join(lines)).splitlines()
    if start is not None and lines[start].strip() == _FRONTMATTER_FENCE:
        end = None
        for i in range(start + 1, len(lines)):
            if lines[i].strip() == _FRONTMATTER_FENCE:
                end = i
                break
        if end is None:
            return (
                False,
                "Argdown syntax error:\n"
                "Defect: Unclosed frontmatter fence (missing closing '===').\n"
                "Required remediation format:\n"
                "===\n"
                "asks:\n"
                "  <ask_id>: <question or description>\n"
                "answers:\n"
                "  <ask_id>: <line_number | none>\n"
                "===\n"
                "<argument body>",
                None,
            )
        fm_text = textwrap.dedent("\n".join(lines[start + 1 : end])).strip("\n")
        try:
            fm_data = yaml.safe_load(fm_text)
        except yaml.YAMLError as exc:
            return (
                False,
                f"Argdown syntax error:\n"
                f"Defect: Invalid YAML frontmatter: {exc}\n"
                f"Required remediation format:\n"
                f"===\n"
                f"asks:\n"
                f"  <ask_id>: <question or description>\n"
                f"answers:\n"
                f"  <ask_id>: <line_number | none>\n"
                f"===\n"
                f"PASS needs 'Waived: block -- <justification>' if intentionally waiving an unparseable block.",
                None,
            )

        if fm_data is not None and not isinstance(fm_data, dict):
            return (
                False,
                "Argdown frontmatter error:\n"
                f"Defect: Frontmatter must be a YAML mapping (dictionary), got {type(fm_data).__name__}.\n"
                "Required remediation format:\n"
                "===\n"
                "asks:\n"
                "  <ask_id>: <question or description>\n"
                "answers:\n"
                "  <ask_id>: <line_number | none>\n"
                "===",
                None,
            )

        if fm_data:
            asks_val = fm_data.get("asks")
            answers_val = fm_data.get("answers")
            if asks_val and isinstance(asks_val, dict):
                if answers_val is None:
                    return (
                        False,
                        "Argdown frontmatter error:\n"
                        "Defect: Missing 'answers:' section in frontmatter when 'asks:' is defined.\n"
                        "Required remediation format:\n"
                        "answers:\n" + "\n".join(f"  {k}: <line_number | none>" for k in asks_val),
                        None,
                    )
                if not isinstance(answers_val, dict):
                    return (
                        False,
                        "Argdown frontmatter error:\n"
                        f"Defect: 'answers:' section must be a mapping of ask IDs to line numbers, got {type(answers_val).__name__}.\n"
                        "Required remediation format:\n"
                        "answers:\n" + "\n".join(f"  {k}: <line_number | none>" for k in asks_val),
                        None,
                    )
                unmapped = [k for k in asks_val if k not in answers_val]
                if unmapped:
                    return (
                        False,
                        f"Argdown frontmatter error:\n"
                        f"Defect: Unmapped ask(s) in frontmatter answers: {', '.join(unmapped)}.\n"
                        f"Required remediation format:\n"
                        f"answers:\n" + "\n".join(f"  {k}: <line_number | none>" for k in unmapped),
                        None,
                    )
                parenthesized_answers = []
                for k, v in answers_val.items():
                    s_val = str(v).strip()
                    if re.match(r"^\(\d+\)$", s_val):
                        parenthesized_answers.append((k, s_val, s_val.strip("()")))
                if parenthesized_answers:
                    defect_items = ", ".join(f"'{k}: {v}'" for k, v, _ in parenthesized_answers)
                    remedy_lines = "\n".join(
                        f"  {k}: {clean}" for k, _, clean in parenthesized_answers
                    )
                    return (
                        False,
                        f"Argdown frontmatter error:\n"
                        f"Defect: Parenthesized line number in frontmatter answers: {defect_items}. "
                        f"Argdown frontmatter requires raw integer line numbers without parentheses, or 'none'.\n"
                        f"Required remediation format:\n"
                        f"answers:\n"
                        f"{remedy_lines}",
                        None,
                    )
                invalid_answers = [
                    (k, str(v))
                    for k, v in answers_val.items()
                    if not isinstance(v, int)
                    and str(v).strip().lower() != "none"
                    and not re.match(r"^\(\d+\)$", str(v).strip())
                ]
                if invalid_answers:
                    defect_items = ", ".join(f"'{k}: {v}'" for k, v in invalid_answers)
                    return (
                        False,
                        f"Argdown frontmatter error:\n"
                        f"Defect: Invalid answer value in frontmatter answers: {defect_items}. Must be an integer line number or 'none'.\n"
                        f"Required remediation format:\n"
                        f"answers:\n"
                        + "\n".join(f"  {k}: <line_number | none>" for k, _ in invalid_answers),
                        None,
                    )

        body_lines = textwrap.dedent("\n".join(lines[end + 1 :])).splitlines()
    else:
        body_lines = textwrap.dedent("\n".join(lines)).splitlines()

    statements: dict[str, dict[str, Any]] = {}
    numbered_map: dict[int, str] = {}
    inferences: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    current_inference: dict[str, Any] | None = None
    last_stmt_or_arg: str | None = None

    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Headings: # Heading
        if re.match(r"^#{1,6}\s+", stripped):
            last_stmt_or_arg = None
            continue

        # Inference line: -- ... -- or — ... —
        if stripped.startswith(("--", "—")):
            if line.startswith((" ", "\t")) and _premise_basis(stripped):
                continue
            if _INFERENCE.match(stripped):
                inf: dict[str, Any] = {"text": stripped, "conclusion": None}
                inferences.append(inf)
                current_inference = inf
                last_stmt_or_arg = None
                continue
            return (
                False,
                f"Argdown syntax error:\n"
                f"Defect: Malformed inference line (missing closing '--'): {stripped}\n"
                f"Required remediation format:\n"
                f"-- <warrant rule>. Unless: <defeater>; <status>. --",
                None,
            )

        # Numbered item: (1) ...
        if m_num := _NUMBERED.match(stripped):
            n = int(m_num.group("n"))
            rest = m_num.group("text")
            if rest.startswith(":"):
                return (
                    False,
                    f"Argdown syntax error:\n"
                    f"Defect: Premise number followed by colon '({n}):' is not valid Argdown syntax.\n"
                    f"Required remediation format:\n"
                    f"({n}) {rest.lstrip(':').strip()}",
                    None,
                )
            m_title = re.match(r"^\[(?P<title>[^\]]+)\](?::\s*(?P<text>.*))?$", rest)
            if m_title:
                title = m_title.group("title")
                stmt_text = m_title.group("text") or title
            else:
                title = str(n)
                stmt_text = rest
            numbered_map[n] = title
            stmt = statements.setdefault(
                title,
                {
                    "title": title,
                    "text": stmt_text,
                    "isUsedAsPremise": False,
                    "isUsedAsMainConclusion": False,
                    "isUsedAsIntermediaryConclusion": False,
                    "relations": [],
                    "members": [
                        {
                            "role": "premise" if current_inference is None else "conclusion",
                            "text": stmt_text,
                        }
                    ],
                },
            )
            if current_inference is not None:
                current_inference["conclusion"] = n
                stmt["isUsedAsMainConclusion"] = True
                stmt["members"].append({"role": "conclusion", "text": stmt_text})
                current_inference = None
            else:
                stmt["isUsedAsPremise"] = True
            last_stmt_or_arg = title
            continue

        # Titled statement: [Title]: text or [Title]
        if m_stmt := re.match(r"^\[(?P<title>[^\]]+)\](?::\s*(?P<text>.*))?$", stripped):
            title = m_stmt.group("title")
            stmt_text = m_stmt.group("text") or title
            statements.setdefault(
                title,
                {
                    "title": title,
                    "text": stmt_text,
                    "isUsedAsPremise": False,
                    "isUsedAsMainConclusion": False,
                    "isUsedAsIntermediaryConclusion": False,
                    "relations": [],
                    "members": [],
                },
            )
            last_stmt_or_arg = title
            continue

        # Argument: <Title>: text or <Title>
        if m_arg := re.match(r"^<(?P<title>[^>]+)>(?::\s*(?P<text>.*))?$", stripped):
            title = m_arg.group("title")
            last_stmt_or_arg = title
            continue

        # Relation: +>, ->, _>, ><
        if m_rel := re.match(r"^(?P<rel>\+>|->|_>|><)\s*(?P<target>.*)$", stripped):
            rel_sym = m_rel.group("rel")
            raw_target = m_rel.group("target").strip()
            if not raw_target:
                return (
                    False,
                    f"Argdown syntax error:\n"
                    f"Defect: Relation missing target: {stripped}\n"
                    f"Required remediation format:\n"
                    f"{rel_sym} (n)           # target a numbered line\n"
                    f"{rel_sym} [Statement]   # target a statement title\n"
                    f"{rel_sym} <Inference>   # target an inference",
                    None,
                )
            rel_type = {
                "+>": "support",
                "->": "attack",
                "_>": "undercut",
                "><": "contradict",
            }[rel_sym]

            m_t_stmt = re.match(r"^\[(?P<title>[^\]]+)\]", raw_target)
            m_t_num = re.match(r"^\((?P<n>\d+)\)", raw_target)
            m_t_arg = re.match(r"^<(?P<title>[^>]+)>", raw_target)

            if m_t_stmt:
                to_target = m_t_stmt.group("title")
                to_type = "statement"
                statements.setdefault(
                    to_target, {"title": to_target, "text": to_target, "relations": []}
                )
            elif m_t_num:
                n = int(m_t_num.group("n"))
                to_target = numbered_map.get(n, str(n))
                to_type = "statement"
            elif m_t_arg:
                to_target = m_t_arg.group("title")
                to_type = "inference" if rel_sym == "_>" else "argument"
            else:
                to_target = raw_target
                to_type = "statement"

            src = last_stmt_or_arg or "unknown"
            relations.append(
                {
                    "relationType": rel_type,
                    "from": src,
                    "to": to_target,
                    "toType": to_type,
                }
            )
            if src in statements:
                statements[src].setdefault("relations", []).append(to_target)
            continue

        # Indented metadata or tags under previous statement: {attr: ...} or #tag
        if line.startswith((" ", "\t")) and (stripped.startswith(("{", "#"))):
            continue

        # If line does not match any valid Argdown construct, it is a syntax error
        m_md_num = re.match(r"^(\d+)[.)]\s*(.*)$", stripped)
        if m_md_num:
            n, text = m_md_num.group(1), m_md_num.group(2)
            return (
                False,
                f"Argdown syntax error:\n"
                f"Defect: Markdown numbered list '{stripped}' is not valid Argdown syntax.\n"
                f"Required remediation format:\n"
                f"({n}) {text} -- <basis phrase>",
                None,
            )
        m_colon_num = re.match(r"^\((\d+)\):\s*(.*)$", stripped)
        if m_colon_num:
            n, text = m_colon_num.group(1), m_colon_num.group(2)
            return (
                False,
                f"Argdown syntax error:\n"
                f"Defect: Premise number followed by colon '({n}):' is not valid Argdown syntax.\n"
                f"Required remediation format:\n"
                f"({n}) {text}",
                None,
            )
        return (
            False,
            f"Argdown syntax error:\n"
            f"Defect: Unexpected syntax: '{stripped}'\n"
            f"Required remediation format:\n"
            f"Argdown lines must be one of:\n"
            f"  (n) <statement>. -- <basis phrase> ^note       # Numbered premise\n"
            f"  -- <warrant>. Unless: <defeater>; <status>. --  # Inference bar\n"
            f"  (n) So, <conclusion>.                           # Conclusion line\n"
            f"  [Title]: <statement text>                       # Statement declaration\n"
            f"  +> (n) | -> (n) | _> <Inference>                # Relation line",
            None,
        )

    ast_data: dict[str, Any] = {
        "statements": statements,
        "relations": relations,
        "inferences": inferences,
    }

    # Machine Check 1: Undercut check: any undercut (_>) must target an inference
    for r in relations:
        if r.get("relationType") == "undercut":
            if r.get("toType") != "inference":
                target = r.get("to")
                target_type = r.get("toType")
                src = r.get("from")
                return (
                    False,
                    f"Argdown argument invalid: undercut from '{src}' targets {target_type} '{target}' instead of an inference\n"
                    f"Defect: Undercut (_>) from '{src}' targets {target_type} '{target}' instead of an inference.\n"
                    f"Required remediation format:\n"
                    f"Undercuts (_>) must target an inference bar title (<Inference>), not a statement or line number.\n"
                    f"Example:\n"
                    f"<Warrant Title>\n"
                    f"-- Warrant rule. Unless: defeater; status. --\n"
                    f"(n) Conclusion.\n\n"
                    f"[{src}]\n"
                    f"  _> <Warrant Title>    # undercut targets the inference\n"
                    f"# OR if attacking a statement directly, use attack (->):\n"
                    f"  -> ({target})",
                    ast_data,
                )

    # Machine Check 2: Orphan statement check: statements must have relations or argument membership
    connected_statements: set[str] = set()
    for r in relations:
        rel_from = r.get("from")
        if isinstance(rel_from, str):
            connected_statements.add(rel_from)
        rel_to = r.get("to")
        if isinstance(rel_to, str):
            connected_statements.add(rel_to)
    for title, stmt in statements.items():
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

    for title, stmt in statements.items():
        if title not in connected_statements:
            text = stmt.get("text") or title
            return (
                False,
                f"Argdown argument invalid: orphan statement '{title}' ('{text}') has no relations or argument membership\n"
                f"Defect: Statement '[{title}]' ('{text}') has no relations or argument membership.\n"
                f"Required remediation format:\n"
                f"Connect the statement using a relation or include it as a numbered premise/conclusion:\n"
                f"[{title}]: {text}\n"
                f"  +> (n)    # supports line (n)\n"
                f"# OR make it a numbered premise:\n"
                f"(n) {text} -- <basis phrase>",
                ast_data,
            )

    return True, "", ast_data


# ---------------------------------------------------------------------------
# The checker's reason
# ---------------------------------------------------------------------------


def _parse_waived_entries(
    waived_lines: list[str], vocab: Vocabulary
) -> tuple[list[str], list[str]]:
    items: list[str] = []
    bad: list[str] = []
    for entry in waived_lines:
        parts = entry.split(";")
        in_justification = False
        for part in parts:
            p = part.strip()
            if not p or _is_none(p):
                continue
            item = match_format_item(p, vocab)
            if item:
                if item not in items:
                    items.append(item)
                seps = list(_SEPARATOR.finditer(p))
                in_justification = bool(seps)
            else:
                seps = list(_SEPARATOR.finditer(p))
                if in_justification and not seps:
                    continue
                bad.append(p)
                in_justification = bool(seps)
    return items, bad


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

    def valid_entries(self) -> list[ValidMatch | None]:
        return [_match_valid_part(e) for e in self.get("Valid")]

    def defect_tags(self, vocab: Vocabulary) -> list[str]:
        tags: list[str] = []
        for m in self.valid_entries():
            if not m:
                continue
            sub_matches = m.clauses if m.clauses else (m,)
            for sub in sub_matches:
                if sub.word == "fails":
                    rest = sub.rest.strip()
                    for tag in _TAG.findall(rest.split(" -- ")[0].split(" — ")[0]):
                        if tag in vocab.defect_tags:
                            tags.append(tag)
        return tags

    def waived_items(self, vocab: Vocabulary) -> list[str]:
        return _parse_waived_entries(self.get("Waived"), vocab)[0]

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
    current_key: str | None = None
    for raw_line in (text or "").splitlines():
        if m := line_re.match(raw_line):
            current_key = str(m.group("key"))
            val = m.group("value").strip()
            if val:
                if current_key == "Valid":
                    parts = [p.strip() for p in re.split(r";\s*(?=\(\d+\))", val) if p.strip()]
                    reason.entries.setdefault(current_key, []).extend(parts)
                else:
                    reason.entries.setdefault(current_key, []).append(val)
        elif current_key is not None:
            stripped = raw_line.strip()
            if not stripped:
                continue
            if (
                raw_line.startswith((" ", "\t"))
                or stripped.startswith(("- ", "* "))
                or (current_key == "Valid" and stripped.startswith("("))
            ):
                val = re.sub(r"^[-*]\s+", "", stripped)
                if current_key == "Valid":
                    parts = [p.strip() for p in re.split(r";\s*(?=\(\d+\))", val) if p.strip()]
                    reason.entries.setdefault(current_key, []).extend(parts)
                else:
                    reason.entries.setdefault(current_key, []).append(val)
            else:
                current_key = None
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


def remediation_for_failure(failure: str) -> str:
    """Return actionable remediation guidance for a pass failure message."""
    if "0 inference lines" in failure:
        return (
            "Required remediation format: Add at least one inference bar followed by a conclusion:\n"
            "(1) <empirical observation>. -- <basis phrase>\n"
            "-- <warrant rule>. Unless: <defeater>; <status>. --\n"
            "(2) So, <conclusion answering ask>."
        )
    if "missing keyed lines" in failure:
        return (
            "Required remediation format: Reason must include all 7 keyed lines:\n"
            "Judged: <claim_id>; asks <ask_id>\n"
            "Valid: (n) holds -- <rule and why it yields (n)>\n"
            "Supported: weakest <basis phrase> -- (<premise n>) <reason>\n"
            "Answered: <ask_id> ← (n)\n"
            "Sufficient: (n) material; obvious; no objection\n"
            "Waived: none\n"
            "Relay: none"
        )
    if "Judged ask ids" in failure and "do not equal" in failure:
        return (
            "Required remediation format: Ensure Judged names the exact ask IDs in the block's frontmatter:\n"
            "Judged: <claim_id>; asks <ask_id>, <ask_id>\n"
            "# Or if wording was modified, waive ask wording: Waived: ask wording -- <justification>"
        )
    if "no ask ids" in failure:
        return (
            "Required remediation format:\n"
            "In block frontmatter:\n"
            "===\n"
            "asks:\n"
            "  <task_id/ACn>: <description>\n"
            "answers:\n"
            "  <task_id/ACn>: <line_number>\n"
            "===\n"
            "In reason:\n"
            "Judged: <claim_id>; asks <task_id/ACn>"
        )
    if "Answered entries not in the form" in failure:
        return (
            "Required remediation format:\n"
            "Answered: <ask_id> ← (n)        # note left arrow and parenthesized line number\n"
            "# or:\n"
            "Answered: <ask_id> unanswered"
        )
    if "Answered names lines not in the block" in failure:
        return (
            "Required remediation format: Point Answered to conclusion lines defined in the block:\n"
            "Answered: <ask_id> ← (<existing_line_number>)"
        )
    if "the block's answers are not a line number or none" in failure:
        return (
            "Required remediation format:\n"
            "===\n"
            "answers:\n"
            "  <ask_id>: <line_number | none>    # raw integer, e.g. 4, not (4)\n"
            "==="
        )
    if "the block's answers name lines not in the block" in failure:
        return (
            "Required remediation format: Ensure frontmatter answers reference line numbers defined in the block:\n"
            "answers:\n"
            "  <ask_id>: <line_number_in_block>"
        )
    if "unmapped ask(s) in block frontmatter" in failure:
        return (
            "Required remediation format: Map each ask to an answering line number or 'none':\n"
            "answers:\n"
            "  <ask_id>: <line_number | none>"
        )
    if "no Answered line for ask ids" in failure:
        return (
            "Required remediation format: Add an Answered entry for each ask ID in the reason:\n"
            "Answered: <ask_id> ← (n)\n"
            "# or:\n"
            "Answered: <ask_id> unanswered"
        )
    if "Valid entries not in the form" in failure:
        return (
            "Required remediation format:\n"
            "Valid: (n) holds -- <rule and why it yields (n)>\n"
            "# or on failure:\n"
            "Valid: (n) fails #<defect-tag> -- <explanation>"
        )
    if "Valid says fails" in failure:
        return (
            "Required remediation: A PASS verdict requires all inference steps to hold. "
            "If any step fails, record REVISE or FAIL instead:\n"
            "  verdict.py --claim <id> --verdict REVISE --reason-file <path>"
        )
    if "inference line with no conclusion line" in failure:
        return (
            "Required remediation format: Add a numbered conclusion line immediately after the inference bar:\n"
            "-- <warrant rule>. Unless: <defeater>; <status>. --\n"
            "(n) So, <conclusion>."
        )
    if "Valid has" in failure and "entries for" in failure:
        return (
            "Required remediation format: Valid must account for each inference line's yielded conclusion:\n"
            "Valid: (<conclusion_n>) holds -- <rule>"
        )
    if "Valid is keyed by lines" in failure:
        return (
            "Required remediation format: Key Valid entries by the yielded conclusion numbers:\n"
            "Valid: (<conclusion_n>) holds -- <rule>"
        )
    if "Supported names no basis phrase" in failure:
        return (
            "Required remediation format: Use an exact basis phrase from the closed vocabulary:\n"
            "Supported: weakest <basis phrase> -- (<premise n>) <reason>"
        )
    if "the block's weakest premise is" in failure:
        return (
            "Required remediation format: Supported must name the lowest-ranking basis among all premises:\n"
            "Supported: weakest <weakest_basis_phrase> -- (<weakest_premise_number>) <reason>"
        )
    if "Waived entries that do not start" in failure:
        return (
            "Required remediation format:\n"
            "Waived: none\n"
            "# or:\n"
            "Waived: <format item> -- <justification>"
        )
    if "the judged text has no argdown block that parses" in failure:
        return (
            "Required remediation: Fix syntax/formatting so the argdown block parses, "
            "or record 'Waived: block -- <justification>'."
        )
    if "Relay names" in failure:
        return (
            'Required remediation format:\nRelay: "<sentence to relay>" ← (n)\n# or:\nRelay: none'
        )
    return ""


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
    waived = reason.waived_items(vocab)
    block_waived = "block" in waived
    ask_wording_waived = "ask wording" in waived

    missing = [k for k in vocab.reason_keys if not reason.get(k)]
    if missing:
        failures.append(f"missing keyed lines: {', '.join(missing)}")
    for key in ("Judged", "Supported"):
        count = len(reason.get(key))
        if count > 1:
            failures.append(f"{key} must appear exactly once; found {count}")

    judged_asks = reason.judged_asks
    if block is not None and not block_waived and not ask_wording_waived:
        if sorted(set(judged_asks)) != sorted(set(block.asks)):
            failures.append(
                f"Judged ask ids {sorted(set(judged_asks))} do not equal the block's "
                f"asks {sorted(set(block.asks))}"
            )
    ask_ids = judged_asks if (block is None or block_waived or ask_wording_waived) else block.asks
    if not ask_ids:
        failures.append(
            "no ask ids: the block's frontmatter has no asks and Judged names none"
            if (block is not None and not block_waived)
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
    if block is not None and not block_waived:
        named = {a[1] for a in answered if a and a[1] is not None}
        absent = sorted(named - set(block.lines))
        if absent:
            failures.append(
                f"Answered names lines not in the block ({', '.join(map(str, absent))})"
            )
    if block is not None and not block_waived:
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
        unmapped_block_asks = sorted(set(block.asks) - set(block.answers.keys()))
        if unmapped_block_asks:
            failures.append(
                f"unmapped ask(s) in block frontmatter: {', '.join(unmapped_block_asks)}"
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
    fails: list[str] = []
    for m in valid:
        if not m:
            continue
        sub_list = m.clauses if m.clauses else (m,)
        for sub in sub_list:
            if sub.word == "fails":
                fails.extend(str(ln) for ln in sub.lines)
    if fails:
        failures.append(f"Valid says fails for ({'), ('.join(fails)})")
    if block is not None and not block_waived:
        if len(block.inferences) == 0:
            failures.append(
                "report argument block has 0 inference lines (-- <warrant>. Unless: <defeater>; <status>. --); cannot record PASS"
            )
        else:
            orphans = [inf.text for inf in block.inferences if inf.conclusion is None]
            if orphans:
                failures.append(
                    "inference line with no conclusion line after it: "
                    + "; ".join(repr(t) for t in orphans)
                )
            keyed = sorted({line for m in valid if m for line in m.lines})
            if len(keyed) != len(block.inferences):
                failures.append(
                    f"Valid has {len(keyed)} entries for {len(block.inferences)} inference lines"
                )
            elif not orphans:
                expected = sorted(int(inf.conclusion or 0) for inf in block.inferences)
                if keyed != expected:
                    failures.append(
                        f"Valid is keyed by lines {keyed}; the inference lines yield {expected}"
                    )

    if block is not None and not block_waived and block.premises and reason.get("Supported"):
        named = reason.supported_basis(vocab)
        if named is None:
            failures.append(
                f"Supported names no basis phrase from {vocab.path.name}: "
                f"{reason.get('Supported')[0]!r}"
            )
        else:
            basis_wording_waived = "basis wording" in waived
            premise_ranks: list[tuple[Premise, int]] = []
            for p in block.premises:
                if p.basis is not None:
                    premise_ranks.append((p, p.rank))
                elif basis_wording_waived:
                    premise_ranks.append((p, named.rank))
                else:
                    premise_ranks.append((p, 0))
            lowest = min(r for _, r in premise_ranks)
            if named.rank != lowest:
                weakest_p = min(premise_ranks, key=lambda pr: pr[1])[0]
                shown = weakest_p.basis.phrase if weakest_p.basis else "an unmatched basis"
                failures.append(
                    f"Supported names {named.phrase!r} (rank {named.rank}); the block's weakest "
                    f"premise is ({weakest_p.number}) {shown!r} (rank {lowest})"
                )
    elif (
        block is None or block_waived or (block is not None and not block.premises)
    ) and reason.get("Supported"):
        named = reason.supported_basis(vocab)
        if named is None:
            failures.append(
                f"Supported names no basis phrase from {vocab.path.name}: "
                f"{reason.get('Supported')[0]!r}"
            )

    _, bad_waived = _parse_waived_entries(reason.get("Waived"), vocab)
    if bad_waived:
        failures.append(
            "Waived entries that do not start with a format item "
            f"({', '.join(vocab.format_items)}): " + "; ".join(repr(e) for e in bad_waived)
        )
    if block is None and not block_waived:
        failures.append(
            "the judged text has no argdown block that parses: PASS needs 'Waived: block -- ...'"
        )

    for entry in reason.get("Relay"):
        if _is_none(entry):
            continue
        refs = relay_refs(entry)
        if not refs:
            failures.append(f"Relay names no line: {entry!r}")
        elif block is not None and not block_waived:
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

    keyed_lines = {line for m in reason.valid_entries() if m for line in m.lines}
    attrs["premise_check.inference_count"] = (
        len(block.inferences)
        if block is not None
        else (len(keyed_lines) or len(reason.get("Valid")))
    )
    tags = reason.defect_tags(vocab)
    attrs["premise_check.defect_tags"] = tags
    attrs["premise_check.defect_tag_count"] = len(tags)
    attrs["premise_check.waived_items"] = reason.waived_items(vocab)
    attrs["premise_check.no_claim"] = reason.no_claim
    return attrs
