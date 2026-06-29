#!/usr/bin/env bash
# review-attestation.sh
#
# Fail-closed liveness + named-reviewer attestation for the PR pipeline
# (specs/workflows/pr-pipeline.md §3.7, GitHub issue #1450).
#
# Problem this defends against: the deep-review pipeline can be silently DEAD —
# a startup_failure, a skipped run, or a reusable workflow that never executed —
# in which case the named reviewer statuses are simply ABSENT on the merged SHA,
# and absence is silently treated as a pass. Separately, a stale status (a
# success carrying a *different* SHA's attestation in its target_url) must not be
# read as "this diff was reviewed".
#
# This script makes the named-reviewer evidence an EXPLICIT, fail-closed signal.
# It independently re-reads each named reviewer's commit status on the EXACT SHA
# under review and decides:
#   - success  ONLY IF every named reviewer posted a genuine terminal `success`
#              whose attestation `target_sha` (from the §10 target_url channel)
#              equals HEAD_SHA — i.e. a named reviewer provably ran on THIS SHA.
#   - failure  otherwise — including absent, pending, failure/error, or stale
#              (target_sha != HEAD_SHA). Default-deny: anything short of positive
#              proof of a live pass on this SHA fails closed.
#
# The decision is emitted as `state=` / `description=` lines on stdout (and into
# $GITHUB_OUTPUT when set). The calling workflow posts the `review-attestation`
# commit status and fails the job when state != success, so a dead/skipped
# pipeline reads RED, never as a silent pass. `review-attestation` is a REQUIRED
# check (ruleset 13762049), so an absent attestation (workflow startup_failure)
# leaves the required check unsatisfied and the PR unmergeable.
#
# The `gh api` call is isolated behind STATUSES_JSON so the decision logic is a
# pure function over the statuses array and is unit-tested without a gh stub
# (tests/test_review_attestation.py).
#
# Required env:
#   REPO       owner/name (only used for the live gh api fetch).
#   HEAD_SHA   the exact PR head SHA under review.
# Optional env:
#   REVIEWERS     space-separated named-reviewer status contexts that must have
#                 run on this SHA. Default: "enforcer-status qa-status".
#   STATUSES_JSON path to a file containing the commit-statuses JSON array
#                 (testing / offline). When unset, fetched live via gh api.

set -euo pipefail

REPO="${REPO:?REPO is required}"
HEAD_SHA="${HEAD_SHA:?HEAD_SHA is required}"
REVIEWERS="${REVIEWERS:-enforcer-status qa-status}"  # allow-fallback: optional, configurable reviewer set; default = the framework's two named merge-gate reviewers (§4.2)

if [[ -n "${STATUSES_JSON:-}" ]]; then
  statuses="$(cat "$STATUSES_JSON")"
else
  statuses="$(gh api "repos/${REPO}/commits/${HEAD_SHA}/statuses?per_page=100")"
fi

short="${HEAD_SHA:0:12}"
missing=""

for ctx in $REVIEWERS; do
  # Latest status for this context, by created_at (the genuine verdict, not a
  # superseded earlier pending/failure on the same SHA).
  latest="$(jq -c --arg c "$ctx" \
    '[.[] | select(.context == $c)] | sort_by(.created_at) | last // empty' <<<"$statuses")"

  if [[ -z "$latest" || "$latest" == "null" ]]; then
    missing="${missing} ${ctx}:absent"
    continue
  fi

  state="$(jq -r '.state // ""' <<<"$latest")"
  url="$(jq -r '.target_url // ""' <<<"$latest")"

  if [[ "$state" != "success" ]]; then
    # pending / failure / error — not a live pass.
    missing="${missing} ${ctx}:${state:-unknown}"  # allow-fallback: display-only label in the failure message when a status row carries no state field
  elif [[ "$url" != *"target_sha=${HEAD_SHA}"* ]]; then
    # success, but the attestation is for a different SHA (stale) — this diff was
    # not the one reviewed. Fail closed.
    missing="${missing} ${ctx}:stale"
  fi
done

# Trim leading whitespace.
missing="${missing# }"

if [[ -z "$missing" ]]; then
  out_state="success"
  out_desc="Named reviewers ran live on ${short}: ${REVIEWERS// /, }"
else
  out_state="failure"
  # The commit-status description is capped (~140 chars), so it carries only the
  # terse token list; the actionable cause + remedy goes to the run summary below.
  out_desc="Liveness FAIL on ${short} -- no live pass from: ${missing} (see run summary for cause + fix)"
fi

printf 'state=%s\n' "$out_state"
printf 'description=%s\n' "$out_desc"

# Rich, actionable failure explanation in the GitHub Actions run summary (the
# "check / action interface"). Length-unbounded here, unlike the commit-status
# description. Written only on failure and only when a summary sink exists, so
# the pure stdout contract (state=/description=) the tests assert is unchanged.
if [[ "$out_state" != "success" && -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "## ❌ Review attestation failed on \`${short}\`"
    echo
    echo "The named merge-gate reviewers are not *proven* to have run on this exact commit, so the PR cannot merge (fail-closed; specs/workflows/pr-pipeline.md §3.7)."
    echo
    echo "| Reviewer | State on \`${short}\` |"
    echo "| --- | --- |"
    for tok in $missing; do
      echo "| \`${tok%%:*}\` | ${tok#*:} |"
    done
    echo
    echo "### What this means and how to fix it"
    case " $missing " in
      *:absent*) cat <<'EOF'
- **`absent`** — no verdict was posted on this commit. Most common cause: **the PR is not admitted yet** (the enforcer/qa reviewers only run after a maintainer approves the PR), or the pipeline failed to start / is wedged.
  - **Fix:** approve the PR to admit it, **or** run the **Force Review** workflow (Actions → *Force Review* → enter the PR number) to force the reviewers onto this commit.
EOF
      ;;
    esac
    case " $missing " in
      *:stale*) echo "- **\`stale\`** — a reviewer passed, but on a *different* commit; this exact diff was never reviewed. Push again or run **Force Review** to review this commit." ;;
    esac
    case " $missing " in
      *:failure*|*:error*) echo "- **\`failure\`/\`error\`** — a reviewer returned a genuine **red verdict** on this commit. Read its check output and address the finding; this is a real result, not a pipeline fault." ;;
    esac
    case " $missing " in
      *:pending*) echo "- **\`pending\`** — a reviewer is still running. Wait for it to finish; the attestation re-evaluates when the workflow re-runs on completion." ;;
    esac
  } >> "$GITHUB_STEP_SUMMARY"
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    printf 'state=%s\n' "$out_state"
    printf 'description=%s\n' "$out_desc"
  } >>"$GITHUB_OUTPUT"
fi
