---
name: experiment-tracker
description: Review conversation transcripts to identify, catalog, and track academicOps framework errors, agent performance issues, and experiments. Search exhaustively for existing GitHub issues to avoid duplication. Create or update GitHub issues in nicsuzor/academicOps repository only. Maintain experiment logs and ensure ARCHITECTURE.md stays current. Use when agent violations occur, experiments complete, or framework behavior needs documentation. Never modifies third-party projects or leaks sensitive data across boundaries.
---

# Experiment Tracker

## Overview

Systematically catalog agent performance issues, framework errors, and experimental outcomes in the academicOps project. This skill serves as the framework's memory, ensuring patterns are recognized, experiments are tracked, and the project evolves based on evidence rather than speculation.

## When to Use This Skill

Use experiment-tracker when:

1. **Agent violations observed** - Agent violated core axioms or instructions
2. **Framework errors encountered** - Hooks, scripts, or infrastructure failed
3. **Experiments completed** - Testing framework changes, need to document results
4. **Conversation review requested** - Analyzing transcript for patterns and issues
5. **Architecture drift detected** - ARCHITECTURE.md doesn't match reality

**Concrete trigger examples**:
- "The developer agent created a new file instead of editing the existing one"
- "Review this conversation for framework violations"
- "Document the experiment results for the new validation hook"
- "Check if this failure pattern has been reported before"
- "Update ARCHITECTURE.md to reflect the new skills system"

**CRITICAL**: This skill works from ANY repository but ONLY writes to `nicsuzor/academicOps` GitHub. Never modifies third-party projects.

## Core Philosophy

### Zero Duplication

Search exhaustively before creating issues. Multiple GitHub issues for the same root cause dilutes tracking and creates confusion. Categorize behaviors by underlying patterns, not surface symptoms.

**Search strategy**:
- Error messages and stack traces
- Component names (agents, hooks, scripts, skills)
- Behavioral patterns (defensive behavior, scope creep, DRY violations)
- Related keywords and symptoms
- Check closed issues for recurrence

### Evidence-Based Tracking

Document what actually happened, not speculation:
- Quote exact agent output
- Link to conversation transcripts
- Include file paths and line numbers
- Reference commits and experiments
- Measure outcomes against success criteria

### Transparent Memory

All tracking happens in public GitHub issues and experiment logs:
- `experiments/` directory - chronological experiment logs
- `experiments/INDEX.md` - master tracking index
- GitHub issues - authoritative source of truth
- ARCHITECTURE.md - current system state

## Workflow Decision Tree

```
START: Analyzing conversation or receiving failure report
↓
Q1: Is this academicOps framework-related?
YES → Continue to Q2
NO → STOP. This skill only tracks academicOps framework issues

Q2: Working in which repository?
nicsuzor/academicOps → Can write locally AND to GitHub
Other repository → ONLY write to GitHub (never modify local files)

Q3: What type of issue?
├─ Agent violation → Follow Agent Violation Workflow
├─ Experiment result → Follow Experiment Logging Workflow
├─ Architecture drift → Follow Architecture Update Workflow
└─ General framework error → Follow Error Cataloging Workflow
```

## Agent Violation Workflow

**Objective**: Document agent behavior that violated core axioms or instructions.

### Step 1: Identify the Violation

Extract from conversation:
1. **What happened** - Exact agent behavior
2. **What should have happened** - Expected behavior per instructions
3. **Which axiom/rule violated** - Reference specific section (e.g., "_CORE.md Axiom #10")
4. **Evidence** - Quote relevant agent output

### Step 2: Search for Existing Issues

MANDATORY: Search GitHub with 3+ different strategies before creating new issue.

```bash
# Search by component
gh issue list --repo nicsuzor/academicOps --search "agent-developer"

# Search by axiom/pattern
gh issue list --repo nicsuzor/academicOps --search "DRY violation"

# Search by behavior
gh issue list --repo nicsuzor/academicOps --search "creates new file"

# Check recently updated
gh issue list --repo nicsuzor/academicOps --state all --limit 20
```

**Decision point**:
- Found matching issue → Update it (Step 3A)
- No match after exhaustive search → Create new (Step 3B)

### Step 3A: Update Existing Issue

Add comment with new evidence:

```bash
gh issue comment [NUMBER] --repo nicsuzor/academicOps --body "$(cat <<'EOF'
## New Instance: [Date]

**Context**: [Where this occurred - which repo, what task]

**Violation**: [What happened]

**Evidence**:
```
[Quoted agent output or behavior]
```

**Pattern Confirmation**: [How this matches the existing issue]

**Related**: [Links to experiments, commits, or other issues if any]
EOF
)"
```

