#!/bin/bash
# patch-cowork-mcp.sh — DEPRECATED.
#
# This patch script is no longer needed as of 2026-04-27. PKB_MCP_URL is now
# resolved inside the plugin's run-mcp.sh script (which sources ~/.env.local
# and falls back to local `pkb mcp` stdio transport when no URL is set).
#
# The .mcp.json env block — the source of the original problem, never
# resolved by Cowork's userConfig substitution — has been removed entirely
# from the plugin manifest.
#
# What you used to need this script for: rewriting the installed plugin's
# .mcp.json after every reinstall to hardcode PKB_MCP_URL into the env block.
#
# What replaces it: nothing. Set PKB_MCP_URL in ~/.env.local once
# (or rely on the local-`pkb`-binary fallback) and reinstall the plugin
# normally. No post-install step required.
#
# This script is retained as a deprecation signpost. Remove the file once
# all plugin installations have been refreshed past 2026-04-27.

cat >&2 <<'MSG'
patch-cowork-mcp.sh is deprecated.

The plugin no longer reads PKB_MCP_URL from .mcp.json's env block — instead,
scripts/run-mcp.sh inside the plugin sources ~/.env.local at launch and falls
back to local `pkb mcp` stdio when PKB_MCP_URL is unset.

To configure: add 'export PKB_MCP_URL=http://localhost:3001/mcp' to
~/.env.local, or install the `pkb` binary (cargo binstall --git
https://github.com/nicsuzor/mem pkb).

No post-install patching is required.
MSG
exit 0
