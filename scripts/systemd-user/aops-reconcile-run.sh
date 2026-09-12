#!/bin/sh
# Headless entrypoint invoked by aops-reconcile.service. Does no
# reconciliation logic of its own -- it only launches the agent, which
# does the work via the /pkb:reconcile skill. See aops-reconcile.timer
# for install and the required first-live-run write check.
#
# Sourcing $HOME/.env.local (not sourced by systemd's EnvironmentFile=
# because it is shell syntax, not KEY=VALUE lines) keeps this carrying
# no hardcoded host, path, or token -- same source of truth the macOS
# launchd path uses (scripts/macos-launchd/).
[ -f "$HOME/.env.local" ] && . "$HOME/.env.local"

set -eu

# Step 1: reconcile -- truth maintenance over the task graph (merged PRs,
# abandoned claims, stale assumptions). Must not invent scope.
claude -p "/pkb:reconcile" --output-format json < /dev/null

# Step 2: capture pickup -- routes mobile/webhook captures into the graph.
# Runs on this same trigger as its own step, deliberately not folded into
# Step 1: reconcile maintains truth about existing claims and must not
# invent scope, while routing a capture to task/note/discard is judgment
# work that belongs to pkb:q (decision recorded on aops_reconcile_trigger).
# Not yet wired: aops_capture_intake_route has not landed. Once it does,
# add its `claude -p` invocation here as its own line, not inside Step 1's
# prompt.
