import sys
from pathlib import Path
import pytest

# Add aops-core to path
# __file__ is aops-core/tests/test_tasks_server_markers.py
# parent is aops-core/tests/
# parent.parent is aops-core/
AOPS_CORE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(AOPS_CORE_DIR))

# Import the function to test
from mcp_servers.tasks_server import _check_incomplete_markers

def test_empty_body():
    """Empty body or None should return no markers."""
    assert _check_incomplete_markers("") == []
    assert _check_incomplete_markers(None) == []

def test_remaining_section():
    """'Remaining:' section headers should be detected."""
    assert "Remaining: section" in _check_incomplete_markers("## Remaining:\n- item 1")
    assert "Remaining: section" in _check_incomplete_markers("### REMAINING:\nsome content")
    assert "Remaining: section" in _check_incomplete_markers("# Remaining:")

    # Should NOT be flagged if it's just text, not a header
    assert "Remaining: section" not in _check_incomplete_markers("Just mentioning remaining: stuff")

def test_percent_complete():
    """'X% complete' should be flagged if X < 100."""
    assert "50% complete" in _check_incomplete_markers("I am 50% complete with this")
    assert "0% complete" in _check_incomplete_markers("0% complete")
    assert "99% complete" in _check_incomplete_markers("99% complete")

    # 100% complete should NOT be flagged
    assert _check_incomplete_markers("100% complete") == []
    # Values >= 100 should not be flagged
    assert _check_incomplete_markers("110% complete") == []

def test_unchecked_items():
    """Unchecked markdown checklist items should be detected."""
    body = "- [ ] Unfinished item\n- [x] Finished item"
    res = _check_incomplete_markers(body)
    assert "Unfinished item" in res
    assert "Finished item" not in res
    assert len(res) == 1

def test_wip_markers():
    """WIP and in-progress markers should be detected (case-insensitive)."""
    assert "WIP" in _check_incomplete_markers("This is a WIP task")
    assert "in-progress" in _check_incomplete_markers("Work is in-progress here")
    assert "wip" in _check_incomplete_markers("this is a wip")
    assert "IN-PROGRESS" in _check_incomplete_markers("STILL IN-PROGRESS")

    # Should not match parts of words
    assert _check_incomplete_markers("SWIPING is fun") == []

def test_checked_items_not_flagged():
    """Checked markdown checklist items should NOT be flagged."""
    body = "- [x] Item 1\n- [x] Item 2\n* [x] Starred item"
    assert _check_incomplete_markers(body) == []

def test_mixed_markers():
    """Multiple different markers should all be detected."""
    body = """
# Task Title
This is a WIP.
- [x] Done this
- [ ] Still need this

## Remaining:
- More stuff

Almost 75% complete.
    """
    res = _check_incomplete_markers(body)
    assert "WIP" in res
    assert "Still need this" in res
    assert "Remaining: section" in res
    assert "75% complete" in res
    assert len(res) == 4
