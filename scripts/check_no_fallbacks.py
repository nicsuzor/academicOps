#!/usr/bin/env -S uv run python
"""Pre-commit hook: Block silent fallback patterns.

Enforces P#8 / `halt-on-failure` (Fail-Fast Code): No defaults, no fallbacks, no workarounds,
no silent failures. Required values fail loudly when absent.

Detects, across Python / shell / agent-env-map.conf:

Python (AST):
  1. .get(..., "") / .get(..., []) / .get(..., {}) — empty fallbacks (legacy)
  2. ... or "" / ... or [] / ... or {}            — empty fallback chains
  3. os.environ.get(KEY, "non-empty-literal")      — env-var literal default
  4. os.getenv(KEY, "non-empty-literal")           — env-var literal default
  5. os.environ.setdefault(KEY, "literal")         — env-var literal default
  6. {**a, **b} (2+ ** unpackings)                 — dict-merge backfill: one
                                                     source silently backfills
                                                     another (#1918).
  7. except ...: return {} / "" / [] / None        — swallow-to-empty: a failure
                                                     is swallowed into an empty
                                                     value a caller will backfill
                                                     (#1918).
  8. a.get(x) or b.get(x) / a.get(x) or b[x]       — get-or-get chain: the right
                                                     operand is a DIFFERENT source
                                                     lookup, masking the first
                                                     source's value (#1918).

Shell (regex on .sh files):
  6. ${VAR:-non-empty-literal}                     — env-var literal default
                                                     (computed defaults like
                                                     $(whoami) are allowed)

agent-env-map.conf (regex):
  7. KEY:=non-empty-literal                        — leaks the literal into
                                                     every consumer of the
                                                     env-map (host SessionStart
                                                     hook + container launcher).
                                                     Use KEY=KEY (forward) and
                                                     set the literal at the
                                                     point of need.

Allowlists:
  - A trailing comment '# allow-fallback: <reason>' on the same line
    suppresses the violation. Reason is required — empty allows are
    treated as violations.

Usage:
    check_no_fallbacks.py [files...]
    check_no_fallbacks.py --update-baseline

    With no args: scans ALL first-party Python / shell / agent-env-map.conf
    under $AOPS/{aops-core,polecat,scripts,aops-tools} (excluding vendored /
    build trees: .venv, dist, node_modules, __pycache__, .claude). This is the
    SAME surface the pre-commit `files:` glob matches, so a bare run and the
    hook agree (see `_in_scope`).

    --update-baseline: regenerate `check_no_fallbacks_baseline.json` from the
    current scan. The baseline grandfathers PRE-EXISTING violations (per file,
    per pattern) so the widened glob can land before the P0 content-sweep
    (aops-682e75a5) finishes burning them down. NEW fallbacks — beyond the
    grandfathered per-(file, pattern) counts — still fail loudly. The baseline
    shrinks to {} as the sweep lands; delete the file once empty.

Exit codes:
    0: clean (or only grandfathered violations remain)
    1: new violation(s) detected (blocks commit)
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath

# ---------------------------------------------------------------------------
# Allow-fallback comment: a strict opt-out marker that requires a reason.
# Format:  # allow-fallback: <non-empty reason text>
# Empty or absent reasons are not honoured — they are treated as violations.
# ---------------------------------------------------------------------------
_ALLOW_RE = re.compile(r"#\s*allow-fallback:\s*(\S.*)$")


def _line_allowed(
    source_lines: list[str], start_lineno: int, end_lineno: int | None = None
) -> bool:
    """Return True if any line in the range [start_lineno, end_lineno] (1-based, inclusive)
    ends with an `allow-fallback` comment carrying a non-empty reason."""
    if end_lineno is None:
        end_lineno = start_lineno
    for line_num in range(start_lineno, end_lineno + 1):
        if 0 < line_num <= len(source_lines):
            if _ALLOW_RE.search(source_lines[line_num - 1]):
                return True
    return False


# ---------------------------------------------------------------------------
# Python AST checker
# ---------------------------------------------------------------------------


_ENV_GETTERS = {
    # qualified name → arg index of the default value
    "os.environ.get": 1,
    "os.getenv": 1,
    "os.environ.setdefault": 1,
}


def _qualified_name(node: ast.AST) -> str | None:
    """Best-effort qualified name reconstruction for Attribute/Name chains."""
    parts: list[str] = []
    cur: ast.AST | None = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


class FallbackDetector(ast.NodeVisitor):
    """AST visitor that detects silent-fallback patterns in Python."""

    def __init__(self, filepath: Path, source_lines: list[str]) -> None:
        self.filepath = filepath
        self.source_lines = source_lines
        self.violations: list[dict] = []
        self.current_statement_span: tuple[int, int] | None = None

    def visit(self, node: ast.AST) -> None:
        is_stmt = isinstance(node, ast.stmt)
        old_span = self.current_statement_span
        if is_stmt:
            self.current_statement_span = (
                node.lineno,
                getattr(node, "end_lineno", None) or node.lineno,
            )
        try:
            super().visit(node)
        finally:
            if is_stmt:
                self.current_statement_span = old_span

    # -- helpers ------------------------------------------------------------

    def _record(self, node: ast.expr, pattern: str, message: str) -> None:
        if self.current_statement_span:
            start_line, end_line = self.current_statement_span
        else:
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", None) or start_line
        if _line_allowed(self.source_lines, start_line, end_line):
            return
        self.violations.append(
            {
                "file": str(self.filepath),
                "line": node.lineno,
                "col": node.col_offset,
                "pattern": pattern,
                "message": message,
            }
        )

    @staticmethod
    def _is_empty_value(node: ast.expr) -> bool:
        if isinstance(node, ast.Constant) and node.value == "":
            return True
        if isinstance(node, ast.List) and len(node.elts) == 0:
            return True
        if isinstance(node, ast.Dict) and len(node.keys) == 0:
            return True
        return False

    @staticmethod
    def _is_empty_return_value(node: ast.expr | None) -> str | None:
        """If `node` is an empty literal eligible for the swallow-to-empty
        check (``{}``, ``""``, ``[]`` or ``None`` / bare return), return a short
        rendering of it; else return None.

        Bare `return` (node is None) and `return None` both count: they swallow
        a failure into a None that a caller will treat as 'absent' and backfill."""
        if node is None:
            return "None"
        if isinstance(node, ast.Constant):
            if node.value == "":
                return '""'
            if node.value is None:
                return "None"
            return None
        if isinstance(node, ast.List) and len(node.elts) == 0:
            return "[]"
        if isinstance(node, ast.Dict) and len(node.keys) == 0:
            return "{}"
        return None

    @staticmethod
    def _handler_returns(body: list[ast.stmt]):
        """Yield `return` statements that belong to an except handler body:
        descend into plain control-flow blocks (if/for/while/with/try) but stop
        at nested function/class defs (their returns are unrelated) and at nested
        except handlers (each reports its own returns — no double-counting)."""
        stack = list(body)
        while stack:
            stmt = stack.pop()
            if isinstance(stmt, ast.Return):
                yield stmt
                continue
            if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                continue
            if isinstance(stmt, ast.Try):
                stack.extend(stmt.body)
                stack.extend(stmt.orelse)
                stack.extend(stmt.finalbody)
                # NB: stmt.handlers are intentionally skipped — each nested
                # except handler is visited on its own.
                continue
            for child in ast.iter_child_nodes(stmt):
                if isinstance(child, ast.stmt):
                    stack.append(child)
        # (order does not matter — violations are sorted/counted downstream)

    @staticmethod
    def _is_source_lookup(node: ast.expr) -> bool:
        """True if `node` reads a value out of some source: ``x.get(...)`` or a
        subscript ``x[...]``. Used by the get-or-get chain check to tell a
        value-masking cross-source fallback (``a.get(k) or b.get(k)``) apart
        from an empty-literal fallback (already covered by visit_BoolOp)."""
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and len(node.args) >= 1
        ):
            return True
        if isinstance(node, ast.Subscript):
            return True
        return False

    @staticmethod
    def _lookup_source_name(node: ast.expr) -> str | None:
        """Best-effort name of the object a source lookup reads FROM, so we can
        tell whether two lookups hit DIFFERENT sources. ``a.get(k)`` -> 'a';
        ``a[k]`` -> 'a'; ``self.cfg.get(k)`` -> 'self.cfg'."""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            return _qualified_name(node.func.value)
        if isinstance(node, ast.Subscript):
            return _qualified_name(node.value)
        return None

    @staticmethod
    def _is_nonempty_literal(node: ast.expr) -> bool:
        """A literal with a non-empty *primitive* value: str, int, float, bool.
        We deliberately do *not* flag None (signals 'unset' explicitly), nor
        function calls like os.path.expanduser / Path.home / os.getcwd
        (those are computed at runtime, not silent literal defaults)."""
        if isinstance(node, ast.Constant):
            v = node.value
            if v is None or v == "":
                return False
            return isinstance(v, str | int | float | bool)
        return False

    # -- visitors -----------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        # Pattern 1: x.get(key, EMPTY)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and len(node.args) >= 2:
            default_arg = node.args[1]
            if self._is_empty_value(default_arg):
                self._record(
                    node,
                    f".get(..., {ast.unparse(default_arg)})",
                    "Silent fallback to empty value. Raise if value required, "
                    "or annotate with `# allow-fallback: <reason>`.",
                )

        # Patterns 3-5: env-var getters with literal defaults
        qname = _qualified_name(node.func) if isinstance(node.func, ast.Attribute) else None
        if qname in _ENV_GETTERS and len(node.args) > _ENV_GETTERS[qname]:
            default_arg = node.args[_ENV_GETTERS[qname]]
            if self._is_nonempty_literal(default_arg):
                self._record(
                    node,
                    f"{qname}(..., {ast.unparse(default_arg)})",
                    "Env-var literal default. Required values must fail-fast "
                    "if unset. Move the default to polecat.yaml, or annotate "
                    "`# allow-fallback: <reason>` if genuinely optional.",
                )

        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if isinstance(node.op, ast.Or):
            last = node.values[-1]
            if self._is_empty_value(last):
                self._record(
                    node,
                    f"... or {ast.unparse(last)}",
                    "Silent fallback chain. Raise if value required.",
                )
            else:
                # Pattern 8: get-or-get chain — `a.get(x) or b.get(x)` /
                # `a.get(x) or b[x]`. We flag each adjacent (left `or` right)
                # pair where BOTH sides are source lookups AND they read from
                # DIFFERENT sources: that masks the first source's value with a
                # second source's value (the value-masking cross-source fallback
                # the empty-literal check above is blind to). Same-source pairs
                # (`d.get(a) or d.get(b)`) are NOT flagged — that is ordinary
                # short-circuit selection within one source, not a fallback.
                for left, right in zip(node.values, node.values[1:], strict=False):
                    if self._is_source_lookup(left) and self._is_source_lookup(right):
                        lname = self._lookup_source_name(left)
                        rname = self._lookup_source_name(right)
                        if lname is not None and rname is not None and lname != rname:
                            self._record(
                                node,
                                f"{ast.unparse(left)} or {ast.unparse(right)}",
                                "Cross-source value-masking fallback "
                                f"(reads {lname!r}, then silently falls back to "
                                f"{rname!r}). Raise if the value is required, or "
                                "annotate `# allow-fallback: <reason>`.",
                            )
                            break
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        # Pattern 6: dict-merge backfill — `{**a, **b}` with 2+ `**` unpackings.
        # In an ast.Dict, a `**x` unpacking is a key of None. Two or more such
        # unpackings means one source silently backfills another. We are
        # judicious (2+ unpackings, not a single `{**a, "k": v}` add) but per A8
        # surfacing these for explicit `# allow-fallback:` annotation is correct.
        unpack_count = sum(1 for k in node.keys if k is None)
        if unpack_count >= 2:
            self._record(
                node,
                "{**a, **b}",
                "Dict-merge backfill: merging 2+ sources silently lets one "
                "backfill another. Make the precedence/required source explicit "
                "and raise if absent, or annotate `# allow-fallback: <reason>`.",
            )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # Pattern 7: swallow-to-empty — an except handler whose body returns an
        # empty literal (`return {}` / `return ""` / `return []` / `return None`
        # / bare `return`). The failure is swallowed into an empty value a caller
        # will treat as 'absent' and backfill. We scan only `return` statements
        # in the handler body (including nested ones), since that is the shape
        # that leaks the empty value back to the caller. We collect returns that
        # belong to THIS handler — descending into plain blocks (if/for/with/try)
        # but NOT into nested functions/classes (their returns are unrelated) nor
        # nested except handlers (each handler reports its own returns, so we
        # avoid double-counting).
        for stmt in self._handler_returns(node.body):
            rendered = self._is_empty_return_value(stmt.value)
            if rendered is None:
                continue
            # Record against the return statement so the allow-fallback
            # annotation can sit on the `return ...` line itself (or, for a
            # bare `return` / `return None`, anywhere on that statement).
            span = (stmt.lineno, getattr(stmt, "end_lineno", None) or stmt.lineno)
            if _line_allowed(self.source_lines, span[0], span[1]):
                continue
            self.violations.append(
                {
                    "file": str(self.filepath),
                    "line": stmt.lineno,
                    "col": stmt.col_offset,
                    "pattern": f"except: return {rendered}",
                    "message": (
                        "Swallow-to-empty: an exception handler returns an empty "
                        "value, hiding the failure from the caller (which will "
                        "backfill it). Re-raise, return a loud sentinel, or "
                        "annotate `# allow-fallback: <reason>`."
                    ),
                }
            )
        self.generic_visit(node)


def check_python_file(filepath: Path) -> list[dict]:
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {filepath}: {e}", file=sys.stderr)
        return []
    detector = FallbackDetector(filepath, source.splitlines())
    detector.visit(tree)
    return detector.violations


# ---------------------------------------------------------------------------
# Shell checker — ${VAR:-DEFAULT} where DEFAULT is a non-empty literal.
# We allow:
#   - ${VAR:?msg}            (fail-fast — that's what we want)
#   - ${VAR:-$OTHER}         (delegate to another env var; not a literal)
#   - ${VAR:-$(...)}         (computed default)
#   - ${VAR:-${OTHER...}}    (delegate / nested expansion; not a literal)
# We flag:
#   - ${VAR:-some_string}
#   - ${VAR:-/some/path}
#   - ${VAR:-true} / :-false / :-0 / :-1
# ---------------------------------------------------------------------------


# Captures: (1) var name, (2) operator (:- or :=), (3) the default body.
# We deliberately keep the default body shallow — anything containing $ or
# `(` is treated as computed and skipped below.
_SHELL_DEFAULT_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-|:=)([^}]*)\}")


def _shell_logical_end(source_lines: list[str], lineno: int) -> int:
    """Find the ending line number of a shell statement that continues via backslash."""
    idx = lineno - 1
    while idx < len(source_lines):
        line = source_lines[idx]
        code, _, _ = line.partition("#")
        if code.rstrip().endswith("\\"):
            idx += 1
        else:
            break
    return min(idx + 1, len(source_lines))


def check_shell_file(filepath: Path) -> list[dict]:
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return []

    violations: list[dict] = []
    lines = source.splitlines()
    for lineno, line in enumerate(lines, start=1):
        # Strip trailing comments before matching to avoid false positives on
        # commented-out examples. Full-line comments produce an empty `code`.
        code, _, _ = line.partition("#")
        if not code.strip():
            continue
        for m in _SHELL_DEFAULT_RE.finditer(code):
            var, _op, default = m.group(1), m.group(2), m.group(3)
            # Skip computed defaults (env-var delegation, command substitution).
            if not default or "$" in default or "`" in default:
                continue
            end_lineno = _shell_logical_end(lines, lineno)
            if _line_allowed(lines, lineno, end_lineno):
                continue
            violations.append(
                {
                    "file": str(filepath),
                    "line": lineno,
                    "col": m.start() + 1,
                    "pattern": f"${{{var}{_op}{default}}}",
                    "message": (
                        f"Shell literal default for ${var}. Use ${{{var}:?msg}} to "
                        "fail-fast, delegate to another env var, or annotate "
                        "`# allow-fallback: <reason>`."
                    ),
                }
            )
    return violations


# ---------------------------------------------------------------------------
# agent-env-map.conf checker — KEY:=non-empty literal.
# Empty literal (KEY:=) is the documented "clear/unset" form — allowed.
# ---------------------------------------------------------------------------


_ENVMAP_LITERAL_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*:=\s*(.+?)\s*$")


def check_envmap_file(filepath: Path) -> list[dict]:
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return []

    violations: list[dict] = []
    lines = source.splitlines()
    for lineno, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Strip inline comments (`KEY:=value  # comment`) before matching value.
        code, _sep, _comment = line.partition("#")
        m = _ENVMAP_LITERAL_RE.match(code.strip())
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if value == "":
            continue  # documented "clear" form
        if _line_allowed(lines, lineno):
            continue
        violations.append(
            {
                "file": str(filepath),
                "line": lineno,
                "col": 1,
                "pattern": f"{key}:={value}",
                "message": (
                    f"Literal default for {key} in agent-env-map.conf. This file "
                    "is applied by the host SessionStart hook AND the container "
                    "launcher — literal defaults leak into every host session "
                    "(see issue #930). Use `KEY=KEY` to forward from parent and "
                    "set the literal at the point of need, or annotate "
                    "`# allow-fallback: <reason>`."
                ),
            }
        )
    return violations


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _check_path(filepath: Path) -> list[dict]:
    name = filepath.name
    if name == "agent-env-map.conf":
        return check_envmap_file(filepath)
    if filepath.suffix == ".py":
        return check_python_file(filepath)
    if filepath.suffix == ".sh":
        return check_shell_file(filepath)
    return []


# ---------------------------------------------------------------------------
# Scope — the single source of truth for "which files do we check".
#
# `_in_scope` is the predicate; `_default_targets` walks it for a bare run.
# The pre-commit `files:` / `exclude:` regex in .pre-commit-config.yaml is a
# hand-maintained second copy of this predicate. The two are kept honest by
# tests/hooks/test_check_no_fallbacks.py::test_bare_run_and_precommit_scope_agree,
# which loads the real glob from the config and asserts it makes the SAME
# include/exclude decision as `_in_scope` on representative paths — so silent
# drift between the two fails CI. Keep them in lock-step when widening scope.
# ---------------------------------------------------------------------------

# First-party Python homes. Everything under these (recursively) is in scope;
# vendored / build / worktree trees below are pruned by `_EXCLUDE_PARTS`.
_SCOPE_DIRS = ("aops-core", "polecat", "scripts", "aops-tools")

# Path components that take a file out of scope no matter where they appear:
# virtualenvs, build output, package caches, and isolated worktrees.
_EXCLUDE_PARTS = frozenset({".venv", "dist", "node_modules", "__pycache__", ".claude"})

# The one non-suffix file we check by name (literal defaults here leak into
# every host session — issue #930). Only the canonical top-level copy.
_ENVMAP_REL = "aops-core/agent-env-map.conf"


def _repo_root() -> Path:
    # Anchor on this script's own location, NOT $AOPS: the script lives inside
    # the repo it checks (scripts/check_no_fallbacks.py -> repo root), so it
    # must scan THIS checkout even when $AOPS points at a different deployed
    # install (e.g. /app while committing from a /workspace worktree).
    return Path(__file__).resolve().parent.parent


def _in_scope(relpath: str) -> bool:
    """True if `relpath` (repo-root-relative, POSIX) is first-party code we
    check. Mirrors the pre-commit `files:`/`exclude:` regex."""
    p = PurePosixPath(relpath)
    parts = p.parts
    if not parts or parts[0] not in _SCOPE_DIRS:
        return False
    if _EXCLUDE_PARTS.intersection(parts):
        return False
    if p.name == "agent-env-map.conf":
        return relpath == _ENVMAP_REL
    return p.suffix in (".py", ".sh")


def _default_targets() -> list[Path]:
    root = _repo_root()
    targets: list[Path] = []
    for scope_dir in _SCOPE_DIRS:
        base = root / scope_dir
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_PARTS]
            for filename in filenames:
                candidate = Path(dirpath) / filename
                try:
                    rel = candidate.resolve().relative_to(root).as_posix()
                except ValueError:
                    continue
                if _in_scope(rel):
                    targets.append(candidate)
    return sorted(targets)


# ---------------------------------------------------------------------------
# Baseline — grandfather PRE-EXISTING violations so the widened glob can land
# before the P0 content-sweep (aops-682e75a5) burns them down. Keyed by
# (repo-relative file, pattern); a per-pattern COUNT is stored. NEW violations
# (beyond the grandfathered count) still fail — line-number-independent so the
# baseline survives edits elsewhere in a file.
# ---------------------------------------------------------------------------

_BASELINE_PATH = Path(__file__).resolve().parent / "check_no_fallbacks_baseline.json"


def _rel_key(filepath: Path) -> str:
    root = _repo_root()
    try:
        return filepath.resolve().relative_to(root).as_posix()
    except ValueError:
        # Outside the repo (e.g. a test tmp file) — never matches the baseline,
        # so such a file's violations always surface. That is the desired
        # behaviour for the regression test.
        return filepath.as_posix()


def _load_baseline() -> dict[str, dict[str, int]]:
    if not _BASELINE_PATH.is_file():
        return {}
    try:
        data = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: could not read baseline {_BASELINE_PATH}: {e}", file=sys.stderr)
        return {}
    if not isinstance(data, dict):
        return {}
    # Absent "baseline" key genuinely means "no grandfathered sites".
    return data.get(
        "baseline", {}
    )  # allow-fallback: the absence of a baseline key in the loaded configuration JSON dictionary means that there are no grandfathered sites to track


def _apply_baseline(violations: list[dict], baseline: dict[str, dict[str, int]]) -> list[dict]:
    """Drop up to the grandfathered count of each (file, pattern); return the
    rest (the net-new violations that must block)."""
    seen: dict[tuple[str, str], int] = defaultdict(int)
    surviving: list[dict] = []
    for v in violations:
        rel = _rel_key(Path(v["file"]))
        pattern = v["pattern"]
        file_baseline = (
            baseline.get(rel) or {}
        )  # allow-fallback: when a file is absent from the baseline configuration, it is treated as having zero grandfathered violations initially
        allowed = file_baseline.get(pattern, 0)
        seen[(rel, pattern)] += 1
        if seen[(rel, pattern)] > allowed:
            surviving.append(v)
    return surviving


def _generate_baseline() -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for filepath in _default_targets():
        if not filepath.is_file():
            continue
        rel = _rel_key(filepath)
        for v in _check_path(filepath):
            counts[rel][v["pattern"]] += 1
    return {rel: dict(sorted(counts[rel].items())) for rel in sorted(counts)}


def main() -> int:
    args = sys.argv[1:]

    if "--update-baseline" in args:
        baseline = _generate_baseline()
        payload = {
            "_comment": (
                "Grandfathered silent-fallback sites pending burn-down by the P0 "
                "content-sweep aops-682e75a5. Keyed by repo-relative file -> "
                "pattern -> count. NEW fallbacks beyond these counts still fail. "
                "Regenerate with `scripts/check_no_fallbacks.py --update-baseline`; "
                "delete this file once the sweep empties it."
            ),
            "baseline": baseline,
        }
        _BASELINE_PATH.write_text(
            json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )
        total = sum(sum(p.values()) for p in baseline.values())
        print(
            f"Wrote baseline: {total} grandfathered site(s) across {len(baseline)} file(s) -> {_BASELINE_PATH}"
        )
        return 0

    files = [Path(f) for f in args] if args else _default_targets()

    all_violations: list[dict] = []
    checked = 0
    for filepath in files:
        if filepath.is_file():
            checked += 1
            all_violations.extend(_check_path(filepath))

    baseline = _load_baseline()
    total_found = len(all_violations)
    all_violations = _apply_baseline(all_violations, baseline)
    grandfathered = total_found - len(all_violations)

    if all_violations:
        print(f"ERROR: {len(all_violations)} silent-fallback pattern(s) detected:\n")
        for v in all_violations:
            print(f"  {v['file']}:{v['line']}:{v['col']}")
            print(f"    Pattern: {v['pattern']}")
            print(f"    Fix:     {v['message']}\n")
        print("halt-on-failure / P#8: No defaults, no fallbacks, no silent failures.")
        print("Required values must fail-fast when absent. Optional values must")
        print("be annotated with `# allow-fallback: <reason>` on the same line.")
        return 1

    msg = f"OK: No new silent-fallback patterns in {checked} file(s)"
    if grandfathered:
        msg += f" ({grandfathered} grandfathered site(s) pending burn-down by aops-682e75a5)"
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
