---
name: agent-optimization
description: This skill should be used when reviewing and improving agents, skills, hooks, permissions, and configurations. It enforces an experiment-driven, anti-bloat approach with enforcement hierarchy of Scripts, Hooks, Config, then Instructions. The skill prevents adding repetitive or overly specific instructions, understands how different enforcement mechanisms fit together, and makes strategic decisions about where to intervene. Use this skill when agent performance issues arise, when evaluating new techniques, or when maintaining the agent framework. Always test before claiming something works. Specific to academicOps framework.
---

# Agent Optimization

You are responsible for agent performance in the @nicsuzor/academicOps project.

## Overview

Maintain and optimize agent framework performance through surgical, experiment-driven interventions. This skill enforces anti-bloat principles, prioritizes architectural solutions over instructions, and ensures changes are tested rather than speculated.

## When to Use This Skill

Use agent-optimization when:

1. **Agent performance issues** - Agent violated standards or instructions
2. **Framework improvements** - Proposing new techniques or tools
3. **Bloat prevention** - Reviewing proposed instruction additions
4. **Architecture decisions** - Choosing between scripts/hooks/config/instructions
5. **Experiment evaluation** - Analyzing test results and metrics

**Concrete trigger examples**:

- "Agent X didn't follow instruction Y - how do we fix this?"
- "Should we add these 50 lines to the agent instructions?"
- "I found a new prompting technique - should we adopt it?"
- "This agent keeps making the same mistake"
- "Evaluate whether this change actually improved performance"

**Core principle**: We NEVER know if something will work until we test it. Embrace uncertainty with rigorous experiments.

## Core Philosophy

### 1. Experiment-Driven Development

**We don't know until we test**:

- No speculation about what "will work"
- Every change requires evaluation metric
- Test with real conversations, not theory
- Document outcomes in experiments dataset

**Single change per intervention**:

- One variable at a time
- Explicit success/failure criteria
- Before/after metrics comparison
- No wholesale rewrites

### 2. Anti-Bloat: Enforcement Hierarchy

**Scripts > Hooks > Config > Instructions** (Most → Least Reliable):

1. **Scripts**: Code that prevents bad behavior (MOST reliable)
2. **Hooks**: Automated checks at key moments
3. **Configuration**: Permissions, tool restrictions
4. **Instructions**: LAST resort (agents forget in long conversations)

**If agents consistently disobey instruction → Move enforcement UP**

### 3. Modular Documentation (DRY)

**ONE canonical source per concept**:

- If content appears in >1 place, that's a BUG
- Reference, don't duplicate
- Default: DELETE documentation rather than add
- Longer ≠ Better (LLMs get lost in bloat)

### 4. Surgical Interventions

**Maximum 3 changes** per intervention:

- Small, precise modifications (<10 lines)
- New files minimal (<50 lines)
- Larger changes → GitHub issue for discussion
- No sweeping rewrites

## Follow Agent Optimization Workflow

### Phase 1: Investigation & Diagnostics

**Objective**: Understand root cause, not symptoms.

**Process**:

1. **Analyze the problem**:
   - What specific behavior failed?
   - What was the agent trying to do?
   - What should have happened?

2. **MANDATORY: Search GitHub** (3+ searches):

   ```bash
   gh issue list --repo nicsuzor/academicOps --search "keyword1"
   gh issue list --repo nicsuzor/academicOps --search "keyword2"
   gh issue list --repo nicsuzor/academicOps --search "keyword3"
   ```

   - Search for patterns, not specific symptoms
   - Find related issues
   - Check if this has happened before

3. **Reconstruct agent's context**:
   - What instructions did the agent have?
   - What documentation was available?
   - Was it clear and sufficient?
   - Read the actual files agent would have seen

4. **Identify root cause** (one level deep):
   - Documentation gap?
   - Unclear instruction?
   - Missing guardrail?
   - Infrastructure issue?

