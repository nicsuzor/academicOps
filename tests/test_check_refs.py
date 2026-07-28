"""The documented-reference check: scripts/check_refs.py.

Two things are proved here. First, that the check catches a broken reference —
a check that cannot fail is not a check. Second, that it stays quiet about the
kinds of reference it is designed to leave alone: URLs, container paths, PKB
wikilinks, and fenced examples.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_refs import RefCheck, candidates, clean, is_repo_shaped  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """A minimal git repo with the same config shape as the real one."""
    (tmp_path / "specs").mkdir()
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "real.md").write_text("real\n")
    (tmp_path / "pyproject.toml").write_text(
        "[tool.refcheck]\n"
        'include = ["specs/**/*.md"]\n'
        "\n"
        "[[tool.refcheck.allow]]\n"
        'docs = "specs/allowed.md"\n'
        'refs = ["lib/elsewhere.md"]\n'
        'reason = "test fixture"\n'
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def write(repo: Path, name: str, body: str) -> None:
    path = repo / "specs" / name
    path.write_text(body)
    subprocess.run(["git", "add", str(path)], cwd=repo, check=True)


def refs(repo: Path) -> list[str]:
    return [m.ref for m in RefCheck(repo).run()[0]]


# --- It fails on a broken reference ---------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        "See `lib/gone.md` for the rules.\n",
        "See [the rules](../lib/gone.md).\n",
        "See [[lib/gone.md]].\n",
        "@include gone.md\n",
    ],
    ids=["code-span", "markdown-link", "wikilink", "include"],
)
def test_broken_reference_fails(fake_repo: Path, body: str) -> None:
    write(fake_repo, "doc.md", body)
    misses, _ = RefCheck(fake_repo).run()
    assert len(misses) == 1, misses
    assert "gone.md" in misses[0].ref
    assert misses[0].doc == "specs/doc.md"


def test_live_reference_passes(fake_repo: Path) -> None:
    write(fake_repo, "doc.md", "See `lib/real.md` and [it](../lib/real.md) and [[lib/real.md]].\n")
    assert refs(fake_repo) == []


def test_anchor_is_stripped_not_checked(fake_repo: Path) -> None:
    write(fake_repo, "doc.md", "See [it](../lib/real.md#no-such-heading).\n")
    assert refs(fake_repo) == []


# --- It stays quiet about what is not ours to verify ----------------------


@pytest.mark.parametrize(
    "body",
    [
        "Fetch <https://example.com/lib/gone.md>.\n",
        "Read [docs](https://example.com/lib/gone.md).\n",
        "Config lives at `/etc/aops/gone.md` inside the container.\n",
        "Config lives at `~/.claude/gone.md`.\n",
        "Config lives at `$ACA_DATA/lib/gone.md`.\n",
        "Every `lib/*.md` is injected.\n",
        "Run `cat lib/gone.md` to see it.\n",
        "See [[some-pkb-note]] for background.\n",
        "The `finalize` step writes `report.json`.\n",
    ],
    ids=[
        "autolink",
        "url",
        "absolute",
        "home",
        "env-var",
        "glob",
        "command-line",
        "pkb-wikilink",
        "bare-filename",
    ],
)
def test_foreign_reference_is_ignored(fake_repo: Path, body: str) -> None:
    write(fake_repo, "doc.md", body)
    assert refs(fake_repo) == []


def test_fenced_block_is_not_scanned(fake_repo: Path) -> None:
    write(fake_repo, "doc.md", "Example tree:\n\n```\nlib/gone.md\n```\n\nEnd.\n")
    assert refs(fake_repo) == []


# --- The allowlist --------------------------------------------------------


def test_allowance_excuses_a_named_reference(fake_repo: Path) -> None:
    write(fake_repo, "allowed.md", "See `lib/elsewhere.md` in the other repo.\n")
    misses, unused = RefCheck(fake_repo).run()
    assert (misses, unused) == ([], [])


def test_allowance_does_not_excuse_a_different_reference(fake_repo: Path) -> None:
    write(fake_repo, "allowed.md", "See `lib/elsewhere.md` and `lib/gone.md`.\n")
    assert refs(fake_repo) == ["lib/gone.md"]


def test_allowance_does_not_reach_another_document(fake_repo: Path) -> None:
    write(fake_repo, "other.md", "See `lib/elsewhere.md`.\n")
    assert refs(fake_repo) == ["lib/elsewhere.md"]


def test_unused_allowance_is_reported(fake_repo: Path) -> None:
    write(fake_repo, "allowed.md", "Nothing to see.\n")
    _, unused = RefCheck(fake_repo).run()
    assert [a.docs for a in unused] == ["specs/allowed.md"]


# --- Units ----------------------------------------------------------------


def test_clean_strips_anchors_and_rejects_foreign_shapes() -> None:
    assert clean("lib/a.md#heading") == "lib/a.md"
    assert clean("lib/axioms/") == "lib/axioms"
    assert clean("https://example.com/a.md") is None
    assert clean("{{ template }}/a.md") is None


def test_repo_shaped_needs_a_directory_component() -> None:
    top = {"specs", "lib"}
    assert is_repo_shaped("lib/a.md", top)
    assert is_repo_shaped("../lib/a.md", top)
    assert is_repo_shaped("elsewhere/a.md", top)  # extension makes it a filename
    assert not is_repo_shaped("finalize.py", top)
    assert not is_repo_shaped("elsewhere/thing", top)


def test_candidates_report_the_line_of_a_wrapped_link() -> None:
    text = "one\ntwo\n[a label\nspanning lines](../lib/a.md)\n"
    found = [(line, kind, raw) for line, kind, raw, _ in candidates(text)]
    assert (3, "link", "../lib/a.md") in found


# --- The real tree --------------------------------------------------------


def test_repository_has_no_broken_references() -> None:
    misses, unused = RefCheck(REPO_ROOT).run()
    assert not misses, "\n".join(m.render() for m in misses)
    assert not unused, "\n".join(a.render() for a in unused)
