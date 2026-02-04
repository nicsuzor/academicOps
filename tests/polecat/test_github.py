import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

# Add repo root to path so we can import polecat
REPO_ROOT = Path(__file__).parents[2].resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from polecat.github import generate_pr_body

# Mock Task object
def mock_task(id="task-1", title="My Task", body=""):
    return SimpleNamespace(id=id, title=title, body=body)

def test_generate_pr_body_standard():
    body = """# My Task

This is the description.

## Acceptance Criteria
- [ ] Do thing A
- [ ] Do thing B
"""
    task = mock_task(body=body)
    pr_body = generate_pr_body(task)
    
    assert "This is the description." in pr_body
    assert "# My Task" not in pr_body # Title removed from body (handled by PR title)
    assert "## Acceptance Criteria" in pr_body
    assert "- [ ] Do thing A" in pr_body
    assert "Closes task-1" in pr_body

def test_generate_pr_body_implicit_checklist():
    body = """# My Task

Description here.
- [ ] Item 1
- [ ] Item 2
"""
    task = mock_task(body=body)
    pr_body = generate_pr_body(task)
    
    # Description should still contain the items in implicit mode (context preservation)
    assert "Description here." in pr_body
    
    # But we also add an explicit AC section
    assert "## Acceptance Criteria" in pr_body
    assert "- [ ] Item 1" in pr_body

def test_generate_pr_body_relationships_stripped():
    body = """# My Task

Description.

## Relationships
- [parent] [[other-task]]

## Acceptance Criteria
- [ ] Check me
"""
    task = mock_task(body=body)
    pr_body = generate_pr_body(task)
    
    assert "Description." in pr_body
    assert "## Relationships" not in pr_body
    assert "## Acceptance Criteria" in pr_body
    assert "- [ ] Check me" in pr_body

def test_generate_pr_body_checked_items_become_unchecked():
    body = """# My Task

## Acceptance Criteria
- [x] Already done (maybe via decomposition)
"""
    task = mock_task(body=body)
    pr_body = generate_pr_body(task)
    
    assert "- [ ] Already done" in pr_body
    assert "- [x]" not in pr_body
