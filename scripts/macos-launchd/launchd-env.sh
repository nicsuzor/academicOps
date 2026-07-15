#!/bin/sh
# Env-var injection for GUI Claude.app / launchd sessions on macOS.
#
# This file is sourced by ~/Library/LaunchAgents/com.aops.envvars.plist at
# login and exports vars into the per-user launchd context so GUI-launched
# processes (Claude.app -> Claude Code / Cowork tabs, scheduled runs) inherit
# them. It must NOT be sourced from interactive shell rc files.
#
# Install: copy to "$POLECAT_HOME/launchd-env.sh" (default ~/.aops/launchd-env.sh).
# The plist looks there by default -- adjust the plist if you keep it elsewhere.
#
# SCOPE: This file only exports the bot PAT (AOPS_BOT_GH_TOKEN and its
# GH_TOKEN/GITHUB_TOKEN aliases) plus AOPS directory vars into the GLOBAL
# per-user launchd context. It deliberately does NOT set any global SSH
# lockdown (SSH_AUTH_SOCK / GIT_SSH_COMMAND) or global git-config hijack
# (GIT_CONFIG_*): doing so globally re-breaks VS Code and every other GUI app
# that relies on the user's personal SSH identity (documented failure
# note-4d4a97c2). Session-scoped credential isolation for Claude/bot sessions
# is instead applied per-session by aops/hooks/router.py via CLAUDE_ENV_FILE.

# --- AOPS directories ---
[ -n "$AOPS_SESSIONS" ] && launchctl setenv AOPS_SESSIONS "$AOPS_SESSIONS"
[ -n "$ACA_DATA" ] && launchctl setenv ACA_DATA "$ACA_DATA"
[ -n "$POLECAT_HOME" ] && launchctl setenv POLECAT_HOME "$POLECAT_HOME"

# --- Bot PAT pass-through ---
# AOPS_BOT_GH_TOKEN is expected in ~/.env.local (sourced by the plist before
# this file). Each export is gated on a non-empty token; skip silently if absent.
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv AOPS_BOT_GH_TOKEN "$AOPS_BOT_GH_TOKEN"
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv GH_TOKEN "$AOPS_BOT_GH_TOKEN"
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv GITHUB_TOKEN "$AOPS_BOT_GH_TOKEN"
