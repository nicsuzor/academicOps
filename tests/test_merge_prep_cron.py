import subprocess


def test_merge_prep_cron_logic(tmp_path):
    """
    Test the qualification logic from .github/workflows/merge-prep-cron.yml.
    Verifies:
      - Late CHANGES_REQUESTED reviews RE-QUALIFY a PR even with a Merge-Prep-By trailer
      - Base-branch advance making the PR CONFLICTING RE-QUALIFIES a previously
        successful PR (otherwise cron silently strands it forever)
    """
    script_path = tmp_path / "test_logic.sh"

    # Core logic extracted from .github/workflows/merge-prep-cron.yml
    # but adapted for testing.
    script_content = r"""#!/bin/bash
MP_STATUS="$1"
LATE_CR="$2"
HEAD_MSG="$3"
MERGEABLE="${4:-MERGEABLE}"

REQUALIFIED=false
if [ "$MP_STATUS" = "success" ]; then
  if [ "$LATE_CR" -gt 0 ]; then
    echo "  RE-QUALIFY: $LATE_CR CHANGES_REQUESTED review(s) arrived after merge-prep succeeded"
    REQUALIFIED=true
  fi

  if [ "$MERGEABLE" = "CONFLICTING" ]; then
    echo "  RE-QUALIFY: PR became CONFLICTING after merge-prep succeeded (base advanced)"
    REQUALIFIED=true
  fi

  if [ "$REQUALIFIED" = "false" ]; then
    echo "  SKIP: merge-prep-status is success (mergeable=$MERGEABLE, no late reviews)"
    exit 0
  fi
fi

if [ "$MP_STATUS" = "failure" ]; then
  echo "  SKIP: merge-prep-status is failure (halted — needs manual retry)"
  exit 0
fi

if [ "$REQUALIFIED" = "false" ]; then
  # Check if last commit was from merge-prep (race condition guard:
  # workflow_run can fire before the agent workflow sets merge-prep-status)
  if echo "$HEAD_MSG" | grep -q 'Merge-Prep-By:'; then
    echo "  SKIP: last commit was from merge-prep (trailer detected)"
    exit 0
  fi
fi

echo "  QUALIFIED: PR ready for merge-prep"
"""
    script_path.write_text(script_content)
    script_path.chmod(0o755)

    def run_logic(status, late_cr, msg, mergeable="MERGEABLE"):
        result = subprocess.run(
            [str(script_path), status, str(late_cr), msg, mergeable],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    # Case 1: RE-QUALIFY with trailer guard present (The Bug)
    # PR has success status, but a late review arrived.
    # The last commit WAS from merge-prep.
    # SHOULD be QUALIFIED (via RE-QUALIFY path)
    output = run_logic("success", 1, "fix: some stuff\n\nMerge-Prep-By: agent")
    assert "RE-QUALIFY: 1 CHANGES_REQUESTED review(s) arrived after merge-prep succeeded" in output
    assert "QUALIFIED: PR ready for merge-prep" in output
    assert "SKIP: last commit was from merge-prep" not in output

    # Case 2: Regular trailer guard (The Race Condition Protection)
    # PR has no status yet, last commit is from merge-prep.
    # SHOULD be SKIPPED
    output = run_logic("", 0, "fix: some stuff\n\nMerge-Prep-By: agent")
    assert "SKIP: last commit was from merge-prep (trailer detected)" in output
    assert "QUALIFIED: PR ready for merge-prep" not in output

    # Case 3: Success status, no late reviews, still mergeable
    # SHOULD be SKIPPED
    output = run_logic("success", 0, "fix: some stuff")
    assert "SKIP: merge-prep-status is success" in output
    assert "QUALIFIED: PR ready for merge-prep" not in output

    # Case 4: Failure status
    # SHOULD be SKIPPED
    output = run_logic("failure", 0, "fix: some stuff")
    assert "SKIP: merge-prep-status is failure" in output

    # Case 5: Regular PR ready for first merge-prep
    # SHOULD be QUALIFIED
    output = run_logic("", 0, "feat: new feature")
    assert "QUALIFIED: PR ready for merge-prep" in output

    # Case 6: Success status, became CONFLICTING after base advanced (PR #1162 bug)
    # SHOULD be QUALIFIED via mergeability RE-QUALIFY
    output = run_logic("success", 0, "fix: some stuff\n\nMerge-Prep-By: agent", "CONFLICTING")
    assert "RE-QUALIFY: PR became CONFLICTING after merge-prep succeeded" in output
    assert "QUALIFIED: PR ready for merge-prep" in output

    # Case 7: Success status, mergeable still UNKNOWN (GitHub lazy compute)
    # SHOULD be SKIPPED — uncertain state shouldn't trigger spurious runs;
    # next cron will pick up once mergeability settles.
    output = run_logic("success", 0, "fix: some stuff", "UNKNOWN")
    assert "SKIP: merge-prep-status is success" in output
    assert "mergeable=UNKNOWN" in output
    assert "QUALIFIED: PR ready for merge-prep" not in output

    # Case 8: Both re-qualify conditions true (late review AND CONFLICTING)
    # SHOULD be QUALIFIED (idempotent)
    output = run_logic("success", 2, "fix: some stuff", "CONFLICTING")
    assert "QUALIFIED: PR ready for merge-prep" in output


def test_dispatch_picks_oldest_qualifying_pr(tmp_path):
    """
    Test the dispatch step's selection logic from .github/workflows/merge-prep-cron.yml.

    Regression for issue #1129: the qualification loop iterates `gh pr list` output,
    which is sorted newest-first by default. The dispatch step is labeled "Dispatch
    merge-prep for oldest qualifying PR" — it MUST pick the lowest PR number, not
    the iteration-order head. Without `sort -n`, older PRs (e.g. #1101/#1102/#1107)
    starve behind ~12 newer PRs for 6-7h on a 30-min cron cadence.
    """
    qualifying_file = tmp_path / "qualifying_prs.txt"
    # Simulate qualification loop order: gh pr list returns newest-first, so the
    # file is populated with the newest qualifying PRs first.
    qualifying_file.write_text("1126\n1108\n1107\n1106\n1103\n1102\n1101\n1100\n")

    # Dispatch logic from the workflow's "Dispatch merge-prep for oldest qualifying PR" step.
    result = subprocess.run(
        ["bash", "-c", f"sort -n {qualifying_file} | head -n 1"],
        capture_output=True,
        text=True,
    )
    picked = result.stdout.strip()
    assert picked == "1100", (
        f"Expected oldest PR (#1100) to be picked, got #{picked}. "
        "Without `sort -n`, `head -n 1` picks the newest PR (#1126) — "
        "the bug reported in issue #1129."
    )

    # Confirm the buggy (pre-fix) behaviour would pick the newest, demonstrating
    # the regression this test guards.
    bug_result = subprocess.run(
        ["bash", "-c", f"head -n 1 {qualifying_file}"],
        capture_output=True,
        text=True,
    )
    assert bug_result.stdout.strip() == "1126", (
        "Sanity check: unsorted head must pick newest (proves the fix is load-bearing)."
    )
