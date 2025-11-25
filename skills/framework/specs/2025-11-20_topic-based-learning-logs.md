# Task Spec: Topic-Based Learning Logs

**Date**: 2025-11-20
**Stage**: 2 (Scripted Tasks)
**Priority**: P1 (LOG.md becoming unmanageable, impacting context windows)

## Problem Statement

**What manual work are we automating?**

LOG.md has grown to 548 lines with 61 entries and continues growing indefinitely. When framework agents or /log command need to load learning patterns, they must process the entire file, wasting context window space. Additionally, discovering related patterns requires reading the entire log rather than leveraging semantic search capabilities.

**Why does this matter?**

1. **Context window waste**: Loading 548+ lines when only 20-50 relevant lines needed
2. **Poor discoverability**: Can't leverage bmem's semantic search to find related patterns
3. **Scalability**: File will become completely unmanageable as more patterns accumulate
4. **Natural clustering lost**: Related observations scattered throughout chronological log

**Who benefits?**

- Framework agents: Get relevant context efficiently without reading entire log
- /log command: Can route observations to topically-related content
- Nic: Better pattern discovery through semantic search across topic domains
- Framework maintenance: Related learnings grouped together for easier analysis

## Success Criteria

**The automation is successful when**:

1. No single learning file exceeds 200 lines (context window friendly)
2. bmem semantic search finds relevant patterns across topic files with >0.4 relevance
3. /log command successfully routes 90%+ of observations to correct topic file
4. Framework skill context loading retrieves only relevant topic files, not all learning content
5. INDEX.md stays under 150 lines while providing discovery mechanism

**Quality threshold**:
- Fail-fast if topic routing is ambiguous (ask user for clarification)
- Best-effort if multiple topics apply (pick primary, cross-reference in Relations)
- Never lose historical content (all migrations preserve full text)

## Scope

### In Scope

- Migrate existing LOG.md (61 entries) into topic-based files
- Create INDEX.md for recent highlights and topic directory
- Update /log command to route observations to topic files
- Design topic routing algorithm using bmem semantic similarity + tags
- Update framework SKILL.md to reference distributed learning files
- Create integration tests validating bmem discovery and topic routing

### Out of Scope

- Automatic topic creation (start with 6 predefined topics, expand manually)
- Changing LOG.md entry format (preserve existing structure)
- Migrating old experiment files beyond LOG.md
- Automated topic merging/splitting logic
- Cross-topic pattern analysis automation

**Boundary rationale**:

Per AXIOMS.md #1 (Do One Thing), this task focuses solely on reorganizing existing learning patterns for better context management. Topic taxonomy and advanced analytics are separate concerns to be addressed later if needed.

## Dependencies

### Required Infrastructure

- bmem MCP server operational (for semantic search)
- bmem format validator (`bmem_tools.py`) working
- Framework skill already uses bmem search (verified in analysis)
- /log command infrastructure exists
- Topic files must have valid bmem frontmatter

### Data Requirements

- LOG.md exists at `$ACA_DATA/projects/aops/experiments/LOG.md`
- All entries have required metadata: Date, Type, Pattern tags
- bmem database indexed (or will auto-index on creation)
- Topic routing needs example entries for similarity matching

**Fail-fast if**:
- LOG.md missing or corrupted
- bmem MCP server unavailable
- Topic file frontmatter validation fails

## Integration Test Design

**Test must be designed BEFORE implementation**

### Test 1: Topic Routing Accuracy

**Setup**:
```bash
# Create test observations covering different topics
mkdir -p tests/fixtures/learning-logs/
cat > tests/fixtures/learning-logs/test-observations.json <<EOF
{
  "git_safety": "Agent used --no-verify to bypass pre-commit validation",
  "bmem_integration": "Framework skill reads markdown files instead of using bmem search",
  "verify_first": "Agent stated confident diagnosis without checking git status first",
  "skill_invocation": "Agent bypassed skill instructions despite explicit invocation"
}
EOF
```

**Execution**:
```python
def test_topic_routing_accuracy():
    """Route observations to correct topic files based on content and tags"""
    with open("tests/fixtures/learning-logs/test-observations.json") as f:
        observations = json.load(f)

    routes = {}
    for topic, obs_text in observations.items():
        routes[topic] = route_to_topic(obs_text)

    assert routes["git_safety"] == "git-safety-quality-gates"
    assert routes["bmem_integration"] == "bmem-integration"
    assert routes["verify_first"] == "agent-behavior-patterns"
    assert routes["skill_invocation"] == "skill-invocation"
```

**Validation**:
- Routing accuracy >= 90%
- No observations routed to wrong topic
- Ambiguous cases flagged for manual review

### Test 2: Cross-File Discovery via bmem

