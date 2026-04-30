"""Tests for scripts/next_p_number.py — the P# allocator and collision lint."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "next_p_number.py"


@pytest.fixture(scope="module")
def allocator():
    """Load the script as a module without depending on package layout."""
    spec = importlib.util.spec_from_file_location("next_p_number", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["next_p_number"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# parse_existing_pnumbers
# ---------------------------------------------------------------------------


def test_parse_existing_pnumbers_extracts_anchors(allocator, tmp_path):
    f = tmp_path / "H.md"
    f.write_text(
        "# Heuristics\n\n"
        '<a id="P7"></a>\n## Project Independence\n\n'
        '<a id="P11"></a>\n## Single-Purpose\n\n'
        '<a id="P123"></a>\n## Some Rule\n',
        encoding="utf-8",
    )
    assert allocator.parse_existing_pnumbers(f) == {7, 11, 123}


def test_parse_existing_pnumbers_empty_for_missing_file(allocator, tmp_path):
    assert allocator.parse_existing_pnumbers(tmp_path / "nope.md") == set()


def test_parse_existing_pnumbers_ignores_unrelated_p_mentions(allocator, tmp_path):
    f = tmp_path / "H.md"
    f.write_text(
        'Refer to P#123 elsewhere — but only the anchor counts.\n<a id="P5"></a>\n',
        encoding="utf-8",
    )
    assert allocator.parse_existing_pnumbers(f) == {5}


def test_parse_existing_pnumbers_real_file(allocator):
    """Sanity check against the actual repo file."""
    nums = allocator.parse_existing_pnumbers(allocator.HEURISTICS_PATH)
    assert nums, "expected at least one P# anchor in HEURISTICS.md"
    assert all(isinstance(n, int) and n > 0 for n in nums)


# ---------------------------------------------------------------------------
# next_free
# ---------------------------------------------------------------------------


def test_next_free_returns_max_plus_one(allocator):
    assert allocator.next_free({1, 2, 3}, set()) == 4


def test_next_free_considers_reserved(allocator):
    # Existing tops at 100; an open PR reserves 105 -> next is 106.
    assert allocator.next_free({1, 50, 100}, {105}) == 106


def test_next_free_does_not_fill_holes(allocator):
    # Holes are load-bearing (cross-refs). Always max+1.
    assert allocator.next_free({1, 2, 5}, set()) == 6


def test_next_free_empty_starts_at_one(allocator):
    assert allocator.next_free(set(), set()) == 1


# ---------------------------------------------------------------------------
# parse_open_pr_pnumbers (mocked gh)
# ---------------------------------------------------------------------------


def test_parse_open_pr_pnumbers_handles_missing_gh(allocator):
    with mock.patch.object(allocator, "_run_gh", return_value=None):
        assert allocator.parse_open_pr_pnumbers() == {}


def test_parse_open_pr_pnumbers_extracts_added_anchors(allocator):
    fake_diff = (
        "diff --git a/aops-core/HEURISTICS.md b/aops-core/HEURISTICS.md\n"
        "+++ b/aops-core/HEURISTICS.md\n"
        '+<a id="P200"></a>\n'
        "+## Some New Heuristic\n"
        '-<a id="P150"></a>\n'  # deletion - must NOT count
        ' <a id="P140"></a>\n'  # context - must NOT count
    )

    def fake_run(args):
        if args[:2] == ["pr", "list"]:
            return '[{"number": 857}]'
        if args[:2] == ["pr", "diff"]:
            return fake_diff
        return None

    with mock.patch.object(allocator, "_run_gh", side_effect=fake_run):
        result = allocator.parse_open_pr_pnumbers()
    assert result == {857: [200]}


def test_parse_open_pr_pnumbers_excludes_self(allocator):
    def fake_run(args):
        if args[:2] == ["pr", "list"]:
            return '[{"number": 857}, {"number": 999}]'
        if args[:2] == ["pr", "diff"]:
            return '+<a id="P210"></a>\n'
        return None

    with mock.patch.object(allocator, "_run_gh", side_effect=fake_run):
        result = allocator.parse_open_pr_pnumbers(exclude_pr=857)
    assert 857 not in result
    assert 999 in result


def test_parse_open_pr_pnumbers_handles_bad_json(allocator):
    with mock.patch.object(allocator, "_run_gh", return_value="not-json"):
        assert allocator.parse_open_pr_pnumbers() == {}


# ---------------------------------------------------------------------------
# find_collisions
# ---------------------------------------------------------------------------


def test_find_collisions_detects_duplicate_pnumber(allocator):
    # Local diff proposes P123; open PR #857 also proposes P123 -> collision.
    staged = '+++ b/aops-core/HEURISTICS.md\n+<a id="P123"></a>\n+## Local Rule\n'
    pr_map = {857: [123]}
    assert allocator.find_collisions(staged, pr_map) == [(123, 857)]


def test_find_collisions_no_overlap(allocator):
    staged = '+<a id="P124"></a>\n'
    pr_map = {857: [123]}
    assert allocator.find_collisions(staged, pr_map) == []


def test_find_collisions_ignores_context_and_deleted(allocator):
    # The "+++" header and the leading-space context line must not register.
    staged = '+++ b/aops-core/HEURISTICS.md\n <a id="P123"></a>\n-<a id="P125"></a>\n'
    pr_map = {857: [123, 125]}
    assert allocator.find_collisions(staged, pr_map) == []


def test_find_collisions_multiple_collisions(allocator):
    staged = '+<a id="P123"></a>\n+<a id="P124"></a>\n'
    pr_map = {857: [123], 860: [124]}
    out = allocator.find_collisions(staged, pr_map)
    assert sorted(out) == [(123, 857), (124, 860)]


# ---------------------------------------------------------------------------
# CLI integration (via main())
# ---------------------------------------------------------------------------


def test_main_default_prints_next_free(allocator, capsys):
    with (
        mock.patch.object(allocator, "parse_existing_pnumbers", return_value={1, 2, 100}),
        mock.patch.object(allocator, "parse_open_pr_pnumbers", return_value={857: [101]}),
    ):
        rc = allocator.main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "102"


def test_main_check_clean_returns_zero(allocator):
    with (
        mock.patch.object(allocator, "_staged_diff", return_value=""),
        mock.patch.object(allocator, "parse_open_pr_pnumbers", return_value={}),
    ):
        assert allocator.main(["--check"]) == 0


def test_main_check_collision_returns_one(allocator, capsys):
    staged = '+<a id="P123"></a>\n'
    with (
        mock.patch.object(allocator, "_staged_diff", return_value=staged),
        mock.patch.object(allocator, "parse_open_pr_pnumbers", return_value={857: [123]}),
    ):
        rc = allocator.main(["--check"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "P123" in captured.err
    assert "857" in captured.err
