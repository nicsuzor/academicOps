---
name: skill-discovery
description: This skill should be used when scanning repositories to identify workflow migration candidates - procedural knowledge in agent definitions and documentation that could become portable, reusable skills. It analyzes files, scores migration opportunities by priority, detects duplication across files, and produces a prioritized list of skill candidates. Use this before skill-migration to discover what should be migrated.
---

# Skill Discovery

## Overview

Scan repositories to identify and prioritize workflow migration candidates. This skill analyzes agent definitions and documentation to find procedural knowledge that should become atomic, portable skills, then ranks candidates by migration value.

## When to Use This Skill

Use skill-discovery when:

1. **Starting a migration project** - "What in my repository should become skills?"
2. **Auditing documentation** - "Find all the workflows embedded in my agents"
3. **Identifying duplication** - "Which procedures appear in multiple files?"
4. **Planning cleanup** - "What's the highest priority content to migrate?"
5. **Building skill library** - "Map out all potential skills in my codebase"

**Concrete trigger examples**:
- "Scan my repository for skill migration candidates"
- "What workflows in my agents should become skills?"
- "Find duplicated procedures across my documentation"
- "Audit my agent files to plan skill migrations"
- "Show me the highest priority workflows to extract"

**This skill is the discovery phase** - use it first, then use `skill-migration` to actually migrate the identified candidates.

## Discovery Workflow

Follow this workflow to comprehensively discover and prioritize skill candidates.

### Step 1: Scan Repository Files

**Objective**: Identify all files that might contain workflow content.

**Process**:

1. **Find agent definition files**:
   - Use Glob to find `agents/*.md`
   - Use Glob to find `.claude/agents.backup/*.md` (deprecated agents)
   - Note file paths for analysis

2. **Find documentation files**:
   - Use Glob to find `docs/**/*.md` (all documentation)
   - Use Glob to find `docs/_UNUSED/**/*.md` (deprecated docs)
   - Use Glob to find project-specific `docs/agents/*.md`
   - Note file paths for analysis

3. **Find slash command definitions** (potential skill candidates):
   - Use Glob to find `.claude/commands/*.md`
   - These are often good skill candidates
   - Note file paths for analysis

4. **Create file inventory**:
   - List all files found
   - Categorize by type (agent, doc, command)
   - Track repository locations

**Output**: Complete list of files to analyze.

**Example**:
```
Files to analyze:
  Agents (6 files):
    - agents/REVIEW.md
    - agents/SUPERVISOR.md
    - agents/TEST-CLEANER.md
    - agents/STRATEGIST.md
    - agents/TRACKER.md
    - agents/trainer.md

  Documentation (8 files):
    - docs/git-workflow.md
    - docs/hooks_guide.md
    - docs/_UNUSED/mentor.md
    - ...

  Commands (3 files):
    - .claude/commands/ttd.md
    - .claude/commands/dev.md
    - .claude/commands/ops.md
```

### Step 2: Extract Workflow Content

**Objective**: Use automated analysis to extract workflow sections from each file.

**Process**:

1. **Run extract_workflow.py on each file**:
   ```bash
   # Use the skill-migration helper script
   uv run python .claude/skill-migration/scripts/extract_workflow.py <file> --output temp_<file>.json
   ```

2. **Collect extraction results**:
   - Numbered lists (procedural steps)
   - Workflow sections (headers with workflow keywords)
   - Code examples and templates
   - Confidence scores

3. **Aggregate results** across all files:
   - Build comprehensive dataset
   - Track which files contain workflows
   - Note confidence scores

**Use the scan_repository.py helper script** to automate this:
```bash
uv run python .claude/skill-discovery/scripts/scan_repository.py
```

This script orchestrates extraction across all files and aggregates results.

### Step 3: Detect Duplication

**Objective**: Find workflows that appear in multiple files (high-value migration candidates).

**Process**:

1. **Compare workflow content** across files:
   - Look for similar numbered lists
   - Find matching section headers
   - Identify repeated code examples
   - Calculate similarity scores

2. **Group duplicates**:
   - Cluster similar workflows together
   - Identify the authoritative/best version
   - Count how many files have duplicate content

3. **Calculate duplication score**:
   - More files = higher duplication score
   - Similar content = higher confidence in duplication

