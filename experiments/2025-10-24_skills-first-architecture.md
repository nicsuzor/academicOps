# Skills-First Architecture Shift

## Metadata
- Date: 2025-10-24
- Issue: TBD (to be created)
- Commit: TBD
- Model: claude-sonnet-4-5
- Status: In Progress

## Hypothesis

Shifting from instruction-heavy to skills-first architecture with just-in-time context loading will:

1. **Reduce token usage** - Less upfront instruction loading
2. **Improve context relevance** - Right context at right time
3. **Increase skill utilization** - Skills become primary mechanism
4. **Simplify agent instructions** - Thin orchestration layer only

## Background: Architecture Evolution

### Previous Approach (Invalidated)
- Heavy SessionStart instruction loading
- Agent files 500+ lines of procedural details
- Context loaded upfront regardless of task
- Instructions as primary mechanism

**Problems:**
- High token cost
- Agents forget instructions in long conversations
- Irrelevant context loaded unnecessarily
- Duplication across agent files

### New Approach (Testing)

**Three pillars:**

1. **Skills as Primary Mechanism**
   - Packaged workflows in `~/.claude/skills/`
   - Bundled scripts + references + procedural knowledge
   - Invoked when needed, not loaded upfront

2. **CLAUDE.md Just-In-Time Loading**
   - Directory-specific context files
   - `@references` to modular docs
   - Auto-loaded when agent enters directory

3. **Hook-Based Instruction Stacking**
   - Intercept reads to `bot/prompts/*`
   - Return 3-tier stacked content: framework + user + project
   - Dynamic aggregation on demand

## Changes Made

### Phase 1: Foundation (Week 1) - IN PROGRESS

#### 1.1 Experiment Infrastructure
- [x] Created this experiment log
- [ ] Create GitHub issue for tracking
- [ ] Invalidate prior experiments (mark as DEPRECATED)

#### 1.2 Instruction Stacking Hook
- [x] Implement `bots/hooks/stack_instructions.py`
- [x] Add to `~/.claude/settings.json` as PostToolUse hook
- [x] Updated to handle `/bots/**/*.md` patterns (not `bot/prompts/`)
- [x] Handles Read failures (provides content even when file doesn't exist locally)
- [x] Test with reads to `/bots/agents/DEVELOPER.md`
- [x] Verify 3-tier aggregation works
- [x] Add discovery mode to `load_instructions.py` (SessionStart hook)
- [x] Discovery manifest lists available bot instruction files
- [x] Comprehensive testing: all tests pass

#### 1.3 CLAUDE.md Templates
- [ ] Create `CLAUDE.md` template with best practices
- [ ] Document when/where to use CLAUDE.md files
- [ ] Add to key directories as proof of concept

#### 1.4 Architecture Documentation
- [ ] Update ARCHITECTURE.md with new model
- [ ] Document skill-first philosophy
- [ ] Explain just-in-time context loading
- [ ] Clarify enforcement hierarchy (Skills > Hooks > Config > Instructions)

### Phase 2: CLAUDE.md Rollout (Week 2)
- [ ] Add CLAUDE.md to `tests/` directories
- [ ] Add CLAUDE.md to `scripts/` directories
- [ ] Add CLAUDE.md to `bots/` directories
- [ ] Create project-specific CLAUDE.md templates

### Phase 3: Agent Instruction Reduction (Week 3)
- [ ] Thin out developer agent instructions
- [ ] Thin out trainer agent instructions
- [ ] Convert procedural content to skill references
- [ ] Keep only orchestration logic

### Phase 4: Validation (Week 4)
- [ ] A/B test old vs new architecture
- [ ] Measure token usage before/after
- [ ] Measure skill invocation rates
- [ ] Collect user feedback

## Success Criteria

### Quantitative Metrics

1. **Token Usage** (baseline to be measured):
   - SessionStart context: DECREASE by >30%
   - Per-conversation token usage: DECREASE by >20%
   - Relevant context ratio: INCREASE

2. **Skill Invocation** (baseline to be measured):
   - Skills invoked per conversation: INCREASE by >50%
   - Skill success rate: MAINTAIN >90%

3. **Agent Instruction Size**:
   - Agent file sizes: DECREASE from ~500 lines to <100 lines
   - Modular doc files: INCREASE (more granular)

### Qualitative Indicators

- [ ] Agents reliably invoke skills when appropriate
- [ ] Context appears when needed, not upfront
- [ ] Directory-specific guidance works correctly
- [ ] 3-tier instruction stacking provides complete picture
- [ ] User reports improved agent performance

## Baseline Measurements (Before Changes)

**To be collected:**
- Current SessionStart token count
- Average agent instruction file size
- Skill invocation rate per conversation
- User satisfaction score

## Results

*To be filled after implementation and testing*

## Outcome

*To be determined: Success/Failure/Partial*

## Learnings

*To be documented after experiments complete*

## Next Experiments

*Based on outcomes, what to try next*

## Related Experiments (INVALIDATED)

All prior experiments testing:
- SessionStart instruction loading approaches
- Agent instruction effectiveness
- Per-project hook configurations

**Reason for invalidation**: Fundamental architecture change makes comparison invalid.
