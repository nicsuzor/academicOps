"""Nested code fences in tracked markdown.

An inner fence as long as its outer fence closes the outer one early. The
formatter then re-fences the leftovers and swallows the prose that follows into
a code block. That is how Argdown examples nested inside handback templates
were broken. A labelled inner fence is legal only inside a longer, labelled
outer fence (````markdown around ```argdown).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*([^`\s]*)")


def fence_collisions(text: str) -> list[int]:
    """Line numbers of labelled fences nested where they break their outer fence."""
    bad: list[int] = []
    outer: tuple[str, int, str] | None = None
    for n, line in enumerate(text.splitlines(), 1):
        m = _FENCE.match(line)
        if not m:
            continue
        fence, info = m.group(1), m.group(2)
        if outer is None:
            outer = (fence[0], len(fence), info)
            continue
        char, length, outer_info = outer
        if fence[0] != char:
            continue
        if not info and len(fence) >= length and not line.strip().strip(char):
            outer = None
        elif info and (len(fence) >= length or not outer_info):
            bad.append(n)
    return bad


def tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [REPO_ROOT / p for p in out.splitlines()]


@pytest.mark.parametrize(
    "body",
    [
        "```markdown\nVERDICT: PASS\n```argdown\n[C1]: x\n```\n```\n",
        "````\n- rule\n```argdown\n[C1]: x\n```\n````\n",
    ],
    ids=["equal-length-nesting", "unlabelled-outer"],
)
def test_collision_is_caught(body: str) -> None:
    assert fence_collisions(body)


def test_longer_labelled_outer_passes() -> None:
    body = (
        "````markdown\nVERDICT: PASS\n```argdown\n[C1]: x\n```\n````\n\n```argdown\n[C2]: y\n```\n"
    )
    assert fence_collisions(body) == []


def test_repo_markdown_has_no_fence_collisions() -> None:
    found = {
        str(p.relative_to(REPO_ROOT)): lines
        for p in tracked_markdown()
        if p.exists() and (lines := fence_collisions(p.read_text(encoding="utf-8")))
    }
    assert found == {}