**Use the detect_duplicates.py helper script**:
```bash
uv run python .claude/skill-discovery/scripts/detect_duplicates.py --input scan_results.json --output duplicates.json
```

**High-value finding**: Workflows duplicated across 3+ files are prime candidates for extraction.

### Step 4: Score Migration Priority

**Objective**: Rank candidates by migration value to guide prioritization.

**Scoring Criteria**:

1. **Duplication Score** (0-40 points):
   - 0 files: 0 points
   - 2 files: 20 points
   - 3+ files: 40 points
   - Rationale: Duplicated content violates DRY, highest ROI to extract

2. **Workflow Complexity** (0-30 points):
   - Simple (1-3 steps): 10 points
   - Medium (4-10 steps): 20 points
   - Complex (10+ steps): 30 points
   - Rationale: Complex workflows benefit most from having single authoritative source

3. **Portability Value** (0-20 points):
   - Repository-specific: 5 points
   - Somewhat portable: 10 points
   - Universal workflow: 20 points
   - Rationale: Portable workflows can be reused across projects

4. **Code/Template Content** (0-10 points):
   - No code examples: 0 points
   - Has code examples: 5 points
   - Has reusable scripts/templates: 10 points
   - Rationale: Code benefits from deterministic scripts in skills

**Total Score**: 0-100 points

**Priority Levels**:
- **Critical (80-100)**: Migrate immediately - high duplication, complex, portable
- **High (60-79)**: Migrate soon - substantial value
- **Medium (40-59)**: Migrate when convenient - moderate value
- **Low (0-39)**: Migrate if time permits - low value or already clean

**Use the score_candidates.py helper script**:
```bash
uv run python .claude/skill-discovery/scripts/score_candidates.py --input scan_results.json --duplicates duplicates.json --output scored_candidates.json
```

### Step 5: Generate Discovery Report

**Objective**: Produce human-readable prioritized list of skill candidates.

**Report Structure**:

```markdown
# Skill Discovery Report

**Repository**: <repo-name>
**Scan Date**: <date>
**Files Analyzed**: <count>
**Candidates Found**: <count>

## Summary Statistics

- Critical Priority: <count> candidates
- High Priority: <count> candidates
- Medium Priority: <count> candidates
- Low Priority: <count> candidates

## Critical Priority Candidates

### 1. git-commit (Score: 95/100)

**Why Migrate**:
- Appears in 3 files (REVIEW.md, git-workflow.md, dev.md)
- Complex 8-step workflow
- Universal/portable
- Contains code examples

**Source Files**:
- agents/REVIEW.md (lines 120-180)
- docs/git-workflow.md (lines 45-95)
- .claude/commands/dev.md (lines 30-70)

**Suggested Skill Structure**:
- Type: Workflow-based
- Resources needed: references/commit-message-guide.md
- Estimated effort: Medium

**Next Steps**:
1. Use skill-migration to create git-commit skill
2. Clean up all 3 source files
3. Migrate duplicated content

---

### 2. test-writing-patterns (Score: 88/100)

[Similar detailed breakdown]

## High Priority Candidates

[Continue for each priority level]

## Migration Roadmap

**Recommended Order**:
1. git-commit (affects 3 files, highest ROI)
2. test-writing-patterns (affects 2 files, complex workflow)
3. validation-rules (affects 2 files, highly reusable)
...

**Estimated Total Effort**: <hours/days>
**Cleanup Impact**: <number> files will be simplified
```

**Process**:

1. **Load scored candidates** from JSON
2. **Sort by priority score** (descending)
3. **Group by priority level**
4. **Generate detailed report** for each candidate
5. **Create migration roadmap** with recommended order
6. **Output to markdown file** for review

**Use the generate_report.py helper script**:
```bash
uv run python .claude/skill-discovery/scripts/generate_report.py --input scored_candidates.json --output DISCOVERY_REPORT.md
```

### Step 6: Review and Refine

**Objective**: Human review of automated findings to validate priorities.

**Process**:

1. **Present report to user**:
   - Show full discovery report
   - Highlight critical candidates
   - Explain scoring rationale

2. **Ask for feedback**:
   - "Do these priorities make sense?"
   - "Any candidates we missed or shouldn't migrate?"
   - "Any you want to prioritize differently?"

3. **Refine based on feedback**:
   - Adjust scores if needed
   - Add/remove candidates
   - Reorder priorities