**Setup**:
```bash
# Ensure topic files indexed in bmem
python3 bmem_tools.py sync --force
```

**Execution**:
```python
def test_bmem_cross_file_discovery():
    """Framework skill finds patterns across topic files via semantic search"""
    # Search for validation bypass patterns
    results = search_notes("validation bypass quality gates")

    # Should find entries in git-safety-quality-gates.md
    file_paths = [r.get("file_path") for r in results]
    assert any("git-safety-quality-gates.md" in path for path in file_paths)

    # Check relevance scores
    relevant_results = [r for r in results if r.get("relevance", 0) > 0.4]
    assert len(relevant_results) > 0
```

**Validation**:
- Semantic search finds patterns across multiple topic files
- Relevance scores > 0.4 for actual matches
- Search doesn't require knowing exact file name

### Test 3: INDEX.md Size Bounded

**Setup**:
```bash
# After migration, check INDEX.md size
```

**Execution**:
```python
def test_index_size_bounded():
    """INDEX.md stays under 150 lines after migration"""
    index_path = Path(os.getenv("ACA_DATA")) / "projects/aops/experiments/INDEX.md"

    with open(index_path) as f:
        lines = f.readlines()

    assert len(lines) < 150, f"INDEX.md has {len(lines)} lines, exceeds 150 limit"

    # Verify it's still valid bmem format
    result = subprocess.run(
        ["python3", "bmem_tools.py", "validate", str(index_path)],
        capture_output=True
    )
    assert result.returncode == 0
```

**Validation**:
- INDEX.md < 150 lines
- Valid bmem frontmatter
- Contains recent entries + topic directory

### Test 4: /log Command Uses Topic Routing

**Setup**:
```bash
# Create test environment
export ACA_DATA="$(pwd)/tests/fixtures/learning-logs"
mkdir -p "$ACA_DATA/projects/aops/experiments/learning"
```

**Execution**:
```python
def test_log_command_topic_routing():
    """Verify /log creates entries in topic files, not monolithic LOG.md"""
    observation = "Agent used git reset --hard without user permission"

    # Invoke /log (via SlashCommand tool)
    result = invoke_log_command(observation)

    # Should route to git-safety topic
    assert "git-safety-quality-gates.md" in result.file_path
    assert "learning/" in result.file_path

    # Entry should have valid frontmatter
    assert validate_bmem_entry(result.entry)
```

**Validation**:
- Observation routed to correct topic file
- No entries added to old LOG.md
- bmem frontmatter valid

### Success Conditions

