#!/bin/sh
# Credential-isolation chain for GUI Claude.app sessions on macOS.
#
# This file is sourced by ~/Library/LaunchAgents/com.aops.envvars.plist at
# login and exports vars into the per-user launchd context. It must NOT be
# sourced from interactive shell rc files — these lockdowns hijack git so
# every operation uses the bot PAT, which would break normal terminal usage
# under the user's personal identity.
#
# Install: copy to "$POLECAT_HOME/launchd-env.sh" (default ~/.aops/launchd-env.sh).
# The plist looks there by default — adjust the plist if you keep it elsewhere.
#
# Mirrors aops-core/agent-env-map.conf + hooks/session_env_setup.py for
# environments where session_env_setup.py can't run (i.e. before any session
# starts, or in Claude Code versions whose harness doesn't source the
# session-env file before Bash tool subprocesses).

# --- Bot PAT pass-through ---
# AOPS_BOT_GH_TOKEN is expected in ~/.env.local (sourced by the plist before
# this file). Skip silently if absent.
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv GH_TOKEN "$AOPS_BOT_GH_TOKEN"
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv GITHUB_TOKEN "$AOPS_BOT_GH_TOKEN"
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv AOPS_BOT_GH_TOKEN "$AOPS_BOT_GH_TOKEN"

# --- SSH lockdown ---
# Prevent SSH from finding personal keys via ssh-agent or macOS Keychain.
# GIT_SSH_COMMAND=false makes any SSH attempt fail loudly rather than
# silently authenticating with the wrong identity.
launchctl setenv SSH_AUTH_SOCK ""
launchctl setenv GIT_SSH_COMMAND "false"

# --- Git config override chain ---
# Git reads GIT_CONFIG_COUNT and the indexed KEY_n/VALUE_n pairs in addition
# to system/user config. We use 4 entries:
#   0,1: rewrite git@/ssh://github.com → https://github.com so even SSH
#        remotes are routed through HTTPS.
#   2:   empty-string clears any inherited credential.helper list (git
#        treats `helper` as list-typed; empty entry resets the list).
#   3:   installs a single shell-function credential helper that emits the
#        bot PAT for github.com.
launchctl setenv GIT_CONFIG_COUNT "4"
launchctl setenv GIT_CONFIG_KEY_0 "url.https://github.com/.insteadOf"
launchctl setenv GIT_CONFIG_VALUE_0 "git@github.com:"
launchctl setenv GIT_CONFIG_KEY_1 "url.https://github.com/.insteadOf"
launchctl setenv GIT_CONFIG_VALUE_1 "ssh://git@github.com/"
launchctl setenv GIT_CONFIG_KEY_2 "credential.https://github.com.helper"
launchctl setenv GIT_CONFIG_VALUE_2 ""
launchctl setenv GIT_CONFIG_KEY_3 "credential.https://github.com.helper"
# Single fail-closed impl, identical to hooks/session_env_setup.py step 5b: the
# credential helper emits AOPS_BOT_GH_TOKEN *directly* (empty => auth fails).
# NO GH_TOKEN/GITHUB_TOKEN fallback chain (A8: no silent fallbacks; do not keep
# a second divergent credential-isolation impl). GH_TOKEN/GITHUB_TOKEN are set
# above to track AOPS_BOT_GH_TOKEN exactly, so the single source is the bot PAT.
launchctl setenv GIT_CONFIG_VALUE_3 '!f() { test "$1" = get && printf "username=x-access-token\npassword=%s\n" "${AOPS_BOT_GH_TOKEN}"; }; f'
