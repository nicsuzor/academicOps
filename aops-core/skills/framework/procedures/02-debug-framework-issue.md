---
title: Debug Framework Issue
type: automation
category: instruction
permalink: workflow-debug-framework-issue
description: Process for diagnosing and fixing framework component failures and integration issues
---

# Workflow 2: Debug Framework Issue

**When**: Framework component failing, unexpected behavior, integration broken.

**Key principle**: Use **controlled tests in /tmp** to run experiments and validate hypotheses. Read **session transcripts** to understand agent behavior.

**Detailed procedures and tools**: See **[[debug-details]]**.

**Steps**:

1. **Generate transcript FIRST (MANDATORY)**
   - Run: `cd $AOPS && uv run python scripts/transcript.py <session.jsonl>`
   - Abridged version is usually sufficient.

2. **Reproduce the issue with controlled test**
   - Run test with `--debug` flag in `/tmp` directory.
   - Document exact steps to trigger issue and verify it exists.

3. **Read the transcript to understand behavior**
   - Look for tool calls, errors, and agent reasoning.
   - To verify hook behavior, grep raw JSONL for `system-reminder`.

4. **Form hypothesis about root cause**
   - Analyze agent behavior: correct context? correct interpretation?
   - Check for duplication, conflicts, or SSoT violations.

5. **Test hypothesis with controlled experiment**
   - Pattern: Change → Test → Generate transcript → Refine hypothesis.
   - Modify one variable at a time and confirm behavior change.

6. **Design minimal fix**
   - Minimal change addressing root cause without workarounds.
   - Add validation that fails immediately on misconfiguration.

7. **Create/update integration test**
   - Test must fail initially and pass after fix.
   - Cover regression cases with E2E validation.

8. **Validate fix with full test suite**
   - Run all integration tests with `--debug` enabled.
   - Confirm documentation consistency and no new conflicts.

9. **Log in experiment if significant**
   - Document issue, root cause, fix, and lessons learned.
   - Update tests to prevent recurrence.

**ALWAYS generate transcript first** - raw JSONL/JSON wastes tokens and is hard to read.
