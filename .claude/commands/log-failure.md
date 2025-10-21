---
description: Log agent performance failure to experiment tracking system
---
Immediately read and adopt:

* .academicOps/agents/TRAINER.md

You are now the trainer agent investigating an agent performance failure.

## Your Task

The user is reporting that an agent violated coding standards, instructions, or expected behavior.

**You MUST follow this exact workflow:**

### Step 1: Gather Context

Ask the user to clarify (if not already provided):
* What agent was active (or should have been)?
* What task was being performed?
* What violations occurred?
* What was the expected behavior?

### Step 2: Search for Related Issues

```bash
# Search for existing tracking issues
gh issue list --repo nicsuzor/academicOps --search "[relevant keywords]" --state all
```

Use at least 3 different keyword searches.

### Step 3: Log to Experiment Tracking

Create experiment log in `bot/experiments/`:

**Filename format**: `YYYY-MM-DD_brief-description.md`

**Required sections**:

```markdown
# Experiment: [Name]

**Date**: YYYY-MM-DD
**Commit**: [git hash if applicable, or "(not committed)"]
**Issue**: #[number]
**Agent**: [which agent performed work or should have]

## Hypothesis
[What was the agent trying to accomplish?]

## Implementation
[What did the agent actually do?]

## Violations
- [Standard violated with reference to instruction file:line]
- [Another violation]

## Outcome
[SUCCESS/FAILED and why]

## Lessons

### For [Instruction File] Enforcement
[What needs to change in instructions or enforcement]

### For [System Component]
[Other systemic issues discovered]

## Related Issues
- #[number]: [brief description]

## Modified Files
- [path] ([what changed])
```

### Step 4: Update Experiment INDEX

Add entry to `bot/experiments/INDEX.md` under "Active Experiments" section.

### Step 5: Create or Update GitHub Issue

**IMPORTANT**: All framework/agent issues go to `nicsuzor/academicOps` (see TRAINER.md lines 336-400)

**Decision tree**:
* If related issue exists → Add comment with experiment file reference
* If no related issue → Create new issue with `prompts` label

**Comment format**:

```markdown
## Experiment Logged: [Name]

**File**: `bot/experiments/YYYY-MM-DD_brief-description.md`
**Violations**: [list]
**Status**: [FAILED/SUCCESS]

See experiment log for full analysis.

Modified files:
- bot/experiments/YYYY-MM-DD_brief-description.md (created)
- bot/experiments/INDEX.md (updated)
```

### Step 6: Commit Experiment Log

```bash
cd .academicOps/
git add experiments/
git commit -m "experiment: [brief description]

Logged agent failure: [summary]

Violations:
- [violation 1]
- [violation 2]

Related: #[issue]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 7: Report Back

Tell the user:
* Experiment logged to `bot/experiments/[filename]`
* GitHub issue #[number] updated
* Committed as [hash]
* What systemic changes are recommended (if any)

## Critical Rules

* ALWAYS log to `bot/experiments/` BEFORE claiming work complete
* ALWAYS update `experiments/INDEX.md`
* ALWAYS link experiment file in GitHub issue
* Framework/agent issues ALWAYS go to nicsuzor/academicOps (agents know repo from git context)
* NEVER post sensitive info to wrong repository

## References

* TRAINER.md lines 126-153: Experimental testing requirements
* TRAINER.md lines 299-427: GitHub issue management
* Issue #118: Experiment tracking enforcement
