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
uv run --directory ${AOPS} python aops-core/scripts/transcript.py "$SESSION_FILE"
```

### 2. Deep Root Cause Analysis (Crucial)

Before creating the issue, investigate **why** the failure was not prevented by the framework. Do not stop at "agent execution failure."

**Check the following layers**:

1. **Discovery Gap**: Did the **Prompt Hydrator** have the necessary information?
   - Check if local project workflows (`.agent/workflows/*.md`) were indexed.
   - Check if relevant specifications were injected into the Hydrator's context.
2. **Detection Failure**: Did the agent/hydrator see the information but fail to act on it?
   - Was the "Intent Envelope" correctly identified?
   - Did the "Execution Plan" include the necessary quality gates (CHECKPOINTs)?
3. **Instruction Weighting**: Did the agent skip a mandated step in favor of a "shortcut"?
4. **Index Lag**: Was the failure caused by an outdated `INDEX.md` or `graph.json`?

### 3. Extract Minimal Bug Reproduction

Review the abridged transcript and extract the minimum turns (ideally < 5) to demonstrate the bug.
Identify:

- **Expected**: What should have happened (e.g., "Hydrator should have selected the local evaluation workflow")
- **Actual**: What actually happened (e.g., "Hydrator fell back to generic investigation; Agent skipped visual step")

### 4. Create GitHub Issue (Async)

**Command**:

```bash
REPO="nicsuzor/academicOps" # Adjust as needed

BODY=$(cat <<EOF
## Failure Summary
[One sentence summary: e.g., Prompt Hydrator Discovery Gap for project-scoped workflows]

## Root Cause Analysis
[Detailed explanation of the framework failure: Discovery, Detection, or Execution gap]

## Minimal Bug Reproduction
[Context + Failure Sequence]

## Expected vs Actual
- **Expected**: [What should have happened]
- **Actual**: [What actually happened]

## Session Reference
- Session ID: [8-char ID]
- Transcript: [Full path to -full.md]
EOF
)

gh issue create --repo "$REPO" --title "[Learn] <brief-slug>" --body "$BODY"
```

### 5. Create Single Follow-up Task (Optional)

Create **ONE** task if immediate action is required.

```python
mcp__pkb__create_task(
  title="[Learn] <slug>",
  project="aops",
  priority=2,
  body="Reference GitHub Issue: [link]\n\nProposed fix: ..."
)
```

## Framework Reflection

```
## Framework Reflection
**Prompts**: [The observation/feedback that triggered /learn]
**Outcome**: success
**Accomplishments**: GitHub Issue created: [link]
**Root cause**: [Clarity | Context | Blocking | Detection | Discovery Gap | Shortcut Bias]
```
