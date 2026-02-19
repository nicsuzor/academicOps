import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add repo root to path so we can import polecat
REPO_ROOT = Path(__file__).parents[2].resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import the function to test
# Since it's at the top level of cli.py, we can import it
from polecat.cli import _fetch_github_issue


def test_fetch_github_issue_id_synthesis():
    """Test that safe task IDs are synthesized from issue references."""

    # Mock subprocess.run to simulate 'gh issue view'
    mock_result = MagicMock()
    mock_result.stdout = '{"title": "Bug report", "body": "It broke", "number": 123, "url": "https://github.com/owner/repo/issues/123"}'
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        # Case 1: Full URL
        issue = _fetch_github_issue("https://github.com/owner/repo/issues/123", None)
        assert issue["id"] == "gh-owner-repo-123"
        assert issue["number"] == 123
        assert issue["repo"] == "owner/repo"

        # Case 2: owner/repo#N
        issue = _fetch_github_issue("owner/repo#456", None)
        assert issue["id"] == "gh-owner-repo-456"
        assert issue["number"] == 456

        # Case 3: Bare #N with project
        issue = _fetch_github_issue("#789", "myproject")
        # synthesized ID uses project slug if repo not in ref
        assert issue["id"] == "gh-myproject-789"
        assert issue["number"] == 789


def test_fetch_github_issue_id_validation():
    """Test that synthesized IDs pass the polecat validation."""
    from polecat.validation import validate_task_id

    mock_result = MagicMock()
    mock_result.stdout = '{"title": "T", "body": "B", "number": 1, "url": "U"}'
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        issue = _fetch_github_issue("owner/repo#123", None)
        assert validate_task_id(issue["id"]) is True

        # Test with complex repo names
        issue = _fetch_github_issue("Org-Name/Repo_Name.Dot#1", None)
        assert issue["id"] == "gh-org-name-repo_name-dot-1"
        assert validate_task_id(issue["id"]) is True
