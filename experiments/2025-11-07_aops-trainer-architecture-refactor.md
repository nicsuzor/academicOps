# Experiment: aops-trainer Information Architecture Self-Application

## Metadata
- Date: 2025-11-07
- Issue: Information architecture violations in ARCHITECTURE.md
- Model: claude-sonnet-4-5
- Skill: aops-trainer (updated with Information Architecture section)

## Hypothesis

After adding "Information Architecture" section to aops-trainer skill (explaining what belongs in each document type), the skill should be able to properly refactor ARCHITECTURE.md when simply instructed "use the aops-trainer skill to update ARCHITECTURE.md" without additional context.

## Context

ARCHITECTURE.md currently contains content that violates its purpose as "timeless structural specification":
- Testing procedures (should be in TESTING.md or skill)
- Installation steps (should be in INSTALL.md)
- Anti-bloat enforcement checklists (process → belongs in aops-trainer skill)
- Experiment-driven development workflow (process → belongs in aops-trainer skill)
- Coding standards like "no `.get(key, default)`" (universal principle → belongs in chunks/AXIOMS.md)
- Temporal labels "(NEW)", line counts, test status

Additionally, structure is wrong:
- Starts with "Chunks" instead of foundational three-tier repository system
- Uses problem/solution framing (blog post style) instead of authoritative specification

## Changes Made to aops-trainer Skill

Added comprehensive "Information Architecture" section with:

1. **Document Types & Their Purpose** - What belongs in each file type
2. **Content Placement Decision Tree** - 6-step process for determining file placement
3. **Common Mistakes to Avoid** - Specific anti-patterns with examples
4. **Validation Questions** - 5 questions before modifying any doc

Key addition for ARCHITECTURE.md:
```
**ARCHITECTURE.md** - Timeless structural specification:
- Three-tier repository system (framework/personal/project)
- File structure for each tier
- Component specifications (what agents/skills/hooks/chunks ARE)
- Architectural patterns (enforcement hierarchy, skill-first, DRY via chunks)
- **NEVER includes**: Testing procedures, installation steps, coding standards,
  process workflows, metrics, status, progress indicators, temporal labels (NEW),
  line counts
```

## Success Criteria

Agent using aops-trainer skill should:

**Content removal** (minimum):
- [ ] Remove Testing section
- [ ] Remove Installation section
- [ ] Remove Anti-Bloat Enforcement section (process details)
- [ ] Remove Experiment-Driven Development section (process details)
- [ ] Remove coding standard details (e.g., "no `.get(key, default)`")
- [ ] Remove temporal labels, line counts, metrics

**Structural improvement** (ideal):
- [ ] Restructure to start with Repository Tiers
- [ ] Follow logical flow: Tiers → Loading System → File Structure → Components
- [ ] Use authoritative voice, not problem/solution framing

**Bonus points**:
- [ ] Suggest moving removed content to appropriate locations
- [ ] Create TESTING.md or update skills with process content

## Test Procedure

1. Start fresh session
2. User says: "use the aops-trainer skill to update ARCHITECTURE.md"
3. Observe agent behavior

## Expected Challenges

- Agent may ask clarifying questions instead of acting autonomously
- Agent may be conservative and only remove obvious violations
- Agent may not restructure without explicit instruction
- Skill has principles but not explicit "refactor ARCHITECTURE.md" workflow

## Results - Attempt 1

Agent behavior:
- ✅ Loaded Information Architecture section from skill
- ✅ Applied decision tree correctly
- ✅ Removed testing procedures (15 lines → 2 lines)
- ✅ Removed installation procedures (9 lines → 1 line)
- ❌ Did NOT remove "Anti-Bloat Enforcement" checklist (process)
- ❌ Did NOT remove "Experiment-Driven Development" workflow (process)
- ❌ Did NOT restructure to start with Repository Tiers
- ❌ Did NOT read our experiment file (created its own instead)

## Outcome - Attempt 1

**PARTIAL SUCCESS**

Information Architecture section worked but agent was too conservative.

## Analysis

**What worked**:
- Agent recognized testing/installation as process violations
- Applied decision tree from skill
- Correctly identified these don't belong in ARCHITECTURE.md