4. **Finalize migration list**:
   - Create final prioritized list
   - Ready to hand off to skill-migration

### Step 7: Hand Off to Migration

**Objective**: Provide clear next steps for using skill-migration on identified candidates.

**Output**:

```
Ready to migrate! Here are your next steps:

For each candidate (starting with Critical priority):

1. Invoke skill-migration:
   "Use skill-migration to create a <skill-name> skill from <source-files>"

2. Example for highest priority:
   "Use skill-migration to create a git-commit skill from agents/REVIEW.md,
   docs/git-workflow.md, and .claude/commands/dev.md"

3. Continue down the priority list until satisfied

The discovery phase is complete. Use skill-migration to execute the migrations.
```

## Helper Scripts

This skill includes helper scripts to automate the discovery workflow:

### scripts/scan_repository.py

Orchestrates full repository scan using extract_workflow.py:
- Finds all agent and documentation files
- Runs extraction on each file
- Aggregates results into single dataset
- Outputs consolidated JSON

Usage:
```bash
uv run python .claude/skill-discovery/scripts/scan_repository.py --output scan_results.json
```

### scripts/detect_duplicates.py

Analyzes scan results to find duplicated workflows:
- Compares content across files
- Calculates similarity scores
- Groups duplicate workflows
- Outputs duplication report

Usage:
```bash
uv run python .claude/skill-discovery/scripts/detect_duplicates.py --input scan_results.json --output duplicates.json
```

### scripts/score_candidates.py

Scores each workflow candidate using priority criteria:
- Applies scoring rubric (duplication, complexity, portability, code)
- Calculates total scores (0-100)
- Assigns priority levels (Critical/High/Medium/Low)
- Outputs scored candidates

Usage:
```bash
uv run python .claude/skill-discovery/scripts/score_candidates.py --input scan_results.json --duplicates duplicates.json --output scored_candidates.json
```

### scripts/generate_report.py

Creates human-readable discovery report:
- Loads scored candidates
- Sorts by priority
- Generates detailed markdown report
- Includes migration roadmap

Usage:
```bash
uv run python .claude/skill-discovery/scripts/generate_report.py --input scored_candidates.json --output DISCOVERY_REPORT.md
```

## Quick Reference

**Full discovery workflow (automated)**:

```bash
# 1. Scan repository
uv run python .claude/skill-discovery/scripts/scan_repository.py --output scan_results.json

# 2. Detect duplicates
uv run python .claude/skill-discovery/scripts/detect_duplicates.py --input scan_results.json --output duplicates.json

# 3. Score candidates
uv run python .claude/skill-discovery/scripts/score_candidates.py --input scan_results.json --duplicates duplicates.json --output scored_candidates.json

# 4. Generate report
uv run python .claude/skill-discovery/scripts/generate_report.py --input scored_candidates.json --output DISCOVERY_REPORT.md

# 5. Review DISCOVERY_REPORT.md and proceed with skill-migration on top candidates
```

## Integration with skill-migration

**Discovery → Migration Flow**:

1. **skill-discovery** (this skill):
   - Input: Repository files
   - Output: Prioritized list of skill candidates
   - Answers: "WHAT to migrate?"

2. **skill-migration**:
   - Input: Specific candidate from discovery report
   - Output: Portable skill + cleaned source files
   - Answers: "HOW to migrate?"

**Example Usage**:

```
# Phase 1: Discovery
User: "Scan my repository for skill migration candidates"
AI: [Uses skill-discovery]
AI: "Found 12 candidates. Top priority: git-commit (95/100) in 3 files"

# Phase 2: Migration
User: "Use skill-migration to create git-commit skill from those 3 files"
AI: [Uses skill-migration]
AI: "Created git-commit skill, cleaned up 3 source files"
```

## Success Criteria

A successful discovery achieves:

1. **Comprehensive scan**: All relevant files analyzed
2. **Accurate detection**: Duplicates correctly identified
3. **Meaningful scores**: Priorities reflect actual migration value
4. **Actionable report**: Clear what to migrate and why
5. **Clear handoff**: Ready to use skill-migration on top candidates

## Notes

- This skill is **read-only** - it analyzes but doesn't modify files
- Discovery can be re-run anytime to find new candidates
- Scores are recommendations - user can override priorities
- Works best with skill-migration for complete workflow
- Can be run on any repository, not just the current one
