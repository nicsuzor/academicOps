# Automation Task Specification: Framework Logger Agent

**Date**: 2025-11-18
**Stage**: 2 (Scripted Tasks)
**Priority**: P2 (Medium impact, improves framework maintenance workflow)

## Problem Statement

**What manual work are we automating?**

Currently, /log command invokes framework skill in "documentation-only mode" which requires the skill to:
1. Categorize observations (Meta-Framework, Component-Level, Behavioral Pattern)
2. Determine success/failure type
3. Format entry correctly
4. Append to LOG.md

This is inefficient because:
- Framework skill is designed for strategic partnership, not routine logging
- No diagnostic capability - just logs what user reports without investigation
- Can't leverage specialized debugging tools (framework-debug skill)
- Can't cross-reference with existing knowledge (bmem skill)
- Manual context loading required

**Why does this matter?**

**Impact**:
- Reduces cognitive load on user reporting observations (just describe, agent handles classification)
- Improves log quality through diagnostic investigation before logging
- Enables root cause analysis using framework-debug skill
- Creates knowledge graph connections via bmem skill
- Time savings: 5-10 minutes per log entry (investigation + formatting) → <1 minute (just describe issue)

**Who benefits?**

Nic (primary), when reporting agent behavior patterns for institutional learning. Also benefits future framework maintenance by creating higher-quality, better-connected log entries.

## Success Criteria

**The automation is successful when**:

1. User invokes /log with description → agent handles full workflow autonomously
2. Agent performs diagnostic investigation when error/failure reported (>80% of entries have investigation context)
3. Log entries include bmem cross-references to related framework concepts (>60% of entries)
4. Categorization accuracy ≥95% (Meta-Framework vs Component-Level vs Behavioral Pattern)
5. Formatting compliance 100% (all entries match LOG.md format specification)
6. User review time reduced from 5-10 min → <1 min per entry

**Quality threshold**:
- HALT if cannot categorize observation (ask user for clarification)
- HALT if LOG.md frontmatter invalid (must be bmem-compliant)
- Best effort on investigation (document what was found, even if incomplete)

## Scope

### In Scope

- Accept user description of observation (via /log command arguments)
- Invoke framework skill to understand context (what should be happening)
- Invoke framework-debug skill to investigate errors/failures (when applicable)
- Invoke bmem skill to cross-reference related concepts and document findings
- Categorize observation automatically (Meta-Framework / Component-Level / Behavioral Pattern)
- Determine type (✅ Success / ❌ Failure)
- Assign pattern tags based on content
- Format entry per LOG.md specification
- Append to $ACA_DATA/projects/aops/experiments/LOG.md
- Validate LOG.md frontmatter is bmem-compliant before appending

### Out of Scope