### Step 3B: Create New Issue

Only after exhaustive search confirms no match exists:

```bash
gh issue create --repo nicsuzor/academicOps \
  --title "[Component]: Brief violation description" \
  --label "bug,agent-behavior" \
  --body "$(cat <<'EOF'
## Violation Summary

**Agent**: [Which agent violated]
**Axiom/Rule**: [Specific reference to _CORE.md or agent instructions]
**Date**: [When observed]
**Repository**: [Where this occurred]

## What Happened

[Detailed description of agent behavior]

## What Should Have Happened

[Expected behavior per instructions]

## Evidence

```
[Quoted agent output, file diffs, or conversation transcript]
```

## Root Cause Analysis

[One level deep - why this happened]
- Was instruction unclear?
- Was guardrail missing?
- Was this infrastructure issue?

## Categorization

**Pattern**: [Behavioral pattern - e.g., defensive behavior, scope creep, DRY violation]
**Severity**: [Low/Medium/High/Critical]
**Frequency**: [First occurrence / recurring]

## Related Issues

[Search results showing similar patterns]

## Proposed Solution

[Brief suggestion - preferring scripts > hooks > config > instructions]
EOF
)"
```

### Step 4: Create Experiment Log (if warranted)

For significant violations requiring framework changes:

```bash
# Only if in academicOps repository
cat > experiments/$(date +%Y-%m-%d)_[descriptive-name].md <<'EOF'
# Experiment: [Name]

**Date**: $(date +%Y-%m-%d)
**Commit**: [pending]
**Issue**: #[NUMBER]
**Agent**: [which agent violated]

## Hypothesis

[If this is addressed, what behavior will change]

## Violation

[What happened that shouldn't have]

## Pattern

[Underlying behavioral pattern]

## Lessons

### For [Component] Enforcement

[Specific recommendation with code/instruction examples]

### For Instruction Clarity

[If instruction changes needed, what and why]

## Related Issues

[Links to GitHub issues]

## Modified Files

[List of files that will be modified to address this]
EOF
```

### Step 5: Update Experiment Index

```bash
# Only if in academicOps repository
# Add entry to experiments/INDEX.md under "Active Experiments"
```

## Experiment Logging Workflow

**Objective**: Document results of framework experiments (hook changes, instruction updates, etc.)

### Step 1: Locate Experiment Log

Experiments live in `experiments/YYYY-MM-DD_name.md` format.

If experiment log exists → Update it
If new experiment → Create it (use template from Agent Violation Workflow Step 4)

### Step 2: Document Results

Update the experiment log's Results and Outcome sections:

```markdown
## Results

**Test Runs**: [Number of tests performed]
**Success Rate**: [X/Y successful]

**Metrics**:
- [Metric 1]: [Before] → [After]
- [Metric 2]: [Before] → [After]

**Observations**:
- [What happened during testing]
- [Unexpected behaviors]
- [Edge cases discovered]

## Outcome

**Status**: [SUCCESS / FAILED / PARTIAL]

**Decision**: [Keep changes / Revert / Iterate]

**Rationale**: [Why this decision]

**Next Steps**: [If any follow-up needed]
```

### Step 3: Update GitHub Issue

Link experiment results to related issue:

```bash
gh issue comment [NUMBER] --repo nicsuzor/academicOps --body "$(cat <<'EOF'
## Experiment Results

**Experiment Log**: `experiments/[DATE]_[name].md`
**Outcome**: [SUCCESS/FAILED/PARTIAL]

**Key Findings**:
- [Finding 1]
- [Finding 2]

**Metrics**: [Before → After]

**Decision**: [Keep/Revert/Iterate]

[If SUCCESS]: Closing as resolved.
[If FAILED]: Documented failure, reverting changes.
[If PARTIAL]: Continuing investigation with refinements.
EOF
)"

# If resolved
gh issue close [NUMBER] --repo nicsuzor/academicOps --comment "Resolved via experiment [DATE]_[name]"
```

### Step 4: Update Experiment Index

Move completed experiments from "Active" to "Closed" in `experiments/INDEX.md`.

## Error Cataloging Workflow

**Objective**: Document framework errors (scripts, hooks, infrastructure failures).

### Step 1: Identify Error Type

Categorize the error:
- **Script failure** - Python script crashed or produced wrong output
- **Hook failure** - SessionStart, PreToolUse, etc. failed
- **Permission issue** - Tool blocked when shouldn't be (or allowed when should be blocked)
- **Environment issue** - Missing dependencies, wrong paths, env vars not set
- **Integration issue** - Claude Code, gh CLI, git, uv, pytest problems

