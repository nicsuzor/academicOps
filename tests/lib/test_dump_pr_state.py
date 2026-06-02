import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add aops-core/scripts to path for imports
SCRIPT_DIR = Path(__file__).parents[2] / "aops-core" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from dump_pr_state import _extract_trailers, _project_pr, apply_triage, fetch_prs

# Use a dynamically computed recent date so tests don't silently break when the
# hardcoded date crosses the 7-day stale threshold in dump_pr_state.apply_triage.
_RECENT = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def test_apply_triage_label_edit_failure_is_nonfatal(tmp_path, capsys):
    """apply_triage must not raise when gh pr edit --add-label exits non-zero."""
    pr = {
        "number": 42,
        "labels": [],
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [],
        "headRefName": "feature/x",
        "author": {"login": "someuser"},
        "updatedAt": "2026-05-01T00:00:00Z",
    }
    err = subprocess.CalledProcessError(
        1, ["gh", "pr", "edit", "42", "--add-label", "triage:pipeline"]
    )
    err.stderr = b"Label 'triage:pipeline' not found"
    with patch("dump_pr_state.subprocess.run", side_effect=err):
        apply_triage(pr, tmp_path)  # must not raise

    captured = capsys.readouterr()
    assert "Warning: label-edit failed" in captured.err
    assert "42" in captured.err


def test_apply_triage_catchall_is_pipeline(tmp_path):
    """Healthy PRs not matching other buckets get triage:pipeline, not needs-judgment."""
    pr = {
        "number": 10,
        "labels": [],
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [],
        "headRefName": "feature/x",
        "author": {"login": "someuser"},
        "updatedAt": _RECENT,
    }
    calls = []

    def capture_run(cmd, **kwargs):
        calls.append(cmd)
        return MagicMock()

    with patch("dump_pr_state.subprocess.run", side_effect=capture_run):
        apply_triage(pr, tmp_path)

    # The label-edit call should add triage:pipeline
    label_cmd = calls[0]
    assert "--add-label" in label_cmd
    idx = label_cmd.index("--add-label")
    assert label_cmd[idx + 1] == "triage:pipeline"


def test_apply_triage_auto_mergeable_for_green_approved_pr(tmp_path):
    """PRs that are mergeable, all-green CI, and approved get triage:auto-mergeable."""
    pr = {
        "number": 20,
        "labels": [],
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "reviewDecision": "APPROVED",
        "statusCheckRollup": [
            {"name": "lint", "conclusion": "SUCCESS", "status": "COMPLETED"},
            {"name": "test", "conclusion": "SUCCESS", "status": "COMPLETED"},
        ],
        "headRefName": "feature/y",
        "author": {"login": "someuser"},
        "updatedAt": _RECENT,
    }
    calls = []

    def capture_run(cmd, **kwargs):
        calls.append(cmd)
        return MagicMock()

    with patch("dump_pr_state.subprocess.run", side_effect=capture_run):
        apply_triage(pr, tmp_path)

    label_cmd = calls[0]
    assert "--add-label" in label_cmd
    idx = label_cmd.index("--add-label")
    assert label_cmd[idx + 1] == "triage:auto-mergeable"


def test_apply_triage_pipeline_when_not_yet_approved(tmp_path):
    """PRs with passing CI but no approval yet get triage:pipeline (not auto-mergeable)."""
    pr = {
        "number": 30,
        "labels": [],
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "reviewDecision": "REVIEW_REQUIRED",
        "statusCheckRollup": [
            {"name": "lint", "conclusion": "SUCCESS", "status": "COMPLETED"},
        ],
        "headRefName": "feature/z",
        "author": {"login": "someuser"},
        "updatedAt": _RECENT,
    }
    calls = []

    def capture_run(cmd, **kwargs):
        calls.append(cmd)
        return MagicMock()

    with patch("dump_pr_state.subprocess.run", side_effect=capture_run):
        apply_triage(pr, tmp_path)

    label_cmd = calls[0]
    assert "--add-label" in label_cmd
    idx = label_cmd.index("--add-label")
    assert label_cmd[idx + 1] == "triage:pipeline"


def test_apply_triage_escalate_labels_but_does_not_create_issue(tmp_path):
    """Escalated PRs get triage:escalate label but must NOT trigger gh issue create."""
    pr = {
        "number": 99,
        "url": "https://github.com/org/repo/pull/99",
        "labels": [],
        "isDraft": False,
        "mergeable": "CONFLICTING",
        "statusCheckRollup": [],
        "headRefName": "feature/conflict",
        "author": {"login": "someuser"},
        "updatedAt": _RECENT,
    }
    calls = []

    def capture_run(cmd, **kwargs):
        calls.append(cmd)
        return MagicMock()

    with patch("dump_pr_state.subprocess.run", side_effect=capture_run):
        apply_triage(pr, tmp_path)

    # Should have exactly one gh call: the label-edit
    assert len(calls) == 1
    assert "--add-label" in calls[0]
    idx = calls[0].index("--add-label")
    assert calls[0][idx + 1] == "triage:escalate"

    # No gh issue create call anywhere
    for cmd in calls:
        assert "issue" not in cmd, f"Unexpected gh issue call: {cmd}"


def test_fetch_prs_open_prs_populated_when_triage_fails(tmp_path):
    """open_prs must be returned even when apply_triage raises."""
    fake_pr = {
        "number": 1,
        "title": "test",
        "url": "https://github.com/org/repo/pull/1",
        "state": "open",
        "isDraft": False,
        "author": {"login": "user", "is_bot": False},
        "createdAt": "2026-05-01T00:00:00Z",
        "updatedAt": "2026-05-14T00:00:00Z",
        "headRefName": "feature/x",
        "baseRefName": "main",
        "body": "",
        "mergeable": "MERGEABLE",
        "reviewDecision": None,
        "statusCheckRollup": [],
        "files": [],
        "labels": [],
    }
    mock_result = MagicMock()
    mock_result.stdout = __import__("json").dumps([fake_pr])

    def run_side_effect(cmd, **kwargs):
        if "list" in cmd:
            return mock_result
        raise subprocess.CalledProcessError(1, cmd, stderr=b"label not found")

    with patch("dump_pr_state.subprocess.run", side_effect=run_side_effect):
        prs = fetch_prs(tmp_path, "open", limit=10)

    assert len(prs) == 1
    assert prs[0]["number"] == 1
