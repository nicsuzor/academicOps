#!/usr/bin/env -S uv run python
"""
Normalize Gemini-form MCP tool names back to canonical Claude double-underscore form.

Inverse of the transform in scripts/build.py:698 which converts
`mcp__server__tool` -> `mcp_server_tool` at distribution time for Gemini.

Gemini polecat workers see the single-underscore form in their own tool catalog
and sometimes write it back into source files when editing SKILL.md or agent
prompts. This hook auto-heals such corruption at commit time.

Strategy: server-allowlist matching. Because server names themselves can contain
underscores (e.g. `plugin_aops-core_pkb`), a blind regex would split the wrong
underscore. We hardcode the set of known canonical server prefixes and only
rewrite identifiers that match `mcp_<known-server>_<tool>`.

Exits 1 if any file was modified, so pre-commit aborts the commit and the user
re-stages and re-commits (same UX as ruff --fix / trailing-whitespace).
"""

import re
import sys
from pathlib import Path

# Canonical MCP server names — kept in sync with the forms that actually
# appear (with `mcp__<server>__`) anywhere in `aops-core/` and `.github/agents/`.
# To regenerate: `grep -rhoE 'mcp__[a-zA-Z0-9_-]+__' aops-core/ .github/agents/ | sort -u`
KNOWN_SERVERS = [
    "context7",
    "memory",
    "omcp",
    "osb",
    "outlook",
    "pbk",
    "pkb",
    "playwright",
    "plugin_0_2_25_pkb",
    "plugin_aops-core_memory",
    "plugin_aops-core_pkb",
    "plugin_aops-core_tasks",
    "plugin_context7-plugin_context7",
    "zot",
    # Servers that appear in agent frontmatter / tool catalogs but aren't yet
    # referenced in body text. Listed for completeness so corruption is caught
    # the first time it lands rather than after the second occurrence.
    "discord",
    "computer-use",
    "claude-in-chrome",
    "Claude_Preview",
    "plugin_discord_discord",
]

# Order matters: try longest servers first so `plugin_aops-core_pkb` is matched
# before `pkb` would greedily steal the tail of a longer name.
KNOWN_SERVERS.sort(key=len, reverse=True)

# Build one combined regex. `(?<![_a-zA-Z0-9-])` is a left-anchor that allows
# `(` or whitespace or backtick to precede but rejects mid-identifier matches.
# `(?![_a-zA-Z0-9-])` does the same on the right of the tool name.
_SERVER_ALT = "|".join(re.escape(s) for s in KNOWN_SERVERS)
GEMINI_NAME_RE = re.compile(
    rf"(?<![_a-zA-Z0-9-])mcp_({_SERVER_ALT})_([a-zA-Z][a-zA-Z0-9_-]*)(?![_a-zA-Z0-9-])"
)


def normalize_text(text: str) -> tuple[str, list[str]]:
    """Return (rewritten_text, list_of_replacements_made)."""
    replacements: list[str] = []

    def _sub(m: re.Match[str]) -> str:
        original = m.group(0)
        server = m.group(1)
        tool = m.group(2)
        canonical = f"mcp__{server}__{tool}"
        replacements.append(f"{original} -> {canonical}")
        return canonical

    new_text = GEMINI_NAME_RE.sub(_sub, text)
    return new_text, replacements


def process_file(path: Path) -> int:
    """Returns 1 if file was rewritten, 0 otherwise."""
    try:
        original = path.read_text()
    except (OSError, UnicodeDecodeError) as e:
        print(f"normalize_mcp_names: skip {path}: {e}", file=sys.stderr)
        return 0

    rewritten, replacements = normalize_text(original)
    if not replacements:
        return 0

    path.write_text(rewritten)
    print(f"normalize_mcp_names: rewrote {path}")
    for r in replacements:
        print(f"  {r}")
    return 1


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv[1:]]
    if not files:
        return 0

    changed = 0
    for f in files:
        if not f.is_file():
            continue
        changed += process_file(f)

    if changed:
        print(
            f"\nnormalize_mcp_names: rewrote {changed} file(s). Re-stage and re-commit.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
