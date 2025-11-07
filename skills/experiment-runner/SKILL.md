---
name: experiment-runner
description: Manages complete experiment lifecycle for academicOps framework changes - from hypothesis design through execution to evaluation. Handles experiment log creation, Claude Code headless execution, failure analysis, and iterative refinement. Use when testing agent instructions, skills, hooks, or framework changes empirically.
license: Apache-2.0
permalink: aops/skills/experiment-runner
---

# Experiment Runner

You are responsible for empirically testing academicOps framework changes through rigorous experiments.

## Framework Context

@resources/AXIOMS.md @resources/INFRASTRUCTURE.md

## Overview

Manage the complete experiment lifecycle: design hypothesis → create experiment log → execute test → analyze results → iterate. This skill enforces experiment-driven development by making testing systematic and reproducible.

**Core principle**: We NEVER know if something will work until we test it. This skill makes testing rigorous and measurable.

## When to Use This Skill

Use experiment-runner when:

1. **Testing framework changes** - Modified agent instructions, skills, hooks, configs
2. **Validating improvements** - Want to prove change actually helps
3. **Measuring impact** - Need before/after metrics
4. **Reproducing issues** - Need controlled test environment
5. **Iterating on failures** - Previous experiment failed, need refinement

**Concrete triggers**:

- "Test if this instruction change improves agent behavior"
- "Run an experiment to validate the new skill works"
- "Measure if this refactoring actually helped"
- "Reproduce the bug the agent reported"
- "The experiment failed - iterate and try again"

## Experiment Lifecycle

### Phase 1: Design

**Purpose**: Define what you're testing and how to measure success.

**Required elements**:

1. **Hypothesis** - What you expect to happen (falsifiable)
   - ✅ GOOD: "Adding explicit ✅/❌ examples will improve agent pattern recognition from 40% to >80%"
   - ❌ BAD: "Examples might help" (not measurable)

2. **Success criteria** - Explicit, measurable outcomes
   - ✅ GOOD: "Agent removes all 5 process violations from ARCHITECTURE.md"
   - ❌ BAD: "Agent does better" (not measurable)

3. **Control baseline** - What's the current state?
   - Document current behavior/metrics before changes

4. **Single variable** - Change ONE thing per experiment
   - If testing multiple changes, run multiple experiments sequentially

**Checklist before proceeding**:

- [ ] Hypothesis is falsifiable (could be proven wrong)
- [ ] Success criteria are measurable (numbers, specific outcomes)
- [ ] Baseline documented (what happens now)
- [ ] Single variable identified (not changing multiple things)

### Phase 2: Create Experiment Log

**Purpose**: Document experiment for reproducibility and future learning.

**File location**: `experiments/YYYY-MM-DD_descriptive-name.md`

**Template**:

```markdown
# Experiment: [Descriptive Title]

## Metadata

- Date: YYYY-MM-DD
- Issue: [GitHub issue number if applicable]
- Commit: [hash of changes being tested]
- Model: [claude-sonnet-4-5 / gemini-2.0-flash / etc]

## Hypothesis

[What you expect to happen and why]

## Context

[Why this experiment is needed - what problem/question prompted it]

## Changes Made

[Specific modifications to test]

## Success Criteria

[Measurable outcomes - be specific]

- [ ] Criterion 1
- [ ] Criterion 2

## Test Procedure

[Exact steps to reproduce]

1. [Step 1]
2. [Step 2]

## Expected Challenges

[What might go wrong or confuse the agent]

## Results

[To be filled after execution]

## Outcome

[Success/Failure/Partial]

## Analysis

[What worked, what didn't, why]

## Next Steps

[Based on outcome]
```

**Common mistakes to avoid**:

❌ **Vague success criteria**:

- "Agent performs better" → Not measurable
- ✅ "Agent removes 5/5 violations (100% success rate)"

❌ **Missing baseline**:

- No "before" state documented
- ✅ "Current: Agent removes 2/5 violations (40% success)"

❌ **Multiple variables**:

- Changed instructions AND file structure AND added examples
- ✅ "Only added ✅/❌ examples, all else unchanged"

### Phase 3: Execute Test

**Purpose**: Run the experiment in controlled environment and capture results.

**Execution methods**:

#### Method A: Headless Claude Code (Automated)

Use for testing agent behavior with specific prompts:

```bash
# Basic execution
claude --headless --prompt "your test prompt here"

# With session log capture
claude --headless --prompt "use the aops-trainer skill to update ARCHITECTURE.md" > session-log.txt 2>&1

# With specific working directory
cd /path/to/test/repo && claude --headless --prompt "test prompt"
```

**Headless execution checklist**:

- [ ] Test repo is in clean state (git status clean)
- [ ] Working directory is correct ($ACADEMICOPS or test location)
- [ ] Prompt is exact (copy from experiment log)
- [ ] Session log captured for analysis
- [ ] Timeout set if needed (default: 10 minutes)

**Example headless test**:

```bash
# Setup
cd $ACADEMICOPS
git checkout experiment-branch
git status  # Verify clean

# Execute
claude --headless --prompt "use the aops-trainer skill to update ARCHITECTURE.md" > experiments/session-logs/2025-11-07-attempt-2.txt 2>&1

# Capture state
git diff > experiments/diffs/2025-11-07-attempt-2.diff
git status > experiments/status/2025-11-07-attempt-2.txt
```

#### Method B: Manual Interactive Testing

Use for complex workflows or debugging:

1. Open fresh Claude Code session
2. Execute exact prompt from experiment log
3. Observe behavior and capture:
   - What tools agent used
   - What decisions agent made
   - Where agent succeeded/failed
4. Save session log for analysis

**Interactive testing checklist**:

- [ ] Fresh session (no prior context)
- [ ] Exact prompt from experiment log
- [ ] Session log saved
- [ ] Screenshots/notes of key decisions

#### Method C: Multiple Runs (Statistical Validation)

Use when testing non-deterministic behavior:

```bash
for i in {1..5}; do
  git reset --hard baseline-commit
  claude --headless --prompt "test prompt" > run-$i.txt 2>&1
  git diff > diff-$i.txt
done

# Analyze variance across runs
```

**When to use multiple runs**:

- Testing instruction clarity (does it work consistently?)
- Measuring success rate (3/5 runs succeed vs 5/5)
- Validating non-deterministic behavior

### Phase 4: Analyze Results

**Purpose**: Determine if hypothesis was validated and understand why/why not.

**Analysis workflow**:

1. **Compare to success criteria**:
   ```
   Success criteria: Agent removes 5/5 violations
   Actual result: Agent removed 5/5 violations
   Outcome: SUCCESS ✅
   ```

2. **Measure improvement**:
   - Before: 40% success rate (2/5 violations)
   - After: 100% success rate (5/5 violations)
   - Improvement: +60 percentage points

3. **Identify what worked**:
   - Which specific changes correlated with improvement?
   - What did agent do differently?
   - Example: "Agent used ✅/❌ examples to identify patterns"

4. **Identify what didn't work**:
   - Where did agent still fail or struggle?
   - What confusion remains?
   - Example: "Agent missed X because no explicit guidance on Y"

5. **Extract learnings**:
   - General principles (apply to future work)
   - Specific patterns (document in BEST-PRACTICES.md)
   - Anti-patterns to avoid

**Analysis template**:

```markdown
## Analysis

**Success criteria assessment**:

- [Criterion 1]: ✅/❌ [Details]
- [Criterion 2]: ✅/❌ [Details]

**Measurements**:

- Before: [Baseline metric]
- After: [Result metric]
- Change: [Delta]

**What worked**:

- [Specific element 1] → [Observed positive effect]
- [Specific element 2] → [Observed positive effect]

**What didn't work**:

- [Specific element 1] → [Observed negative effect]
- [Missing element] → [Consequence of absence]

**Key insights**:

1. [General principle learned]
2. [Specific pattern to document]
3. [Anti-pattern to avoid]
```

