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
