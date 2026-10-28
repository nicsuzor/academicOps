"""Parse `trigger: always_on` frontmatter out of a plugin's shipped axioms skill (skills/axioms/*.md).

Shared by both client adapters — parsing frontmatter is not client-specific.
What gets emitted from the parsed result (axioms.jsonl vs rules/*.md) is
client-specific and stays in build/clients/.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

# The axioms ship as the files of a skill, so any agent can load them from the
# skill's own directory on every client.
AXIOMS_SUBDIR = Path("skills") / "axioms"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def load_always_on_axioms(axioms_dir: Path) -> list[dict[str, Any]]:
    """Axioms carry simple `key: value` frontmatter (no nested YAML needed).
    Only `trigger: always_on` files are universal rules that get wired into a
    client's native rule mechanism — other axioms/*.md files are reference
    docs, shipped verbatim but not auto-merged into every session."""
    if not axioms_dir.exists():
        return []

    axioms: list[dict[str, Any]] = []
    for md_file in sorted(axioms_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue

        meta: dict[str, str] = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

        if meta.get("trigger") != "always_on":
            continue

        axioms.append(
            {
                "slug": md_file.stem,
                "description": meta.get("description", ""),
                "body": m.group(2).strip(),
                "source_file": md_file.name,
            }
        )

    return axioms


def generate_axioms_readme(axioms_dir: Path) -> str:
    """Generate the Markdown content of README.md indexing the axioms in axioms_dir.

    Single Source of Truth: every row is derived directly from the axiom's
    own frontmatter (description and trigger), never authored separately.
    """
    if not axioms_dir.exists():
        return ""

    lines = [
        "---",
        "description: Index of academicOps axioms.",
        "---",
        "",
        "# Axioms",
        "",
        "| Slug | Core Principle | Trigger |",
        "| - | - | - |",
    ]
    for md_file in sorted(axioms_dir.glob("*.md")):
        if md_file.name in ("README.md", "SKILL.md"):
            continue
        text = md_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue

        meta: dict[str, str] = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

        desc = meta.get("description", "")
        trig = meta.get("trigger", "always_on")
        lines.append(f"| `{md_file.stem}` | {desc} | {trig} |")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or check axioms README index")
    parser.add_argument(
        "--axioms-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "plugins" / "rbg" / "skills" / "axioms",
        help="Path to axioms skill directory",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether README.md matches generated index without updating",
    )
    args = parser.parse_args(argv)

    readme_path = args.axioms_dir / "README.md"
    expected = generate_axioms_readme(args.axioms_dir)
    current = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

    if current != expected:
        if args.check:
            print(
                f"ERROR: {readme_path} is out of sync with canonical axiom files.", file=sys.stderr
            )
            return 1
        readme_path.write_text(expected, encoding="utf-8")
        print(f"Updated {readme_path}")
    else:
        if args.check:
            print(f"OK: {readme_path} matches canonical axiom files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
