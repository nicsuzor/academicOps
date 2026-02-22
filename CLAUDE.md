# academicOps Framework Guide

This directory contains the academicOps framework for managing complex workflows through an LLM-driven system with structured enforcement, task management, and governance.

## Key Components

- **.agent/**: Instructions for working on the academicOps framework
- **aops-core/**: Framework core (hooks, enforcement, skills)
- **aops-tools/**: Additional tools and utilities
- **config/**: Configuration files (Claude, Gemini, environment)
- **specs/**: Framework specifications and architecture
- **tests/**: All tests (at repo root, NOT in aops-core/). Subdirs: `hooks/`, `integration/`, `lib/`, `e2e/`

## PR Review Management

When invoked on a PR (via `@claude` comment or as an agent), you can and should manage review state:

- **Dismiss stale reviews** when you have addressed the reviewer's concerns or the human has overridden them. Use: `gh api repos/{owner}/{repo}/pulls/{pr}/reviews/{review_id}/dismissals -f message="..." -f event="DISMISS"`
- **Interpret human intent.** If a maintainer says "leave those changes in" or "that's fine, merge it" about a reviewer's concern, that is an override — dismiss the review with a message noting the maintainer's decision.
- **After fixing code issues** that a reviewer flagged as CHANGES_REQUESTED, dismiss that review with a message summarising what was fixed.
- **Always include a clear dismissal message** explaining why: what was fixed, or which human decision overrides the concern.
- **Never dismiss a review you haven't addressed.** If a concern is still valid and unresolved, leave the review in place and flag it for the human.
