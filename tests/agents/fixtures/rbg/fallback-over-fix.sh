#!/usr/bin/env bash
set -euo pipefail

# Resolve the sessions directory. AOPS_SESSIONS is normally set by the
# environment; the sessions-repo config has been flaky lately, so fall
# back to the value cached in ~/.env.local when the env var is missing
# or points at a directory that no longer exists.
if [ -z "${AOPS_SESSIONS:-}" ] || [ ! -d "${AOPS_SESSIONS:-/nonexistent}" ]; then
  echo "WARNING: AOPS_SESSIONS is unset or invalid; falling back to cached value in ~/.env.local" >&2
  if [ -f "$HOME/.env.local" ]; then
    AOPS_SESSIONS=$(grep '^AOPS_SESSIONS=' "$HOME/.env.local" | cut -d= -f2-)
    export AOPS_SESSIONS
    echo "Using cached AOPS_SESSIONS=$AOPS_SESSIONS from ~/.env.local" >&2
  fi
fi

echo "$AOPS_SESSIONS"
