#!/usr/bin/env bash
# check-unresolved-comments.sh
#
# Gate decision feeding the REQUIRED `comment-triage-status` check
# (specs/workflows/pr-pipeline.md §5, §3.10) and the mechanic's
# review-response dispatch (admit-on-review.yml's `decide-mechanic`).
#
# WHY THIS EXISTS (PR #2094 incident). A PR can have `enforcer-status` and
# `qa-status` both green — our own axiom/QA bots found nothing — while a
# third-party reviewer (Copilot, Gemini, ...) has left substantive review
# feedback that was never addressed. That feedback lands as a `COMMENTED`-state
# review, NOT `CHANGES_REQUESTED`, so it never trips `admit-on-review.yml`'s
# `authorize-changes`/`review-response` path (wired to
# `review.state == 'changes_requested'` only) — and it carries no commit-status
# signal at all, so the reviewer-colour + mergeability check never sees it
# either. Result: a PR with valid, unaddressed third-party feedback sails
# straight from admission to auto-merge with nobody ever reading it. (PR #2094,
# 2026-07-04: two Copilot inline comments landed, the human approved ~74s
# later, admit+enforcer+qa were already green, and the PR merged ~50s after
# approval — before the fixes for either comment existed.)
#
# This script restores the v1 `merge-prep` invariant (pr-pipeline.md "F5":
# "Read ALL reviews — framework agents + Gemini + Copilot + humans") as a
# DETERMINISTIC, fail-closed signal over TWO surfaces:
#   1. Inline review-comment threads (`GET /pulls/{pr}/comments`).
#   2. Review bodies (`GET /pulls/{pr}/reviews`) — a COMMENTED/CHANGES_REQUESTED
#      review can carry substantive feedback in its body with ZERO inline
#      comments attached; checking only inline threads would miss that class.
#
# It makes NO qualitative judgment about content (genuine bug vs. false
# positive) — that triage is the mechanic's job once dispatched in
# `review-response` mode. A thread/review counts as addressed by ANY
# subsequent reply/comment (from a human or a bot) — presence, not content.
# Same pure-function pattern as check-mechanical-red.sh / review-attestation.sh.
#
# FAIL-CLOSED (unlike v1 of this script): any `gh api` fetch failure, or a
# payload that doesn't parse as the expected JSON array, is treated as
# "unresolved comments present" — matching review-attestation.sh's convention
# for this class of required, merge-blocking check. A silent fail-open here
# would recreate exactly the failure mode this script exists to close.
#
# Outputs (stdout and $GITHUB_OUTPUT when set):
#   has_unresolved_comments — "true" or "false"
#   reason                  — human-readable diagnostic string
#
# Required env:
#   REPO         — owner/name (e.g. nicsuzor/academicOps).
#   PR_NUMBER    — the PR number.
# Optional env:
#   COMMENTS_JSON       — path to a file containing the `pulls/{pr}/comments`
#                         JSON array (testing / offline).
#   REVIEWS_JSON        — path to a file containing the `pulls/{pr}/reviews`
#                         JSON array (testing / offline).
#   ISSUE_COMMENTS_JSON — path to a file containing the `issues/{pr}/comments`
#                         (PR-level, not inline) JSON array (testing / offline).
#                         Used only to decide whether a review body was
#                         followed by ANY later PR-level comment (the mechanic's
#                         `gh pr comment` triage summary is exactly such a
#                         comment in production).
#   When any *_JSON var is unset, the corresponding list is fetched live via
#   `gh api --paginate`.
#   EXCLUDE_LOGINS — space-separated GitHub logins whose comments/reviews/
#                    replies do NOT count (our own automation — a bot replying
#                    to itself is not "addressing" anything). Default covers
#                    the identities this repo's agents actually post/reply as
#                    (agent-qa.yml/agent-enforcer.yml authenticate as
#                    claude[bot] regardless of the job's GH_TOKEN;
#                    AOPS_BOT_GH_TOKEN-driven API calls post as botnicbot).

set -euo pipefail

REPO="${REPO:?REPO is required}"
PR_NUMBER="${PR_NUMBER:?PR_NUMBER is required}"
EXCLUDE_LOGINS="${EXCLUDE_LOGINS:-claude[bot] botnicbot github-actions[bot]}"  # allow-fallback: optional override; default is this repo's own automation identities (see header)

emit() {
  printf 'has_unresolved_comments=%s\n' "$1"
  printf 'reason=%s\n' "$2"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      printf 'has_unresolved_comments=%s\n' "$1"
      printf 'reason=%s\n' "$2"
    } >>"$GITHUB_OUTPUT"
  fi
}

# ── Fetch a paginated GitHub list, fail CLOSED on any error (testable via a
# ── *_JSON override file). A live `gh api` failure or a payload that doesn't
# ── parse as a JSON array both count as "cannot prove nothing is unresolved".
#
# NOTE: this function is always called as `var="$(fetch_or_fail_closed ...)"` —
# a command substitution, which runs the function body in a SUBSHELL. An
# `exit` inside that subshell would only end the subshell, silently letting
# the main script continue with garbage input — so failure is signalled via
# return code ONLY; the caller does the emit+exit in the main shell.
fetch_or_fail_closed() {
  local override_var="$1" endpoint="$2" label="$3" out
  local override_val="${!override_var:-}"
  if [[ -n "$override_val" ]]; then
    out="$(cat "$override_val")"
  elif ! out="$(gh api "repos/${REPO}/${endpoint}?per_page=100" --paginate 2>/dev/null)"; then
    echo "gh api fetch for ${label} FAILED" >&2
    return 1
  fi
  if ! jq -e 'type == "array"' <<<"${out:-}" >/dev/null 2>&1; then
    echo "${label} payload was not a valid JSON array" >&2
    return 1
  fi
  printf '%s' "$out"
}