5. **MANDATORY: Document diagnostics in GitHub**:

   ```bash
   gh issue comment [number] --repo nicsuzor/academicOps --body "$(cat <<'EOF'
   ## Diagnostic Analysis

   **Problem Instance:** [What specifically failed]
   **Agent Context:** [What information/instructions agent had]
   **Root Cause:** [Why it happened - one level deep]
   **Related Issues:** [Links from search results]

   Solution design will follow in separate comment.
   EOF
   )"
   ```

**WHY MANDATORY**: Protects work if interrupted, creates knowledge artifact, separates facts from opinions.

**Checkpoint**: Did you post diagnostic comment? If NO, STOP.

### Phase 2: Solution Design

**Objective**: Choose MINIMUM intervention following enforcement hierarchy.

**Process**:

6. **MANDATORY: Enforcement Hierarchy Decision Tree**:

   ```
   START: Agent behavior problem identified
   ↓
   Q1: Can SCRIPTS prevent this?
       (e.g., validation script, automation tool)
   YES → Design script solution, SKIP instructions
   NO ↓

   Q2: Can HOOKS enforce this?
       (e.g., pre-commit, SessionStart validation)
   YES → Design hook solution, SKIP instructions
   NO ↓

   Q3: Can CONFIGURATION block this?
       (e.g., .claude/settings.json permissions)
   YES → Design config solution, SKIP instructions
   NO ↓

   Q4: Is this truly instruction-only territory?
   YES → Proceed to Anti-Bloat Protocol (Step 7)
   NO → STOP. Missed architectural solution. Go back to Q1.
   ```

   **Document your answers** to Q1-Q4 in GitHub.

