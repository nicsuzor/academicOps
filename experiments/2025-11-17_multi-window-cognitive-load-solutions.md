# Experiment: Multi-Window Cognitive Load Reduction

**Date**: 2025-11-17
**Status**: Planning
**Issue**: Multi-window context loss across all projects and repositories
**Pattern**: General workflow problem (not framework-specific)

## Problem Statement

**Context**: Works across multiple terminals/repositories simultaneously with Claude Code workflows running 1-120 minutes. Constantly struggles with:
1. **Short-term UX**: "What am I doing in THIS window?"
2. **Medium-term orchestration**: "What should I work on next in THIS repo?"
3. **Meta-framework**: "How is the framework evolving and what does /meta know?"

**Scope**: This affects ALL academic work across ALL projects, not just academicOps framework development. Solutions must work universally across all repositories and contexts.

**Strategic alignment**:
- VISION.md: Framework must work within "solo academic schedule (fragmented time, context switching)" and "ADHD accommodations (zero-friction capture, clear boundaries)"
- ACCOMMODATIONS.md line 30: Multi-window context loss is a general workflow problem
- ROADMAP: Currently Stage 1→2 transition, but experiencing Stage 4-5 pain (proactive task surfacing)

## Proposed Solutions (Layered Approach)

### Level 1: Immediate Tactical (Stage 2 Compatible)

**Target**: "What am I doing in THIS window?"

**Solution**: Lightweight session state tracking

**Mechanism Options**:
1. **tmux status line** (if using tmux): Show repo + active task
2. **Shell prompt enhancement**: Add task context to PS1
3. **Simple state file**: `.claude-session-state` in each repo that agents update

**Implementation**:
```bash
# In each terminal window, visible in prompt or tmux status:
# - Current repo
# - Active task (from data/tasks/ or brief description)
# - Estimated time remaining (if known)
# - Session ID (to correlate with Claude Code instance)
```

**Advantages**:
- No complex infrastructure
- Visual glanceable state
- Works across all repos immediately

**Disadvantages**:
- Requires agent discipline to update state
- Doesn't solve queue management
- Manual setup per repo

**Status**: Experimental - needs testing to find what actually helps

---

### Level 2: Medium-term Framework Enhancement (Stage 2 Target)

**Target**: "What should I work on next in THIS repo?"

**Solution**: Task queue management per repository

**Mechanism**:
- `data/tasks/queue.jsonl` in each repo
- Tasks marked: `queued | active | blocked | completed`
- Agent reads queue at session start
- Agent updates state as tasks progress
- Simple CLI: `task queue`, `task active`, `task block <id> "reason"`

**Integration with existing**:
- Builds on current task scripts (task_add.py, task_view.py)
- Adds state transitions and blocking reasons
- Enables: "I can't start task X because task Y is running"

**Implementation priority**: Near-term (next 2-4 weeks)

**Advantages**:
- Addresses queue management pain
- Aligns with Stage 2 "Task Capture and Filing"
- Uses existing task infrastructure
- Per-repo isolation (AXIOM 4: Project Independence)

**Disadvantages**:
- Still requires manual "what's next" decisions
- Doesn't surface tasks proactively
- Requires agent adherence (known problem per ROADMAP line 258)

**Critical insight**: Task system integration isn't a recommendation - it's the whole point. Must work across ALL repositories.

---

### Level 3: Meta-Framework Improvements (Foundational)

**Target**: "/meta skill isn't sufficiently cognizant without close supervision"

**Solution A: Learning Consolidation**

**Mechanism**:
- Create `experiments/LOG.md` ✅ (DONE 2025-11-17)
- After each experiment, extract lessons to LOG.md
- Meta skill ALWAYS loads LOG.md first
- Format: Pattern-based entries (what worked, what didn't, why)

**Status**: ✅ COMPLETED - LOG.md created with initial patterns

---

**Solution B: Framework State Tracking**

**Mechanism**:
- `framework/STATE.md` - current status snapshot
- Updated after each significant change
- Contains:
  - Current stage (from ROADMAP)
  - Recent decisions and rationale
  - Active blockers
  - Next priorities
- Meta skill loads STATE.md for "where are we" queries

**Implementation priority**: Immediate (this week)

**Advantages**:
- Makes meta skill trustworthy (AXIOM 14: NO EXCUSES)
- Provides "ground truth" to reference
- Enables better context recovery

**Disadvantages**:
- Additional file (conflicts with MINIMAL principle)
- Requires discipline to maintain
- Risk of becoming outdated

**Justification**: Worth the file cost if it makes meta skill actually trustworthy

---

**Solution C: Decision Log**

**Mechanism**:
- `framework/DECISIONS.md` - append-only decision log
- Each entry: Date, Question, Decision, Reasoning, Outcome
- Provides: "Why did we choose X over Y?"
- Meta skill searches DECISIONS for rationale queries

**Implementation priority**: Defer until STATE.md proves useful

**Advantages**:
- Builds institutional memory across sessions
- Solves: "Why did we make decision X?"
- Append-only = no conflicts

**Disadvantages**:
- Another file (more bloat concern)
- Overlap with experiments/LOG.md
- Need clear distinction between decisions vs learnings

---

## Recommendation Summary

**Immediate (this week)**:
1. ✅ Level 3A: Create experiments/LOG.md - DONE
2. Level 3B: Create framework/STATE.md - current state snapshot

**Near-term (next 2-4 weeks)**:
3. Level 2: Task queue state - enhance existing task scripts with status tracking

**Experimental (when bandwidth available)**:
4. Level 1: Try session state tracking - test different approaches

**Defer (until Stage 4)**:
5. Proactive task surfacing, intelligent priority suggestions, anticipatory scheduling

## Core Tension

ROADMAP exists because rushing to Stage 4-5 solutions (proactive task surfacing) without Stage 2-3 foundations (reliable task scripts) leads to brittle complexity. But the pain is acute NOW. Solution: Tactical Stage 2-compatible improvements that help immediately without over-engineering.

## Next Actions

**User decision needed on**:
1. Which level resonates most strongly with immediate pain?
2. Should we capture this as experiment or update ROADMAP directly?
3. Are we open to adding framework/LOG.md + framework/STATE.md despite MINIMAL concerns?
4. What's minimum viable improvement for next 2 weeks?

## Success Criteria

TBD based on which solutions are implemented.

## Related Issues

- ROADMAP blockers: Task management reliability (agents bypass scripts)
- VISION constraint: Solo academic schedule with fragmented time
- ACCOMMODATIONS: Multi-window context loss affects ALL projects
