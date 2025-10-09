---
name: Agent Failure Analysis
about: Document systematic analysis of agent failures and systemic improvements
title: '[AGENT FAILURE] '
labels: prompts, agent-failure
assignees: ''
---

## Failure Summary

**What failed**: [Brief description]

**When**: [Date/conversation/context]

**Severity**: [Critical/High/Medium/Low]

**Root cause category**: [Instructions/Architecture/Technical/Process/Tooling]

## Initial Context

[Describe what happened - the specific instance that revealed the systemic issue]

## Analysis Checklist

Before closing this issue, the following MUST be documented in comments:

- [ ] **Root cause analysis** - Multi-layer analysis (instructions, architecture, technical, process)
- [ ] **Solution design** - Multi-layer prevention strategy (config, hooks, docs, monitoring)
- [ ] **External tool research** - Tools evaluated, pros/cons, recommendations
- [ ] **Implementation roadmap** - Phased approach with specific files to modify
- [ ] **Related issues** - Links to connected work and patterns
- [ ] **Modified files** - List of all files changed with brief descriptions

## Documentation Requirements

**Add these as separate comments (not in issue body):**

### 1. Executive Summary Comment
- What failed (brief)
- Root causes identified
- Solution approach
- Current status

### 2. Root Cause Analysis Comment
- Layer 1: What specifically failed?
- Layer 2: Why did instructions not prevent it?
- Layer 3: What architectural gaps exist?
- Layer 4: What technical enforcement is missing?
- Layer 5: What external tools could help?

### 3. Solution Design Comment
- Layer 1: Configuration-based prevention
- Layer 2: Technical enforcement (hooks, permissions)
- Layer 3: Documentation/education
- Layer 4: Monitoring and detection
- Benefits and limitations of each layer

### 4. External Research Comment
- Tools evaluated (with links)
- Pros and cons of each
- Recommendations (with rationale)

### 5. Implementation Roadmap Comment
- Phase 1: Immediate fixes
- Phase 2: Structured infrastructure
- Phase 3: Documentation
- Phase 4: Long-term maintenance
- Specific files to modify
- Risk assessment

### 6. Files Modified Comment (After Implementation)
- List all modified files
- Note renames/moves
- Brief description of changes
- Confirm index updated

## Related Issues

[Link to related issues - patterns, dependencies, similar failures]

## Open Questions

[Unresolved decisions, trade-offs to discuss, areas needing user input]

---

**Note**: This template enforces the standard that issues are knowledge artifacts, not just task trackers. Future agents and reviewers should be able to understand the full context, analysis, and solution from reading this issue.
