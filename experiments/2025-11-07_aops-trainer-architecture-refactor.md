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

## Results

[To be filled after test]

## Outcome

[Success/Failure/Partial]

## Analysis

[What worked, what didn't, what needs improvement in skill]

## Next Steps

[Based on outcome]
