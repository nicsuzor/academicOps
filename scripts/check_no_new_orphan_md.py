#!/usr/bin/env -S uv run python
"""Pre-commit hook: block new orphan markdown files (R5.6).

Fails when a commit adds a new `.md` file outside the canonical-location
allowlist. Modifications and renames of existing files are permitted.

Canonical locations (allowed adds):
- aops-core/<UPPERCASE>.md           framework top-level files
- aops-core/skills/**/*.md           skill content
- aops-core/agents/**/*.md           agent definitions
- aops-core/workflows/**/*.md        workflows
- aops-core/commands/**/*.md         commands
- aops-core/hooks/**/*.md            hook templates
- aops-core/policies/**/*.md         policy files
- aops-core/.claude-plugin/**/*.md   plugin metadata
- tests/**/*.md                      test fixtures + evidentiary data
- templates/**/*.md                  scaffold templates
- .agents/**/*.md                    project-local rules + status
- .github/**/*.md                    GitHub-surface docs
- README.md, CHANGELOG.md, GEMINI.md, INSTALL.md  at repo root only

The point: agents must place new markdown in a canonical home, or the
content belongs in the task body / parent epic / PKB instead.

Reference: aops-core/RULES.md R5.6.
"""

from __future__ import annotations

import re
import subprocess
import sys

ALLOWED_PATTERNS = [
    "aops-core/[A-Z]*.md",
    "aops-core/skills/**/*.md",
    "aops-core/agents/**/*.md",
    "aops-core/workflows/**/*.md",
    "aops-core/commands/**/*.md",
    "aops-core/hooks/**/*.md",
    "aops-core/policies/**/*.md",
    "aops-core/.claude-plugin/**/*.md",
    "tests/**/*.md",
    "templates/**/*.md",
    ".agents/**/*.md",
    ".github/**/*.md",
]

ALLOWED_ROOT_FILES = {"README.md", "CHANGELOG.md", "GEMINI.md", "INSTALL.md"}


def _to_regex(pattern: str) -> re.Pattern[str]:
    """Translate glob with ** to regex. ** matches any number of path segments
    (including zero); * matches one segment."""
    out: list[str] = ["^"]
    i = 0
    while i < len(pattern):
        if pattern[i : i + 3] == "**/":
            out.append("(?:.*/)?")
            i += 3
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] in ".+()|^$":
            out.append(re.escape(pattern[i]))
            i += 1
        else:
            out.append(pattern[i])
            i += 1
    out.append("$")
    return re.compile("".join(out))


_COMPILED = [_to_regex(p) for p in ALLOWED_PATTERNS]


def is_allowed(path: str) -> bool:
    if "/" not in path:
        return path in ALLOWED_ROOT_FILES
    return any(rx.match(path) for rx in _COMPILED)


def added_md_files(staged_only: bool = True) -> list[str]:
    """Return paths added (status=A) in the index. Renames (R) are excluded."""
    args = ["git", "diff", "-z", "--cached", "--name-status", "--diff-filter=A"]
    if not staged_only:
        args = ["git", "diff", "-z", "--name-status", "--diff-filter=A", "HEAD"]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    paths: list[str] = []
    # -z output: status\0path\0status\0path\0... (NUL-delimited, no quoting)
    parts = out.split("\0")
    for i in range(0, len(parts) - 1, 2):
        status = parts[i]
        path = parts[i + 1]
        if status == "A" and path.endswith(".md"):
            paths.append(path)
    return paths


def main(argv: list[str]) -> int:
    # When pre-commit invokes us, it passes the staged file list as args.
    # We still derive added-only via git index for diff-filter=A semantics.
    paths = added_md_files()
    blocked = [p for p in paths if not is_allowed(p)]

    if not blocked:
        return 0

    sys.stderr.write(
        "BLOCK: new orphan markdown files (R5.6 — no new orphan markdown).\n"
        "\n"
        "These adds are outside the canonical-location allowlist:\n"
    )
    for p in blocked:
        sys.stderr.write(f"  - {p}\n")
    sys.stderr.write(
        "\nWorker findings, capability docs, summaries, and explainers belong\n"
        "in: the task body, the parent epic, the PKB (via the remember skill),\n"
        "or a file explicitly named in an approved plan.\n"
        "\n"
        "Canonical locations for new .md files:\n"
        "  - aops-core/skills/**/*.md     tests/**/*.md\n"
        "  - aops-core/agents/**/*.md     templates/**/*.md\n"
        "  - aops-core/workflows/**/*.md  .agents/**/*.md\n"
        "  - aops-core/commands/**/*.md   .github/**/*.md\n"
        "  - aops-core/hooks/**/*.md\n"
        "  - aops-core/<UPPERCASE>.md     README.md / CHANGELOG.md (root)\n"
        "\n"
        "If this addition is legitimate, surface it to the user; once\n"
        "authorised in-session, R8.1's in-session-authorisation carve-out\n"
        "permits committing with --no-verify.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
