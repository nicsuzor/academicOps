---
name: aops
description: Maintain and optimize the aOps automation framework. Track bugs, agent
  violations, and improvements. Enforce anti-bloat principles and experiment-driven
  development. Has authority to modify any file in ${AOPS}. Use EVERY time improvements
  to the automation framework are required. Can be invoked from projects using the
  framework, but should ONLY EVER modify framework files, NOT user data or project files.
permalink: aops/skills/aops/skill
---

# aOps Framework Maintenance

You are responsible for maintaining the aOps automation framework in `${AOPS}`.

## Scope and Authority

**What this skill does**:

- Track and fix bugs in ${AOPS} (hooks, scripts, skills, config)
- Document agent violations and behavioral patterns
- Optimize framework performance and reduce bloat
- Maintain framework documentation
- Manage experiments and improvements
- Enforce core axioms and principles

**Authority**: Full read/write access to all files in `${AOPS}`.

**What this skill does NOT do**:

- Work on user projects or data (those belong in `${ACA}`)
- General GitHub issue management (use github-issue skill)
- Project-specific debugging

## Core Principles

Follow all axioms from @docs/AXIOMS.md in all framework work.

## Reference Hygiene

@docs/chunks/REFERENCE-HYGIENE.md

**Critical**: Detect and remove "Reference + Summary" violations where content is @referenced then repeated/summarized. This is a DRY violation that wastes tokens and creates drift.

**Red flags to detect**:
- @reference followed by numbered/bulleted list of same content
- Words like "key", "important", "main" near @reference (arbitrary selection)
- Content after @reference that repeats concepts from referenced file
- Same file @referenced multiple times in one skill
- Hook-loaded content also @referenced

**When reviewing documentation**: Apply Reference Hygiene checklist from above. Remove all summaries after @references.

## Behavioral Patterns

Use @docs/chunks/BEHAVIORAL-PATTERNS.md to categorize agent violations by underlying pattern, not surface symptom.

## Working on Skills

@docs/resources/claude/skills_guide.md

**MANDATORY**: Read the complete guide above before creating, modifying, or reviewing any skill.

Apply all principles when maintaining skills in `${AOPS}/skills/`.

## When to Use This Skill

**Use aops when**:

1. **Agent violates core axioms** - Document and fix
2. **Framework bug encountered** - Scripts, hooks, infrastructure failing
3. **Experiment needs tracking** - Testing framework changes
4. **Documentation drift** - Files don't match reality
5. **Bloat detected** - Files growing unnecessarily
6. **Optimization needed** - Framework performance issues

**Concrete triggers**:

- "Agent created _new file instead of editing"
- "Hook validate_tool.py failed with error"
- "Document experiment results for new pre-commit check"
- "SKILL.md exceeds 500 lines, needs chunking"
- "This instruction is duplicated in 3 files"
- "Create new skill" or "Modify existing skill"

## Framework Structure

Per `${AOPS}/paths.toml`:

```
${AOPS}/
├── skills/          # Claude Code skills
├── hooks/           # Lifecycle hooks
├── scripts/         # Utility scripts
├── config/          # Configuration (settings.json, mcp.json)
├── docs/
│   ├── chunks/      # Atomic reusable chunks
│   ├── _CORE.md     # Core instructions
│   └── _AXIOMS.md   # Foundational principles
├── resources/       # External references
└── experiments/     # Experiment tracking
```

**Installation**: Symlinks in `~/.claude/` → `${AOPS}/`

## Workflows

### Workflow 1: Agent Violation

**When**: Agent violates core axioms or instructions.

**Steps**:

1. **Identify violation**
   - What happened vs what should have happened
   - Which axiom violated (reference @docs/AXIOMS.md)
   - Evidence (quoted output)

2. **Categorize pattern**
   - Use @docs/chunks/BEHAVIORAL-PATTERNS.md
   - Identify: Defensive, Scope Creep, DRY, Authority, etc.

3. **Search existing issues**
   - Search by axiom name, pattern, component
   - Decision: Update existing or create new

4. **Document**
   - Update existing issue with new instance
   - OR create new issue if no match after 3+ searches