### Step 2: Extract Technical Details

Gather complete error information:
```markdown
**Error Message**: [Full error text]
**Stack Trace**: [If available]
**Component**: [Which script/hook/tool]
**File Path**: [Exact location - e.g., scripts/load_instructions.py:45]
**Environment**: [Repository, Python version, OS]
**Reproduction Steps**: [How to trigger this error]
```

### Step 3: Search for Existing Issues

Same exhaustive search as Agent Violation Workflow:

```bash
# Search by error message
gh issue list --repo nicsuzor/academicOps --search "KeyError"

# Search by component
gh issue list --repo nicsuzor/academicOps --search "load_instructions.py"

# Search by pattern
gh issue list --repo nicsuzor/academicOps --search "environment variable"
```

### Step 4: Create or Update Issue

If new error:

```bash
gh issue create --repo nicsuzor/academicOps \
  --title "[Component]: Error description" \
  --label "bug,infrastructure" \
  --body "$(cat <<'EOF'
## Error Summary

**Component**: [Script/Hook/Tool]
**File**: [Path and line number]
**Date**: [When encountered]

## Error Details

```
[Full error message and stack trace]
```

## Reproduction Steps

1. [Step 1]
2. [Step 2]
3. [Observe error]

## Environment

- **Repository**: [Which repo]
- **Python**: [Version]
- **OS**: [Linux/Mac/Windows version]
- **Dependencies**: [uv, gh, git versions if relevant]

## Root Cause

[Analysis - one level deep]

## Impact

[Who is affected, what breaks]

## Proposed Fix

[Technical solution]
EOF
)"
```

If updating existing issue, add new occurrence evidence.

## Architecture Update Workflow

**Objective**: Keep ARCHITECTURE.md synchronized with actual system state.

### Step 1: Detect Drift

Compare ARCHITECTURE.md against reality:
- New components added (skills, agents, scripts, hooks)
- Workflows changed
- Directory structure evolved
- Design decisions made
- Open questions resolved

### Step 2: Research Current State

Verify actual implementation:

```bash
# List current agents
ls -1 agents/*.md

# List current skills
ls -1d .claude/skills/*/

# List current scripts
ls -1 scripts/*.py

# Check hooks configuration
cat .claude/settings.json | grep -A 20 hooks
```

### Step 3: Update ARCHITECTURE.md

Edit sections to match reality:

**When adding NEW component**:
- Add to relevant section (Agents, Skills, Scripts, Hooks)
- Document purpose and usage
- Include examples

**When design decision made**:
- Move from "Open Questions" to implementation section
- Document rationale
- Include references to issues/experiments

**When workflow changed**:
- Update workflow description
- Add/remove steps
- Update examples

**Writing style**: Descriptive voice (not imperative)
- ✅ "The system loads instructions from..."
- ❌ "You must load instructions from..."

### Step 4: Create GitHub Issue for Major Drifts

If ARCHITECTURE.md significantly out of date:

```bash
gh issue create --repo nicsuzor/academicOps \
  --title "docs: ARCHITECTURE.md drift from reality" \
  --label "documentation" \
  --body "$(cat <<'EOF'
## Drift Summary

ARCHITECTURE.md does not reflect current system state.

## Discrepancies Identified

1. [Missing component/workflow]
2. [Outdated description]
3. [Open question that was resolved]

## Required Updates

- [ ] Section X: [What needs updating]
- [ ] Section Y: [What needs updating]

## Current State Verification

[Evidence from codebase showing actual implementation]
EOF
)"
```

## Privacy & Security Boundaries

### CRITICAL: Data Boundaries

**When working in academicOps repository**:
- ✅ Can write to local files (experiments/, ARCHITECTURE.md)
- ✅ Can write to GitHub issues
- ✅ Can reference all framework files

**When working in other repositories**:
- ❌ NEVER modify local files
- ✅ CAN write to nicsuzor/academicOps GitHub issues only
- ❌ NEVER include sensitive data in GitHub issues (API keys, credentials, private project details)
- ✅ Sanitize examples and quotes

### Sanitization Rules

Before posting to GitHub from non-academicOps repos:

1. **Remove credentials**: API keys, tokens, passwords, connection strings
2. **Generalize paths**: `/home/nic/private-client/` → `[project-directory]/`
3. **Remove proprietary info**: Client names, private data, business logic
4. **Keep framework errors**: Stack traces, agent behaviors, axiom violations are safe

**Example sanitization**:

```markdown
# ❌ BAD - includes sensitive data
Error in /home/nic/client-acme/api_key.py: Invalid key sk_live_abc123

# ✅ GOOD - sanitized
Error in [project]/config.py: Invalid API key format
```

