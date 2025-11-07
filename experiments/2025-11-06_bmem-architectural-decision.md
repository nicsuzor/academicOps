# Architectural Decision: Adopt bmem (basic-memory) as Core Knowledge System

## Metadata

- Date: 2025-11-06
- Issue: #193
- Commit: [to be added]
- Model: claude-sonnet-4-5-20250929
- Type: Architectural decision (documentation)

## Context

**Problem**: Documentation fragmentation and inefficient context loading

- Documentation scattered across chunks/, docs/, references/, skills/
- SessionStart loads entire instruction trees (high token cost)
- Limited cross-repository context visibility
- No learning loops (static documentation)

**Previous State**:

- Phases 1-2 complete in writing repo (infrastructure + task conversion)
- 280 tasks migrated to markdown with YAML frontmatter
- bmem MCP server installed and functional
- Proof-of-concept validated (<1s search time)

## Decision Statement

**Adopt `basic-memory` (internal ref: `bmem`) as the core knowledge organization system for academicOps framework and $ACADEMICOPS_PERSONAL repositories.**

**Naming Convention**:

- Package: `basic-memory`
- Internal reference: `bmem` (avoids confusion with 'buttermilk')
- MCP server: `basic-memory`

## Rationale

**Problems Solved**:

1. **Documentation Discoverability**: Vector search enables concept discovery
2. **Token Efficiency**: Just-in-time loading vs load-all SessionStart
3. **Cross-Repository Context**: Unified knowledge graph (aops + personal)
4. **Learning Loops**: Agents update concepts from experiment outcomes
5. **Task Management**: Markdown-first workflow with semantic search

**Evidence from Phases 1-2**:

- ✅ Search working: <1s response time, relevant results
- ✅ Task conversion: 280 tasks → markdown preserving all metadata
- ✅ MCP integration: write_note, search_notes functional
- ✅ Cross-project config: "aops" and "ns" projects working

## Changes Made

### 1. Documentation Updates

**chunks/INFRASTRUCTURE.md**:

- Added "Knowledge Organization (bmem)" section
- Documented MCP server tools
- Specified project names (aops, ns)
- Added directory conventions for concepts/ and data/tasks_md/
- Referenced Issue #193 for integration status

**README.md**:

- Added "6. Knowledge Organization (bmem)" to Core Principles
- Explained vector search + relational mapping
- Documented integration architecture
- Listed benefits (token cost, discoverability, learning loops)
- Marked status as "Integration in progress (Issue #193)"

### 2. GitHub Issue Documentation

**Issue #193 Comment**:

- Formal architectural decision statement
- Complete rationale with problems solved
- Integration architecture (repos, directory structure, MCP tools)
- Changes required (Phases 3-7 breakdown)
- Success criteria (functional + non-functional)
- Risk analysis with mitigations
- Timeline estimate (~6-9 hours remaining)
- Documentation update requirements

## Success Criteria

**Documentation**:

- [x] INFRASTRUCTURE.md includes bmem section
- [x] README.md includes bmem in Core Principles
- [x] Issue #193 updated with formal decision
- [ ] ARCHITECTURE.md updated (future: when implementation progresses)

**Implementation** (deferred to Phases 3-7):

- [ ] Task management scripts using bmem
- [ ] Concept graph extraction
- [ ] Skills rewrite with bmem integration
- [ ] E2E testing
- [ ] Performance validation

## Results

**Documentation Changes**:

- ✅ chunks/INFRASTRUCTURE.md: Added 19 lines (bmem section + integration note)
- ✅ README.md: Added 26 lines (Core Principle #6)
- ✅ Issue #193: Comprehensive architectural decision documented

**No Code Changes**: This experiment documents the decision; implementation follows in subsequent experiments.

**Review Points**:

1. Is bmem terminology clear (vs "basic-memory")?
2. Is the integration architecture well-documented?
3. Are success criteria appropriate?
4. Should any other core docs be updated now?

## Outcome

**Success (Documentation)** - Architectural decision formally adopted and documented.

**Next Steps**:

1. User review and approval
2. Proceed with Phase 3 (task management scripts)
3. Continue through Phases 4-7 as separate experiments
4. Update ARCHITECTURE.md when implementation progresses

**Note**: This is a SPECIFICATION experiment (documents decision), not an IMPLEMENTATION experiment. Implementation tracked in separate experiment logs per phase.

## References

- Issue #193: https://github.com/nicsuzor/academicOps/issues/193
- Phases 1-2 log: /home/nic/src/writing/experiments/2025-11-06_bm-integration.md
- basic-memory repo: https://github.com/cyanheads/basic-memory
