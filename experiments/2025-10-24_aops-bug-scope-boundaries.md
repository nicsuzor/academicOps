# Experiment: Define aops-bug Scope Boundaries

## Metadata

- **Date**: 2025-10-24
- **Issue**: #157
- **Commit**: bc71b94
- **Agent**: Claude Sonnet 4.5
- **Invocation Context**: `/log-failure` command via trainer

## Hypothesis

Adding explicit scope boundaries to the aops-bug skill and /log-failure command will prevent the skill from attempting fixes when invoked for documentation-only purposes.

**Expected Behavior**:
- When invoked via `/log-failure`: Analyze, categorize, document in GitHub, STOP
- Agent will NOT fix user's original request
- Agent will NOT implement solutions
- Agent will NOT investigate deeply beyond pattern identification

## Problem Context

**Issue Instance**: 2025-10-24 conversation
- User: `/log-failure task skills in personal repo has no idea how to use task tools`
- Agent (aops-bug skill):
  1. ✅ Correctly identified violation (didn't read tool docs)
  2. ✅ Found and updated issue #155
  3. ❌ THEN fixed user's original request (archived Klaus task)
  4. ❌ THEN discovered new infrastructure bug (hardcoded paths)
  5. ❌ THEN documented new bug in issue #155

**Root Cause**: aops-bug skill had no defined stopping point for documentation-only invocations. Treated all invocations as "analyze AND implement".

## Changes Made

### 1. `.claude/skills/aops-bug/SKILL.md` (~59 lines added)

Added "Scope Boundaries" section after "When to Use This Skill":

**Mode 1: Documentation-Only (via `/log-failure`)**:
- ✅ DO: Analyze, search, document, report
- ❌ DO NOT: Fix original request, implement solutions, investigate deeply

**Mode 2: Full Intervention (direct invocation)**:
- Full scope including investigation, experiments, solutions

**Example provided** showing correct vs wrong behavior.

### 2. `.claude/commands/log-failure.md` (~13 lines added)

Added "CRITICAL - Documentation-Only Mode" section:
- Explicit DO/DO NOT list
- Rationale for single data point logging
- Reinforces scope limitation at invocation point

## Success Criteria

**Primary Metric**: Next `/log-failure` invocation should:
1. ✅ Document violation in GitHub
2. ✅ STOP after documentation
3. ✅ NOT fix user's original request
4. ✅ NOT implement solutions

**Secondary Metrics**:
- No user reports of aops-bug overstepping scope
- Issues properly categorized and linked
- Clear separation between logging and fixing

**Test Scenarios**:
1. `/log-failure` with simple violation → Should document only
2. `/log-failure` with infrastructure bug discovered → Should note but not fix
3. Direct aops-bug invocation → Should proceed with full intervention

## Implementation Notes

**Enforcement Hierarchy Assessment**:
- Q1 (Scripts): NO - Behavior depends on invocation context
- Q2 (Hooks): POTENTIALLY - Could detect aops-bug via /log-failure and warn on Write/Edit tools, but fragile
- Q3 (Config): NO - Too dynamic
- Q4 (Instructions): YES - Context-dependent behavior, instruction-only territory

**Anti-Bloat Protocol**:
- [ ] Hierarchy Check: ✅ Verified scripts/hooks/config won't work
- [ ] Bloat Estimate: ~72 lines total (~1800 tokens)
- [ ] Modularity: ✅ Separate modes clearly defined in single location
- [ ] DRY Check: ✅ Not repeating other content
- [ ] Complexity Budget: ✅ SKILL.md total size reasonable
- [ ] Justification: Critical behavioral boundary, prevents scope creep

**Bloat Justification**:
- Prevents entire class of violations (fixing on single data points)
- Establishes clear operational modes for skill
- Small token cost for major behavioral clarity

## Results

[To be filled after testing in real conversations]

**Test 1**: [Date] - [Scenario] - [Outcome]

**Test 2**: [Date] - [Scenario] - [Outcome]

**Metrics**:
- Documentation-only adherence rate: [X/Y]
- User satisfaction: [Feedback]
- False positives (stopped when should have proceeded): [Count]

## Outcome

[To be determined after validation period]

**Status**: PENDING VALIDATION

**Next Steps**:
1. Commit changes
2. Monitor next 5-10 `/log-failure` invocations
3. Update this log with results
4. Decide: Keep/Revert/Iterate

## Related Issues

- #155: Agent violated Axiom #7 (existing issue being tracked)
- #157: This experiment (scope boundaries for /log-failure)
