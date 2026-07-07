"""Reviewer-decision PR-body structure on bot PRs (task aops_2abaf040).

Two things are asserted here:

1. `_generate_pr_body` — the polecat bot PR path — scaffolds the reviewer-decision
   section skeleton onto every generated PR body, and does NOT duplicate it when
   the agent already authored the sections into `task.body` (mechanism (b)) or on
   re-emit of a previously-generated body (idempotency).
2. The hand-opened equivalent `.github/PULL_REQUEST_TEMPLATE.md` stays in sync
   with the operative code skeleton, so the two copies can't silently drift.
"""

from pathlib import Path
from types import SimpleNamespace

from polecat.cli import (
    PR_BODY_SECTION_HEADERS,
    PR_BODY_SKELETON,
    _generate_pr_body,
    _has_reviewer_decision_structure,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PR_TEMPLATE = REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"


def _task(id="task-1", title="My Task", body=""):
    return SimpleNamespace(id=id, title=title, body=body)


# --- bot path: scaffold is applied ---------------------------------------


def test_bot_pr_body_carries_all_sections():
    """A plain task body (no structure) → every reviewer-decision header lands."""
    out = _generate_pr_body(_task(body="Fix the widget.\n"))
    for header in PR_BODY_SECTION_HEADERS:
        assert header in out, f"missing {header!r} in generated bot PR body"
    # Posture must be an honest three-way choice, not a single checkbox.
    assert out.count("- [ ]") >= 3
    # Existing footer still emitted (not duplicated by the scaffold).
    assert "Closes task-1" in out


def test_scaffold_skipped_when_agent_authored_structure():
    """Mechanism (b): if the task body already carries the structure, do not
    scaffold a second copy — the headers appear exactly once."""
    body = PR_BODY_SKELETON + "\n\nFilled in by the agent.\n"
    out = _generate_pr_body(_task(body=body))
    for header in PR_BODY_SECTION_HEADERS:
        assert out.count(header) == 1, f"{header!r} duplicated"


def test_re_emit_is_idempotent():
    """Feeding a generated body back through the generator must not double the
    skeleton (simulates a re-run over a task whose body already has it)."""
    first = _generate_pr_body(_task(body="Fix the widget.\n"))
    second = _generate_pr_body(_task(body=first))
    for header in PR_BODY_SECTION_HEADERS:
        assert second.count(header) == 1, f"{header!r} duplicated on re-emit"


def test_acceptance_criteria_still_extracted_alongside_scaffold():
    body = "Do the thing.\n\n## Acceptance Criteria\n- [ ] check A\n"
    out = _generate_pr_body(_task(body=body))
    assert "## Acceptance Criteria" in out
    assert "- [ ] check A" in out
    assert "## Summary" in out  # scaffold present too


def test_structure_detector_threshold():
    assert _has_reviewer_decision_structure(PR_BODY_SKELETON)
    # A body with only one incidental header is not "structured".
    assert not _has_reviewer_decision_structure("## Summary\nblah\n")


# --- sync invariant: the two hand-maintained copies must agree ------------


def test_static_template_mirrors_code_skeleton():
    """`.github/PULL_REQUEST_TEMPLATE.md` (hand-opened PRs) must carry the same
    reviewer-decision sections as the operative code skeleton (bot PRs)."""
    assert PR_TEMPLATE.exists(), f"{PR_TEMPLATE} missing"
    template = PR_TEMPLATE.read_text()
    for header in PR_BODY_SECTION_HEADERS:
        assert header in template, f"template missing section {header!r}"
    # Same honest three-way Posture choice.
    assert template.count("- [ ]") >= 3
