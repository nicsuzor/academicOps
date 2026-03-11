"""Tests for normalize_gemini_project() helper."""

import pytest
from lib.transcript_parser import normalize_gemini_project


@pytest.mark.parametrize(
    "dir_name,expected",
    [
        # SHA-256 hash (64 hex chars) -> gemini-{first 8}
        ("1c1c500b" + "a" * 56, "gemini-1c1c500b"),
        ("abcdef01" * 8, "gemini-abcdef01"),
        # Plain named dirs -> as-is
        ("buttermilk", "buttermilk"),
        ("brain", "brain"),
        ("mem", "mem"),
        # Named + numeric suffix -> strip suffix
        ("aops-1", "aops"),
        ("aops-6", "aops"),
        ("brain-42", "brain"),
        # Named + 8-char hex suffix -> strip suffix
        ("aops-6fbe707a", "aops"),
        ("mem-12915b4d", "mem"),
        ("buttermilk-abcd1234", "buttermilk"),
        # Edge: short names that could look like hex but aren't 8 chars
        ("aops-abc", "aops-abc"),
        # Edge: already clean
        ("aops", "aops"),
    ],
)
def test_normalize_gemini_project(dir_name, expected):
    assert normalize_gemini_project(dir_name) == expected