### Phase 5: Decide and Iterate

**Purpose**: Determine next action based on outcome.

**Decision tree**:

```
SUCCESS (met all success criteria)
├─→ Keep changes
├─→ Update experiment log with "SUCCESS" outcome
├─→ Commit changes with experiment reference
├─→ Close related GitHub issue if applicable
└─→ Document learnings in BEST-PRACTICES.md if generalizable

PARTIAL (met some criteria, missed others)
├─→ Analyze which criteria failed
├─→ Design targeted improvement for failures only
├─→ Create new experiment (Iteration 2) testing refinement
└─→ Keep successes, iterate on failures

FAILURE (met few/no criteria)
├─→ Analyze root cause of failure
├─→ Question hypothesis - was it wrong?
├─→ Design different approach
├─→ Create new experiment with alternative strategy
└─→ Document why approach failed (anti-pattern)
```

**Iteration workflow** (for PARTIAL or FAILURE):

1. **Update experiment log**:
   - Mark outcome (PARTIAL/FAILURE)
   - Document analysis
   - Identify specific gap

2. **Design iteration**:
   - What one thing would address the gap?
   - New hypothesis for iteration
   - Updated success criteria

3. **Create iteration experiment**:
   - Same file, new section: "## Iteration 2"
   - Reference what changed from Iteration 1
   - New test procedure

4. **Execute iteration**:
   - Run test with refinements
   - Compare to both baseline AND previous iteration

**Example iteration**:

```markdown
## Iteration 1: PARTIAL (2/5 criteria met)

[Results and analysis]

**Gap identified**: Agent missed checklists as process

## Iteration 2: Design

**Refinement**: Added explicit "Remove ALL: checklists" to guidance

**Hypothesis**: Explicit list will enable agent to identify checklists

**Success criteria**:

- [ ] Agent removes checklists (missed in Iteration 1)
- [ ] Agent maintains previous successes (2/5 from Iteration 1)

## Iteration 2: Results

[Execute and analyze]
```

## Working with GitHub Issues

**When experiments relate to issues**:

1. **Reference issue in experiment metadata**:
   ```markdown
   ## Metadata

   - Issue: #123
   ```

2. **Comment progress on issue**:
   ```bash
   gh issue comment 123 --body "$(cat <<'EOF'
   ## Experiment Progress

   Created experiment: experiments/2025-11-07_test-name.md

   **Hypothesis**: [Brief summary]
   **Status**: In progress / Results pending
   EOF
   )"
   ```

3. **Update issue with results**:
   ```bash
   gh issue comment 123 --body "$(cat <<'EOF'
   ## Experiment Results

   **Outcome**: SUCCESS ✅ / PARTIAL / FAILURE

   **Key findings**:
   - [Finding 1]
   - [Finding 2]

   **Next steps**: [Keep changes / Iterate / Different approach]

   See experiments/2025-11-07_test-name.md for full analysis
   EOF
   )"
   ```

4. **Close issue if SUCCESS**:
   ```bash
   gh issue close 123 --comment "Experiment validated solution. Changes committed in [commit-hash]"
   ```

## Headless Claude Code Reference

**Common options**:

```bash
# Basic headless execution
claude --headless --prompt "your prompt"

# Specify model
claude --headless --model sonnet --prompt "your prompt"
claude --headless --model opus --prompt "your prompt"

# Set timeout (in seconds)
claude --headless --timeout 600 --prompt "your prompt"

# Set working directory
cd /path/to/repo && claude --headless --prompt "your prompt"

# Capture full session log
claude --headless --prompt "your prompt" > session.txt 2>&1

# Non-interactive (fail if user input needed)
claude --headless --non-interactive --prompt "your prompt"
```

**Analyzing headless output**:

```bash
# Check if agent loaded specific skill
grep -i "skill-name" session.txt

# See what tools agent used
grep "Tool:" session.txt

# Extract agent reasoning
grep -A 5 "thinking" session.txt

# Check for errors
grep -i "error\|fail" session.txt

# See git operations
grep "git " session.txt
```