## Categorization Strategy

### Behavioral Patterns (for agent violations)

Group issues by underlying behavior, not surface symptoms:

**Defensive Behavior**:
- Creating `_new` files instead of editing
- Adding try/except fallbacks
- Building workarounds instead of fixing root cause

**Scope Creep**:
- Fixing problems not requested
- Expanding task beyond original ask
- Launching into solutions before answering questions

**DRY Violations**:
- Duplicating content across files
- Repeating core axioms in agent files
- Creating similar scripts/functions

**Authority Violations**:
- Wrong agent doing wrong work (trainer fixing code)
- Bypassing required agents (committing without code-review)

**Axiom Violations**:
- DO ONE THING - doing extra work
- ANSWER DIRECT QUESTIONS - launching into solutions
- VERIFY FIRST - assuming instead of checking
- NO EXCUSES - rationalizing failures

### Error Patterns (for infrastructure issues)

**Environment Errors**:
- Missing dependencies
- Wrong paths
- Env vars not set

**Integration Errors**:
- Tool compatibility issues
- API failures
- Version mismatches

**Hook/Script Errors**:
- Logic bugs
- Edge cases
- Performance issues

## Quality Standards

Every issue must have:
- [ ] Clear, specific title
- [ ] Proper labels (bug/enhancement/documentation)
- [ ] Complete technical details
- [ ] Evidence (quotes, stack traces, file refs)
- [ ] Severity/priority assessment
- [ ] Links to related issues
- [ ] Proposed solution direction

Every experiment log must have:
- [ ] Date, issue link, commit ref
- [ ] Clear hypothesis
- [ ] Documented changes
- [ ] Success criteria
- [ ] Results (after testing)
- [ ] Outcome decision

ARCHITECTURE.md must:
- [ ] Describe current state (not aspirational)
- [ ] Use descriptive voice (not imperative)
- [ ] Include concrete examples
- [ ] Reference actual files/paths
- [ ] Keep concise (link to details elsewhere)

## Anti-Patterns to Avoid

**Don't create duplicate issues**:
- ❌ Three issues for "agent doesn't follow DRY"
- ✅ One issue tracking DRY violations with multiple examples

**Don't leak sensitive data**:
- ❌ Including API keys, private paths, client names in GitHub
- ✅ Sanitizing all examples before posting

**Don't modify third-party projects**:
- ❌ Creating experiment logs in client repos
- ✅ Only documenting to academicOps GitHub

**Don't speculate**:
- ❌ "This probably happens because..."
- ✅ "This happened when X, error message shows Y"

**Don't ignore existing work**:
- ❌ Creating issue without searching first
- ✅ Exhaustive search, then create or update

## Quick Reference

**Search before creating** (minimum 3 searches):
```bash
gh issue list --repo nicsuzor/academicOps --search "[error-msg]"
gh issue list --repo nicsuzor/academicOps --search "[component]"
gh issue list --repo nicsuzor/academicOps --search "[pattern]"
```

**Create agent violation issue**:
```bash
gh issue create --repo nicsuzor/academicOps \
  --title "[Agent]: Violation description" \
  --label "bug,agent-behavior"
```

**Create infrastructure error issue**:
```bash
gh issue create --repo nicsuzor/academicOps \
  --title "[Component]: Error description" \
  --label "bug,infrastructure"
```

**Update experiment log**:
```bash
# Edit experiments/YYYY-MM-DD_name.md
# Update Results and Outcome sections
```

**Update ARCHITECTURE.md**:
```bash
# Edit ARCHITECTURE.md
# Move from "Open Questions" to implementation sections
# Document current state in descriptive voice
```

**Repository boundary check**:
```bash
# Am I in academicOps repo?
pwd  # Should contain /academicOps or /bot

# If NO → Only write to GitHub, never local files
# If YES → Can write locally and to GitHub
```

## Resources

### references/

This skill includes detailed reference documentation:

- **categorization-guide.md** - Comprehensive guide to categorizing errors and violations by behavioral patterns
- **github-search-strategies.md** - Advanced GitHub search techniques and query patterns

### scripts/

Helper scripts for experiment tracking operations:

- **sanitize_github.py** - Sanitize conversation transcripts before posting to public GitHub (uses DataFog library)
- **check_architecture_drift.py** - Compare ARCHITECTURE.md against actual codebase state

**Deprecated**:
- **sanitize_for_github.py** - Old 163-line custom implementation (replaced by sanitize_github.py). Use DataFog instead per Axiom #11.

Use these scripts when processing data for GitHub issues or validating documentation currency.
