#!/usr/bin/env python3
"""Fail when a document references a repository path that does not exist.

Configured under ``[tool.refcheck]`` in ``pyproject.toml``: ``include`` lists the
document globs scanned, and each ``[[tool.refcheck.allow]]`` entry exempts named
references that deliberately point outside this repository.

Run directly (``uv run python scripts/check_refs.py``) or via ``make lint``.
Exits 0 when every reference resolves, 1 otherwise.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Documents only. A markdown file is prose about the tree; a shell or YAML file
# is code, where backticks and slashes mean something else entirely.
DOC_SUFFIXES = (".md", ".md.template")

# --- What counts as a reference --------------------------------------------

_MD_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)>\s]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)", re.S)
_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", re.S)
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_FENCE = re.compile(r"^\s*(```|~~~)")

# A URI scheme, a home/absolute/variable-rooted path, or a placeholder: each
# names something outside this repository, and none of them is ours to verify.
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_FOREIGN_PREFIXES = ("/", "~", "$", "{", "<", "@", "!", "%", "#")
# Globs, shell metacharacters, and whitespace mean the span is a pattern or a
# command line, not one concrete path.
_NOT_A_PATH = set("*?<>|$ \t'\"()[]{}=;&")
# A pinpoint line citation — ``handlers.py:99``, ``SKILL.md:1-5``, ``x.md:53,55``.
# It addresses a location *inside* a file, so it is no more part of the filename
# than a ``#anchor`` is; the existence claim is about the file it hangs off.
_LINE_CITATION = re.compile(r":\d+(?:[-,]\d+)*$")
# A trailing extension is what turns `foo/bar` from a phrase into a filename.
_FILE_SUFFIX = re.compile(
    r"\.(md|py|sh|yml|yaml|json|jsonl|toml|txt|cfg|ini|lock|template|ts|tsx|js|sql|css|html)$"
)


@dataclass(frozen=True)
class Miss:
    doc: str
    line: int
    kind: str
    ref: str
    tried: tuple[str, ...]

    def render(self) -> str:
        tried = ", ".join(self.tried) or "(resolves outside the repository)"
        return f"{self.doc}:{self.line}: {self.kind} '{self.ref}' does not exist — tried {tried}"


@dataclass(frozen=True)
class Allowance:
    docs: str
    refs: frozenset[str]
    reason: str

    def render(self) -> str:
        return (
            f"pyproject.toml: [[tool.refcheck.allow]] docs = '{self.docs}' matches no live "
            f"reference: {sorted(self.refs)} — remove it"
        )


# --- Extraction ------------------------------------------------------------


def mask_fences(text: str) -> str:
    """Blank every fenced code block, keeping line numbers intact.

    Fenced blocks are illustrative by construction — shell transcripts, sample
    trees, worked examples — so fencing a path is the visible, deliberate way to
    write one that makes no claim about this tree.
    """
    out, fenced = [], False
    for line in text.split("\n"):
        if _FENCE.match(line):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    return "\n".join(out)


def candidates(text: str):
    """Yield ``(line, kind, raw, unconditional)`` for one document.

    A link target is checked whatever it looks like;
    a wikilink or a code span is checked only when it is repo-shaped, because
    both are also used for PKB notes and for paths in other repositories.
    """
    body = mask_fences(text)
    found = [
        *((m, "link", m.group(1), True) for m in _MD_LINK.finditer(body)),
        *((m, "wikilink", m.group(1), False) for m in _WIKILINK.finditer(body)),
        *((m, "path", m.group(1), False) for m in _CODE_SPAN.finditer(body)),
    ]
    for match, kind, raw, unconditional in found:
        yield body.count("\n", 0, match.start()) + 1, kind, raw, unconditional


def clean(raw: str) -> str | None:
    """Normalise a candidate, or return None when it cannot name a repo path."""
    ref = raw.strip().split("#", 1)[0].split("?", 1)[0].strip()
    if not ref or _SCHEME.match(ref) or ref.startswith(_FOREIGN_PREFIXES):
        return None
    ref = _LINE_CITATION.sub("", ref).strip()
    if not ref:
        return None
    if any(c in _NOT_A_PATH for c in ref):
        return None
    return ref.rstrip("/") or None


def is_repo_shaped(ref: str, top_level: set[str]) -> bool:
    """True when a bare code span names a location rather than a thing.

    Three ways to qualify: an explicitly relative path, a path whose first
    segment names a top-level entry here, or a path with a directory component
    and a file extension. A bare filename never qualifies — ``finalize.py`` in
    prose names a concept, and a whole-tree basename search would guess.
    """
    if ref.startswith(("./", "../")):
        return True
    if "/" not in ref:
        return False
    return ref.split("/", 1)[0] in top_level or bool(_FILE_SUFFIX.search(ref))


# --- The check -------------------------------------------------------------


class RefCheck:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.includes, self.allowances = self._config()
        self.paths = self._repo_paths()
        self.top_level = {p.split("/", 1)[0] for p in self.paths}

    def _config(self) -> tuple[list[str], list[Allowance]]:
        data = tomllib.loads((self.root / "pyproject.toml").read_text(encoding="utf-8"))
        cfg = data.get("tool", {}).get("refcheck")
        if not cfg:
            raise SystemExit("x [tool.refcheck] is missing from pyproject.toml")
        allowances = []
        for entry in cfg.get("allow", []):
            missing = {"docs", "refs", "reason"} - set(entry)
            if missing:
                raise SystemExit(
                    f"x [[tool.refcheck.allow]] entry is missing {sorted(missing)}: {entry}"
                )
            allowances.append(Allowance(entry["docs"], frozenset(entry["refs"]), entry["reason"]))
        return list(cfg.get("include", [])), allowances

    def _repo_paths(self) -> set[str]:
        """Every path git knows about, plus every directory containing one.

        Tracked and untracked-but-not-ignored files both count; ignored build
        output under ``dist/`` does not, so a reference that resolves only on a
        dirty working tree still fails in CI.
        """

        def ls(*args: str) -> list[str]:
            out = subprocess.run(
                ["git", "-C", str(self.root), "ls-files", *args],
                capture_output=True,
                text=True,
                check=True,
            )
            return out.stdout.splitlines()

        paths: set[str] = set()
        for name in [*ls(), *ls("--others", "--exclude-standard")]:
            paths.add(name)
            for parent in Path(name).parents:
                if str(parent) != ".":
                    paths.add(str(parent))
        return paths

    def documents(self) -> list[Path]:
        found: set[Path] = set()
        for pattern in self.includes:
            for path in self.root.glob(pattern):
                if path.is_file() and path.name.endswith(DOC_SUFFIXES):
                    found.add(path)
        return sorted(found)

    def _bases(self, doc: Path) -> list[Path]:
        """Where a reader would look: beside the document, at the root of the
        skill bundle that owns it, then at the repository root."""
        bases = [doc.parent]
        bases += [p for p in doc.parents if (p / "SKILL.md").is_file()]
        return [*bases, self.root]

    def _targets(self, ref: str, doc: Path) -> tuple[str, ...]:
        """Every repo-relative path the reference could mean, in reading order."""
        tried: list[str] = []
        for base in self._bases(doc):
            try:
                rel = (base / ref).resolve().relative_to(self.root).as_posix()
            except ValueError:
                continue  # escapes the repository; not ours to verify
            if rel not in tried:
                tried.append(rel)
        return tuple(tried)

    def run(self) -> tuple[list[Miss], list[Allowance]]:
        """Return unresolved references, and allowances nothing used."""
        used: set[Allowance] = set()
        misses: list[Miss] = []

        for doc in self.documents():
            rel_doc = doc.relative_to(self.root).as_posix()
            text = doc.read_text(encoding="utf-8", errors="replace")
            exempt = [a for a in self.allowances if fnmatch(rel_doc, a.docs)]
            for lineno, kind, raw, unconditional in candidates(text):
                ref = clean(raw)
                if ref is None:
                    continue
                if not unconditional and not is_repo_shaped(ref, self.top_level):
                    continue
                tried = self._targets(ref, doc)
                if set(tried) & self.paths:
                    continue
                allowed = next((a for a in exempt if raw.strip() in a.refs), None)
                if allowed:
                    used.add(allowed)
                    continue
                misses.append(Miss(rel_doc, lineno, kind, raw.strip(), tried))

        return misses, [a for a in self.allowances if a not in used]


def main(root: Path = ROOT) -> int:
    misses, unused = RefCheck(root).run()
    for item in [*misses, *unused]:
        print(item.render())
    if misses or unused:
        print(
            f"\nx {len(misses)} broken reference(s), {len(unused)} stale allowance(s).\n"
            "  Repoint the reference, delete it along with the claim that rested on it,\n"
            "  fence it as an example, or add a [[tool.refcheck.allow]] entry naming it.",
            file=sys.stderr,
        )
        return 1
    print("✓ every documented repository path exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