## Common Experiment Patterns

### Pattern 1: Testing Instruction Changes

**Scenario**: Modified agent instructions, want to verify improvement.

**Workflow**:

1. Document baseline (run test with old instructions)
2. Commit instruction changes to experiment branch
3. Run headless test with same prompt
4. Compare outcomes (git diff, success criteria)
5. Decide: keep/revert/iterate

**Example**:

```bash
# Baseline
git checkout main
claude --headless --prompt "test prompt" > baseline.txt
git diff > baseline.diff

# Test change
git checkout experiment-branch
claude --headless --prompt "test prompt" > experiment.txt
git diff > experiment.diff

# Compare
diff baseline.diff experiment.diff
```

### Pattern 2: Testing Skill Effectiveness

**Scenario**: Created new skill, want to verify it works.

**Workflow**:

1. Install skill to ~/.claude/skills/
2. Design test prompt that should invoke skill
3. Run headless test
4. Verify skill was invoked (grep session log)
5. Verify skill achieved intended outcome

**Success criteria examples**:

- [ ] Agent invoked skill (appears in session log)
- [ ] Skill completed without errors
- [ ] Agent followed skill's workflow
- [ ] Agent achieved intended outcome

### Pattern 3: A/B Testing Multiple Approaches

**Scenario**: Two different solutions, want to compare.

**Workflow**:

1. Create experiment log with two approaches
2. Run Approach A test → measure results
3. Reset to clean state
4. Run Approach B test → measure results
5. Compare metrics, choose winner

**Example**:

```bash
# Approach A
git checkout approach-a-branch
claude --headless --prompt "test prompt" > approach-a.txt
# Record metrics: time, success rate, line changes, etc.

# Reset
git checkout main

# Approach B
git checkout approach-b-branch
claude --headless --prompt "test prompt" > approach-b.txt
# Record same metrics

# Compare
# Which succeeded better? Faster? Cleaner?
```

## Validation and Quality Checks

**Before executing experiment**:

- [ ] Hypothesis is specific and falsifiable
- [ ] Success criteria are measurable
- [ ] Baseline documented
- [ ] Single variable changed
- [ ] Test procedure is reproducible
- [ ] Experiment log created

**During execution**:

- [ ] Session log captured
- [ ] Working directory correct
- [ ] Clean state verified (git status)
- [ ] Errors noted

**After execution**:

- [ ] Results documented in experiment log
- [ ] Outcome marked (SUCCESS/PARTIAL/FAILURE)
- [ ] Analysis completed (what worked/didn't work)
- [ ] Next steps determined
- [ ] Learnings extracted
- [ ] GitHub issue updated if applicable

## Critical Rules

**NEVER**:

- Claim something works without testing
- Run experiments without documented hypothesis
- Change multiple variables simultaneously
- Skip baseline measurement
- Forget to capture session logs
- Fail to analyze failures (failed experiments teach too!)
- Run experiments in dirty git state (uncommitted changes)

**ALWAYS**:

- Document hypothesis before testing
- Define measurable success criteria
- Test in clean environment
- Capture full session logs
- Analyze results even if experiment fails
- Iterate on partial success
- Update experiment log with outcomes
- Extract generalizable learnings

## Quick Reference

**Experiment lifecycle**:

1. Design → Hypothesis + success criteria
2. Create log → experiments/YYYY-MM-DD_name.md
3. Execute → Headless/manual test, capture session log
4. Analyze → Compare to criteria, measure improvement
5. Decide → Keep/iterate/different approach

**Headless test**:

```bash
cd $ACADEMICOPS
git status  # Verify clean
claude --headless --prompt "exact test prompt" > session.txt 2>&1
git diff > result.diff
```

**Analysis template**:

- Before/After metrics
- What worked → Why
- What didn't → Why
- Key insights → General principles

**Decision tree**: SUCCESS → Keep | PARTIAL → Iterate | FAILURE → New approach
