#!/usr/bin/env python3
"""Agent compliance lint — validates frontmatter against the four-axes
permissions schema for the academicOps framework.

Axes:
  1. tools: list[str]
  2. mcp_servers: list[str] (optional)
  3. bash_scopes: list[str] (required if Bash in tools)
  4. file_access: { read: [glob], write: [glob] } (required if filesystem tools used)

Rules:
  R1 (error): Bash without bash_scopes
  R2 (error): filesystem tool without file_access.read
  R3 (error): write tool without file_access.write
  R4 (error): unknown bash_scopes value
  R5 (warn):  bash_scopes contains 'unrestricted'
  R6 (error): tools missing or not a list (also: missing/broken frontmatter)
  R7 (warn):  Skill in tools, body suggests sub-agent spawn, but no Agent tool

Exemption: a file with `runtime: github-actions` in its frontmatter is
governed by the workflow YAML's `permissions:` block and the runner's
toolchain, not by the four-axes harness schema. R1–R7 are skipped for
exempt files; only frontmatter parseability (R6's broken-frontmatter
sub-rule) still applies. See `aops-core/AGENT-COMPLIANCE-MATRIX.md`
§ ".github/agents/" for the rationale.

CLI:
  python aops-core/scripts/agent_compliance_lint.py [PATH ...] \
      [--format text|json] [--strict] [--quiet]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

# TODO: skill-side rules out of scope for v1: callable-by-symmetry,
# nested reachability across skill graph. Track via:
SKILL_LINT_RULES_TODO = "skill-side reachability + callable-by symmetry"

DEFAULT_PATHS = ("aops-core/agents", ".github/agents")

DEFAULT_BASH_SCOPES: frozenset[str] = frozenset(
    {
        "git:read",
        "git:write",
        "gh:read",
        "gh:write",
        "pytest",
        "ruff",
        "fs:read",
        "fs:write",
        "net:http",
        "pkg:install",
        "docker",
        "unrestricted",
    }
)

FILESYSTEM_TOOLS: frozenset[str] = frozenset(
    {
        "Read",
        "Write",
        "Edit",
        "NotebookEdit",
        "Glob",
        "Grep",
    }
)
WRITE_TOOLS: frozenset[str] = frozenset({"Write", "Edit", "NotebookEdit"})

EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
    }
)


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    level: str  # "error" | "warning"
    rule: str
    msg: str

    def sort_key(self) -> tuple[str, int, str]:
        return (self.file, self.line, self.rule)

    def format_text(self) -> str:
        return f"{self.file}:{self.line}: {self.level}: {self.rule}: {self.msg}"


def load_bash_scopes(repo_root: Path | None = None) -> frozenset[str]:
    """Load allowed bash_scopes from policies file, fall back to defaults."""
    if repo_root is None:
        return DEFAULT_BASH_SCOPES
    policy = repo_root / "aops-core" / "policies" / "bash_scopes.toml"
    if not policy.is_file():
        return DEFAULT_BASH_SCOPES
    try:
        try:
            import tomllib  # py311+
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(policy.read_text(encoding="utf-8"))
        scopes = data.get("scopes")
        if isinstance(scopes, dict):
            return frozenset(scopes.keys())
        if isinstance(scopes, list):
            return frozenset(str(s) for s in scopes)
    except Exception:
        pass
    return DEFAULT_BASH_SCOPES


def _split_frontmatter(text: str) -> tuple[str | None, int]:
    """Return (yaml_text, line_offset_of_yaml_start) or (None, 1) if missing.

    line_offset is 1-indexed file line where YAML body begins (i.e. line 2
    when the file starts with '---\\n').
    """
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None, 1
    # Skip opening fence
    after = text.split("\n", 1)[1] if "\n" in text else ""
    # Find closing fence: a line that is exactly '---'
    lines = after.split("\n")
    end_idx = None
    for i, ln in enumerate(lines):
        if ln.rstrip("\r") == "---":
            end_idx = i
            break
    if end_idx is None:
        return None, 1
    yaml_text = "\n".join(lines[:end_idx])
    return yaml_text, 2  # YAML body starts at file line 2


def _yaml_line_to_file_line(yaml_line: int, offset: int) -> int:
    """yaml_line is 1-indexed within the YAML block; offset is file line of YAML start."""
    return offset + max(yaml_line, 1) - 1


def _find_key_line(yaml_text: str, key: str) -> int:
    """Best-effort: find the 1-indexed YAML line where a top-level `key:` appears."""
    for i, ln in enumerate(yaml_text.splitlines(), start=1):
        stripped = ln.lstrip()
        if stripped.startswith(f"{key}:") and ln[: len(ln) - len(stripped)] == "":
            return i
    return 1


def lint_file(
    path: str | os.PathLike[str], allowed_bash_scopes: frozenset[str] | None = None
) -> list[Violation]:
    """Lint a single agent markdown file. Returns sorted list of violations."""
    if allowed_bash_scopes is None:
        allowed_bash_scopes = DEFAULT_BASH_SCOPES
    p = Path(path)
    file_str = str(p)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        return [Violation(file_str, 1, "error", "R6", f"cannot read file: {e}")]

    yaml_text, yaml_offset = _split_frontmatter(text)
    if yaml_text is None:
        return [Violation(file_str, 1, "error", "R6", "missing or unterminated YAML frontmatter")]

    try:
        data = yaml.safe_load(yaml_text) if yaml_text.strip() else None
    except yaml.YAMLError as e:
        line = 1
        mark = getattr(e, "problem_mark", None)
        if mark is not None:
            line = _yaml_line_to_file_line(mark.line + 1, yaml_offset)
        return [Violation(file_str, line, "error", "R6", f"invalid YAML frontmatter: {e}")]

    violations: list[Violation] = []

    if not isinstance(data, dict):
        return [Violation(file_str, yaml_offset, "error", "R6", "frontmatter is not a mapping")]

    # Exemption: runtime: github-actions opts out of four-axes checks. See
    # aops-core/AGENT-COMPLIANCE-MATRIX.md § ".github/agents/".
    if data.get("runtime") == "github-actions":
        return []

    tools = data.get("tools")
    tools_line_yaml = _find_key_line(yaml_text, "tools")
    tools_line = _yaml_line_to_file_line(tools_line_yaml, yaml_offset)

    if "tools" not in data or not isinstance(tools, list):
        violations.append(
            Violation(
                file_str,
                tools_line if "tools" in data else yaml_offset,
                "error",
                "R6",
                "missing or non-list `tools` field — every agent must declare tools",
            )
        )
        # Without tools we cannot evaluate other rules meaningfully; return.
        return sorted(violations, key=Violation.sort_key)

    tool_set = {str(t) for t in tools if isinstance(t, str)}

    # R1: Bash without bash_scopes
    bash_scopes = data.get("bash_scopes")
    bash_scopes_line_yaml = _find_key_line(yaml_text, "bash_scopes")
    bash_scopes_line = _yaml_line_to_file_line(bash_scopes_line_yaml, yaml_offset)
    if "Bash" in tool_set:
        if not isinstance(bash_scopes, list) or not bash_scopes:
            violations.append(
                Violation(
                    file_str,
                    tools_line,
                    "error",
                    "R1",
                    "`Bash` declared in tools but no `bash_scopes` provided",
                )
            )

    # R4 / R5: validate scope values
    if isinstance(bash_scopes, list):
        for scope in bash_scopes:
            if not isinstance(scope, str):
                violations.append(
                    Violation(
                        file_str,
                        bash_scopes_line,
                        "error",
                        "R4",
                        f"bash_scopes entry is not a string: {scope!r}",
                    )
                )
                continue
            if scope == "unrestricted":
                violations.append(
                    Violation(
                        file_str,
                        bash_scopes_line,
                        "warning",
                        "R5",
                        "bash_scopes contains `unrestricted` — broad grant",
                    )
                )
            elif scope not in allowed_bash_scopes:
                violations.append(
                    Violation(
                        file_str,
                        bash_scopes_line,
                        "error",
                        "R4",
                        f"unknown bash_scope: {scope!r}",
                    )
                )

    # R2 / R3: file_access checks
    fs_used = tool_set & FILESYSTEM_TOOLS
    write_used = tool_set & WRITE_TOOLS
    file_access = data.get("file_access")
    file_access_line_yaml = _find_key_line(yaml_text, "file_access")
    file_access_line = _yaml_line_to_file_line(file_access_line_yaml, yaml_offset)

    if fs_used:
        read_globs = None
        write_globs = None
        if isinstance(file_access, dict):
            read_globs = file_access.get("read")
            write_globs = file_access.get("write")
        if not isinstance(read_globs, list) or not read_globs:
            violations.append(
                Violation(
                    file_str,
                    tools_line,
                    "error",
                    "R2",
                    f"filesystem tools {sorted(fs_used)} declared without `file_access.read` globs",
                )
            )
        if write_used:
            if not isinstance(write_globs, list) or not write_globs:
                violations.append(
                    Violation(
                        file_str,
                        file_access_line if isinstance(file_access, dict) else tools_line,
                        "error",
                        "R3",
                        f"write tools {sorted(write_used)} declared without "
                        "`file_access.write` globs",
                    )
                )

    # R7: Skill present, body suggests subagent spawn, no Agent tool
    if "Skill" in tool_set and "Agent" not in tool_set:
        body_start = 0
        # body begins after closing '---' fence
        if text.startswith("---\n") or text.startswith("---\r\n"):
            after = text.split("\n", 1)[1] if "\n" in text else ""
            lines = after.split("\n")
            for i, ln in enumerate(lines):
                if ln.rstrip("\r") == "---":
                    body_start = i + 1
                    break
            body = "\n".join(lines[body_start:])
        else:
            body = text
        signals = ("Agent(", "subagent", "Agent tool")
        if any(s in body for s in signals):
            violations.append(
                Violation(
                    file_str,
                    tools_line,
                    "warning",
                    "R7",
                    "body suggests sub-agent spawning but `Agent` not in tools",
                )
            )

    return sorted(violations, key=Violation.sort_key)


def _iter_agent_files(paths: Iterable[str | os.PathLike[str]]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        if p.is_symlink():
            continue
        if p.is_file():
            if p.suffix == ".md":
                rp = p.resolve()
                if rp not in seen:
                    seen.add(rp)
                    out.append(p)
            continue
        if p.is_dir():
            for root, dirs, files in os.walk(p, followlinks=False):
                # prune
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for fn in files:
                    if not fn.endswith(".md"):
                        continue
                    fp = Path(root) / fn
                    if fp.is_symlink():
                        continue
                    rp = fp.resolve()
                    if rp in seen:
                        continue
                    seen.add(rp)
                    out.append(fp)
    return sorted(out)


def _violations_to_json(violations: list[Violation], files_checked: int) -> dict[str, Any]:
    errors = sum(1 for v in violations if v.level == "error")
    warnings = sum(1 for v in violations if v.level == "warning")
    return {
        "violations": [asdict(v) for v in violations],
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "files_checked": files_checked,
        },
    }


def _find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent_compliance_lint",
        description="Validate agent frontmatter against four-axes permissions schema.",
    )
    parser.add_argument("paths", nargs="*", help="Files or directories to lint.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors for exit code."
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress per-violation output; print summary only."
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse exits 2 on bad usage, which matches our contract.
        return int(e.code) if isinstance(e.code, int) else 2

    paths = args.paths if args.paths else list(DEFAULT_PATHS)
    repo_root = _find_repo_root(Path.cwd())
    allowed = load_bash_scopes(repo_root)

    files = _iter_agent_files(paths)
    all_violations: list[Violation] = []
    for f in files:
        all_violations.extend(lint_file(f, allowed_bash_scopes=allowed))
    all_violations.sort(key=Violation.sort_key)

    errors = sum(1 for v in all_violations if v.level == "error")
    warnings = sum(1 for v in all_violations if v.level == "warning")

    if args.format == "json":
        payload = _violations_to_json(all_violations, len(files))
        if args.quiet:
            # Quiet for json: emit only summary (still as json).
            print(json.dumps({"summary": payload["summary"]}, sort_keys=True))
        else:
            print(json.dumps(payload, sort_keys=True))
    else:
        if not args.quiet:
            for v in all_violations:
                print(v.format_text())
        print(
            f"agent-compliance-lint: {len(files)} files checked, "
            f"{errors} error(s), {warnings} warning(s)"
        )

    failing = errors + (warnings if args.strict else 0)
    return 1 if failing > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
