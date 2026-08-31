---
title: Session Handover
type: template
category: gate
description: Structured session completion and handover protocol — commit changes, release claims, report status, and emit clean handover summary. Select at session exit.
tags: [handover, session-exit, git-commit, status, gate]
---

# Gate: Session Handover

Terminal session exit protocol to ensure work is safely persisted and traceable.

## 1. Workspace and Git Cleanliness

- Stage and commit modified files with a clear, standard commit message referencing task ID.
- Ensure no unintended temporary files, `.bak` files, or uncommitted edits remain.

## 2. Test Suite Confirmation

- Run local test suite to confirm committed code passes all verification checks.

## 3. Task Status Update

- Update task record with completion status (`done`, `merge_ready`, or `in_progress`).
- Record commit hash and PR pointers under task pointers section.

## 4. Handover Summary

- Emit a concise handover summary:
  - What was completed during the session.
  - Current verification and test status.
  - Clear next steps or open items for the next agent or user.

## Exit Condition

Git working tree clean, tests passing, and handover summary emitted.
