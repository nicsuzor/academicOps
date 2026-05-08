import sys
from pathlib import Path

# Add aops-core/scripts to path for imports
SCRIPT_DIR = Path(__file__).parents[2] / "aops-core" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from dump_pr_state import _extract_trailers, _project_pr


def test_extract_trailers_short_body():
    body = "Fixes: #123\nCloses: #456\nSome text here."
    trailers = _extract_trailers(body)
    assert trailers == ["Fixes: #123", "Closes: #456"]


def test_extract_trailers_long_body_with_tail_trailers():
    body = "A" * 4000 + "\nFixes: #789\nRefs: https://github.com/org/repo/issues/1"
    trailers = _extract_trailers(body)
    assert trailers == ["Fixes: #789", "Refs: https://github.com/org/repo/issues/1"]


def test_extract_trailers_no_trailers():
    body = "A" * 4000 + "\nNo trailers here."
    trailers = _extract_trailers(body)
    assert trailers == []


def test_extract_trailers_case_insensitivity():
    body = "fixes: #123\nCLOSES: #456\nresolves: #789"
    trailers = _extract_trailers(body)
    assert trailers == ["fixes: #123", "CLOSES: #456", "resolves: #789"]


def test_extract_trailers_multiline():
    body = "Some text.\nFixes: #123\nMore text.\nRefs: #456"
    trailers = _extract_trailers(body)
    assert trailers == ["Fixes: #123", "Refs: #456"]


def test_extract_trailers_complex_values():
    body = "Closes: #123, #456\nRefs: https://github.com/org/repo/issues/1 (comment)"
    trailers = _extract_trailers(body)
    assert trailers == [
        "Closes: #123, #456",
        "Refs: https://github.com/org/repo/issues/1 (comment)",
    ]


def test_project_pr_preserves_trailers_after_truncation():
    long_body = "A" * 3000 + "\nFixes: #999"
    pr = {"number": 1, "body": long_body, "author": {"login": "user", "is_bot": False}}
    projected = _project_pr(pr, is_open=True)

    # Body should be truncated
    assert len(projected["body"]) < len(long_body)
    assert "... [truncated]" in projected["body"]

    # Trailers should be preserved in the new field
    assert projected["trailers"] == ["Fixes: #999"]


def test_project_pr_no_body():
    pr = {"number": 1, "author": {"login": "user"}}
    projected = _project_pr(pr, is_open=True)
    assert projected["trailers"] == []
    assert "body" not in projected
