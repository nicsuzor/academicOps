---
title: Hooks
permalink: hooks
type: index
tags: [framework, hooks, lifecycle]
---

# Hooks

## Overview
Python hooks for session lifecycle management, context injection, and policy enforcement. Hooks extend Claude Code functionality through event-driven scripts that inject context, enforce policies, and log activity.

## Session Initialization

- [[sessionstart_load_axioms]] - Load FRAMEWORK, AXIOMS, HEURISTICS, and CORE at session start
- [[terminal_title]] - Set terminal title to project name for visual identification
- [[session_env_setup.sh]] - Set AOPS and PYTHONPATH environment variables

## Request Handling

- [[user_prompt_submit]] - Load context from prompts/user-prompt-submit.md
- [[prompt_router]] - Two-tier routing: keyword match to skills or semantic classification via Haiku

## Policy Enforcement

- [[policy_enforcer]] - Block destructive git, GUIDE.md files, and oversized markdown

## State Management

- [[autocommit_state]] - Auto-commit and push data/ changes after state-modifying operations
- [[request_scribe]] - Remind agent to document work to memory server

## Logging and Observability

- [[hook_logger]] - Shared logging module for hook events
- [[session_logger]] - Session logging with transcript summaries
- [[unified_logger]] - Universal event logger for all hook types
- [[hook_debug]] - Debug logging utilities for development

## Testing and Development

- [[test_marker_hook]] - Deterministic test hook for verifying additionalContext processing
- [[verify_conclusions]] - Disabled stub

## Prompts

- [[prompts]] - Prompt templates directory
  - [[prompts/user-prompt-submit.md]] - Context for UserPromptSubmit hook
  - [[prompts/intent-router.md]] - Template for semantic skill classification

