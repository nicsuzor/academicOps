---
name: learn
type: command
category: instruction
description: Rapid async knowledge capture for framework failures
triggers:
  - "framework issue"
  - "fix this pattern"
  - "improve the system"
  - "knowledge capture"
  - "bug report"
modifies_files: true
needs_task: false
mode: execution
domain:
  - framework
allowed-tools: Bash, Task
permalink: commands/learn
---

# /learn - Rapid Knowledge Capture

**Purpose**: Diagnose a framework failure, apply a fix to the framework file that would have prevented it, and file a GitHub issue for the record. Capture is not enough — the fix is the deliverable.

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
5. **Cross-workflow enforcement gap**: Did one workflow detect a problem but lack the mechanism to block another workflow? Check GitHub PR logs (`gh api repos/.../pulls/{pr}/reviews`, `gh api repos/.../pulls/{pr}/comments`) for the full timeline of reviews, dismissals, and merge actions. Common pattern: a reviewer posts `COMMENTED` (advisory) when it should post `CHANGES_REQUESTED` (blocking), so the merge agent can legitimately defer the concern.

### 3. Map to Enforcement Ladder (MANDATORY)

Consult [[docs/ENFORCEMENT.md]] and map the root cause to an enforcement level. This determines what kind of fix is needed:

| Root Cause                      | Typical Enforcement Level                                | Fix Target                          |
| ------------------------------- | -------------------------------------------------------- | ----------------------------------- |
| Agent lacked information        | Level 1c (reasoned prompt) or Level 2 (router/command)   | Skill/command/workflow instructions |
| Agent had info but skipped step | Level 2b (strengthen command) or Level 4 (pre-tool hook) | Command file or hook                |
| No mechanism to prevent         | Level 3-5 (tool restriction / hooks)                     | New enforcement mechanism           |
| Behavior should never occur     | Level 6-7 (deny rule / pre-commit)                       | settings.json or pre-commit config  |
| Cross-workflow enforcement gap  | Workflow agent prompts + review mechanism                | Agent prompt + workflow YAML + spec |

Include the enforcement level and proposed mechanism in the GitHub issue (step 5).

### 4. Extract Minimal Bug Reproduction

Review the abridged transcript and extract the minimum turns (ideally < 5) to demonstrate the bug.
Identify:

- **Expected**: What should have happened (e.g., "Hydrator should have selected the local evaluation workflow")
- **Actual**: What actually happened (e.g., "Hydrator fell back to generic investigation; Agent skipped visual step")

### 5. Create GitHub Issue (Async)

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

## Proposed Fix
- **Enforcement level**: [from step 3 — e.g., Level 2b (command instructions)]
- **Target file**: [path to the framework file that needs changing]
- **Proposed change**: [specific edit description]

## Session Reference
- Session ID: [8-char ID]
- Transcript: [Full path to -full.md]
EOF
)

gh issue create --repo "$REPO" --title "[Learn] <brief-slug>" --body "$BODY"
```

### 6. Apply the Fix (MANDATORY)

Capturing the failure is not enough. **Identify and edit the framework file that would prevent recurrence.** This is the whole point of /learn — if you only file an issue, you've logged the problem but not fixed it.

Ask: **"Which file, if it had contained the right instruction, would have prevented this failure?"**

For Level 1-2 fixes (prompt text, command instructions), apply the edit in this session. For Level 3+ fixes (tool restrictions, hooks, deny rules), create a task (step 7) with the specific file and change needed.

Common fix targets:

- **Skill/command definitions** (`aops-core/commands/*.md`, `aops-core/skills/*/SKILL.md`) — add a missing step, checkpoint, or constraint
- **Workflow definitions** (`.agent/workflows/*.md`) — add a gate or validation
- **Agent instructions** (`.agent/agents/*.md`, `.github/agents/*.md`) — strengthen an instruction the agent ignored
- **Specs** (`specs/*.md`) — correct a design gap

### 7. Create Follow-up Task (if fix exceeds session scope)

Create **ONE** task if the fix is too large to apply now (typically Level 3+ enforcement). Resolve parent per [[references/hierarchy-quality-rules]] first. The task must specify the **target file, enforcement level, and proposed change**, not just reference the issue.

```python
mcp__pkb__create_task(
  title="[Learn] <slug>",
  project="aops",
  parent="<resolved-parent-id>",
  priority=2,
  body="Reference GitHub Issue: [link]\n\nEnforcement level: [from step 3]\nTarget file: [path]\nProposed change: [specific edit description]"
)
```

## Framework Reflection

```
## Framework Reflection
**Prompts**: [The observation/feedback that triggered /learn]
**Outcome**: success
**Accomplishments**: GitHub Issue created: [link]. Fix applied: [file path and change summary] OR Follow-up task created: [task-id]
**Root cause**: [Clarity | Context | Blocking | Detection | Discovery Gap | Shortcut Bias]
**Enforcement level**: [Level X — mechanism name from docs/ENFORCEMENT.md]
```
