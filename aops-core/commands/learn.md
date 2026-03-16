---
name: learn
type: command
category: instruction
description: Diagnose framework failures, determine enforcement level, and create actionable follow-up
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
allowed-tools: Bash, Read, Grep, Glob, mcp__pkb__search, mcp__pkb__task_search, mcp__pkb__create_task, mcp__pkb__update_task, mcp__pkb__retrieve_memory
permalink: commands/learn
---

# /learn - Diagnose, Enforce, Track

**Purpose**: Diagnose a framework failure, determine the right enforcement level, and create trackable follow-up work so the fix actually gets implemented. This is NOT just a bug reporter — it's the framework's immune system.

**Privacy rule**: NEVER include direct logs, session dumps, real people's names, email addresses, student details, or personal information in reports or issues.

**CRITICAL**: You MUST complete ALL 6 steps in order. Each step produces structured output that feeds into the next. Skipping steps means the learning rots — which is the exact failure this command exists to prevent.

## Workflow

### 1. Capture Failure Context

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
  uv run python "$TRANSCRIPT_SCRIPT" "$SESSION_FILE"
else
  uv run python -m aops_core.scripts.transcript "$SESSION_FILE"
fi
```

If analyzing the current session, use the conversation context directly — no transcript needed.

### 2. Root Cause Analysis (MANDATORY structured output)

**CRITICAL: Your output is parsed by downstream steps.** You MUST emit the structured block below. Do not skip fields. Do not summarize. Each field forces you to actually investigate — fabricating answers defeats the purpose.

Before filling this out, you MUST:

1. Read the relevant framework files (AXIOMS.md, HEURISTICS.md, ENFORCEMENT.md, the skill/command that failed)
2. Search PKB for prior incidents: `mcp__pkb__task_search(query="<failure keywords>")`
3. Trace the causal chain: trigger → what should have happened → what actually happened → why

**Emit this block:**

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
- File: [path to the file that should have prevented this]
- Current enforcement level: [1a-7 from ENFORCEMENT.md, or "none"]

**Prior incidents**: [PKB task IDs of similar failures, or "none found"]

**Expected vs Actual**:
- Expected: [What VISION.md / AXIOMS.md says should happen]
- Actual: [What happened]
```

**If you cannot fill a field**: Write "UNKNOWN — needs investigation" and flag it as a follow-up task in Step 5. Do NOT leave fields blank or skip the block.

### 3. Determine Enforcement Level

Read `ENFORCEMENT.md` (specifically the Mechanism Ladder and Diagnosis → Solution Mapping table). Based on the root cause from Step 2, determine:

**Emit this block:**

```yaml
## Enforcement Decision

**Current level**: [What enforcement exists now — e.g., "Level 1b: rule in SKILL.md says 'must do X'"]
**Why it failed**: [Why the current level was insufficient — e.g., "competes with task urgency, no task-specific reason given"]
**Proposed level**: [Target level from the ladder — e.g., "Level 1c: emphatic + reasoned, with specific stakes"]
**Why this level**: [Why this is the minimum effective level — reference the Diagnosis → Solution Mapping]
**Why not lower**: [What was tried or why lower levels won't work]
**Why not higher**: [Why we don't need to escalate further — or "escalation needed, see justification"]
```

**Key principle**: Start at the lowest effective level. Escalate only with evidence that lower levels have failed. If this is a repeat failure (prior incidents found in Step 2), escalate one level above the current enforcement.

### 4. Propose Enforcement Change

Using the Level 1d Structured Justification Format from ENFORCEMENT.md, draft the actual change. This is not a suggestion — it's the specific text/code that needs to be added.

**Emit this block:**

```yaml
## Rule Change Justification

**Scope**: [AXIOMS.md | HEURISTICS.md | skill file | command file | hook | settings.json]

**Rules Loaded**:
- AXIOMS.md: [P#X, P#Y — or "not relevant"]
- HEURISTICS.md: [H#X, H#Y — or "not relevant"]
- ENFORCEMENT.md: [entry name — or "not relevant"]

**Prior Art**:
- Search query: "[keywords used]"
- Related tasks: [task IDs, or "none"]
- Pattern: [existing pattern | novel pattern]

**Intervention**:
- Type: [corollary to P#X | new heuristic | enforcement hook | command strengthening | etc.]
- Level: [1a-7]
- Change: [THE EXACT TEXT OR CODE to add/modify — max 3 sentences for prompt changes, full snippet for hooks]
- Target file: [exact path]

**Minimality**:
- Why not lower level: [explanation]
- Why not narrower scope: [explanation]

**Escalation**: [auto | critic | custodiet | human]
```

### 5. File Issue AND Create Trackable Work

**CRITICAL**: Filing an issue alone is a dropped thread. You MUST create PKB tasks so the work gets pulled from the queue.

#### 5a. File the GitHub issue

Combine Steps 2-4 into a diagnostic report and file it:

```bash
gh issue create --repo nicsuzor/academicOps --title "Enforce: <brief-slug>" --body-file <path-to-report.md>
```

#### 5b. Create PKB work task

Create a task for the actual enforcement change:

```
mcp__pkb__create_task(
  title="[Enforce] <description of the change>",
  type="task",
  project="aops",
  body="## Context\n<link to GH issue>\n\n## Change\n<exact change from Step 4>\n\n## Acceptance Criteria\n1. Change applied to <target file>\n2. Evidence of compliance in next 3 sessions",
  tags=["enforcement", "learn"]
)
```

#### 5c. Create PKB waiting task (if change requires review)

If the escalation level is "critic", "custodiet", or "human":

```
mcp__pkb__create_task(
  title="[Waiting] Review enforcement: <slug>",
  type="task",
  project="aops",
  status="blocked",
  depends_on=["<work-task-id>"],
  body="Blocked on review of enforcement change. Verify compliance after 3 sessions.",
  tags=["enforcement", "review"]
)
```

### 6. Persist Learning

Invoke `/remember` to capture the generalized pattern (not the specific incident):

- **What to remember**: The generalizable principle — e.g., "Filing external work without PKB tasks drops the thread"
- **What NOT to remember**: The specific incident details (those live in the GH issue and PKB tasks)
- **Test**: Would this memory help an agent working on a DIFFERENT component? If not, it's too specific.

## Anti-patterns (things this command must NOT do)

| Anti-pattern                                       | Why it's wrong                                  | What to do instead                       |
| :------------------------------------------------- | :---------------------------------------------- | :--------------------------------------- |
| Skip root cause, jump to fix                       | Treats symptoms, failure recurs                 | Complete Step 2 structured output        |
| File issue without PKB tasks                       | Work rots — nothing pulls from GH issues        | Always do Step 5b (and 5c if needed)     |
| Propose enforcement without reading ENFORCEMENT.md | May duplicate or contradict existing mechanisms | Step 3 requires reading the file         |
| Remember the specific incident                     | Too narrow to help future agents                | Remember the generalizable pattern       |
| Stop after filing                                  | No one tracks whether the fix worked            | Create waiting task with verification AC |

## Framework Reflection

```
## Framework Reflection
**Prompts**: [The observation/feedback that triggered /learn]
**Outcome**: success
**Accomplishments**: Root cause diagnosed, enforcement level determined, GH issue filed, PKB tasks created.
**Root cause**: [Category from Step 2]
**Enforcement**: [Level proposed in Step 3]
**Tasks created**: [task IDs from Step 5]
```
