---
name: learn
type: command
category: instruction
description: File high-quality, anonymised bug reports to GitHub Issues for framework failures and knowledge capture.
triggers:
  - "framework issue"
  - "fix this pattern"
  - "improve the system"
  - "knowledge capture"
  - "bug report"
modifies_files: false
needs_task: false
mode: observation
domain:
  - framework
allowed-tools: Bash, Read, Grep, Glob
permalink: commands/learn
---

# /learn - Knowledge Capture & Bug Reporting

**Purpose**: Capture framework failures, recurring friction, and knowledge by filing high-quality, anonymised bug reports to GitHub Issues. We no longer make code changes directly; if a code change is warranted, someone will pick up the issue and address it. Not every issue will get addressed, as we use volume indicators to let the most active and critical issues float to the top.

**Privacy rule**: You MUST anonymise bug reports and transcripts before sending them out. NEVER include direct logs, session dumps, real people's names, email addresses, student details, or personal information.

## Workflow

### 1. Capture & Anonymise Failure Context

**Identify the failure**:

- Where did the mistake occur?
- What was the trigger?

**Generate Session Transcript** (if analyzing a prior session):

```bash
# Locate the session file (For Gemini or Claude)
SESSION_FILE=$(fd -t f -a --newer 1h .json ~/.gemini/tmp | xargs ls -t | head -1)

# Generate transcript using the installed plugin path
TRANSCRIPT_SCRIPT="${ACA_DATA:-~}/.claude/skills/framework/scripts/transcript.py"
if [ -f "$TRANSCRIPT_SCRIPT" ]; then
  uv run python "$TRANSCRIPT_SCRIPT" "$SESSION_FILE" > transcript.md
else
  uv run python -m aops_core.scripts.transcript "$SESSION_FILE" > transcript.md
fi
```

**Anonymisation**: Review `transcript.md` (or the current session context) and manually strip any PII, replacing it with placeholders like `[REDACTED_NAME]` or `[REDACTED_PROJECT]`.

### 2. Look for Existing GitHub Issues

We track volume by adding activity to existing issues rather than creating duplicates.

Search GitHub Issues for prior occurrences:

```bash
gh issue list --repo nicsuzor/academicOps --search "<failure keywords>"
```

If an existing issue matches the failure:

- **Do not create a new issue.**
- Add a comment to the existing issue with your anonymised context to increase its volume indicator:
  ```bash
  gh issue comment <issue-number> --repo nicsuzor/academicOps --body-file <path-to-anonymised-comment.md>
  ```
- _Stop here._ The increased activity will help the issue float to the top.

### 3. Root Cause Analysis (MANDATORY structured output)

If no existing issue is found, perform a root cause analysis to include in the new bug report.

**Emit this block in the issue body:**

```yaml
## Root Cause Analysis

**Failure**: [1-sentence description of what went wrong]

**Causal chain**:
1. [Trigger event]
2. [What the framework was supposed to do]
3. [What actually happened instead]
4. [Why — the root cause, not the symptom]

**Root cause category**: [Discovery Gap | Detection Failure | Instruction Weighting | Index Lag | Cross-workflow Gap | Enforcement Gap | Dropped Thread]

**Framework layer that failed**:
- Component: [skill/command/hook/workflow name]
- File: [path to the relevant file]

**Expected vs Actual**:
- Expected: [What VISION.md / AXIOMS.md says should happen]
- Actual: [What happened]
```

### 4. Determine Criticality Flags

Assess the severity of the issue to apply the correct labels. Critical issues will float to the top of the queue.

- **Critical**: System crash, data loss, or total blockage of a core workflow.
- **High**: Significant friction, workarounds required, but progress is possible.
- **Medium**: Annoyance, minor efficiency loss.
- **Low**: Polish, cosmetic, or edge-case behavior.

### 5. File the GitHub Issue

Create the issue with the appropriate labels for criticality and category.

```bash
gh issue create --repo nicsuzor/academicOps --title "Bug: <brief-slug>" --body-file <path-to-report.md> --label "bug" --label "criticality:<level>"
```

**Note**: Your job is now done. Do NOT attempt to fix the issue, create PKB tasks, or modify framework files.

## Anti-patterns (things this command must NOT do)

| Anti-pattern              | Why it's wrong                          | What to do instead                                         |
| :------------------------ | :-------------------------------------- | :--------------------------------------------------------- |
| Create a PKB task         | We use GitHub Issues to track bugs now. | File a GitHub issue or comment on an existing one.         |
| Attempt a direct fix      | `/learn` no longer makes code changes.  | Let someone else pick up the issue.                        |
| Include PII in the report | Violates privacy rules.                 | Anonymise all transcripts and logs before submission.      |
| Create duplicate issues   | Dilutes the volume indicator.           | Search `gh issue list` first and comment to bump activity. |

## Framework Reflection

```
## Framework Reflection
**Prompts**: [The observation/feedback that triggered /learn]
**Outcome**: success
**Accomplishments**: Anonymised context captured, GitHub issue filed/updated.
**Issue**: [GitHub Issue URL]
```
