# Automation Task Specification: Framework Debugging Skill

**Date**: 2025-11-18
**Stage**: 2 (Scripted Tasks)
**Priority**: P2 (Moderate impact, moderate effort)

## Problem Statement

**What manual work are we automating?**

When framework issues occur (hooks failing, agents behaving incorrectly, skills not loading), debugging requires manually:
1. Finding the current session ID
2. Locating relevant log files across multiple directories (`~/.claude/debug/`, `~/.claude/projects/[repo]/`)
3. Identifying which agent logs correspond to the session
4. Searching through large JSONL files for error messages or unexpected behavior
5. Correlating timeline of events across main session and agent sublogs
6. Extracting relevant context without reading entire multi-MB log files

This investigative work can take 10-30 minutes per debugging session, with high cognitive load from manual file navigation and log correlation.

**Why does this matter?**

**Impact**: Reduces debugging time from 10-30 minutes to <2 minutes. More importantly, enables systematic debugging when user is interrupted mid-investigation (ADHD accommodation - don't carry cognitive load). Framework reliability improvements depend on efficient fault diagnosis.

**Who benefits?**

Nic when debugging framework issues across any repository. Particularly valuable given:
- ADHD challenges with task switching and context recovery (ACCOMMODATIONS.md line 30)
- Multi-window workflow where tracking what's running/blocked is difficult (ACCOMMODATIONS.md line 30)
- Session documentation gap created by removing hook session logs (STATE.md P2 blocker, line 123)

## Success Criteria

**The automation is successful when**:

1. Agent can identify current or recent session logs in <10 seconds
2. Agent extracts relevant error messages/tool failures without reading entire logs (>90% of relevant messages found)
3. Agent presents chronological narrative of "what happened" without user needing to correlate timelines
4. Skill works across all repositories (not just academicOps)
5. Investigation is resumable - agent can continue debugging after interruption

**Quality threshold**: Fail-fast if log files are corrupted or unreadable. Best-effort extraction if logs are incomplete (partial session) but report coverage gaps clearly.

## Scope

### In Scope

- Identify current session ID and working directory
- Locate main session log (`~/.claude/projects/[repo-path]/[session-id].jsonl`)
- Locate agent sublogs for the session (files matching `agent-*.jsonl` or session ID)
- Extract messages by type: errors, tool failures, user messages, agent responses
- Present chronological timeline of key events
- Filter to most recent N messages or last T minutes
- Search for specific patterns (e.g., "all errors in last hour")

### Out of Scope

- Automated diagnosis/root cause analysis (agent interpretation, not skill responsibility)
- Log file cleanup or archival
- Real-time monitoring or alerts
- Performance profiling or statistics
- Comparison across multiple sessions
- Git history correlation (which commit was active during session)

**Boundary rationale**: This is an **investigative skill** that efficiently surfaces log data. Analysis and interpretation are agent responsibilities. Keeps skill focused per AXIOMS.md #1 (DO ONE THING).

## Dependencies

### Required Infrastructure

- Claude Code logging system (already exists, writes to `~/.claude/`)
- JSONL log format (established, documented by exploration)
- Session directory naming convention (`~/.claude/projects/[repo-path]/`)
- Agent log naming convention (observed: `agent-[id].jsonl` and `[session-id].jsonl`)

### Data Requirements

- Current working directory (to map to project directory)
- Session ID (available from environment or derivable from recent files)
- Log files must be readable JSONL format
- Timestamp fields in logs for chronological ordering

**Failure handling**: If logs are missing or corrupted, report clearly which files are unavailable and what coverage gaps exist.

## Integration Test Design

### Test Setup

Create test fixture with mock session logs:

```bash
# Create test directory structure
mkdir -p /tmp/test-debug-skill/{debug,projects/-tmp-test-repo}

# Create mock main session log (simplified JSONL)
cat > /tmp/test-debug-skill/projects/-tmp-test-repo/test-session-123.jsonl <<'EOF'
{"type":"user","message":"test message 1","timestamp":"2025-11-18T10:00:00Z"}
{"type":"assistant","message":"test response 1","timestamp":"2025-11-18T10:00:05Z"}
{"type":"tool","message":"Error: Test tool failure","timestamp":"2025-11-18T10:00:10Z"}
{"type":"user","message":"test message 2","timestamp":"2025-11-18T10:01:00Z"}
EOF

# Create mock agent log
cat > /tmp/test-debug-skill/projects/-tmp-test-repo/agent-abc123.jsonl <<'EOF'
{"type":"agentStart","agentId":"abc123","timestamp":"2025-11-18T10:00:15Z"}
{"type":"message","message":"Agent processing","timestamp":"2025-11-18T10:00:20Z"}
{"type":"error","message":"Agent encountered error","timestamp":"2025-11-18T10:00:25Z"}
EOF
```

### Test Execution

```bash
# Run skill with test directory
CLAUDE_DIR=/tmp/test-debug-skill python -c "
from skills.framework_debug import investigate_session
result = investigate_session(session_id='test-session-123', repo_path='/tmp/test-repo')
print(result)
"
```

### Test Validation

```bash
# Verify output contains:
# 1. Session ID identified correctly
# 2. Both main log and agent log found
# 3. Error messages extracted (tool failure + agent error)
# 4. Chronological timeline (10:00:00 → 10:00:05 → 10:00:10 → 10:00:15 → 10:00:20 → 10:00:25 → 10:01:00)
# 5. Clear reporting of what was found vs missing
```

### Test Cleanup

```bash
rm -rf /tmp/test-debug-skill
```

### Success Conditions

- [x] Test initially fails (skill doesn't exist yet)
- [ ] Test passes after implementation
- [ ] Test covers happy path (logs exist, well-formed)
- [ ] Test covers error case (log file missing)
- [ ] Test covers error case (malformed JSONL)
- [ ] Test validates chronological ordering
- [ ] Test is idempotent (can run repeatedly)
- [ ] Test cleanup leaves no artifacts

## Implementation Approach

### High-Level Design

**Agent-driven investigation** (not a script):

1. Agent invokes skill with investigation request (e.g., "what happened in last session?")
2. Skill provides **structured guidance** for agent to use Read/Grep/Bash tools
3. Agent executes investigation using provided commands
4. Agent synthesizes findings into narrative

**Why agent-driven?**: Follows "scripts are simple tools, agents orchestrate" pattern from SKILL.md Script Design section. Agent can adapt investigation based on findings, user can interrupt/redirect, maintains consistency with framework philosophy.

**Components**:

1. **Session Identifier**: Guide agent to find current/recent session ID from file timestamps
2. **Log Locator**: Provide commands to locate main + agent logs for a session
3. **Message Extractor**: Provide jq/grep patterns to filter by message type, time range, content
4. **Timeline Builder**: Guide agent to merge and sort messages chronologically
5. **Narrative Synthesizer**: Agent uses LLM to interpret timeline and explain "what happened"

**Data Flow**:
User request → Skill provides investigation steps → Agent executes with Read/Grep/Bash → Agent synthesizes narrative → User receives explanation

### Technology Choices

**Skill Type**: Claude Code skill (markdown-based, invoked via Skill tool)

**Agent Tools Used**:
- `Bash`: Find log files, check timestamps, count messages
- `Read`: Read log file contents (supports JSONL)
- `Grep`: Filter for specific patterns, error messages
- Built-in jq (if available): Parse JSONL fields

**Rationale**:
- No custom script needed - agent uses existing tools
- Skill provides investigation methodology, not implementation
- Follows framework pattern: "Reference, don't duplicate" tools
- Maximum flexibility - agent can adapt investigation based on findings

### Error Handling Strategy

**Fail-fast cases** (halt immediately):

- Log directory doesn't exist (`~/.claude/` not found)
- Session ID invalid format (if user provides explicit ID)
- Log file exists but is completely unreadable (permissions issue)

**Graceful degradation cases** (best effort):

- Some log files missing (report which files unavailable, continue with available)
- Malformed JSONL lines (skip bad lines, count and report them, continue with valid lines)
- Timestamp parsing failures (report messages without timestamps separately)
- Empty logs (report "no messages found in timeframe")

**Recovery mechanisms**:

- Always report what WAS found, even if incomplete
- Provide coverage metrics (e.g., "analyzed 450/500 lines, 50 lines malformed")
- Suggest alternative investigation paths if primary path fails

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: Log files too large (>100MB), reading entire file is slow/expensive
   - **Detection**: File size check before reading
   - **Impact**: Skill invocation slow, high token usage
   - **Prevention**: Use `tail` or `head` to read recent portion, provide line count guidance
   - **Recovery**: Agent can chunk reading with Read tool's offset/limit parameters

2. **Failure mode**: Multiple sessions active simultaneously, unclear which is "current"
   - **Detection**: Multiple recent session files with timestamps within minutes
   - **Impact**: Agent investigates wrong session
   - **Prevention**: Skill guides agent to list recent sessions with timestamps, ask user which to investigate
   - **Recovery**: User clarifies which session ID to investigate

3. **Failure mode**: Repository path encoding in directory name unclear (e.g., special characters)
   - **Detection**: Directory listing doesn't match expected pattern
   - **Impact**: Can't locate logs for current repository
   - **Prevention**: Skill provides multiple discovery strategies (exact match, fuzzy match, recent files)
   - **Recovery**: Agent lists available project directories, user selects

4. **Failure mode**: Agent logs from different sessions mixed in same directory
   - **Detection**: Agent log files don't clearly indicate which session they belong to
   - **Impact**: Include irrelevant agent messages in timeline
   - **Prevention**: Guide agent to check timestamps, correlation with main session timing
   - **Recovery**: Agent filters by timestamp range, reports potential ambiguity

## Monitoring and Validation

### How do we know it's working in production?

**Metrics to track**:

- Skill invocation frequency (how often is debugging needed?)
- Investigation completion rate (% of invocations that successfully extract logs)
- Time to first findings (how quickly does agent present initial timeline?)
- User satisfaction (qualitative - did investigation help solve problem?)

**Monitoring approach**:

- Track skill invocations via bmem (learning pattern: which issues trigger investigations)
- Log to experiments/LOG.md when skill identifies real bugs/issues
- User feedback after debugging sessions

**Validation frequency**: Quarterly review - is skill still relevant? Has log format changed?

## Documentation Requirements

### Code Documentation

- [ ] Skill markdown with clear invocation examples
- [ ] Documented jq patterns for common JSONL extractions
- [ ] Documented Bash commands for log discovery
- [ ] Troubleshooting section for common issues (logs not found, malformed, etc.)

### User Documentation

- [ ] Add to CORE.md: "For framework debugging, invoke `framework-debug` skill"
- [ ] Update framework/SKILL.md workflows section with debugging workflow reference
- [ ] Add example to skill: "When hook fails, investigate with this skill"

### Maintenance Documentation

- [ ] Known limitations (log format assumptions, size limits)
- [ ] Future improvements (structured error extraction, pattern recognition)
- [ ] Dependencies on Claude Code log format (if format changes, skill needs update)

## Rollout Plan

### Phase 1: Validation (Experiment)

- Create skill with basic investigation guidance
- Test on 3-5 recent debugging scenarios
- Verify agent can successfully extract relevant errors
- Document effectiveness in experiment log

**Criteria to proceed**: Agent successfully identifies errors in 4/5 test scenarios, investigation time <5 minutes

### Phase 2: Limited Deployment

- Add skill to framework skills directory
- Document in CORE.md
- Use for all framework debugging for 2 weeks
- Collect feedback on missing capabilities

**Criteria to proceed**: 2 weeks of use, skill invoked 3+ times, user reports time savings

### Phase 3: Full Deployment

- Refine based on feedback
- Add to standard framework troubleshooting workflow
- Document as "production" in framework
- Reduce monitoring to periodic review

**Rollback plan**: Remove skill, revert to manual log investigation (no dependencies, safe to remove)

## Risks and Mitigations

**Risk 1**: Log format changes break investigation commands

- **Likelihood**: Medium (Claude Code updates could change format)
- **Impact**: High (skill becomes non-functional)
- **Mitigation**: Document log format assumptions clearly, add version check, test on format changes

**Risk 2**: Skill adds more complexity than value (manual investigation faster)

- **Likelihood**: Low (current manual process is clearly painful)
- **Impact**: Medium (wasted development effort)
- **Mitigation**: Validate time savings in Phase 1, be willing to abandon if not valuable

**Risk 3**: Agent misinterprets logs, provides incorrect diagnosis

- **Likelihood**: Medium (LLM interpretation can be wrong)
- **Impact**: Medium (user wastes time on wrong path)
- **Mitigation**: Skill emphasizes "report what's found, don't diagnose" - agent shows raw errors, user interprets

## Open Questions

1. Should skill focus on current session only, or also recent sessions (last N or last day)?
   - **Proposal**: Default to current session, provide option for "recent sessions" (last 3 sessions or last 24 hours)

2. What's the ideal level of detail for timeline extraction - every message or just errors/tools?
   - **Proposal**: Configurable filter: "all", "errors only", "tools only", "errors and tools"

3. Should skill provide pre-built jq filters or teach agent to build them dynamically?
   - **Proposal**: Provide common patterns as examples, agent adapts as needed (maximum flexibility)

## Notes and Context

**Related to STATE.md P2 blocker**: Hook session logs removed (line 123), created potential debugging gap. This skill partially addresses that gap by making remaining logs more accessible.

**Aligns with ACCOMMODATIONS.md**: Multi-window context loss (line 30) - skill helps recover "what's running in each window" and "what happened in this session".

**Framework scope**: Works across ALL repositories (not just academicOps), consistent with VISION.md line 11-15.

---

## Completion Checklist

Before marking this task as complete:

- [ ] All success criteria met and verified
- [ ] Integration test passes reliably (>95% success rate)
- [ ] All failure modes addressed
- [ ] Documentation complete (code, user, maintenance)
- [ ] Experiment log entry created
- [ ] No documentation conflicts introduced
- [ ] Code follows AXIOMS.md principles (fail-fast, DRY, explicit)
- [ ] Monitoring in place and working
- [ ] Rollout plan executed successfully
- [ ] Framework ROADMAP.md updated with progress
