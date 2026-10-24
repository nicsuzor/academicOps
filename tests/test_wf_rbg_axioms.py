"""Test that wf-rbg.md only names shipped axioms from plugins/rbg/skills/axioms/.

Ensures workflow instructions never drift from the canonical shipped axiom set.
Fails if wf-rbg.md names an axiom that no shipped file in plugins/rbg/skills/axioms/ provides.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WF_RBG_PATH = (
    REPO_ROOT / "plugins" / "ida" / "skills" / "workflow-library" / "workflows" / "wf-rbg.md"
)
AXIOMS_DIR = REPO_ROOT / "plugins" / "rbg" / "skills" / "axioms"
POLICY_FILE = REPO_ROOT / "tests" / "policy.toml"


def _normalize(s: str) -> str:
    """Normalize rule names for comparison (lowercase, alphanumeric only)."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def get_axiom_policy() -> tuple[dict[str, str], set[str]]:
    """Load axiom aliases and exempt words from tests/policy.toml."""
    if not POLICY_FILE.exists():
        return {}, set()
    data = tomllib.loads(POLICY_FILE.read_text(encoding="utf-8"))
    rbg_axioms = data.get("rbg", {}).get("axioms", {})
    aliases: dict[str, str] = rbg_axioms.get("aliases", {})
    exempt_words: set[str] = {w.lower() for w in rbg_axioms.get("exempt_words", [])}
    return aliases, exempt_words


def get_shipped_axioms(axioms_dir: Path) -> dict[str, str]:
    """Map normalized identifiers (slugs, titles, headings) to axiom slug."""
    shipped: dict[str, str] = {}
    for md_file in axioms_dir.glob("*.md"):
        if md_file.name == "README.md":
            continue
        slug = md_file.stem
        shipped[_normalize(slug)] = slug

        text = md_file.read_text(encoding="utf-8")
        # Extract title from markdown heading (e.g., '## Data Boundaries')
        for line in text.splitlines():
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
                # Strip subtitles / slogans after colon
                title = heading.split(":", 1)[0].strip()
                shipped[_normalize(title)] = slug
                shipped[_normalize(heading)] = slug

    # Known aliases loaded from policy.toml (Policy as Code)
    aliases, _ = get_axiom_policy()
    for alias, slug in aliases.items():
        if _normalize(slug) in shipped:
            shipped[_normalize(alias)] = slug

    return shipped


def extract_named_axioms(wf_text: str) -> list[str]:
    """Extract axiom names referenced in wf-rbg.md."""
    named: list[str] = []
    _, exempt_words = get_axiom_policy()

    # 1. Governing axioms list in parentheses: 'governing axioms (item1, item2, ...)'
    match = re.search(r"governing axioms\s*\(([^)]+)\)", wf_text, re.IGNORECASE)
    if match:
        items = match.group(1).split(",")
        for item in items:
            cleaned = item.strip()
            if cleaned:
                named.append(cleaned)

    # 2. Markdown links to axioms: e.g. [name](...axioms/<slug>.md)
    link_matches = re.finditer(r"\[([^\]]+)\]\([^)]*axioms/([^)#]+)\.md[^)]*\)", wf_text)
    for m in link_matches:
        named.append(m.group(2))

    # 3. Explicit rule references under Procedure: e.g. 'under `<rule-slug>`'
    proc_match = re.search(r"## Procedure(.*?)(?=\n## |\Z)", wf_text, re.DOTALL)
    if proc_match:
        rule_refs = re.finditer(r"under\s+`([a-z0-9_-]+)`", proc_match.group(1), re.IGNORECASE)
        for m in rule_refs:
            span = m.group(1)
            if span.lower() not in exempt_words:
                named.append(span)

    # Deduplicate preserving order
    seen = set()
    result = []
    for item in named:
        norm = _normalize(item)
        if norm not in seen:
            seen.add(norm)
            result.append(item)
    return result


def find_unshipped_axioms(wf_text: str, axioms_dir: Path) -> list[str]:
    """Return list of axioms named in wf_text that are not in axioms_dir."""
    shipped = get_shipped_axioms(axioms_dir)
    named = extract_named_axioms(wf_text)
    unshipped = []
    for name in named:
        norm = _normalize(name)
        if norm not in shipped:
            unshipped.append(name)
    return unshipped


def test_unshipped_axiom_in_wf_rbg_fails():
    """Fails when wf-rbg.md names an unshipped axiom (demonstrates red test behavior)."""
    synthetic_wf = (
        "## Procedure\n"
        "2. State smallest mechanism; reject excess under `proportionate`.\n"
        "3. **Evaluate against rules** -- test the artifact against governing axioms "
        "(categorical imperative, closure, unshipped-axiom, data boundaries).\n"
    )
    unshipped = find_unshipped_axioms(synthetic_wf, AXIOMS_DIR)
    assert unshipped == ["unshipped-axiom"]


def test_live_wf_rbg_names_only_shipped_axioms():
    """Live verification: plugins/ida/skills/workflow-library/workflows/wf-rbg.md names only shipped axioms."""
    wf_text = WF_RBG_PATH.read_text(encoding="utf-8")
    unshipped = find_unshipped_axioms(wf_text, AXIOMS_DIR)
    assert not unshipped, f"wf-rbg.md names unshipped axioms: {unshipped}"