if ! comments="$(fetch_or_fail_closed COMMENTS_JSON "pulls/${PR_NUMBER}/comments" "inline review comments")"; then
  emit "true" "gh api fetch/parse for inline review comments FAILED — failing closed (cannot prove no unresolved comments exist)"
  exit 0
fi
if ! reviews="$(fetch_or_fail_closed REVIEWS_JSON "pulls/${PR_NUMBER}/reviews" "reviews")"; then
  emit "true" "gh api fetch/parse for reviews FAILED — failing closed (cannot prove no unresolved reviews exist)"
  exit 0
fi
if ! issue_comments="$(fetch_or_fail_closed ISSUE_COMMENTS_JSON "issues/${PR_NUMBER}/comments" "PR-level comments")"; then
  emit "true" "gh api fetch/parse for PR-level comments FAILED — failing closed (cannot prove no unresolved reviews exist)"
  exit 0
fi

exclude_json="$(jq -R -s -c 'gsub("\n"; "") | split(" ") | map(select(length > 0))' <<<"$EXCLUDE_LOGINS")"

# ── Surface 1: inline review-comment threads ────────────────────────────────
# An "open" thread: a root comment (in_reply_to_id absent/null) authored by
# someone NOT in EXCLUDE_LOGINS, with zero comments (from ANYONE) replying to
# it. Reply presence alone marks a thread addressed — content is the
# mechanic's job, not this gate's. Deliberately conservative: a thread a human
# already resolved via GitHub's "Resolve conversation" button with no textual
# reply still reads as unaddressed here (the REST comments API carries no
# `isResolved` field). The cost of that false positive is one extra mechanic
# pass confirming "already resolved, no action needed" — cheap, versus the
# alternative this script exists to prevent.
open_threads="$(jq -c --argjson exclude "$exclude_json" '
  ($exclude | map({(.): true}) | add // {}) as $excl
  | [.[] | select(.in_reply_to_id == null)] as $roots
  | ([.[] | select(.in_reply_to_id != null) | .in_reply_to_id] | unique) as $replied_to
  | [ $roots[]
      | select(($excl[.user.login // ""] // false) | not)
      | . as $root
      | select(($replied_to | index($root.id)) == null)
      | {id: $root.id, login: $root.user.login, path: $root.path, line: ($root.line // $root.original_line)}
    ]
' <<<"$comments")"

# ── Surface 2: review bodies (no inline comment required) ──────────────────
# A COMMENTED/CHANGES_REQUESTED review from someone NOT in EXCLUDE_LOGINS with
# a non-empty body counts as "open" unless a PR-level (issue) comment from
# ANYONE landed strictly after it was submitted — the mechanic's own
# review-response triage summary (`gh pr comment`, mechanic.agent.md) is
# exactly such a comment in production, so a genuinely-triaged review reads as
# addressed. Presence/timing only, not content — same discipline as surface 1.
open_reviews="$(jq -c --argjson exclude "$exclude_json" --argjson issue_comments "$issue_comments" '
  ($exclude | map({(.): true}) | add // {}) as $excl
  | ($issue_comments | map(.created_at)) as $reply_times
  | [ .[]
      | select(.state == "COMMENTED" or .state == "CHANGES_REQUESTED")
      | select((.body // "" | gsub("\\s"; "")) != "")
      | select(($excl[.user.login // ""] // false) | not)
      | . as $review
      | select(($reply_times | map(select(. > $review.submitted_at)) | length) == 0)
      | {id: $review.id, login: $review.user.login, state: $review.state, submitted_at: $review.submitted_at}
    ]
' <<<"$reviews")"

thread_count="$(jq 'length' <<<"$open_threads")"
review_count="$(jq 'length' <<<"$open_reviews")"

if [[ "$thread_count" -eq 0 && "$review_count" -eq 0 ]]; then
  emit "false" "No unaddressed review comment threads or review bodies (all replied to, or all from excluded automation logins)"
  exit 0
fi

reasons=()
if [[ "$thread_count" -gt 0 ]]; then
  authors="$(jq -r '[.[].login] | unique | join(", ")' <<<"$open_threads")"
  reasons+=("${thread_count} unaddressed inline comment thread(s) from: ${authors}")
fi
if [[ "$review_count" -gt 0 ]]; then
  authors="$(jq -r '[.[].login] | unique | join(", ")' <<<"$open_reviews")"
  reasons+=("${review_count} unaddressed review(s) from: ${authors}")
fi

reasons_joined="$(printf '%s; ' "${reasons[@]}")"
reasons_joined="${reasons_joined%; }"
emit "true" "${reasons_joined} — dispatching mechanic to triage before merge"
