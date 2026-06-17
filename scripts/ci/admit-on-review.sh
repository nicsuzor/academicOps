#!/usr/bin/env bash
# admit-on-review.sh
#
# Authorization decision for review-driven PR admission
# (specs/workflows/pr-pipeline.md §3.2). The admission signal for the v2 PR
# pipeline is a maintainer's PR **review approval** — clicking "Approve" on the
# PR is the single human decision "this is a good idea; make it mergeable."
#
# This script is the FAIL-CLOSED, default-deny core of that gate. It decides
# whether a `pull_request_review` event should admit the PR. An approval admits
# ONLY when the reviewer is provably authorised; everything else (a non-approval
# review state, or an approval from someone without write access and not on the
# explicit allowlist) is a `skip`. Default-deny: an external contributor's
# approving review must never admit a PR.
#
# Why a script (not inline `if:`): the same robustness argument as
# review-attestation.sh — the decision is a pure function over a handful of
# inputs, so it is unit-tested without a `gh`/event stub
# (tests/test_admit_on_review.py). The workflow resolves the reviewer's
# repository permission via `gh api` and passes it in; this script holds only
# the policy.
#
# The decision is emitted as `state=` / `description=` lines on stdout (and into
# $GITHUB_OUTPUT when set). `state` is `admit` or `skip`. The calling workflow
# dispatches the admit + mechanic jobs only when state == admit.
#
# Required env:
#   REVIEW_STATE        the review.state from the event: approved | commented |
#                       changes_requested | dismissed.
#   REVIEWER_LOGIN      the login of the reviewer (github.event.review.user.login).
# Optional env:
#   REVIEWER_PERMISSION the reviewer's repo permission as reported by
#                       `repos/{repo}/collaborators/{login}/permission`
#                       (admin | maintain | write | triage | read | none).
#                       Default: "none" (fail closed if the workflow could not
#                       resolve it).
#   ADMIT_ALLOWLIST     space-separated logins that may admit regardless of the
#                       resolved permission (belt-and-suspenders for the
#                       maintainer). Default: empty.

set -euo pipefail

REVIEW_STATE="${REVIEW_STATE:?REVIEW_STATE is required}"
REVIEWER_LOGIN="${REVIEWER_LOGIN:?REVIEWER_LOGIN is required}"
REVIEWER_PERMISSION="${REVIEWER_PERMISSION:-none}"  # allow-fallback: fail closed when the workflow could not resolve a permission
ADMIT_ALLOWLIST="${ADMIT_ALLOWLIST:-}"

emit() {
  printf 'state=%s\n' "$1"
  printf 'description=%s\n' "$2"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      printf 'state=%s\n' "$1"
      printf 'description=%s\n' "$2"
    } >>"$GITHUB_OUTPUT"
  fi
}

# (1) Only an explicit approval is an admission signal. A comment or a
# changes-requested review is never an admission.
if [[ "$REVIEW_STATE" != "approved" ]]; then
  emit "skip" "Not an approval (review state: ${REVIEW_STATE}) — no admission."
  exit 0
fi

# (2) Authorisation: write-class repo permission, OR an explicit allowlist entry.
# Default-deny on anything else (triage/read/none, or an unresolved permission).
authorized="false"
case "$REVIEWER_PERMISSION" in
  admin | maintain | write) authorized="true" ;;
esac
# Read into an array rather than `for login in $ADMIT_ALLOWLIST`: `read -r -a`
# splits on whitespace without pathname expansion, so a stray '*'/'?' in the
# allowlist can't glob against the working directory, and the quoted iteration
# below stays glob-safe too.
read -r -a admit_logins <<<"$ADMIT_ALLOWLIST"
for login in "${admit_logins[@]}"; do
  if [[ "$login" == "$REVIEWER_LOGIN" ]]; then
    authorized="true"
  fi
done

if [[ "$authorized" != "true" ]]; then
  emit "skip" "Approval by ${REVIEWER_LOGIN} ignored — not a maintainer (permission: ${REVIEWER_PERMISSION}). Default-deny."
  exit 0
fi

emit "admit" "Admitted by ${REVIEWER_LOGIN} (permission: ${REVIEWER_PERMISSION}) — good idea, make it mergeable."
