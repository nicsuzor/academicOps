---
name: retro
type: command
category: instruction
description: Critical transcript review - reads recent sessions with a framework-dev lens, identifies problems, and files issues via /learn.
triggers:
  - "review transcript"
  - "session retro"
  - "transcript review"
  - "retro"
  - "review session"
modifies_files: true
needs_task: false
mode: execution
domain:
  - framework
  - quality-assurance
allowed-tools: Bash, Read, Grep, Glob, Edit, Skill, Agent
model: opus
permalink: commands/retro
---

# /retro - Critical Transcript Review

**Purpose**: Read a recent transcript in detail through a framework-development lens. Provide a brutal, concise, critical review identifying problems and potential problems. Log every finding via `/learn`. We are aiming for EXCELLENCE, not "running code".

**Privacy rule**: Anonymise all findings before filing. No real names, emails, student details, or session dumps in GitHub issues.

## Workflow

### 1. Select Transcript

Find the most recent unreviewed transcript(s):

```bash
# List recent transcripts, newest first
ls -lt ~/.aops/sessions/transcripts/*.md | head -20
```

**Skip already-reviewed transcripts** — check for `reviewed_by` in frontmatter:

```bash
# Show transcripts missing reviewed_by (i.e., unreviewed)
for f in $(ls -t ~/.aops/sessions/transcripts/*.md | head -20); do
  grep -q "^reviewed_by:" "$f" || echo "$f"
done | head -10
```

If the user specified a session ID or path, use that instead.

If no unreviewed transcripts exist, report that and stop.

### 2. Read the Full Transcript

Read the selected transcript **in its entirety**. Do not skim. Do not sample. Read every line.

For large transcripts, read in chunks but cover the whole file:

```
Read(file_path="<path>", offset=1, limit=500)
Read(file_path="<path>", offset=500, limit=500)
# ... continue until EOF
```

### 3. Critical Review

Evaluate the session against these lenses. Be **brutal and specific** — quote the transcript when citing problems. Do not soften findings.

#### A. Framework Compliance

- Did the agent follow the task lifecycle (pre-work, planning, implementation, post-work)?
- Did non-trivial work get a plan + pauli review?
- Were tasks tracked? Updated? Completed?
- Did the agent push before claiming done?
- Did the agent run QA/tests?

#### B. Scope Discipline

- Did the agent do what was asked, or did it drift?
- Was there scope expansion without user approval?
- Did the agent add unnecessary features, refactors, or "improvements"?
- Did the agent over-explore when a direct approach would suffice?

#### C. Judgment Quality

- Did the agent HALT when it should have?
- Did the agent guess when it should have investigated?
- Did the agent investigate when it should have asked?
- Were assumptions stated or silently embedded?
- Did the agent notice when it was wrong and correct course?

#### D. Communication

- Was the agent concise or verbose?
- Did it explain decisions or just act?
- Did it waste the user's attention on low-value output?
- Did trailing summaries or restatements add friction?

#### E. Tool Use

- Did the agent use the right tools (dedicated tools vs bash)?
- Were parallel tool calls used where possible?
- Was there redundant work (reading the same file twice, searching then re-searching)?
- Did the agent respect tool boundaries (Read not cat, Edit not sed)?

#### F. Knowledge & Learning

- Did the agent check existing infrastructure before proposing to build?
- Did it update PKB/tasks as information emerged?
- Did it file learnings for friction encountered?
- Did it avoid duplicating existing work?

#### G. Excellence Gap

This is the most important lens. Ask:

- **What would a 10x agent have done differently?**
- Where was the work merely adequate when it could have been outstanding?
- What was the biggest missed opportunity?
- If this session were the only evidence of the framework's quality, what would you conclude?

### 4. Produce the Review

Output a structured review:

```markdown
## Transcript Review: <transcript filename>

**Session**: <session_id>
**Date**: <date>
**Project**: <project>
**Verdict**: [EXCELLENT | GOOD | ADEQUATE | POOR | FAILING]

### Critical Issues (must fix)

1. **[Issue title]**: [Specific quote or reference] — [Why this matters]

### Warnings (should fix)

1. **[Issue title]**: [Specific quote or reference] — [Why this matters]

### Observations (worth noting)

1. **[Observation]**: [Context]

### What Went Well

1. [Genuine strengths — don't manufacture praise]

### Excellence Gap

[The single most impactful thing that would elevate this session from where it landed to EXCELLENT]
```

### 5. File Issues via /learn

For every **Critical Issue** and **Warning**: invoke `/learn` to file or update a GitHub issue.

```
Skill(skill="learn")
```