- Fixing the reported issue (log agent documents, doesn't fix)
- Multi-session pattern analysis (that's framework skill's strategic role)
- Creating new experiment files (only appends to LOG.md)
- User confirmation workflow (agent makes decisions autonomously, logs immediately)
- Retroactive log entry editing

**Boundary rationale**:

Agent does ONE thing (AXIOMS #1): document observations in learning log with appropriate investigation context. Fixing issues is a separate task. Pattern analysis across multiple entries is framework skill's strategic role. This agent is a specialized logging orchestrator.

## Dependencies

### Required Infrastructure

- Framework skill operational (load context, understand framework design)
- Framework-debug skill operational (investigate errors via session logs)
- bmem skill operational (search knowledge base, document findings)
- LOG.md exists at $ACA_DATA/projects/aops/experiments/LOG.md with valid frontmatter
- Session logs available (for framework-debug skill investigation)

### Data Requirements

- User provides: observation description (text)
- Agent needs access to:
  - Current framework documentation (via framework skill)
  - Session logs for debugging (via framework-debug skill)
  - bmem knowledge base (via bmem skill)
  - LOG.md file (read for format, append for new entry)
- Fail-fast if LOG.md frontmatter invalid or file doesn't exist

## Integration Test Design

**Test must be designed BEFORE implementation**

### Test Setup

Create test scenario files:
- Mock observation descriptions (success and failure cases)
- Test LOG.md file with valid frontmatter
- Simulated session log entries

```bash
# Setup test environment
mkdir -p tests/fixtures/log-agent/
cp $ACA_DATA/projects/aops/experiments/LOG.md tests/fixtures/log-agent/LOG-original.md
```

### Test Execution

Test cases:

1. **Happy path - Success observation**
```bash
# Invoke agent with success observation
log-agent "Agent correctly used task scripts instead of writing files directly"
```

2. **Happy path - Failure observation requiring investigation**
```bash
# Invoke agent with failure observation (should trigger framework-debug)
log-agent "Test failed with 'file not found' error when loading AXIOMS.md"
```

3. **Edge case - Ambiguous categorization**
```bash
# Invoke agent with description that could be multiple categories
log-agent "Framework skill loaded wrong context file order"
```

### Test Validation

Verify:
- LOG.md has new entry appended
- Entry has correct format (Date, Type, Pattern, What/Why/Lesson)
- Categorization is accurate (correct category header)
- Pattern tags are relevant
- Investigation context included (for failure cases)
- bmem cross-references present (when applicable)
- LOG.md frontmatter still valid after append

```bash
# Validation checks
grep -A 5 "$(date +%Y-%m-%d)" tests/fixtures/log-agent/LOG.md | grep "Pattern:"
validate_bmem_frontmatter tests/fixtures/log-agent/LOG.md
```

### Test Cleanup

```bash
# Restore original LOG.md
rm tests/fixtures/log-agent/LOG.md
mv tests/fixtures/log-agent/LOG-original.md $ACA_DATA/projects/aops/experiments/LOG.md
```

### Success Conditions

- [x] Test initially fails (no agent exists yet)
- [ ] Test passes after implementation
- [ ] Test covers happy path (success and failure observations)
- [ ] Test covers error cases (ambiguous categorization, invalid LOG.md)
- [ ] Test validates categorization accuracy
- [ ] Test validates format compliance
- [ ] Test validates investigation context inclusion
- [ ] Test is idempotent (can run repeatedly with cleanup)

## Implementation Approach

### High-Level Design

Agent orchestrates workflow using specialized skills:

**Workflow**:
1. Receive observation description from /log command
2. **Context loading**: Invoke framework skill (understand what should be happening)
3. **Investigation** (if failure): Invoke framework-debug skill (diagnose root cause)
4. **Knowledge linking**: Invoke bmem skill (find related concepts, document findings)
5. **Categorization**: Analyze description + investigation → category + type + tags
6. **Formatting**: Structure entry per LOG.md specification
7. **Validation**: Check LOG.md frontmatter is bmem-compliant
8. **Append**: Add entry to LOG.md

**Components**:

1. **Observation Parser**: Extract key information from user description
2. **Skill Orchestrator**: Invoke framework/framework-debug/bmem skills as needed
3. **Categorizer**: Classify observation (Meta/Component/Behavioral + Success/Failure)
4. **Tag Generator**: Assign relevant pattern tags
5. **Formatter**: Structure entry matching LOG.md format
6. **Writer**: Validate frontmatter, append entry to LOG.md

**Data Flow**:
```
User description
  → Parse
  → Context (framework skill)
  → Investigate (framework-debug skill if failure)
  → Link (bmem skill)
  → Categorize
  → Format
  → Validate
  → Append to LOG.md
```

### Technology Choices

**Implementation**: Agent specification (markdown file in agents/ directory)

**Pattern**: Orchestration agent (uses Skill tool to invoke framework/framework-debug/bmem, uses Edit tool to append to LOG.md)

**No scripts needed**: Agent uses existing tools (Read, Edit, Skill) - no new utilities required

**Rationale**:
- Agents are the right abstraction for orchestration workflows
- Existing skills provide all needed capabilities
- Edit tool handles LOG.md append with validation
- No need for script layer (would violate LLM-first architecture)

### Error Handling Strategy

**Fail-fast cases** (HALT immediately):

- LOG.md doesn't exist
- LOG.md frontmatter invalid (not bmem-compliant)
- Cannot determine category after investigation (ask user for clarification)
- User description too vague to classify (ask for more detail)

**Graceful degradation cases** (best effort):

- Framework-debug skill returns no findings (log observation without investigation context)
- bmem skill finds no related concepts (log without cross-references)
- Pattern tags ambiguous (choose most likely tag, note uncertainty in entry)

**Recovery mechanisms**:

- If skill invocation fails → log warning, continue with partial information
- If categorization uncertain → ask user to confirm category before appending
- If append fails → report error, preserve formatted entry for manual addition

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: Incorrect categorization (e.g., Behavioral Pattern logged as Component-Level)
   - **Detection**: User reviews entry, notices wrong category
   - **Impact**: Log organization degraded, pattern analysis harder
   - **Prevention**: Use framework skill context + investigation results for classification
   - **Recovery**: Manual edit of LOG.md entry (git history preserves original)

2. **Failure mode**: Investigation doesn't find root cause (framework-debug returns empty)
   - **Detection**: Log entry has no investigation context
   - **Impact**: Lower quality learning, missed diagnostic opportunity
   - **Prevention**: Document what WAS checked even if inconclusive
   - **Recovery**: Follow-up investigation can be added as separate log entry

3. **Failure mode**: LOG.md frontmatter corruption during append
   - **Detection**: bmem validation fails on next commit
   - **Impact**: Knowledge base corruption
   - **Prevention**: Validate frontmatter BEFORE appending entry
   - **Recovery**: Revert commit, fix frontmatter, re-append entry

4. **Failure mode**: Agent over-investigates simple success observations
   - **Detection**: Agent takes >2 minutes for routine success logging
   - **Impact**: User friction, slow workflow
   - **Prevention**: Skip investigation for explicit success observations
   - **Recovery**: Add heuristic to detect "this worked well" vs "this failed"

## Monitoring and Validation

### How do we know it's working in production?

**Metrics to track**:

- Categorization accuracy: % requiring manual recategorization
- Investigation quality: % failure entries with diagnostic context
- bmem linkage rate: % entries with knowledge graph cross-references
- User time savings: time from /log invocation to entry committed
- Format compliance: % entries matching specification exactly

**Monitoring approach**:

- Weekly review of LOG.md entries (spot check 5-10 recent entries)
- Track user corrections (git commits editing LOG.md entries)
- Measure agent execution time (should be <2 min per entry)

**Validation frequency**: Weekly manual review for first month, then monthly

## Documentation Requirements

### Code Documentation

- [ ] Agent specification clearly documents workflow steps
- [ ] Examples of investigation scenarios (when to invoke framework-debug)
- [ ] Error handling patterns documented
- [ ] Skill invocation sequence explained

### User Documentation

- [ ] Update /log command to invoke log-agent instead of framework skill
- [ ] Document expected behavior (what agent does automatically)
- [ ] Document when agent will ask for clarification
- [ ] Add to framework/workflows/ if needed

### Maintenance Documentation

- [ ] Known limitations: cannot retroactively edit entries
- [ ] Future improvements: multi-entry pattern analysis
- [ ] Dependencies: framework skill, framework-debug skill, bmem skill

## Rollout Plan

### Phase 1: Validation (Experiment)

- Create agent specification
- Test with 10 sample observations (5 success, 5 failure)
- Monitor categorization accuracy and investigation quality
- Collect user feedback on workflow friction

**Criteria to proceed**: ≥90% categorization accuracy, ≥80% investigation context on failures

### Phase 2: Limited Deployment

- Update /log command to invoke log-agent
- Use for all new log entries (1 week trial)
- Keep framework skill as manual fallback
- Monitor for edge cases and correction frequency

**Criteria to proceed**: <10% manual corrections, user confirms workflow improvement

### Phase 3: Full Deployment

- Make log-agent the default logging mechanism
- Document as production in framework
- Archive "documentation-only mode" instructions from /log command
- Update ROADMAP.md with completion

**Rollback plan**: Revert /log command to invoke framework skill directly (one line change)

## Risks and Mitigations

**Risk 1**: Agent over-investigates routine observations, slowing workflow

- **Likelihood**: Medium
- **Impact**: High (user friction)
- **Mitigation**: Add heuristic to detect explicit success vs failure requiring investigation; skip framework-debug for clear success observations

**Risk 2**: Investigation skills not mature enough for reliable diagnostics

- **Likelihood**: Low (framework-debug skill already tested)
- **Impact**: Medium (lower quality log entries)
- **Mitigation**: Document what WAS checked even if inconclusive; graceful degradation to log without investigation context

**Risk 3**: LOG.md grows too large for efficient appending

- **Likelihood**: Low (current 409 lines, append-only adds ~10 entries/month)
- **Impact**: Low (file reads will slow but acceptable for years)
- **Mitigation**: Monitor file size; consider rotation strategy if >1000 entries (not urgent)

## Open Questions

1. Should agent ask user to confirm category when uncertain, or choose best guess and document uncertainty in entry? **Decision**: Choose best guess, document uncertainty with "(agent-categorized)" marker if confidence <80%

2. When should investigation be skipped? Only for explicit "success" keywords in description, or broader heuristic? **Decision**: Skip investigation if description contains success markers (✅, "worked", "correctly", "successfully") AND no failure markers (❌, "failed", "error", "bug")

3. Should bmem skill document the logged observation as a separate knowledge base entry, or just cross-reference existing concepts? **Decision**: Just cross-reference existing concepts; LOG.md itself is the authoritative record

## Notes and Context

This agent implements the "LLM-first architecture" pattern:
- Agent orchestrates using Skill tool
- No scripts needed (Edit tool handles appending)
- Skills provide specialized capabilities (framework context, debugging, knowledge linking)
- Clean separation of concerns

Addresses STATE.md priority: "Add authoritative domain knowledge headers to skills" by making framework skill invocation explicit in workflow.

Related patterns:
- email-extractor agent (assessment + storage orchestration)
- dev agent (routing orchestration)

---

## Completion Checklist

Before marking this task as complete:

- [ ] Agent specification created in agents/log-agent.md
- [ ] /log command updated to invoke log-agent
- [ ] Integration test created and passing
- [ ] Categorization accuracy ≥95% on test cases
- [ ] Investigation context present on ≥80% of failure cases
- [ ] bmem cross-references present on ≥60% of entries
- [ ] LOG.md frontmatter validation working
- [ ] User confirms workflow improvement (faster, less friction)
- [ ] Documentation updated (commands/log.md, framework workflows if needed)
- [ ] Experiment log entry created documenting rollout

## Post-Implementation Review

[After 2 weeks of production use]

**What worked well**:

- [To be filled after deployment]

**What didn't work**:

- [To be filled after deployment]

**What we learned**:

- [To be filled after deployment]

**Recommended changes**:

- [To be filled after deployment]
