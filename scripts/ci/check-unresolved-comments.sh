#!/usr/bin/env bash
# check-unresolved-comments.sh
#
# Gate decision for `admit-on-review.yml`'s `decide-mechanic` job
# (specs/workflows/pr-pipeline.md §5, §3.10).
#
# WHY THIS EXISTS (PR #2094 incident). A PR can have `enforcer-status` and
# `qa-status` both green — our own axiom/QA bots found nothing — while a
# third-party reviewer (Copilot, Gemini, ...) has left substantive inline
# review comments that were never addressed. Those comments land as a
# `COMMENTED`-state review, NOT `CHANGES_REQUESTED`, so they never trip
# `admit-on-review.yml`'s `authorize-changes`/`review-response` path (which is
# wired to `review.state == 'changes_requested'` only) — and they carry no
# commit-status signal at all, so `decide-mechanic`'s enforcer/qa/mergeable
# check never sees them either. Result: a PR with valid, unaddressed
# third-party feedback sails straight from admission to auto-merge with
# nobody ever reading the comments. (PR #2094, 2026-07-04: two Copilot
# comments landed, the human approved 13s later, admit+enforcer+qa were
# already green, and the PR merged 50s after approval — before the fixes for
# either comment existed.)
#
# This script restores the v1 `merge-prep` invariant (pr-pipeline.md "F5":
# "Read ALL reviews — framework agents + Gemini + Copilot + humans") as a
# DISPATCH signal: "is there an inline review comment, from anyone other than
# our own automation, that nobody has replied to?" It makes NO qualitative
# judgment about the comment's content (genuine bug vs. false positive) — that
# triage is the mechanic's job once dispatched (mechanic.agent.md
# `review-response` mode already defines "a thread is open if no reply from a
# bot already acknowledges a fix"; this script applies the same definition as
# a pre-merge gate, not just as in-scope instructions for an already-dispatched
# mechanic).
#
# A thread counts as addressed by ANY reply (from a human or a bot) — this
# script does not evaluate reply content, only presence. That keeps it a pure,
# deterministic function over the comments list, the same pattern as
# check-mechanical-red.sh and review-attestation.sh. It is deliberately
# conservative: a thread a human already resolved via GitHub's "Resolve
# conversation" button with no textual reply will still read as unaddressed
# here (the REST comments API carries no `isResolved` field; that requires a
# separate GraphQL query). The cost of that false positive is one extra
# mechanic pass that confirms "already resolved, no action needed" — cheap,
# versus the alternative this script exists to prevent (silently merging past
# valid unaddressed feedback).
#
# Outputs (stdout and $GITHUB_OUTPUT when set):
#   has_unresolved_comments — "true" or "false"
#   reason                  — human-readable diagnostic string
#
# Required env:
#   REPO         — owner/name (e.g. nicsuzor/academicOps).
#   PR_NUMBER    — the PR number.
# Optional env:
#   COMMENTS_JSON  — path to a file containing the `pulls/{pr}/comments` JSON
#                    array (testing / offline). When unset, fetched live via
#                    gh api --paginate.
#   EXCLUDE_LOGINS — space-separated GitHub logins whose comments/replies do
#                    NOT count (our own automation — a bot replying to itself
#                    is not "addressing" anything). Default covers the
#                    identities this repo's agents actually post/reply as
#                    (agent-qa.yml/agent-enforcer.yml: `gh pr review`/`gh api
#                    .../replies` authenticate as claude[bot] regardless of
#                    the job's GH_TOKEN; AOPS_BOT_GH_TOKEN-driven API calls
#                    post as botnicbot).

set -euo pipefail

REPO="${REPO:?REPO is required}"
PR_NUMBER="${PR_NUMBER:?PR_NUMBER is required}"
EXCLUDE_LOGINS="${EXCLUDE_LOGINS:-claude[bot] botnicbot github-actions[bot]}"  # allow-fallback: optional override; default is this repo's own automation identities (see header)

# ── Fetch review comments (testable via COMMENTS_JSON) ──────────────────────
# Pattern from check-mechanical-red.sh / review-attestation.sh.
if [[ -n "${COMMENTS_JSON:-}" ]]; then
  comments="$(cat "$COMMENTS_JSON")"
else
  comments="$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments?per_page=100" --paginate)"
fi

if ! jq -e 'type == "array"' <<<"${comments:-}" >/dev/null 2>&1; then
  comments="[]"
fi

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

exclude_json="$(jq -R -s -c 'gsub("\n"; "") | split(" ") | map(select(length > 0))' <<<"$EXCLUDE_LOGINS")"

# An "open" thread: a root comment (in_reply_to_id absent/null) authored by
# someone NOT in EXCLUDE_LOGINS, with zero comments (from ANYONE) replying to
# it. Reply presence alone marks a thread addressed — content is the
# mechanic's job, not this gate's.
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

open_count="$(jq 'length' <<<"$open_threads")"

if [[ "$open_count" -eq 0 ]]; then
  emit "false" "No unaddressed review comment threads (all replied, or all from excluded automation logins)"
  exit 0
fi

authors="$(jq -r '[.[].login] | unique | join(", ")' <<<"$open_threads")"
emit "true" "${open_count} unaddressed review comment thread(s) from: ${authors} — dispatching mechanic to triage before merge"
