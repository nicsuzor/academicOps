"""The email-triage process template ships, generically, to every client.

These tests hold that single copy in place — its routing frontmatter, its
genericity, and its arrival in both clients' artifacts — so the next reader
extends it instead of planting a parallel one beside it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from build.build import build_all

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_MARKETPLACE = PROJECT_ROOT / "build" / "marketplace.toml"
WORKFLOW = PROJECT_ROOT / "plugins" / "aops" / "workflows" / "email-triage.md"

# A shipped instruction reaches every user, so it carries no person, organisation,
# address, timezone, or local path. See specs/meta/doc-taxonomy.md.
USER_SPECIFIC = re.compile(
    r"""(?ix)
    \b nic \b | \b suzor \b
    | [\w.+-]+ @ (?!example\.) [\w-]+ \.[a-z]{2,}
    | \b Australia/\w+ | \b Brisbane \b
    | (?<![\w-]) /(?:home|Users)/
    """
)


def _frontmatter(path: Path) -> dict:
    head, _, _ = path.read_text(encoding="utf-8").partition("\n---")
    return yaml.safe_load(head.lstrip("-\n"))


def test_the_email_triage_template_is_the_only_copy():
    """One procedure, one file. A second copy is the defect this guards against."""
    assert WORKFLOW.is_file(), f"expected the email-triage template at {WORKFLOW}"

    duplicates = [
        p
        for p in (PROJECT_ROOT / "plugins").rglob("*email-triage*")
        if p.is_file() and p != WORKFLOW
    ]
    assert not duplicates, (
        "the email-triage procedure is duplicated outside its template: "
        f"{[str(p.relative_to(PROJECT_ROOT)) for p in duplicates]}"
    )


def test_the_template_declares_the_routing_the_library_reads():
    fm = _frontmatter(WORKFLOW)

    assert fm.get("title") == "Email Triage"
    assert fm.get("type") == "template"
    assert fm.get("category") == "process"
    assert "email" in fm.get("tags", [])


def test_the_template_is_generic():
    """It ships to every user, so it names no user."""
    hits = [
        f"{n}: {line.strip()}"
        for n, line in enumerate(WORKFLOW.read_text(encoding="utf-8").splitlines(), 1)
        if USER_SPECIFIC.search(line)
    ]
    assert not hits, "user-specific values in a shipped instruction:\n" + "\n".join(hits)


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_the_template_reaches_the_client_artifact(client, tmp_path):
    dist_root = tmp_path / "dist"
    build_all(
        PROJECT_ROOT,
        dist_root,
        marketplace_path=REAL_MARKETPLACE,
        plugins=["aops"],
        version="0.0.0-test",
    )

    built = dist_root / f"aops-{client}" / "workflows" / "email-triage.md"
    assert built.is_file(), f"the template did not ship to {client}: {built}"
    assert _frontmatter(built).get("type") == "template"
