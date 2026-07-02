#!/usr/bin/env bash
# reviewer-authz.sh
#
# SOURCE this file — it is a library, not a standalone entry point (no shebang
# execution, no `set -euo pipefail` here: sourcing a script that sets shell
# options would silently change the CALLING script's error-exit behaviour for
# everything after the `source` line, which is the wrong contract for a shared
# library). Every caller already sets its own `set -euo pipefail`.
#
# WHY THIS EXISTS (process-drift prevention, specs/workflows/pr-pipeline.md
# §5.1). "Is this reviewer write-class-or-allowlisted?" used to be
# reimplemented independently in three places — scripts/ci/admit-on-review.sh,
# scripts/ci/find-conflicting-admitted-prs.sh, and inline YAML bash in
# admit-on-review.yml's authorize-changes job — with no test enforcing they
# stayed identical. This file is the single source of truth all three now
# source instead.
#
# Usage:
#   source scripts/ci/reviewer-authz.sh
#   if is_authorized_reviewer "$LOGIN" "$PERMISSION" "$ALLOWLIST"; then ...
#
# is_authorized_reviewer LOGIN PERMISSION ALLOWLIST
#   LOGIN       the reviewer's GitHub login.
#   PERMISSION  the reviewer's repo permission (admin | maintain | write |
#               triage | read | none | ""). Only admin/maintain/write pass.
#   ALLOWLIST   space-separated logins that are authorized regardless of
#               PERMISSION (belt-and-suspenders for the maintainer).
#   Returns 0 (authorized) or 1 (not authorized). Never exits the caller — a
#   pure predicate over its three arguments.

# Single source of truth for the belt-and-suspenders allowlist (pr-pipeline.md
# §3.2). Only takes effect if the sourcing script/step hasn't already set
# ADMIT_ALLOWLIST — an explicit env value always wins over this default.
: "${ADMIT_ALLOWLIST:=nicsuzor}"  # allow-fallback: optional belt-and-suspenders allowlist; write-class permission is the primary authorisation (same rationale as the pre-consolidation default it replaces).

is_authorized_reviewer() {
  local login="$1" permission="$2" allowlist="$3"

  case "$permission" in
    admin | maintain | write) return 0 ;;
  esac

  # Read into an array rather than `for login in $allowlist`: `read -r -a`
  # splits on whitespace without pathname expansion, so a stray '*'/'?' in
  # the allowlist can't glob against the working directory.
  local -a allow
  read -r -a allow <<<"$allowlist"
  local a
  for a in "${allow[@]}"; do
    [[ "$a" == "$login" ]] && return 0
  done

  return 1
}