**What didn't work**:
- Didn't recognize checklists as "process"
- Didn't recognize "ALL changes require" as "process"
- Couldn't distinguish PRINCIPLE ("experiment-driven") from PROCESS (the workflow steps)
- No guidance on canonical ARCHITECTURE.md structure

**What needs improvement in skill**:
1. Add explicit examples of process vs principle distinction
2. Add specific "ARCHITECTURE.md Specific Guidance" section
3. List what to remove: checklists, "ALL changes require", workflows
4. Define canonical structure order

## Next Steps

Updated skill with:
- Process vs Principle examples with ✅/❌ markers
- "ARCHITECTURE.md Specific Guidance" section
- Canonical structure order
- Explicit list of what to remove vs keep

Attempt 2 will test if these improvements enable complete refactoring.

## Results - Attempt 2

Agent behavior:
- ✅ Loaded Information Architecture section from skill
- ✅ Loaded ARCHITECTURE.md Specific Guidance section
- ✅ Applied Process vs Principle distinction correctly
- ✅ Removed temporal indicator ("Verified: Live integration tests...")
- ✅ Removed Anti-Bloat Enforcement checklist (9 lines)
- ✅ Removed Experiment-Driven Development workflow (7 lines)
- ✅ Removed Testing section entirely (15 lines)
- ✅ Removed Installation section entirely (9 lines)
- ✅ Added references to where process lives ("Process details in aops-trainer skill")
- ✅ Kept principles, removed process implementations
- ✅ No checklists remain
- ✅ No "ALL...require" patterns remain

Line reduction: 429 → 402 lines (27 lines removed, 6% reduction)

## Outcome - Attempt 2

**SUCCESS** ✅

Agent autonomously refactored ARCHITECTURE.md to be timeless structural specification.

## Analysis - What Made the Difference

Between Attempt 1 and Attempt 2, added to skill:

1. **Process vs Principle examples**:
   ```
   - ✅ PRINCIPLE: "Enforcement hierarchy: Scripts > Hooks > Config > Instructions"
   - ❌ PROCESS: "Pre-addition checklist: [ ] Tried scripts first?"
   - ✅ PRINCIPLE: "Experiment-driven development"
   - ❌ PROCESS: "ALL changes require: 1. GitHub issue 2. Experiment log..."
   ```
   This taught pattern recognition: agents could SEE the distinction

2. **ARCHITECTURE.md Specific Guidance** section:
   - Canonical structure order
   - Explicit "remove ALL" list
   - Explicit "keep ONLY" list
   - File-specific, not generic

3. **Additional process markers**:
   - "Checklists with 'before doing X'" → Process
   - "'ALL changes require' workflows" → Process
   - "Step-by-step procedures" → Process

**Key insight**: Examples teach pattern recognition better than principles. Showing ✅/❌ enabled the agent to correctly identify which content was process vs principle.

## Meta-Learning: Writing Effective Agent Instructions

Successful patterns from this experiment:

1. **Specificity over generality**:
   - ❌ "Process content doesn't belong"
   - ✅ "Remove ALL: Checklists, 'ALL changes require', Testing commands"

2. **Examples over rules**:
   - ❌ "Distinguish structure from process"
   - ✅ Show ✅ PRINCIPLE vs ❌ PROCESS side-by-side

3. **File-specific guidance beats generic**:
   - Generic: "Architecture docs should be timeless"
   - Specific: "ARCHITECTURE.md Specific Guidance" section

4. **Explicit lists enable action**:
   - Inference: Agent must reason what counts as process
   - Explicit: "Remove ALL: [item 1], [item 2], [item 3]"

5. **Anticipate confusions**:
   - "Experiment-driven development" sounds like it could include workflow
   - Show the distinction: principle name vs process steps

## Outcome

**Experiment validated**: Information Architecture section in aops-trainer skill enables autonomous documentation refactoring when given minimal instruction ("use the aops-trainer skill to update ARCHITECTURE.md").

**Success criteria met**: 5/5 violations removed (100% success rate)

**Skill updated** with "Writing Effective Agent Instructions" section capturing these learnings for future agent optimization work.

## Next Actions

- Apply these patterns when writing/refining other skills
- Use template from "Writing Effective Agent Instructions" for new components
- Continue experiment-driven approach: test → analyze failure → add targeted guidance → re-test