Pass the specific finding with enough context for root cause analysis. Do NOT batch findings — each distinct issue gets its own `/learn` invocation so it can be tracked independently.

For **Observations**: only invoke `/learn` if the observation reveals a systemic pattern (not a one-off).

### 6. Stamp the Transcript as Reviewed

After completing the review, add `reviewed_by` metadata to the transcript's YAML frontmatter:

```yaml
reviewed_by:
  - agent: "<model-name>"
    date: "<ISO 8601 datetime>"
    machine: "<hostname>"
    session_id: "<reviewer's session ID>"
    verdict: "<EXCELLENT|GOOD|ADEQUATE|POOR|FAILING>"
    issues_filed: <count>
```

Use `Edit` to insert the `reviewed_by` block into the existing frontmatter (before the closing `---`).

If the transcript has already been reviewed (frontmatter contains `reviewed_by`), **append** to the list rather than replacing — multiple reviews are valid.

**How to get the values**:

- `agent`: Use your model name (e.g., "claude-opus-4-6")
- `date`: Current ISO 8601 datetime
- `machine`: Run `hostname` via Bash
- `session_id`: Read from `~/.claude/sessions/` matching the current PID, or use "unknown"
- `verdict`: From your review in Step 4
- `issues_filed`: Count of /learn invocations from Step 5

### 7. Framework Reflection

```
## Framework Reflection
**Prompts**: /retro [transcript path]
**Outcome**: [success/partial/failure]
**Accomplishments**: Reviewed <transcript>, filed <N> issues, stamped as reviewed.
**Issues filed**: [GitHub Issue URLs from /learn invocations]
```

## Batch Mode

When processing multiple sessions (e.g., via `/loop`), follow these additional guidelines:

### Triage First

Don't retro every session. Have a fast pass (read first/last 50 lines) and prioritise:

- Sessions where the user corrected the agent ("no", "stop", "that's wrong")
- Sessions > 1hr that produced no PR or task
- Sessions rated POOR by their own /dump reflection
- Sessions with interesting new patterns (not just re-confirming known issues)

Skip automated sessions (cron, task notifications) and trivially short sessions with no meaningful interaction.

### Issue Budget

Cap at **3 filed issues per session**: 1 critical, 1 warning, 1 observation. More findings dilute signal. If a pattern is already filed as a GitHub issue, **comment on the existing issue** with the new occurrence rather than filing a duplicate. Volume bumps on existing issues are more valuable than 10 new issues saying the same thing.

### Deduplication

Before filing, check the repo's open issues for existing coverage. The orchestrator should pass a list of already-known issues to each retro agent so they can comment rather than duplicate. Common recurring themes that are likely already filed:

- Subagent over-exploration / token waste
- Push to main bypassing PR pipeline
- Jumping to solutions without diagnosis
- No task tracking for multi-hour sessions
- Scope expansion without user approval
- Custodiet overhead / false positives

### Orchestrator Setup

When running batch retros, the orchestrator should:

1. Create a task list for all sessions to process
2. Maintain max 4 parallel agents
3. Track progress via TaskUpdate
4. Set `ENFORCER_GATE_MODE=off` to avoid ~200K tokens of compliance overhead on a user-directed loop
5. After all sessions complete, produce a summary with verdict distribution and top recurring themes

## What This Command Does NOT Do

- **Does not fix issues** — it identifies and files them. Fixes are separate work.
- **Does not review code** — it reviews agent behavior and framework compliance.
- **Does not generate transcripts** — use `transcript.py` for that. This command reads existing transcripts.
- **Does not soften findings** — if the work was poor, say so. Excellence requires honest assessment.

## Anti-patterns

| Anti-pattern                       | Why it's wrong                 | What to do instead                  |
| :--------------------------------- | :----------------------------- | :---------------------------------- |
| Skimming the transcript            | Misses subtle issues           | Read every line                     |
| "Overall good with minor issues"   | Lazy review, not useful        | Be specific, quote the transcript   |
| Filing one mega-issue              | Can't track or prioritize      | One /learn per distinct finding     |
| Inventing praise                   | Dishonest, wastes attention    | Only note genuine strengths         |
| Reviewing your own session         | Conflict of interest           | Review a DIFFERENT session          |
| Batch-reviewing 20+ sessions       | Diminishing returns after ~8   | Triage first, review selectively    |
| Filing 10 issues from one session  | Noise, can't prioritise        | Cap at 3: 1 critical, 1 warn, 1 obs |
| Filing new issue for known pattern | Duplicates clutter the tracker | Comment on existing issue instead   |
