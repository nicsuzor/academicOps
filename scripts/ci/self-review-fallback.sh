#!/usr/bin/env bash
# self-review-fallback.sh
#
# SOURCE this file — it is a library, not a standalone entry point (no shebang
# execution, no `set -euo pipefail` here: sourcing a script that sets shell
# options would silently change the CALLING script's error-exit behaviour for
# everything after the `source` line, which is the wrong contract for a shared
# library — mirrors scripts/ci/reviewer-authz.sh). Every caller already sets
# its own `set -euo pipefail`.
#
# WHY THIS EXISTS (single-source-of-truth; PR #2081, RBG-caught duplication in
# the PR that first introduced this mechanism). `gh pr review` authenticates
# as `claude[bot]` regardless of the job's GH_TOKEN — that identity belongs to
# claude-code-action's own Bash-tool auth, not this workflow's env (see
# scripts/ci/enforcer-terminal-status.sh's header for the full explanation).
# When a PR's own author identity is also `claude[bot]`, GitHub rejects the
# formal review as a self-review, and enforcer.agent.md / qa.agent.md have the
# agent post its verdict as a PR comment instead, carrying a structured
# `<!-- aops:self-review-fallback agent=<name> sha=<sha> verdict=<...> -->`
# marker. This file is the single place that recovers a verdict from that
# marker — every caller (currently `scripts/ci/enforcer-terminal-status.sh`
# and `agent-qa.yml`'s terminal-status step) sources it instead of
# reimplementing the marker format, the `jq` filter, and the trust-scoping
# check independently. specs/workflows/pr-pipeline.md §4.2 "Self-review
# identity-collision fallback" is the normative contract this implements.
#
# Usage:
#   source scripts/ci/self-review-fallback.sh
#   verdict=$(fallback_verdict_from_comments "$COMMENTS_JSON" "$AGENT_NAME" "$HEAD_SHA")
#
# fallback_verdict_from_comments COMMENTS_JSON AGENT_NAME HEAD_SHA
#   COMMENTS_JSON  the PR's issue-comments JSON array (as returned by
#                  `gh api repos/{repo}/issues/{pr}/comments`), as a string.
#   AGENT_NAME     which agent's fallback to look for (e.g. "enforcer", "qa")
#                  — must match the marker's `agent=` field exactly.
#   HEAD_SHA       exact SHA to match — must match the marker's `sha=` field
#                  exactly. Stale fallback comments from an earlier SHA are
#                  never read as the current SHA's verdict.
#   Prints APPROVED, CHANGES_REQUESTED, or an empty string (no match) to
#   stdout. Never exits the caller — a pure function over its three arguments.
#
#   Trust is scoped to comments authored by `claude[bot]` specifically — the
#   same identity a genuine review would have come from, so this recovers no
#   new trust the review path didn't already grant. An arbitrary commenter
#   (including a malicious PR participant) forging the marker text cannot
#   manufacture a verdict.

fallback_verdict_from_comments() {
  local comments_json="$1" agent_name="$2" head_sha="$3"
  local marker="<!-- aops:self-review-fallback agent=${agent_name} sha=${head_sha} verdict="

  local body
  body="$(jq -r --arg login "claude[bot]" --arg marker "$marker" '
    [.[] | select(.user.login == $login) | select((.body // "") | contains($marker))]
    | last | .body // ""' <<<"$comments_json")"

  # Read the verdict value immediately following the marker, not a substring
  # scan of the whole comment body — a body containing both "verdict=APPROVED"
  # and "verdict=CHANGES_REQUESTED" (e.g. quoted prior text, prose comparing
  # states) would otherwise always match APPROVED first regardless of which
  # one the marker itself carries.
  local after_marker="${body##*"$marker"}"

  case "$after_marker" in
    "APPROVED"*) printf 'APPROVED' ;;
    "CHANGES_REQUESTED"*) printf 'CHANGES_REQUESTED' ;;
    *) printf '' ;;
  esac
}
