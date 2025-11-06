---
name: aops-bug
description: Track bugs, agent violations, and framework improvements in the academicOps
  agent system. Understand core axioms, categorize behavioral patterns, manage experiment
  logs, detect architecture drift, and maintain framework health. Calls github-issue
  skill for GitHub operations. Use when agents violate axioms, framework bugs occur,
  experiments complete, or architecture needs updating. Specific to academicOps framework.
permalink: aops/skills/aops-bug/skill
---

# academicOps Bug and Framework Tracking

You are responsible for bug tracking in the @nicsuzor/academicOps project.

## Overview

Track and manage bugs, agent violations, and improvements specific to the academicOps agent framework. This skill understands framework architecture, core axioms, behavioral patterns, and enforcement hierarchy. It calls the `github-issue` skill for GitHub operations while providing academicOps-specific context and decision-making.

## When to Use This Skill

Use aops-bug when:

1. **Agent violates core axioms** - Agent doesn't follow _CORE.md rules
2. **Framework bug encountered** - Scripts, hooks, or infrastructure failing
3. **Experiment needs tracking** - Testing framework changes
4. **Architecture drift detected** - ARCHITECTURE.md doesn't match reality
5. **Pattern analysis needed** - Understanding recurring agent behaviors

**Concrete trigger examples**:
- "Agent created _new file instead of editing (defensive behavior)"
- "Hook validate_tool.py failed with KeyError"
- "Document experiment results for new pre-commit check"
- "Agent violated fail-fast axiom by using .get() with default"
- "ARCHITECTURE.md missing new skills system description"

**NOT for**:
- General GitHub issue management → Use `github-issue` skill directly
- Project-specific bugs → Use project's issue tracker
- User questions about academicOps → Answer directly, don't track

## Scope Boundaries

This skill operates in **two distinct modes** depending on invocation context:

### Mode 1: Documentation-Only (via `/log-failure` command)

**When invoked via `/log-failure`**, your scope is strictly LIMITED to:

✅ **DO**:
- Analyze the violation/bug pattern
- Search for existing GitHub issues
- Document findings in GitHub (update existing or create new issue)
- Report analysis to user

❌ **DO NOT**:
- Fix the user's original request that triggered the failure
- Implement solutions or code changes
- Investigate deeply beyond initial categorization
- Attempt workarounds for the reported problem

**Rationale**: `/log-failure` is for rapid documentation based on single data points. Fixes require experiment-driven validation with multiple data points.

**Example**:
```
User: "/log-failure agent didn't archive task correctly"

✅ CORRECT:
1. Identify violation pattern (e.g., didn't read tool docs)
2. Search for related issues
3. Update issue #123 with new instance
4. Report: "Documented in issue #123. This is the 3rd instance of not reading tool documentation."

❌ WRONG:
1. Archive the task for the user
2. Fix the tool's code
3. Investigate why the tool failed
4. Propose solutions
```

### Mode 2: Full Intervention (direct invocation)

**When invoked directly** (not via `/log-failure`), full scope includes:

- All documentation steps from Mode 1
- Deep investigation of root causes
- Experiment log creation
- Solution design and implementation
- Testing and validation

**When to use**: After multiple data points confirm a pattern, use direct invocation for comprehensive intervention.

## Follow Core Workflow

This skill uses a **workflow-based** structure with decision trees for different scenarios.

### Workflow Decision Tree

```
START: Problem, violation, or update identified
↓
Q1: What type of issue?
├─ Agent Violation → Agent Violation Workflow
├─ Framework Bug → Framework Bug Workflow
├─ Experiment Result → Experiment Logging Workflow
├─ Architecture Drift → Architecture Update Workflow
└─ Progress Summary → Provide Brief Summary
```

## Workflow 1: Agent Violation

**Objective**: Document agent behavior that violated core axioms or instructions.

### Step 1.1: Identify the Violation

Extract from the problem report:

1. **What happened**: Exact agent behavior
2. **What should have happened**: Expected behavior per instructions
3. **Which axiom/rule violated**: Reference specific axiom from _CORE.md
4. **Evidence**: Quote relevant agent output or behavior

**Example**:
```
What happened: Agent created config_new.yaml instead of editing config.yaml
What should have: Edited config.yaml directly
Axiom violated: #7 Fail-Fast (defensive behavior, no workarounds)
Evidence: Agent output "Creating config_new.yaml to avoid overwriting"
```

### Step 1.2: Categorize by Behavioral Pattern

Use `references/behavioral-patterns.md` to identify the underlying pattern:

**Common patterns**:
- Defensive Behavior (Axiom #7, #8 violations)
- Scope Creep (Axiom #1, #2 violations)
- DRY Violations (Axiom #10 violations)
- Authority Violations (wrong agent doing wrong work)
- Use Standard Tools violations (Axiom #11)
- Infrastructure misuse

**Why categorize**: Groups related violations, identifies systemic vs one-off issues.

### Step 1.3: Search for Existing Issues

Call the `github-issue` skill to search for related issues:

```
Use github-issue skill to search nicsuzor/academicOps with:
- Axiom name ("fail-fast", "DRY", "use standard tools")
- Behavioral pattern ("defensive behavior", "scope creep")
- Component ("trainer agent", "validate_tool.py")
- Symptom keywords
```

**Decision point**:
- Found matching issue → Update it (Step 1.4A)
- No match after 3+ searches → Create new (Step 1.4B)

### Step 1.4A: Update Existing Issue

Add new instance to existing issue via `github-issue` skill:

```markdown
## New Instance: [Date]

**Context**: [Where occurred - which repo, what task]

**Violation**: [What happened]

**Evidence**:
```
[Quoted agent output]
```

**Pattern Confirmation**: [How this matches existing issue]

**Related**: [Links to experiments, commits if any]
```

### Step 1.4B: Create New Issue

Only after exhaustive search, create new issue via `github-issue` skill:

**Title format**: `[Component]: Brief violation description`

**Body structure**:
```markdown
## Violation Summary

**Agent**: [Which agent violated]
**Axiom/Rule**: _CORE.md Axiom #[number] [name]
**Behavioral Pattern**: [From behavioral-patterns.md]
**Date**: [When observed]
**Repository**: [Where occurred]

## What Happened

[Detailed description of agent behavior]

## What Should Have Happened

[Expected behavior per axioms/instructions]

## Evidence

```
[Quoted agent output, file diffs, conversation excerpts]
```

## Root Cause Analysis

[Why this happened - one level deep]
- Was instruction unclear?
- Was guardrail missing?
- Was this infrastructure issue?

## Enforcement Hierarchy Recommendation

Per trainer.md enforcement hierarchy:

**Q1: Can SCRIPTS prevent this?**
[Analysis]

**Q2: Can HOOKS enforce this?**
[Analysis]

**Q3: Can CONFIGURATION block this?**
[Analysis]

**Q4: Is this instruction-only?**
[Analysis]

**Recommendation**: [Scripts / Hooks / Config / Instructions] because [reason]

## Categorization

**Pattern**: [Behavioral pattern name]
**Severity**: [Low / Medium / High / Critical]
**Frequency**: [First occurrence / Recurring]

## Related Issues

[Search results showing similar patterns]

## Success Criteria

- [ ] Enforcement implemented at recommended layer
- [ ] Pattern no longer observed in testing
- [ ] [Specific measurable criteria]
```

**Labels**: `bug`, `agent-behavior`, `prompts`, `[pattern-name]`

### Step 1.5: Create Experiment Log (If Warranted)

For significant violations requiring framework changes:

**Check if in academicOps repo**:
```bash
pwd  # Should contain /academicOps or /bot
```

**If YES**, create experiment log:

**File**: `experiments/YYYY-MM-DD_[descriptive-name].md`

**Content**:
```markdown
# Experiment: [Name]

**Date**: YYYY-MM-DD
**Commit**: [pending]
**Issue**: #[NUMBER]
**Agent**: [which agent violated]

## Hypothesis

[If this enforcement is added, what behavior will change]

## Violation

[What happened that shouldn't have]

## Pattern

[Underlying behavioral pattern from behavioral-patterns.md]

## Implementation

[What will be changed - scripts, hooks, config, or instructions]

## Lessons

### For [Component] Enforcement

[Specific recommendation with code/instruction examples]

### For Instruction Clarity

[If instruction changes needed, what and why]

## Related Issues

[Links to GitHub issues]

## Modified Files

[List of files that will be modified]

## Results

[To be filled after testing]

## Outcome

[SUCCESS / FAILED / PARTIAL - to be filled after testing]
```

**Update INDEX**: Add to `experiments/INDEX.md` under "Active Experiments"

## Workflow 2: Framework Bug

**Objective**: Document infrastructure errors in scripts, hooks, configuration, or tooling.

### Step 2.1: Identify Error Type

Categorize the error:

- **Script failure**: Python script crashed or wrong output
- **Hook failure**: SessionStart, PreToolUse, etc. failed
- **Permission issue**: Tool blocked inappropriately (or allowed when shouldn't)
- **Environment issue**: Missing dependencies, wrong paths, env vars not set
- **Integration issue**: gh CLI, git, uv, pytest compatibility problems

### Step 2.2: Extract Technical Details

Gather complete error information:

```markdown
**Error Message**: [Full error text]
**Stack Trace**: [If available]
**Component**: [Which script/hook/tool]
**File Path**: [Exact location with line number]
**Environment**: [Repository, Python version, OS]
**Reproduction Steps**: [How to trigger error]
```

### Step 2.3: Search for Existing Issues

Use `github-issue` skill to search:
- Error message (exact phrase)
- Component name (script/hook filename)
- Symptom keywords
- Label filters (`infrastructure`, `bug`)

### Step 2.4: Create or Update Issue

**If new error**, create via `github-issue` skill:

**Title**: `[Component]: Error description`

**Body**:
```markdown
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

[Analysis - one level deep, not exhaustive]

## Impact

[Who is affected, what breaks]

## Proposed Fix

[Technical solution - code or config change]
```

**Labels**: `bug`, `infrastructure`

**If updating existing**, add new occurrence evidence via `github-issue` skill.

## Workflow 3: Experiment Logging

**Objective**: Document results of framework experiments (testing hooks, scripts, instruction changes).

### Step 3.1: Locate Experiment Log

Experiments live in `experiments/YYYY-MM-DD_name.md`.

**If experiment log exists**: Update it
**If new experiment**: Create it (use template from Workflow 1 Step 1.5)

### Step 3.2: Document Results

Update experiment log's Results and Outcome sections:

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

### Step 3.3: Update GitHub Issue

Link experiment results to related issue via `github-issue` skill:

```markdown
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
```

**If resolved**, close issue via `github-issue` skill with resolution details.

### Step 3.4: Update Experiment Index

Move completed experiments from "Active" to "Closed" in `experiments/INDEX.md`.

## Workflow 4: Architecture Drift

**Objective**: Keep ARCHITECTURE.md synchronized with actual system state.

### Step 4.1: Detect Drift

Compare ARCHITECTURE.md against reality:
- New components added (skills, agents, scripts, hooks)
- Workflows changed
- Directory structure evolved
- Design decisions made
- Open questions resolved

### Step 4.2: Research Current State

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

### Step 4.3: Update ARCHITECTURE.md

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
- ❌ "load instructions from..."

### Step 4.4: Create GitHub Issue for Major Drifts

If ARCHITECTURE.md significantly out of date, create issue via `github-issue` skill:

**Title**: `docs: ARCHITECTURE.md drift from reality`

**Body**:
```markdown
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
```

**Labels**: `documentation`

## Workflow 5: Progress Summary

**Objective**: Provide brief, actionable summary of issue status when asked.

### When Requested

User asks: "What's the status on [issue/area]?"

### Response Format

**Keep it BRIEF** (2-3 sentences + bullets):

```markdown
## [Issue/Area] Status

[Current state in 1-2 sentences]

**Blockers**:
- [Blocker 1]
- [Blocker 2]

**Outstanding Work**:
- [ ] Item 1
- [ ] Item 2

**Recent Progress**:
- [Update 1]
- [Update 2]

**Decision Points**:
- [Question needing decision]
```

**NO FLUFF**. Technical, concise, actionable.

## Privacy & Security

### Data Boundary Rules

**When working in academicOps repository**:
- ✅ Can write to local files (experiments/, ARCHITECTURE.md)
- ✅ Can write to GitHub issues
- ✅ Can reference all framework files

**When working in third-party repositories**:
- ❌ NEVER modify local files
- ✅ CAN write to nicsuzor/academicOps GitHub issues ONLY
- ❌ NEVER include sensitive data in GitHub
- ✅ Must sanitize examples before posting

### Sanitization Requirements

Before posting to GitHub from non-academicOps repos:

1. **Remove credentials**: API keys, tokens, passwords, connection strings
2. **Generalize paths**: `/home/nic/client-acme/` → `[project-directory]/`
3. **Remove proprietary info**: Client names, private data, business logic
4. **Keep framework errors**: Stack traces, agent behaviors, axiom violations are SAFE

**Tool**: Use `scripts/sanitize_github.py` (DataFog-based) if needed.

**Example**:
```markdown
# ❌ BAD - includes sensitive data
Error in /home/nic/client-acme/api_key.py: Invalid key sk_live_abc123

# ✅ GOOD - sanitized
Error in [project]/config.py: Invalid API key format
```

### Repository Verification

Check CLAUDE.md for repository information. For academicOps work, use `nicsuzor/academicOps` repository.

## Quality Standards

Every issue should have:
- [ ] Clear, specific title with component name
- [ ] Complete technical details
- [ ] Evidence (quotes, stack traces, file refs)
- [ ] Behavioral pattern identified (for violations)
- [ ] Enforcement hierarchy analysis (for violations)
- [ ] Severity/priority assessment
- [ ] Links to related issues
- [ ] Proposed solution direction

Every experiment log should have:
- [ ] Date, issue link, commit ref
- [ ] Clear hypothesis
- [ ] Documented changes
- [ ] Success criteria
- [ ] Results (after testing)
- [ ] Outcome decision
- [ ] Updated in INDEX.md

ARCHITECTURE.md updates should:
- [ ] Describe current state (not aspirational)
- [ ] Use descriptive voice (not imperative)
- [ ] Include concrete examples
- [ ] Reference actual files/paths
- [ ] Stay concise (link to details elsewhere)

## Anti-Patterns

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
- ✅ Exhaustive search via github-issue skill, then create or update

**Don't bypass enforcement hierarchy**:
- ❌ Adding instructions when script could prevent
- ✅ Apply decision tree, use strongest enforcement

## Skill Integration

This skill **calls** the `github-issue` skill for all GitHub operations:

**When to invoke github-issue**:
- Searching for existing issues
- Creating new issues
- Adding comments to issues
- Closing or reopening issues
- Verifying repository

**What aops-bug adds**:
- Framework-specific context (axioms, patterns, architecture)
- Behavioral pattern categorization
- Enforcement hierarchy analysis
- Experiment log management
- Architecture drift detection
- Privacy/sanitization rules

**Example workflow**:
```
User: "Agent violated fail-fast by using .get()"

aops-bug:
1. Identifies: Axiom #7 violation, Defensive Behavior pattern
2. Prepares issue content with framework context
3. Calls github-issue skill:
   - Search for "fail-fast" and "defensive behavior"
   - If not found: Create issue with prepared content
4. If in academicOps repo: Creates experiment log
5. Recommends enforcement layer (likely Scripts)
```

## Quick Reference

### Categorize Violation

1. Read `references/behavioral-patterns.md`
2. Match symptom to pattern
3. Identify violated axiom from `references/framework-architecture.md`
4. Document pattern, not just symptom

### Search for Issues

```
Invoke github-issue skill with:
- Axiom name
- Behavioral pattern
- Component name
- Symptom keywords
```

### Create Issue

```
Invoke github-issue skill with:
- Prepared title (include component)
- Prepared body (violation/bug structure)
- Labels: bug, agent-behavior/infrastructure, pattern
- Repository: nicsuzor/academicOps (always verify)
```

### Experiment Log

```
If in academicOps repo:
1. Create experiments/YYYY-MM-DD_name.md
2. Use template structure
3. Update experiments/INDEX.md
4. Link to GitHub issue
5. Test changes
6. Document results
```

### Architecture Update

```
1. Detect drift (compare ARCHITECTURE.md to codebase)
2. Verify current state (ls, cat, grep)
3. Edit ARCHITECTURE.md (descriptive voice)
4. If major drift: Create issue via github-issue skill
```

## Success Criteria

A well-tracked framework issue achieves:

- ✅ Categorized by behavioral pattern (not just symptom)
- ✅ Linked to core axiom violated
- ✅ Enforcement hierarchy analyzed
- ✅ No duplicate issues (exhaustive search)
- ✅ Complete technical details
- ✅ Experiment log if testing changes
- ✅ ARCHITECTURE.md updated if system changed
- ✅ Privacy boundaries respected
- ✅ Resolution verified before closing

## Resources

This skill includes comprehensive reference documentation:

### references/behavioral-patterns.md

Detailed categorization guide for agent violations:
- Core behavioral patterns (Defensive, Scope Creep, DRY, Authority, etc.)
- Specific axiom violations
- Error categorization
- Pattern lifecycle and evolution
- Issue granularity decisions

### references/framework-architecture.md

Framework-specific knowledge:
- Repository structure
- Core framework files (_CORE.md, trainer.md, ARCHITECTURE.md)
- Enforcement hierarchy details
- Component types (agents, skills, commands, scripts)
- Data boundaries and sanitization
- Common workflows
- Success metrics
