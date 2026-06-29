#!/usr/bin/env bash
# find-conflicting-admitted-prs.sh
#
# Discover open PRs that are CONFLICTING with the base AND already approved by a
# write-class maintainer, and emit the matrix of PRs that need the conflict-
# resolving mechanic dispatched. This is the discover step of the conflict-
# admission sweep (specs/workflows/pr-pipeline.md §3.11).
#
# WHY A SWEEP EXISTS. GitHub never fires `pull_request` *or* `pull_request_review`
# on a conflicting PR — it cannot build the `refs/pull/N/merge` ref those events'
# runs check out, so no run is created (silently). That means neither the triage
# pipeline (`pr-pipeline.yml`) nor the admission workflow (`admit-on-review.yml`)
# can ever reach a conflicting PR. A workflow on `push` to the base branch and on
# `schedule` runs on events immune to the merge-ref constraint, so it is the only
# way to drive the mechanic onto a conflicting PR. The maintainer's existing
# review approval is the admission signal (no second gesture needed).
#
# AUTHORIZATION mirrors scripts/ci/admit-on-review.sh: a PR is "admitted" when the
# latest review by a write-class collaborator (or an ADMIT_ALLOWLIST login) is
# APPROVED, and no write-class reviewer's latest review is CHANGES_REQUESTED.
#
# BOUNDING. A PR is skipped when a *terminal* `mechanic-status` (success/failure)
# already exists on its current head SHA — the mechanic has already run (and
# either resolved → new SHA, or halted → escalated) on this exact diff. This stops
# the schedule from re-dispatching every tick on a SHA the mechanic already
# processed; a new push (new SHA) re-enters the sweep.
#
# Emits to $GITHUB_OUTPUT (and always to stdout):
#   matrix = compact JSON array of {number, ref, sha}  (the mechanic matrix)
#   any    = "true" | "false"
#
# Required env:
#   REPO              owner/name (e.g. nicsuzor/academicOps).
# Optional env:
#   BASE_BRANCH       PR base branch to sweep (default: dev).
#   ADMIT_ALLOWLIST   space-separated logins always treated as write-class
#                     (default: nicsuzor — belt-and-suspenders, same as admit-on-review).
#   PRS_JSON          (test) path to a file holding the `gh pr list` JSON array;
#                     live `gh pr list` is used when unset.
#   PERM_JSON         (test) path to a file holding a {login: permission} map;
#                     live `gh api …/permission` is used when unset.
#   MECH_STATUS_JSON  (test) path to a file holding a {sha: mechanic-state} map;
#                     live `gh api …/statuses` is used when unset.

set -euo pipefail

REPO="${REPO:?REPO is required}"
BASE_BRANCH="${BASE_BRANCH:-dev}"  # allow-fallback: optional; dev is the integration branch all PRs target.
ADMIT_ALLOWLIST="${ADMIT_ALLOWLIST:-nicsuzor}"  # allow-fallback: optional belt-and-suspenders allowlist; write-class permission is the primary authorisation.

# ── Fetch the open PR list (testable via PRS_JSON) ──────────────────────────
if [[ -n "${PRS_JSON:-}" ]]; then
  prs="$(cat "$PRS_JSON")"
else
  prs="$(gh pr list --repo "$REPO" --base "$BASE_BRANCH" --state open --limit 100 \
    --json number,headRefName,headRefOid,mergeable,isDraft,isCrossRepository,latestReviews)"
fi
if ! jq -e 'type == "array"' <<<"${prs:-}" >/dev/null 2>&1; then
  prs="[]"
fi

# ── Per-reviewer permission (live gh api, or injected PERM_JSON for tests) ───
perm_of() {
  local login="$1"
  if [[ -n "${PERM_JSON:-}" ]]; then
    jq -r --arg l "$login" '.[$l] // "none"' "$PERM_JSON"
  else
    gh api "repos/$REPO/collaborators/$login/permission" --jq '.permission' 2>/dev/null || echo "none"
  fi
}

is_writeclass() {
  case "$1" in admin | maintain | write) return 0 ;; esac
  return 1
}

# ── Latest mechanic-status on a SHA (live gh api, or injected for tests) ─────
mech_status_of() {
  local sha="$1"
  if [[ -n "${MECH_STATUS_JSON:-}" ]]; then
    jq -r --arg s "$sha" '.[$s] // ""' "$MECH_STATUS_JSON"
  else
    gh api "repos/$REPO/commits/$sha/statuses?per_page=100" \
      --jq '[.[] | select(.context == "mechanic-status")] | sort_by(.created_at) | last.state // ""' 2>/dev/null || echo ""
  fi
}

matrix='[]'

while IFS= read -r pr; do
  [[ -z "$pr" ]] && continue

  number=$(jq -r '.number' <<<"$pr")
  draft=$(jq -r '.isDraft' <<<"$pr")
  xrepo=$(jq -r '.isCrossRepository' <<<"$pr")
  mergeable=$(jq -r '.mergeable' <<<"$pr")
  ref=$(jq -r '.headRefName' <<<"$pr")
  sha=$(jq -r '.headRefOid' <<<"$pr")

  # Only conflicting, ready, same-repo PRs (a fork PR cannot mint the bot token).
  [[ "$mergeable" == "CONFLICTING" ]] || continue
  [[ "$draft" == "false" ]] || continue
  [[ "$xrepo" == "false" ]] || continue

  # Admission: a write-class maintainer's latest review is APPROVED, and no
  # write-class maintainer's latest review is CHANGES_REQUESTED.
  approved=false
  blocked=false
  while IFS= read -r rv; do
    [[ -z "$rv" ]] && continue
    login=$(jq -r '.author.login // ""' <<<"$rv")
    state=$(jq -r '.state // ""' <<<"$rv")
    [[ -n "$login" ]] || continue

    wc=false
    perm=$(perm_of "$login")
    is_writeclass "$perm" && wc=true
    for a in $ADMIT_ALLOWLIST; do [[ "$a" == "$login" ]] && wc=true; done
    [[ "$wc" == "true" ]] || continue

    case "$state" in
      APPROVED) approved=true ;;
      CHANGES_REQUESTED) blocked=true ;;
    esac
  done < <(jq -c '.latestReviews[]?' <<<"$pr")

  [[ "$approved" == "true" && "$blocked" == "false" ]] || continue

  # Bound: skip if the mechanic already produced a terminal verdict on THIS SHA.
  mstate=$(mech_status_of "$sha")
  case "$mstate" in success | failure) continue ;; esac

  matrix=$(jq -cn --argjson m "$matrix" --arg n "$number" --arg r "$ref" --arg s "$sha" \
    '$m + [{number: ($n | tonumber), ref: $r, sha: $s}]')
done < <(jq -c '.[]' <<<"$prs")

any=false
[[ "$(jq 'length' <<<"$matrix")" -gt 0 ]] && any=true

echo "matrix=$matrix"
echo "any=$any"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "matrix=$matrix"
    echo "any=$any"
  } >>"$GITHUB_OUTPUT"
fi
