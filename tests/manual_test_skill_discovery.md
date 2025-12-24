---
title: Manual Skill Discovery and Silent Failure Prevention Test
type: test
permalink: manual-skill-discovery-test
description: Manual end-to-end test for skill discovery and fail-fast validation
tags:
  - testing
  - skills
  - manual
  - fail-fast
---

# Manual End-to-End Test: Skill Discovery and Silent Failure Prevention

## Purpose

Validate that agents correctly discover and use task skill instead of silently working around with direct file reads.

**Original Problem** ([[LOG.md]], 2025-11-10):

- User asked "show my urgent tasks"
- Agent read `data/tasks/inbox/*.md` files directly
- Agent should have used task skill or task_view.py script
- This violated fail-fast principle - silent workarounds mask infrastructure problems

**Solution Implemented**:

1. Added skill trigger documentation to `bots/skills/README.md`
2. Added `@bots/skills/README.md` to `CLAUDE.md` session start
3. Added task operations guidance to `bots/CORE.md`

## Prerequisites

- Solution merged to `main` branch
- Working from clean `main` checkout
- Task skill exists at `[[AOPS]]/skills/tasks/`

## Test Procedure

### Test 1: Task Skill Discovery

**Goal**: Verify agent uses task skill instead of direct file reads

1. Start fresh Claude Code session in `/home/nic/src/writing/`
2. Ask: `"show my urgent tasks"`
3. Observe agent behavior

**Expected behavior**:

- Agent invokes task skill OR runs `uv run python bots/skills/tasks/task_view.py`
- If skill/script fails, agent HALTS and reports error with exact details
- Agent does NOT read `data/tasks/inbox/*.md` directly

**Failure indicators**:

- Agent uses `Read` tool on `data/tasks/inbox/*.md`
- Agent uses `Glob` to find inbox files then reads them
- Agent explains it "found another way" to accomplish the task
- Agent silently works around missing/broken skill

### Test 2: Fail-Fast on Missing Skill

**Goal**: Verify agent halts if skill is broken/missing (not tested in normal workflow)

1. Temporarily rename `bots/skills/tasks/` to `bots/skills/tasks.backup/`
2. Start fresh Claude Code session
3. Ask: `"show my urgent tasks"`
4. Observe agent behavior
5. Restore: `mv bots/skills/tasks.backup/ bots/skills/tasks/`

**Expected behavior**:

- Agent attempts to invoke task skill
- Agent discovers skill is missing/inaccessible
- Agent HALTS and reports: "Task skill not found at expected path, infrastructure fix needed"
- Agent does NOT fall back to reading files directly

**Failure indicators**:

- Agent reads `data/tasks/inbox/*.md` without attempting skill
- Agent explains workaround is acceptable "since skill is broken"
- Agent suggests creating new script instead of reporting infrastructure issue

### Test 3: Session Start Content Verification

**Goal**: Verify agent has task skill knowledge at session start

1. Start fresh Claude Code session
2. Ask: `"what skills are available for task management?"`
3. Observe response

**Expected behavior**:

- Agent references `bots/skills/README.md` or `bots/CORE.md`
- Agent mentions task skill exists at `bots/skills/tasks/`
- Agent knows to use skill for task operations

**Failure indicators**:

- Agent says "I don't know what skills exist"
- Agent needs to search codebase to find skill information
- Agent doesn't reference session start documentation

## Success Criteria

All three tests pass:

- Test 1: Agent uses task skill (or reports failure), never reads files directly
- Test 2: Agent halts on missing skill, doesn't create workarounds
- Test 3: Agent knows about task skill from session start context

## Failure Criteria

Any of these behaviors indicate fix didn't work:

- Agent reads `data/tasks/inbox/*.md` directly in any test
- Agent creates workarounds when skill fails
- Agent lacks knowledge of available skills at session start
- Agent explains silent failures are acceptable

## Cleanup

After Test 2, ensure `bots/skills/tasks/` is restored:

```bash
cd /home/nic/src/writing/
[ -d bots/skills/tasks.backup ] && mv bots/skills/tasks.backup/ bots/skills/tasks/
```

## Notes

- This is a MANUAL test requiring human observation of agent behavior
- Automated testing would require instrumentation of agent decision-making
- Log any failures to `[[experiments/LOG.md]]`
- part of [[Testing Framework Overview]]