7. **IF instructions necessary → Anti-Bloat Protocol**:

   **Before adding >10 lines, verify ALL**:

   - [ ] **Hierarchy Check**: Verified Q1-Q4 show NO architectural solution
   - [ ] **Bloat Estimate**: Calculated token cost vs writing code
   - [ ] **Modularity**: Can this be separate referenced doc?
   - [ ] **DRY Check**: Does similar guidance exist elsewhere?
   - [ ] **CRITICAL DRY**: Repeating _CORE.md or other agent? Use brief reference instead
   - [ ] **Complexity Budget**: File stays under 500 lines
   - [ ] **Justification**: Documented WHY code/config/hooks won't work

   **AXIOM: DO NOT REPEAT YOURSELF**:
   - Longer instructions NOT more effective
   - If _CORE.md has it → REFERENCE (don't duplicate)
   - Example: "See _CORE.md Axiom #4" NOT 85 lines restating

   **If adding >50 lines**:
   - STOP immediately
   - Create GitHub issue
   - Get user approval
   - This is architectural bloat requiring discussion

8. **Research solutions**:
   - Investigate technical approaches
   - Read relevant documentation
   - Test assumptions
   - Consider constraints (context budget, CWD limitations)

9. **MANDATORY: Document solutions in GitHub** (separate comment):

   ```bash
   gh issue comment [number] --repo nicsuzor/academicOps --body "$(cat <<'EOF'
   ## Solution Design

   **Enforcement Hierarchy Decisions**:
   - Q1 (Scripts): [Answer + justification]
   - Q2 (Hooks): [Answer + justification]
   - Q3 (Config): [Answer + justification]
   - Q4 (Instructions): [Answer + justification]

   **Options Evaluated**:
   1. Script approach: [Pros/cons]
   2. Hook approach: [Pros/cons]
   3. Config approach: [Pros/cons]
   4. Instruction approach: [Pros/cons + bloat cost]

   **Recommendation**: [Choice with justification]

   **Implementation Plan**:
   - Changes: [Specific modifications]
   - Test criteria: [How to evaluate]
   - Rollback plan: [If experiment fails]
   EOF
   )"
   ```

**Checkpoint**: Posted solution design? If NO, STOP.

### Phase 3: Implementation

**Objective**: Make surgical changes and test.

**Process**:

10. **Implement changes** (max 3 edits):
    - Modify specific files
    - Keep changes small (<10 lines each)
    - Use Edit tool for precision

11. **Create experiment log**:

    ```markdown
    # bot/experiments/YYYY-MM-DD_name.md

    ## Metadata
    - Date: YYYY-MM-DD
    - Issue: #NNN
    - Commit: [hash]
    - Model: [claude-sonnet-4-5/gemini-2.0-flash]

    ## Hypothesis
    [What you expect to happen]

    ## Changes Made
    [Specific modifications]

    ## Success Criteria
    [How to measure if this worked]

    ## Results
    [To be filled after testing]

    ## Outcome
    [Success/Failure/Partial]
    ```

12. **Commit changes**:

    ```bash
    git add bot/agents/[file].md
    git add bot/experiments/YYYY-MM-DD_name.md
    git commit -m "experiment(agent): [description]

    Issue #NNN - [Brief explanation]

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>"
    ```

13. **Test with real conversations**:
    - Run actual scenarios
    - Measure against success criteria
    - Document variance (LLMs are non-deterministic)
    - Update experiment log with results

### Phase 4: Evaluation

**Objective**: Measure impact, decide keep/revert/iterate.

**Process**:

14. **Collect metrics**:
    - Success rate over multiple runs
    - User feedback
    - Error rates
    - Before/after comparison

15. **Update experiment log**:
    - Document results
    - Mark outcome (Success/Failure/Partial)
    - Note unexpected findings
    - Recommend next steps

16. **Decide**:
    - **Success** → Keep changes, close issue
    - **Failure** → Revert changes, document why, try different approach
    - **Partial** → Iterate with refinements

17. **Update GitHub issue**:

    ```bash
    gh issue comment [number] --repo nicsuzor/academicOps --body "$(cat <<'EOF'
    ## Experiment Results

    **Outcome**: [Success/Failure/Partial]

    **Metrics**:
    - [Metric 1]: [Before] → [After]
    - [Metric 2]: [Before] → [After]

    **Findings**:
    [What we learned]

    **Decision**: [Keep/Revert/Iterate]

    **Next Steps**: [If any]
    EOF
    )"
    ```

## Framework Architecture Understanding

### Components & Their Roles

**Skills** (`.claude/*/SKILL.md`):

- Atomic, reusable workflows
- Portable across projects
- Invoked by agents
- Should NOT duplicate agent instructions

**Agents** (`agents/*.md`):

- Orchestrate skills
- Light on procedural detail (reference skills)
- Agent-specific context and authority
- Load via Task tool

**Hooks** (`.claude/settings.json`):

- `SessionStart`: Validate environment, load context
- `PreToolUse`: Check permissions before tool use
- `PostToolUse`: React to tool results
- `UserPromptSubmit`: Intercept before processing
- Configure in settings.json

**Permissions** (`.claude/settings.json`):

- Tool restrictions (e.g., `Bash(git:*)`)
- Subagent permissions
- Model selection
- Configured per agent/skill

**Commands** (`.claude/commands/*.md`):

- Slash commands that expand to prompts
- User-facing shortcuts
- Load specific workflows

**Configuration** (`.claude/settings.json`, `.gemini/settings.json`):

- Client-specific settings
- Permission rules
- Hook configurations
- Model preferences

### Decision Matrix: Where to Intervene

**Agent keeps forgetting to X**:

1. Can we write a script that does X automatically? → Script
2. Can we hook the moment before X is needed? → Hook
3. Can we block Y until X happens? → Config
4. Only if none above → Add instruction (with DRY check)

**New workflow to add**:

1. Is it reusable across projects? → Skill
2. Is it agent-specific authority/orchestration? → Agent (referencing skills)
3. Is it user shortcut? → Command

**Validation needed**:

1. Can run automatically at key moment? → Hook
2. Needs human decision? → Instruction to use skill

## Analyzing Subagent Execution Logs

### When to Use Log Analysis

Inspect subagent execution logs when investigating:

1. **Instruction adherence**: Did agent follow workflow guidelines? Did it skip steps?
2. **Delegation patterns**: For supervisor agents, did it delegate to subagents as designed? Or did it attempt solo execution?
3. **Unexpected behavior**: Agent produced wrong output or took unexpected path
4. **Tool usage**: What exact commands/tools did agent invoke? Did it make atomic commits or batch changes?
5. **Git operations**: Verify agent didn't run destructive commands or force pushes

### Locating Logs

Log files are stored in Claude Code project directory structure. Use environment variables rather than hardcoded paths:

```bash
# Find main session log (lists all tool calls and subagent invocations)
ls -t "${CLAUDE_HOME:-$HOME/.claude}"/projects/[project-dir]/*.jsonl | head -1

# When Task tool invoked (main session), response contains agentId:
# Line N: Task tool call
# Line N+3: Response with agentId field
cat session-id.jsonl | jq 'select(.message.content) | .message.content[] | select(.type == "tool_use" and .name == "Task") | .input.skill'

# Find corresponding subagent log using the agentId from Task response:
cat "${CLAUDE_HOME:-$HOME/.claude}"/projects/[project-dir]/agent-[agentId].jsonl
```

### Extracting Tool Call Sequences

Review what tools agent actually invoked:

```bash
# All tool calls from subagent
cat agent-[agentId].jsonl | jq -r 'select(.type == "assistant") | .message.content[] | select(.type == "tool_use") | .name' | sort | uniq -c

# Specific skill/task delegation (shows agent orchestration)
cat agent-[agentId].jsonl | jq 'select(.type == "assistant") | .message.content[] | select(.type == "tool_use" and (.name == "Skill" or .name == "Task")) | {name, input: {skill: .input.skill, command: .input.command}}'

# Git operations (verify workflow compliance)
cat agent-[agentId].jsonl | jq -r 'select(.type == "assistant") | .message.content[] | select(.type == "tool_use" and .name == "Bash") | .input.command' | grep -E "^git"

# File modifications (Edit/Write calls)
cat agent-[agentId].jsonl | jq 'select(.type == "assistant") | .message.content[] | select(.type == "tool_use" and (.name == "Edit" or .name == "Write")) | {name, file_path: .input.file_path}'
```

### Pattern Detection Checklist

Use log analysis to identify:

- **Workflow adherence**: Did agent follow experiment → test → commit cycle?
- **Delegation success**: For supervisor agents, count Task calls to subagents
- **Atomic operations**: Single commit per logical change, or batch modifications?
- **Instruction violations**: Look for git force-push, skipped validation, or unauthorized tools
- **Error handling**: When tools failed, did agent retry or give up?
- **Tool sequencing**: Did agent call tools in correct order (e.g., Edit before Bash)?

### Example: Investigating Delegation Failure

**Scenario**: Supervisor agent should have delegated to git-commit skill but didn't.

```bash
# 1. Find supervisor's task invocation in main session log
grep "Skill.*git-commit" session.jsonl

# 2. If Skill/Task tools appear, extract agentId from response
jq 'select(.type == "user") | .message.content' | tail -10

# 3. If Task tool used, examine what subagent actually did
cat agent-[agentId].jsonl | jq '.message.content[] | select(.type == "tool_use") | .name' | head -20

# 4. If git-commit not invoked, check supervisor's reasoning
jq 'select(.type == "assistant") | .message.content | map(select(.type == "text")) | .[0].text' agent-[supervisor-id].jsonl

# 5. Determine: Was git-commit in agent's available skills? Did it refuse?
# Update agent permissions/instructions and re-test
```

**Key insight**: Logs reveal not just what agent tried, but what tools it had available when it made decisions.

## Common Anti-Patterns to Prevent

### Anti-Pattern 1: Instruction Bloat

**Bad**:

```markdown
# Agent Instructions

When you finish a task, you must:
1. Review all changes
2. Check for errors
3. Run tests
4. Commit changes
5. Push to remote
[... 85 more lines of detailed steps ...]
```

**Good**:

```markdown
# Agent Instructions

After completing tasks, use the `git-commit` skill to validate and commit changes.
```

**Why**: Skill is atomic and tested. Agent just needs to know WHEN to use it.

### Anti-Pattern 2: Repeating Core Axioms

**Bad**:

```markdown
# Developer Agent

## Core Rules
- Fail-fast philosophy: no defaults, no fallbacks
- [85 lines explaining fail-fast]
- DRY principle: one source of truth
- [50 lines explaining DRY]
```

**Good**:

```markdown
# Developer Agent

Follow core axioms in `_CORE.md`:
- Axiom #7: Fail-fast (no defaults)
- Axiom #10: DRY and explicit

Load development workflow via `/dev` command.
```

**Why**: _CORE.md already explains. Reference, don't duplicate.

### Anti-Pattern 3: Adding Instructions When Code Would Work

**Bad**:

```markdown
# Agent Instructions

Before committing, you must:
1. Check that all validation rules pass
2. Verify files are staged
3. Ensure commit message follows format
4. Include attribution footer
[Agent still forgets sometimes]
```

**Good**:

```bash
# pre-commit hook (runs automatically)
if ! validation_check; then
  echo "Validation failed"
  exit 1
fi
```

**Why**: Hook ENFORCES behavior. Instruction SUGGESTS behavior.

### Anti-Pattern 4: Speculative Changes

**Bad**:
"I think adding retry logic would help agents handle API failures better. Let me add 50 lines of retry instructions."

**Good**:
"Agent failed on API timeout (Issue #123).

Hypothesis: Adding hook to catch httpx.TimeoutError would prevent cascade failures.

Experiment: Add PostToolUse hook to detect timeouts.

Success criteria: Zero cascade failures over 10 test runs.

[Implement → Test → Measure → Decide]"

**Why**: We don't know until we test.

## Continuous Research

**Actively research** third-party approaches:

- code-conductor, aider, cursor
- Prompt engineering research
- Agent framework patterns
- LLM client documentation

**When finding useful patterns**:

1. Document in GitHub issue
2. Propose MINIMAL adoption
3. Design experiment to test
4. Measure actual impact

**Integration philosophy**: Steal good ideas, adapt minimally, test rigorously.

## Critical Rules

**NEVER**:

- Add >10 lines without Anti-Bloat Protocol
- Duplicate content from _CORE.md or other files
- Add instructions when scripts/hooks/config would work
- Claim something "will work" without testing
- Make >3 changes per intervention
- Skip GitHub documentation (diagnostics + solution design)

**ALWAYS**:

- Search GitHub first (3+ searches)
- Work through Enforcement Hierarchy Decision Tree
- Document diagnostics before solutions
- Create experiment logs
- Test with real conversations
- Measure actual outcomes
- Update GitHub with results

## Quick Reference

**Enforcement hierarchy** (prefer top):

1. Scripts - Automated code
2. Hooks - SessionStart, PreToolUse, etc.
3. Config - Permissions, restrictions
4. Instructions - Last resort

**Intervention workflow**:

```
1. Search GitHub (3+ searches)
2. Post diagnostic analysis
3. Work through decision tree (Q1-Q4)
4. Post solution design
5. Implement (max 3 changes)
6. Create experiment log
7. Test with real scenarios
8. Update experiment with results
9. Post outcomes to GitHub
10. Decide: keep/revert/iterate
```

**Anti-Bloat checklist** (before adding >10 lines):

- [ ] Tried scripts/hooks/config first
- [ ] Checked for existing content to reference
- [ ] Verified not repeating _CORE.md
- [ ] Calculated bloat cost
- [ ] Justified why architecture won't work
- [ ] File stays under 500 lines

**Experiment log template**:

```markdown
# Metadata
Date, Issue, Commit, Model

# Hypothesis
What we expect

# Changes
What we modified

# Success Criteria
How to measure

# Results
What actually happened

# Outcome
Success/Failure/Partial
```
