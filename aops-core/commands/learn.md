---
name: learn
category: instruction
description: Rapid async knowledge capture for framework failures
allowed-tools: Bash, Task
permalink: commands/learn
---

# /learn - Rapid Knowledge Capture

**Purpose**: Capture a framework failure quickly and asynchronously by creating a GitHub issue. This replaces the heavier task-based decomposition pattern.

## Workflow

### 1. Capture Failure Context

**Identify the failure**:

- Where did the mistake occur?
- What was the trigger?

**Generate Session Transcript**:

```bash
# For Gemini (typical):
SESSION_FILE=$(fd -t f -a --newer 1h .json ~/.gemini/tmp | xargs ls -t | head -1)

# For Claude (if applicable):
# SESSION_FILE=$(find ~/.claude/projects -name "*.jsonl" -mmin -60 -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)

uv run --directory ${AOPS} python aops-core/scripts/transcript.py "$SESSION_FILE"
```

### 2. Extract Minimal Bug Reproduction

Review the abridged transcript (usually `~/writing/sessions/claude/YYYYMMDD-HH-project-ID-slug-abridged.md`) and extract the minimum turns (ideally < 5) to demonstrate the bug.

Identify:

- **Expected**: What should have happened
- **Actual**: What actually happened

### 3. Create GitHub Issue (Async)

Dump the reproduction and transcript reference directly to GitHub issues. This is the primary capture mechanism.

**Command**:

```bash
# Set repo (default to qut-dmrc/academicOps or detected current repo)
REPO="qut-dmrc/academicOps"

BODY=$(cat <<EOF
## Failure Summary
[One sentence summary: what went wrong?]

## Minimal Bug Reproduction
[Context + Failure Sequence]

## Expected vs Actual
- **Expected**: [What should have happened]
- **Actual**: [What actually happened]

## Session Reference
- Session ID: [8-char ID from transcript filename]
- Transcript: [Full path to -full.md transcript]
EOF
)

gh issue create --repo "$REPO" --title "[Learn] <brief-descriptive-slug>" --body "$BODY"
```

### 4. Create Single Follow-up Task (Optional)

If immediate action is required, create **ONE** task. **DO NOT** create task trees, sub-tasks, or complex dependencies.

```python
mcp__plugin_aops-core_task_manager__create_task(
  title="[Learn] <slug>",
  project="aops",
  priority=2,
  body="Reference GitHub Issue: [link to issue]\n\nProposed fix: ..."
)
```

## Core Principles

- **Speed over Depth**: Capture the failure while it's fresh. Don't spend time on deep root cause analysis during the `/learn` command.
- **Async Execution**: Treat the capture as a "fire and forget" operation.
- **No Decomposition**: Do not break the learning into multiple tasks. One issue + one optional task.

## Framework Reflection

After completing the capture, emit a brief reflection:

```
## Framework Reflection
**Prompts**: [The observation/feedback that triggered /learn]
**Outcome**: success
**Accomplishments**: GitHub Issue created: [link], [Optional Task ID]
**Root cause**: [Clarity | Context | Blocking | Detection | Gap]
```
