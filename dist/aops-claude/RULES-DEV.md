---
name: dev-rules
title: Development Context Rules
type: instruction
category: instruction
description: Non-negotiable rules for code, infrastructure, and CI/CD contexts. Enforced by the engineering standards agent.
---

# Development Context Rules

These rules are non-negotiable when writing code, managing infrastructure, or working with CI/CD. They activate alongside the universal axioms when the work involves software development.

## Fail-Fast (Code) (P#8)

No defaults, no fallbacks, no workarounds, no silent failures. Fail immediately when configuration is missing or incorrect.

## Self-Documenting (P#10)

Documentation-as-code first; never make separate documentation files.

## DRY, Modular, Explicit (P#12)

One golden path, no defaults, no guessing, no backwards compatibility.

## Trust Version Control (P#24)

Git is the backup system. NEVER create backup files (`.bak`, `_old`, `_ARCHIVED_*`). Edit directly, rely on git. Commit, PUSH, AND file a Pull Request after completing logical work units. Commit promptly — no hesitation.

**Corollaries**:

- After completing work, always: commit → push to branch → file PR. Review happens at PR integration, not before commit. Never leave work uncommitted or ask the user to commit for you.
- Never assign review/commit tasks to `nic`. The PR process IS the review mechanism.

## Plan-First Development (P#41)

No coding without an approved plan.

## Credential Isolation (P#51)

Agents MUST NOT use human (user) credentials for GitHub operations. They MUST use the provided `AOPS_BOT_GH_TOKEN`, which is exported to the session as both `GH_TOKEN` and `GITHUB_TOKEN`.

**Corollaries**:

- Never search for or use SSH keys (`~/.ssh/`)
- Never use `gh auth login` to authenticate as a human user
- Always rely on the session-provided bot token (`GH_TOKEN` / `GITHUB_TOKEN`) for git and GitHub operations, treating `GH_TOKEN` as the primary interface

**Derivation**: Accountability and risk mitigation. Bot tokens can be scoped and rotated independently of human users, providing a clear audit trail and reducing the risk of accidental exposure of personal credentials.

## Mandatory Reproduction Tests for Fixes (P#82)

Every framework bug fix MUST be preceded by a failing reproduction test case. This applies when implementing a fix, not necessarily during the initial async capture (/learn).

## Never Edit Generated Files (P#97)

Before editing any file, check if it's auto-generated. If so, find and update the source/procedure that generates it.
