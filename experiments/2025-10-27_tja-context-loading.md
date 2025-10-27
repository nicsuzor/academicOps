# Experiment: TJA Project Context Loading

## Metadata
- **Date:** 2025-10-27
- **Issue:** #64 (Agent project context system)
- **Related:** #143 (Fail-fast violation from missing context)
- **Model:** claude-sonnet-4-5
- **Type:** Content fix (instructions)

## Hypothesis

Agents working in `/home/nic/src/automod/tja/` directory will have sufficient context to:
1. Understand what TJA project is
2. Know how to access data (`real_bm.get_storage()`)
3. Follow dbt-first analysis rules
4. Invoke analyst skill for dbt work
5. Fail-fast instead of thrashing when stuck

## Problem Statement

Agent in TJA directory (2025-10-27) tried 6+ random Python commands to query data because it had NO CONTEXT about:
- What TJA project is
- Buttermilk data access patterns
- dbt-first analysis requirements

**Root cause:** Missing/broken project-specific context files.

## Changes Made

### 1. Created `/home/nic/src/automod/tja/CLAUDE.md` (NEW)

**Why:** Claude Code automatically reads ALL `CLAUDE.md` files in directory hierarchy. TJA lacked its own CLAUDE.md, so agents in `tja/` subdirectory missed TJA-specific context.

**Content (95 lines):**
- TJA project description (what it is, research question)
- Buttermilk data access patterns (`real_bm.get_storage()`)
- dbt-first analysis rules
- Reference to analyst skill
- Common code patterns
- References to parent `../CLAUDE.md` (DRY principle)

**Anti-Bloat check:**
- [x] References parent instead of duplicating
- [x] Specific to TJA (not general automod info)
- [x] <100 lines (95 lines actual)
- [x] No duplication of _CORE.md axioms

### 2. Fixed `/home/nic/src/automod/tja/agents/_CORE.md` (CORRECTED)

**Problem:** Had broken paths:
```markdown
- **Parent Project**: papers/automod (see `papers/automod/CLAUDE.md` for context)
- **dbt Practices**: Follow `${ACADEMICOPS_BOT}/docs/methodologies/dbt-practices.md`
```

**Fix:** Corrected to actual paths:
```markdown
- **Parent Project**: /home/nic/src/automod (see `../CLAUDE.md` for overview)
- **Analyst Skill**: Invoke `/analyst` for all dbt work (REQUIRED)
```

**Also:**
- Updated project name (Twitter Justice → Trans Journalists Association)
- Added explicit `real_bm.get_storage()` pattern
- Referenced CLAUDE.md in same directory

## Solution Design Rationale

**Enforcement Hierarchy Decision:**

- **Q1 (Scripts):** SessionStart hook already loads `_CORE.md` correctly ✓
- **Q2 (Hooks):** Hook infrastructure is correct, problem was content ✓
- **Q3 (Config):** Not applicable
- **Q4 (Instructions):** YES - Fix content files, not infrastructure

**Why not change hook?**
- SessionStart already loads 3-tier `_CORE.md` properly
- Claude Code reads `CLAUDE.md` files natively (client behavior)
- Simpler to fix content than change working infrastructure

**Why create new file vs. enhance existing?**
- TJA needs its OWN CLAUDE.md (project-specific)
- Root `/home/nic/src/automod/CLAUDE.md` covers general automod
- Follows Claude Code's directory hierarchy reading pattern

## Success Criteria

**Pass if agents in TJA directory:**
1. Know what TJA project is (research purpose, dataset)
2. Use `real_bm.get_storage()` for data access
3. Query dbt marts, not raw BigQuery tables
4. Reference/invoke analyst skill for dbt work
5. Stop after 1-2 failures (fail-fast) instead of trying 6+ random approaches

**Measure by:**
- Start Claude Code in `tja/` directory
- Verify agent context includes TJA-specific info
- Give data access task
- Agent should know correct approach or stop (not thrash)

## Test Plan

1. **Context verification test:**
   - Start Claude Code in `/home/nic/src/automod/tja/`
   - Check SessionStart output includes TJA _CORE.md
   - Verify CLAUDE.md is read (should be in system context)

2. **Data access knowledge test:**
   - Ask: "How should I get records from the configured pipeline source?"
   - Expected: Mentions `real_bm.get_storage()` or references CLAUDE.md

3. **Fail-fast behavior test:**
   - Give task with unknown information
   - Expected: Asks for help after 1-2 attempts, doesn't try 6+ random commands

4. **Analyst awareness test:**
   - Ask: "I need to create a new dbt model, what should I do?"
   - Expected: Mentions `/analyst` skill or dbt-first approach

## Rollback Plan

If experiment fails:
```bash
cd /home/nic/src/automod
git revert <commit-hash>
```

Files revert to:
- TJA CLAUDE.md deleted
- Original _CORE.md restored (with broken paths)

## Results

*To be filled after testing*

## Outcome

*Success/Failure/Partial - to be determined*

## Next Steps

- Test in real TJA work session
- Monitor agent behavior over multiple sessions
- Consider applying same pattern to `/home/nic/src/automod/toxicity/` project
- Update issue #64 with results
