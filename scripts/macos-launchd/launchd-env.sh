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

# --- AOPS URLs ---
[ -n "$PKB_MCP_URL" ] && launchctl setenv PKB_MCP_URL "$PKB_MCP_URL"

# --- Bot PAT pass-through ---
# AOPS_BOT_GH_TOKEN is expected in ~/.env.local (sourced by the plist before
# this file). Each export is gated on a non-empty token; skip silently if absent.
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv AOPS_BOT_GH_TOKEN "$AOPS_BOT_GH_TOKEN"
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv GH_TOKEN "$AOPS_BOT_GH_TOKEN"
[ -n "$AOPS_BOT_GH_TOKEN" ] && launchctl setenv GITHUB_TOKEN "$AOPS_BOT_GH_TOKEN"

# --- TRACING via OTEL ---
[ -n "$OTEL_METRICS_EXPORTER" ] && launchctl setenv OTEL_METRICS_EXPORTER "$OTEL_METRICS_EXPORTER"
[ -n "$OTEL_LOGS_EXPORTER" ] && launchctl setenv OTEL_LOGS_EXPORTER "$OTEL_LOGS_EXPORTER"
[ -n "$OTEL_TRACES_EXPORTER" ] && launchctl setenv OTEL_TRACES_EXPORTER "$OTEL_TRACES_EXPORTER"
[ -n "$OTEL_EXPORTER_OTLP_ENDPOINT" ] && launchctl setenv OTEL_EXPORTER_OTLP_ENDPOINT "$OTEL_EXPORTER_OTLP_ENDPOINT"
[ -n "$OTEL_EXPORTER_OTLP_PROTOCOL" ] && launchctl setenv OTEL_EXPORTER_OTLP_PROTOCOL "$OTEL_EXPORTER_OTLP_PROTOCOL"
[ -n "$OTEL_RESOURCE_ATTRIBUTES" ] && launchctl setenv OTEL_RESOURCE_ATTRIBUTES "$OTEL_RESOURCE_ATTRIBUTES"
[ -n "$OTEL_LOG_USER_PROMPTS" ] && launchctl setenv OTEL_LOG_USER_PROMPTS "$OTEL_LOG_USER_PROMPTS"
[ -n "$OTEL_LOG_RAW_API_BODIES" ] && launchctl setenv OTEL_LOG_RAW_API_BODIES "$OTEL_LOG_RAW_API_BODIES"
[ -n "$OTEL_LOG_TOOL_DETAILS" ] && launchctl setenv OTEL_LOG_TOOL_DETAILS "$OTEL_LOG_TOOL_DETAILS"
[ -n "$OTEL_LOG_ASSISTANT_RESPONSES" ] && launchctl setenv OTEL_LOG_ASSISTANT_RESPONSES "$OTEL_LOG_ASSISTANT_RESPONSES"
[ -n "$OTEL_METRIC_EXPORT_INTERVAL" ] && launchctl setenv OTEL_METRIC_EXPORT_INTERVAL "$OTEL_METRIC_EXPORT_INTERVAL"
[ -n "$OTEL_LOGS_EXPORT_INTERVAL" ] && launchctl setenv OTEL_LOGS_EXPORT_INTERVAL "$OTEL_LOGS_EXPORT_INTERVAL"
[ -n "$OTEL_TRACES_EXPORT_INTERVAL" ] && launchctl setenv OTEL_TRACES_EXPORT_INTERVAL "$OTEL_TRACES_EXPORT_INTERVAL"

# --- CLAUDE CODE & ANTIGRAVITY TELEMETRY ---
[ -n "$CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" ] && launchctl setenv CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS "$CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"
[ -n "$CLAUDE_CODE_STOP_HOOK_BLOCK_CAP" ] && launchctl setenv CLAUDE_CODE_STOP_HOOK_BLOCK_CAP "$CLAUDE_CODE_STOP_HOOK_BLOCK_CAP"
[ -n "$ANTIGRAVITY_ENABLE_TELEMETRY" ] && launchctl setenv ANTIGRAVITY_ENABLE_TELEMETRY "$ANTIGRAVITY_ENABLE_TELEMETRY"
[ -n "$CLAUDE_CODE_ENABLE_TELEMETRY" ] && launchctl setenv CLAUDE_CODE_ENABLE_TELEMETRY "$CLAUDE_CODE_ENABLE_TELEMETRY"
[ -n "$CLAUDE_CODE_ENHANCED_TELEMETRY_BETA" ] && launchctl setenv CLAUDE_CODE_ENHANCED_TELEMETRY_BETA "$CLAUDE_CODE_ENHANCED_TELEMETRY_BETA"
[ -n "$ENABLE_BETA_TRACING_DETAILED" ] && launchctl setenv ENABLE_BETA_TRACING_DETAILED "$ENABLE_BETA_TRACING_DETAILED"
[ -n "$BETA_TRACING_ENDPOINT" ] && launchctl setenv BETA_TRACING_ENDPOINT "$BETA_TRACING_ENDPOINT"