5. **Determine enforcement**
   - Can SCRIPTS prevent this? (highest priority)
   - Can HOOKS enforce this?
   - Can CONFIG block this?
   - Is this instructions-only? (lowest priority)

6. **Create experiment log** (if warranted)
   - Location: `${AOPS}/experiments/YYYY-MM-DD_name.md`
   - Track hypothesis, implementation, results

**Title format**: `[Component]: Brief violation description`

**Labels**: `bug`, `agent-behavior`, `[pattern-name]`

### Workflow 2: Framework Bug

**When**: Scripts, hooks, or infrastructure failing.

**Steps**:

1. **Reproduce and verify**
   - Read error message carefully
   - Check actual state (don't assume)
   - Verify bug exists

2. **Categorize error type**
   - Environment error (missing deps, wrong paths)
   - Integration error (tool compatibility)
   - Logic bug (edge case not handled)
   - Permission issue

3. **Fix at appropriate layer**
   - Scripts: Logic bugs, validation
   - Hooks: Enforcement mechanisms
   - Config: Permissions, paths
   - Instructions: Behavioral guidance

4. **Test fix**
   - Run actual test case
   - Verify fix works
   - Check for regressions

5. **Document in experiment log** (if significant)

### Workflow 3: Bloat Reduction

**When**: Files growing unnecessarily, duplication detected.

**Steps**:

1. **Identify bloat**
   - File >500 lines (skills)
   - File >300 lines (docs)
   - Duplicated content across files
   - Instructions that should be enforcement
   - **Reference + Summary violations** (see @docs/chunks/REFERENCE-HYGIENE.md)

2. **Check reference hygiene**
   - Search for @references in file
   - Check if content after @reference repeats/summarizes referenced content
   - Look for "key", "important", "main" near @references (arbitrary selection)
   - Verify referenced file not also loaded by SessionStart hook
   - Remove all summaries, keep only WHEN/HOW guidance

3. **Extract to chunks**
   - Create topic-focused file in `docs/chunks/`
   - Replace original with `@reference`
   - Verify all references work
   - **Don't add summaries after @reference**

4. **Move up enforcement hierarchy**
   - Can this be a script instead of instruction?
   - Can this be a hook instead of repeated text?
   - Can this be config instead of guidance?

5. **Validate improvement**
   - Run tests to ensure nothing broke
   - Check file sizes reduced
   - Verify DRY maintained
   - Verify no Reference + Summary violations remain

### Workflow 4: Optimization

**When**: Agent performance issues, inefficiencies detected.

**Steps**:

1. **Analyze problem**
   - What's slow/inefficient?
   - Where does it occur?
   - What's the pattern?

2. **Design intervention**
   - Surgical change, not broad rewrites
   - Test hypothesis first
   - Consider enforcement hierarchy

3. **Create experiment**
   - Document hypothesis
   - Implement change
   - Measure results

4. **Validate or revert**
   - If improved: Keep, document
   - If no change: Revert, try different approach
   - Never leave untested changes

## Enforcement Hierarchy

**Priority order** (enforce at highest possible level):

1. **SCRIPTS** - Automated validation (e.g., check_fail_fast.py)
   - Catches violations automatically
   - Runs in CI/CD
   - Can block commits

2. **HOOKS** - Runtime enforcement (e.g., validate_tool.py)
   - Prevents violations during execution
   - Provides immediate feedback
   - Part of Claude Code lifecycle

3. **CONFIG** - Permission-based blocking (settings.json)
   - Limits what agents can do
   - Simple on/off switches
   - Harder to bypass

4. **INSTRUCTIONS** - Guidance in SKILL.md, axioms (lowest priority)
   - Relies on agent following directions
   - Easy to ignore or misinterpret
   - Last resort only

**Decision tree**:

```
Q1: Can SCRIPTS catch this automatically? → YES: Write script
    ↓ NO
Q2: Can HOOKS enforce at runtime? → YES: Add hook
    ↓ NO
Q3: Can CONFIG block this? → YES: Update settings
    ↓ NO
Q4: Must be instructions → Write clear, specific guidance
```

## Anti-Bloat Protocol

**Hard limits**:

- Skills: 500 lines max
- Docs/chunks: 300 lines max
- Approaching limit? Extract to chunks BEFORE adding content

**Chunking strategy**:

1. **Topic-based splitting** - Extract sections to separate files
2. **Reference over duplicate** - One source, many `@references`
3. **Progressive detail** - Index with summaries, chunks with details

**Example**:

```
Before (700 lines):
  BEST-PRACTICES.md - Everything in one file

After (7 focused files):
  BEST-PRACTICES.md (index, 137 lines)
  CONTEXT-ENGINEERING.md (120 lines)
  SKILL-DESIGN.md (80 lines)
  ... etc
```

## Experiment Tracking

**When to create experiment**:

- Testing new enforcement mechanism
- Trying optimization approach
- Validating framework change
- Investigating recurring pattern

**Location**: `${AOPS}/experiments/YYYY-MM-DD_descriptive-name.md`

**Format**:

```markdown
# Experiment: [Name]

**Date**: YYYY-MM-DD
**Commit**: [hash or pending]
**Issue**: #[number]

## Hypothesis

[What you expect to happen if this change is made]

## Implementation

[What was changed - scripts, hooks, config, or instructions]

## Results

[What actually happened - with evidence]

## Lessons

[What we learned - what worked, what didn't, why]

## Decision

- [X] Keep change (worked as expected)
- [ ] Revert (didn't work)
- [ ] Iterate (partial success, needs refinement)
```

## GitHub Issue Management

**Issue format for violations**:

```markdown
## Violation Summary

**Agent**: [Which agent]
**Axiom/Rule**: [Reference to docs/AXIOMS.md]
**Pattern**: [From BEHAVIORAL-PATTERNS.md]
**Date**: [When observed]

## What Happened

[Detailed description]

## What Should Have Happened

[Expected behavior]

## Evidence

[Quoted output, file diffs, conversation excerpts]

## Enforcement Recommendation

Per enforcement hierarchy:
- Scripts: [Can prevent? How?]
- Hooks: [Can enforce? How?]
- Config: [Can block? How?]
- Instructions: [Last resort only]

**Recommendation**: [Scripts/Hooks/Config/Instructions] because [reason]

## Success Criteria

- [ ] Enforcement implemented
- [ ] Pattern no longer observed
- [ ] [Specific measurable criteria]
```

## Content Placement

**Decision tree for where content belongs**:

1. **Universal principle?** → `docs/AXIOMS.md` or `docs/chunks/`
2. **Behavioral pattern?** → `docs/chunks/BEHAVIORAL-PATTERNS.md`
3. **Step-by-step workflow?** → Skill (this file or other skills)
4. **Framework structure?** → `paths.toml` or `README.md`
5. **Experiment tracking?** → `experiments/` directory
6. **External reference?** → `resources/` directory

**Avoid**:

- Duplicating axioms across files
- Mixing principles with processes
- Temporal markers (NEW, line counts)
- Process checklists in structure docs
- Reference + Summary violations (@reference followed by summary of referenced content)

## Quick Reference

**Common operations**:

```bash
# Check framework structure
cat ${AOPS}/paths.toml

# Find bloat
find ${AOPS} -name "*.md" -exec wc -l {} \; | sort -rn

# Run validation
uv run python ${AOPS}/scripts/validate.py

# Create experiment log
touch ${AOPS}/experiments/$(date +%Y-%m-%d)_name.md
```

**Common patterns**:

- Agent violation → Categorize, search, document, enforce
- Framework bug → Reproduce, fix, test, document
- Bloat detected → Check reference hygiene, extract to chunks, reference (don't summarize)
- Reference + Summary → Remove summary, trust @reference mechanism
- Optimization → Experiment, measure, keep or revert

**Key files**:

- `${AOPS}/paths.toml` - Authoritative structure reference
- `${AOPS}/docs/AXIOMS.md` - Core principles
- `${AOPS}/docs/chunks/BEHAVIORAL-PATTERNS.md` - Violation patterns
- `${AOPS}/docs/chunks/REFERENCE-HYGIENE.md` - DRY enforcement for @references
- `${AOPS}/docs/resources/claude/skills_guide.md` - Mandatory for skill work
- `${AOPS}/README.md` - User-facing overview
