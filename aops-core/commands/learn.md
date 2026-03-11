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
modifies_files: false
needs_task: false
mode: execution
domain:
  - framework
allowed-tools: Bash, Task
permalink: commands/learn
---

# /learn - Rapid Knowledge Capture

**Purpose**: Diagnose a framework failure and generate a high-quality, curated error report for submission to the `nicsuzor/academicOps` repository, without applying direct local fixes.

**Privacy rule**: NEVER include direct logs, session dumps, real people's names, email addresses, student details, or personal information in the curated error report or GitHub issues.

## Workflow

### 1. Capture Failure Context

**Identify the failure**:
- Where did the mistake occur?
- What was the trigger?

**Generate Session Transcript**:
To analyze the incident, you must first render the transcript of the current or failed session. Because the agent may be in a deployed or isolated session, use the framework's module-based path resolution rather than relying on the `$AOPS` environment variable.

```bash
# Locate the session file (For Gemini or Claude)
SESSION_FILE=$(fd -t f -a --newer 1h .json ~/.gemini/tmp | xargs ls -t | head -1)

# Generate transcript using the installed plugin path
TRANSCRIPT_SCRIPT="${ACA_DATA:-~}/.claude/skills/framework/scripts/transcript.py"
if [ -f "$TRANSCRIPT_SCRIPT" ]; then
  uv run python "$TRANSCRIPT_SCRIPT" "$SESSION_FILE"
else
  uv run python -m aops_core.scripts.transcript "$SESSION_FILE"
fi
```

*Note: Since you might not be in the framework repository, adapt the script path discovery as needed using standard bash commands (`find`, etc.) to locate `transcript.py`.*

### 2. Deep Root Cause Analysis (Crucial)

Before recording the incident, investigate **why** the failure was not prevented by the framework. Do not stop at "agent execution failure." Exercise judgment based on the framework's `VISION.md` regarding how the system SHOULD have worked.

**Check the following layers**:
1. **Discovery Gap**: Did the **Prompt Hydrator** have the necessary information?
   - Check if local project workflows (`.agent/workflows/*.md`) were indexed.
   - Check if relevant specifications were injected into the Hydrator's context.
2. **Detection Failure**: Did the agent/hydrator see the information but fail to act on it?
   - Was the "Intent Envelope" correctly identified?
   - Did the "Execution Plan" include the necessary quality gates (CHECKPOINTs)?
3. **Instruction Weighting**: Did the agent skip a mandated step in favor of a "shortcut"?
4. **Index Lag**: Was the failure caused by an outdated `INDEX.md` or `graph.json`?
5. **Cross-workflow enforcement gap**: Did one workflow detect a problem but lack the mechanism to block another workflow?

### 3. Extract Minimal Bug Reproduction

Review the abridged transcript and extract the minimum turns (ideally < 5) to demonstrate the bug.
Identify:
- **Expected**: What should have happened based on `VISION.md` (e.g., "Hydrator should have selected the local evaluation workflow")
- **Actual**: What actually happened (e.g., "Hydrator fell back to generic investigation; Agent skipped visual step")

### 4. Create Curated Diagnostic Report

Draft a high-quality, privacy-scrubbed diagnostic report in Markdown format. The report should focus on the ROOT CAUSE and not just the specific fault.

```markdown
# Bug Report: [Brief summary]

## Incident Context
- **Trigger:** [What caused the issue]
- **Root Cause Category:** [Clarity, Context, Blocking, Detection, Discovery Gap, Shortcut Bias]

## Root Cause Analysis
[Detailed explanation of the framework failure, referencing VISION.md where applicable]

## Minimal Bug Reproduction
- **Expected:** [What should have happened]
- **Actual:** [What actually happened]

## Proposed Framework Fix
- **Suggested target:** [Which component/file should be updated]
- **Proposed change:** [Description of the necessary framework change]
```

### 5. File Issue (or Output for User)

Instead of applying a fix directly to local files (since you may not be in the `academicOps` repository), your deliverable is to file this report as an issue on the `nicsuzor/academicOps` repository.

If you have GitHub CLI access:
```bash
gh issue create --repo nicsuzor/academicOps --title "Bug: <brief-slug>" --body-file <path-to-your-report.md>
```

If you do not have GitHub CLI access, output the curated report to the user and instruct them to file it manually.

## Framework Reflection

```
## Framework Reflection
**Prompts**: [The observation/feedback that triggered /learn]
**Outcome**: success
**Accomplishments**: Curated diagnostic report created and filed (or provided to user).
**Root cause**: [Category]
```
