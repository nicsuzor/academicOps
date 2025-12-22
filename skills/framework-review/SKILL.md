# Framework Review

Analyze session transcripts to identify framework improvement opportunities. Uses parallel batch processing to extract patterns, map to enforcement levels, and update ROADMAP.md.

## Framework Context

@resources/AXIOMS.md
@resources/ENFORCEMENT.md

## When to Invoke

- Periodic framework health check (weekly/monthly)
- After noticing repeated agent failures
- When considering new enforcement mechanisms
- User requests: "review framework", "analyze sessions", "what's not working"

## Workflow

### 1. Discover Transcripts

Find session transcripts to analyze:
```bash
ls $ACA_DATA/sessions/claude/*.md | wc -l
```

Default: Last 7 days of sessions. Accept user override for date range or specific files.

### 2. Batch for Parallel Processing

Group transcripts into 5-8 batches by:
- Date (recent vs older)
- Project (buttermilk, writing, academicOps)
- Type (full vs abridged)

Target: 10-20 files per batch for haiku agents.

### 3. Spawn Parallel Agents

For each batch, spawn haiku agent with structured prompt:

```
Analyze these session transcripts for framework improvement opportunities:
[file list]

For each session, assess:
1. **Prompt effectiveness** - Did user get what they wanted? Why/why not?
2. **Patterns to systematize** - Repeated workflows that could be automated
3. **Typing reduction** - Where user types same things repeatedly
4. **Agent errors** - Repeated mistakes, rule violations
5. **Root causes** - WHY errors occur (missing context? training priors? no enforcement?)

Output: Structured findings with specific evidence (session:line references).
```

### 4. Synthesize Findings

Collect agent outputs. Identify cross-cutting patterns:
- Errors appearing in multiple batches
- Successful patterns worth replicating
- Gaps in current enforcement

### 5. Map to Enforcement Levels

For each identified problem, determine root cause and appropriate fix level:

| Root Cause | Enforcement Level |
|------------|-------------------|
| Missing context | 2 - JIT injection |
| Complex workflow | 3 - Skill abstraction |
| Mechanical precondition | 4 - Pre-tool hook |
| Need verification | 5 - Post-tool hook |
| Must never occur | 6 - Deny rule |

Reference: `docs/ENFORCEMENT.md` mechanism ladder.

**Key insight**: If rule exists but is ignored, adding another rule won't help. Escalate enforcement level.

### 6. Update ROADMAP.md

Add findings to "In Progress" section:

```markdown
### Enforcement Improvements (from YYYY-MM-DD review)

See `docs/ENFORCEMENT.md` for mechanism ladder.

| Fix | Level | Effort | Root Cause |
|-----|-------|--------|------------|
| [specific fix] | [1-7] | [est] | [why it's happening] |
```

### 7. Update Evidence Log (Optional)

Add observations to `docs/ENFORCEMENT.md` evidence log:

```markdown
| Date | Observation | Mechanism Tried | Worked? |
|------|-------------|-----------------|---------|
| YYYY-MM-DD | [what happened] | [level tried] | Yes/No |
```

## Example Output

```markdown
## Framework Review: 2025-12-22

**Analyzed**: 113 sessions (Dec 13-21)

### Critical Findings

| Issue | Frequency | Root Cause | Fix (Level) |
|-------|-----------|------------|-------------|
| File not read before edit | 2-3/day | Mechanical | Pre-edit hook (4) |
| Skill bypass | 8+/week | Training priors | Path enforcement (4) |
| Framework amnesia | Every session | Missing context | ROADMAP injection (2) |

### What Works Well
- Parallel batch processing (gold standard for migrations)
- Subagent delegation for research

### Updated
- ROADMAP.md: Added enforcement improvements
- ENFORCEMENT.md: Added evidence log entries
```

## Anti-Patterns

- ❌ Adding rules when rules already exist but are ignored
- ❌ Proposing "agents should do X better" without enforcement mechanism
- ❌ Diagnosing symptoms instead of root causes
- ❌ Skipping ENFORCEMENT.md level mapping
