# GitHub Issue Quality Standards

**Audience**: Trainer agent and anyone managing academicOps issues

**Purpose**: Define what makes a "good" issue in academicOps - issues that serve as knowledge artifacts for future learning and decision-making.

## Core Principle

**Issues in academicOps are KNOWLEDGE ARTIFACTS, not just task trackers.**

- Issues document thinking, not just conclusions
- Issues enable future decision-making
- Issues track interventions and learnings
- Issues are reviewed during retrospectives

## What Makes a Good Issue

### 1. Complete Documentation

A good issue contains:

- **Executive summary** - What, why, status at a glance
- **Analysis** - Root causes at multiple layers
- **Solution design** - Multi-layer prevention strategies
- **Research** - External tools evaluated
- **Implementation** - Roadmap with specific files
- **Context** - Related issues and patterns
- **Reflections** - Learnings and open questions

### 2. Future-Reader Focus

Good issues are written for someone reading 6 months later:

- Can understand what happened without reading code
- Can see why decisions were made
- Can find related work through links
- Can learn from mistakes and solutions
- Can implement similar fixes elsewhere

### 3. Multi-Layer Analysis

Good issues analyze at multiple levels:

- **Surface**: What specifically failed?
- **Instructions**: Why didn't documentation prevent it?
- **Architecture**: What structural issues exist?
- **Technical**: What enforcement gaps remain?
- **Process**: What systemic patterns allowed this?
- **Meta**: What can we learn about our processes?

### 4. Actionable Roadmap

Good issues provide clear implementation guidance:

- Phased approach (immediate, short-term, long-term)
- Specific files to modify
- Risk assessment
- Success criteria
- Open questions for user decision

### 5. Proper Linkage

Good issues maintain connections:

- Link to related issues (patterns, dependencies)
- Link to commits that addressed the issue
- Link from commits back to issue (Fixes #N)
- Link to modified files in comments (for rename tracking)

## Issue Structure

### Issue Body

**Keep concise** - just enough to understand the problem:

- Brief failure summary
- Initial context
- Checklist of required documentation
- Links to related issues

**Example:**

```markdown
## Problem

Agent modified venv files despite policy in INSTRUCTIONS.md

## Context

- Date: 2025-10-10
- Occurred twice in same conversation
- Policy exists but insufficient

## Analysis Required (as comments)

- [ ] Root cause analysis
- [ ] Solution design
- [ ] External research
- [ ] Implementation roadmap
```

### Comments

**Use comments for detailed analysis** - keeps issue readable:

- Comment 1: Executive summary
- Comment 2: Root cause analysis
- Comment 3: Solution design
- Comment 4: External research
- Comment 5: Implementation roadmap
- Comment 6: Modified files (after implementation)
- Comment N: Learnings and reflections

## Issue Templates

Use provided templates to enforce standards:

- `.github/ISSUE_TEMPLATE/agent_failure_analysis.md` - For agent failures
- Additional templates as needed

Templates ensure:

- Required sections not forgotten
- Consistent structure across issues
- Checklist enforces completeness
- Future readers know what to expect

## Issue Lifecycle

### 1. Creation

**NEVER create empty issues**

- Search first (existing issue may exist)
- Use template if available
- Include initial context in body
- Add appropriate labels

### 2. Documentation

**Add analysis as structured comments**

- Don't cram everything into issue body
- Use separate comments for each analysis section
- Make comments self-contained (can be read independently)
- Link between related comments as needed

### 3. Implementation

**Track work in issue**

- Update status as work progresses
- Document decisions made
- Note deviations from plan
- Link to commits

### 4. Completion

**Verify before closing**

- [ ] All analysis documented
- [ ] Solution implemented or roadmap clear
- [ ] Modified files listed in comments
- [ ] Related issues linked
- [ ] Future reader can understand full context
- [ ] Learnings extracted

## Common Anti-Patterns

### ❌ Empty Issues

**Problem**: Issue created but no analysis added **Why bad**: Defeats purpose, false completion, no learning **Fix**: Add comprehensive analysis before considering "done"

### ❌ Issue Body Overload

**Problem**: All analysis crammed into issue body **Why bad**: Unreadable, hard to find specific analysis **Fix**: Use structured comments for detailed analysis

### ❌ Missing Context

**Problem**: Issue describes symptom but not underlying cause **Why bad**: Can't learn from it, can't prevent recurrence **Fix**: Multi-layer root cause analysis required

### ❌ No Research

**Problem**: Solution proposed without evaluating alternatives **Why bad**: May miss better approaches, no rationale for choice **Fix**: Document tools evaluated and why chosen

### ❌ Vague Implementation

**Problem**: "Fix the instructions" with no specifics **Why bad**: Future implementer doesn't know what to do **Fix**: Specific files, specific changes, phased roadmap

### ❌ Broken Links

**Problem**: Issues not linked to related work **Why bad**: Can't see patterns, duplicate work **Fix**: Always link related issues, commits, patterns

## Labels

Use labels to categorize and filter:

- `prompts` - Agent instruction improvements
- `agent-failure` - Documented agent failures
- `infrastructure` - Configuration, tooling, setup
- `documentation` - Docs improvements
- `process` - Workflow and process changes
- `needs-research` - Requires investigation
- `needs-decision` - User input needed

## Review Process

### Self-Review (Before Closing)

Ask yourself:

1. Can someone understand this in 6 months?
2. Is root cause analysis complete?
3. Are alternatives documented?
4. Is implementation roadmap clear?
5. Are related issues linked?
6. Are modified files tracked?

### Retrospective Review (Quarterly)

Review closed issues for:

- Patterns across failures
- Effectiveness of solutions
- Quality of documentation
- Process improvements needed
- Learnings to extract

## Success Metrics

A good issue:

- **Prevents recurrence** - Pattern fixed, not just instance
- **Enables learning** - Others can learn from reading
- **Guides implementation** - Clear roadmap to follow
- **Maintains links** - Connected to related work
- **Stays relevant** - Referenced in future work

A poor issue:

- No analysis documented
- Just tracks specific instance
- No implementation guidance
- Isolated (no links)
- Never referenced again

## Examples

### Good Issue Example: #87

See issue #87 for a model of comprehensive documentation:

- Executive summary in comment
- Multi-layer root cause analysis
- External tool research
- Phased implementation roadmap
- Meta-failure reflection
- Related issues linked

### Poor Issue Example (Hypothetical)

```markdown
Title: Agent made mistake Body: Agent did the wrong thing. Need to fix.
```

**What's missing:**

- What specifically happened?
- Why did it happen?
- What should be changed?
- How to prevent recurrence?
- Related patterns?

## Tools and Automation

### Issue Templates

- Enforce structure automatically
- Provide checklists
- Guide documentation

### GitHub CLI

- `gh issue list --search` - Find related issues
- `gh issue view` - Read existing context
- `gh issue comment` - Add analysis incrementally

### Future Automation

- Link detection (find related issues automatically)
- Completion verification (checklist enforcer)
- Pattern extraction (identify recurring themes)
- Quality scoring (measure issue completeness)

## Trainer Responsibilities

As the trainer agent, you are responsible for:

1. **Creating quality issues** - Use templates, document thoroughly
2. **Maintaining standards** - Review and improve issue quality
3. **Linking related work** - Connect issues to patterns
4. **Extracting learnings** - Use issues for process improvement
5. **Updating templates** - Improve based on experience

**Remember**: How well issues are documented directly impacts how much we learn from failures and how effectively we prevent recurrence.

## References

- Trainer agent instructions: `bot/agents/trainer.md`
- Issue template: `bot/.github/ISSUE_TEMPLATE/agent_failure_analysis.md`
- Example: Issue #87 (venv modification prevention)