- [x] Test 1 initially fails (no routing logic exists)
- [ ] Test 1 passes after implementation (90%+ accuracy)
- [x] Test 2 initially fails (content not distributed yet)
- [ ] Test 2 passes after migration (semantic search works)
- [x] Test 3 initially fails (INDEX.md doesn't exist)
- [ ] Test 3 passes after implementation (bounded size)
- [x] Test 4 initially fails (/log still uses LOG.md)
- [ ] Test 4 passes after update (routes to topics)
- [ ] All tests idempotent (can run repeatedly)
- [ ] Cleanup leaves no artifacts

## Implementation Approach

### High-Level Design

**Architecture**: Distributed learning files with semantic search discovery

**Components**:

1. **Topic Analyzer**: Determines which topic file an observation belongs to
   - Uses bmem semantic similarity against example entries
   - Analyzes pattern tags for topic matching
   - Returns topic slug + confidence score

2. **Migration Script**: One-time conversion of LOG.md → topic files
   - Reads all 61 entries from LOG.md
   - Routes each to appropriate topic file
   - Preserves all metadata and content
   - Creates INDEX.md with recent highlights

3. **Enhanced /log Command**: Routes new observations to topic files
   - Invokes Topic Analyzer
   - Appends to appropriate learning/[topic].md
   - Optionally adds summary to INDEX.md
   - Cross-references related topics via Relations

4. **INDEX.md Generator**: Creates discovery document
   - Last 10-15 entries across all topics
   - Topic directory with descriptions
   - Cross-references to topic files

**Data Flow**:

```
Observation → Topic Analyzer → Topic File
                ↓
          (if significant)
                ↓
           INDEX.md
```

### Technology Choices

**Language/Tools**: Python with uv (for migration script + topic analyzer)

**Libraries**:
- `mcp__bmem__search_notes` - Semantic similarity matching
- Standard library (pathlib, json, re) - File operations
- `bmem_tools.py` - Validation

**Rationale**:
- Python for complex routing logic (vs bash)
- bmem MCP for semantic search (already available)
- No new dependencies (use existing framework tools)

### Initial Topic Taxonomy

Based on analysis of 61 existing entries, start with 6 topics:

1. **agent-behavior-patterns.md** - Generic agent patterns (verify-first, overconfidence, shortcuts)
2. **git-safety-quality-gates.md** - Git operations, validation bypass, pre-commit hooks
3. **bmem-integration.md** - bmem usage, mental models, format issues
4. **framework-infrastructure.md** - Paths, file locations, repo organization
5. **skill-invocation.md** - Skill loading, instruction following, workflow violations
6. **component-design.md** - Individual component successes/failures

**Topic file template**:

```markdown
---
title: [Topic Name]
permalink: aops-learning-[topic-slug]
type: learning-log
tags: [aops, learning, [topic-specific-tags]]
---

# [Topic Name]

## Context

Learning patterns related to [topic description]. Part of distributed learning logs using bmem semantic search for discovery.

## Observations

[Individual log entries in standard format]

## Relations

- part_of [[Learning Patterns Index]]
- relates_to [[Other Related Topics]]
```

### Error Handling Strategy

**Fail-fast cases** (halt immediately):

- LOG.md missing or unreadable
- Topic file frontmatter validation fails
- bmem MCP server unavailable
- Observation cannot be routed (multiple topics with similar confidence)

**Graceful degradation cases**:

- Low confidence routing (0.3-0.5) → Ask user for clarification
- Missing pattern tags → Use semantic similarity only
- INDEX.md size approaching limit → Warn, suggest archiving old entries

**Recovery mechanisms**:

- Migration script is idempotent (can re-run safely)
- All original LOG.md content preserved until verification complete
- Topic routing failures logged for manual review
- Rollback: Restore LOG.md, remove topic files

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: Topic routing incorrectly categorizes observation
   - **Detection**: User notices entry in wrong file during review
   - **Impact**: Pattern harder to discover, slight organization mess
   - **Prevention**: 90% accuracy threshold, confidence scoring, user review for low confidence
   - **Recovery**: Move entry to correct file, update Relations cross-references

2. **Failure mode**: Migration script loses content during conversion
   - **Detection**: Line count validation (61 entries in → 61 entries out)
   - **Impact**: Critical - historical knowledge lost
   - **Prevention**: Dry-run mode, preserve original LOG.md until verified, checksum validation
   - **Recovery**: Restore from git history, re-run migration with fixes

3. **Failure mode**: bmem search doesn't find patterns after distribution
   - **Detection**: Test 2 fails (semantic search broken)
   - **Impact**: Primary benefit lost, worse than original
   - **Prevention**: Verify bmem indexing works, test search before/after migration
   - **Recovery**: Force re-sync bmem database, verify frontmatter validity

4. **Failure mode**: INDEX.md grows beyond size limit
   - **Detection**: Test 3 fails, file size monitoring
   - **Impact**: Context window problem returns
   - **Prevention**: Archive old entries, keep only recent highlights
   - **Recovery**: Prune older entries from INDEX.md, they remain in topic files

5. **Failure mode**: New topic needed but taxonomy doesn't include it
   - **Detection**: Observations consistently route to multiple topics with low confidence
   - **Impact**: Suboptimal organization, doesn't prevent logging
   - **Prevention**: Monitor routing failures, flag patterns needing new topics
   - **Recovery**: Create new topic file, migrate related entries, update taxonomy

## Monitoring and Validation

### How do we know it's working in production?

**Metrics to track**:

- Topic routing accuracy: % of observations user agrees with routing
- File size distribution: Max/avg lines per topic file
- INDEX.md size: Track over time, warn at 120 lines
- bmem search quality: Relevance scores for pattern discovery queries
- Routing confidence: Distribution of confidence scores

**Monitoring approach**:

- Log all routing decisions with confidence scores
- Monthly review of topic file sizes
- Quarterly review of topic taxonomy (need new topics? merge existing?)
- User feedback when moving entries between topics

**Validation frequency**:
- Automated: Every /log invocation logs routing decision
- Manual: Monthly review of topic organization
- Alert: If any topic file exceeds 180 lines (approaching 200 limit)

## Documentation Requirements

### Code Documentation

- [ ] Topic Analyzer docstrings (inputs, outputs, confidence scoring)
- [ ] Migration script usage instructions
- [ ] Inline comments for routing algorithm
- [ ] Type hints for all functions

### User Documentation

- [ ] Update framework SKILL.md Strategic Partner context loading
  - Remove reference to single LOG.md
  - Document distributed learning files + bmem search
- [ ] Update /log command to document topic routing
- [ ] Create INDEX.md with topic directory
- [ ] Update README.md experiments/ section

### Maintenance Documentation

- [ ] Topic taxonomy definition and evolution guidelines
- [ ] When to create new topics vs use existing
- [ ] How to manually reroute misplaced entries
- [ ] Migration rollback procedure

## Rollout Plan

### Phase 1: Validation (Experiment)

**Actions**:
1. Create topic taxonomy (6 initial topics)
2. Implement Topic Analyzer algorithm
3. Write integration tests (must fail initially)
4. Run migration script in dry-run mode
5. Validate routing accuracy on 20 sample entries

**Criteria to proceed**:
- Tests written and failing appropriately
- Dry-run completes without errors
- Sample routing accuracy >= 85%
- No content lost in dry-run

### Phase 2: Migration Execution

**Actions**:
1. Backup LOG.md to safe location
2. Run migration script (real mode)
3. Verify 61 entries → 61 entries in topic files
4. Force bmem re-sync
5. Run integration tests
6. Manual spot-check of 10 random entries

**Criteria to proceed**:
- All 4 integration tests pass
- No content lost (checksum validation)
- bmem search finds patterns across files
- Spot-check confirms correct routing

### Phase 3: Update /log Command

**Actions**:
1. Update /log command to use Topic Analyzer
2. Test with 5 new observations
3. Verify routing + bmem cross-references work
4. Update documentation

**Criteria to proceed**:
- New observations route correctly
- INDEX.md stays under 150 lines
- Framework skill loads context efficiently

### Phase 4: Framework Documentation Update

**Actions**:
1. Update framework SKILL.md Strategic Partner section
2. Update README.md experiments structure
3. Archive old LOG.md with note pointing to new structure
4. Document in bmem

**Rollback plan**:
- Restore LOG.md from backup
- Delete topic files
- Revert /log command changes
- Re-sync bmem database

**Rollback trigger**: Any of these conditions:
- Content loss detected during migration
- bmem search completely broken
- Topic routing accuracy < 70%
- Integration tests fail after migration

## Risks and Mitigations

**Risk 1**: Topic taxonomy too rigid, doesn't adapt to new patterns

- **Likelihood**: Medium
- **Impact**: Medium (can work around by manually creating new topics)
- **Mitigation**: Start with 6 broad topics, document topic creation process, monitor routing failures
- **Fallback**: Create "uncategorized.md" catchall for ambiguous entries

**Risk 2**: bmem semantic search doesn't work well with distributed files

- **Likelihood**: Low (bmem designed for this)
- **Impact**: High (defeats entire purpose)
- **Mitigation**: Test 2 validates this works before migration, can rollback if broken
- **Fallback**: Revert to monolithic LOG.md, investigate bmem issues separately

**Risk 3**: Migration loses content

- **Likelihood**: Low (careful validation)
- **Impact**: Critical (institutional knowledge lost)
- **Mitigation**: Dry-run mode, checksums, preserve original, git version control
- **Fallback**: Restore from git history + backup

**Risk 4**: Topic files grow beyond limits anyway

- **Likelihood**: Medium-High (popular topics accumulate entries)
- **Impact**: Low-Medium (problem returns gradually)
- **Mitigation**: Monitor file sizes, sub-divide popular topics if needed, archive old entries
- **Fallback**: Further subdivide topics (e.g., git-safety → git-safety-validation, git-safety-operations)

**Risk 5**: User disagrees with routing, too much manual correction needed

- **Likelihood**: Medium
- **Impact**: Low (entries still logged, just in suboptimal location)
- **Mitigation**: Low-confidence routing asks for user input, easy to move entries between files
- **Fallback**: Allow manual topic override flag in /log command

## Implementation Checklist

### Pre-Implementation

- [x] Spec written and reviewed
- [ ] Topic taxonomy defined (6 initial topics)
- [ ] Integration tests written (4 tests, all failing)
- [ ] Migration script dry-run mode implemented

### Implementation

- [ ] Topic Analyzer algorithm implemented
- [ ] Migration script (real mode) implemented
- [ ] INDEX.md generator implemented
- [ ] /log command updated with routing
- [ ] All 4 integration tests passing

### Post-Implementation

- [ ] LOG.md migrated successfully (61 → 61 entries verified)
- [ ] bmem re-synced and validated
- [ ] Framework SKILL.md updated
- [ ] README.md updated
- [ ] Experiment log entry created
- [ ] Document in bmem via bmem skill

## Success Metrics (30-day check-in)

After 30 days of using topic-based logs:

1. **Context efficiency**: Average topic file loaded < 200 lines (vs 548+ for old LOG.md)
2. **Discovery quality**: User successfully finds patterns via bmem search 80%+ of queries
3. **Routing accuracy**: User agrees with topic routing 90%+ of time
4. **Scalability**: No topic file approaching 200-line limit
5. **Usability**: Zero complaints about inability to find historical patterns

**If metrics not met**: Analyze failures, adjust topic taxonomy or routing algorithm, consider rollback if fundamentally broken
