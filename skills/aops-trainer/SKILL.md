---
name: agent-optimization
description: This skill should be used when reviewing and improving agents, skills, hooks, permissions, and configurations. It enforces an experiment-driven, anti-bloat approach with enforcement hierarchy of Scripts, Hooks, Config, then Instructions. The skill prevents adding repetitive or overly specific instructions, understands how different enforcement mechanisms fit together, and makes strategic decisions about where to intervene. Use this skill when agent performance issues arise, when evaluating new techniques, or when maintaining the agent framework. Always test before claiming something works. Specific to academicOps framework.
---

# Agent Optimization

You are responsible for agent performance in the @nicsuzor/academicOps project.

## Framework Context

@resources/SKILL-PRIMER.md
@resources/AXIOMS.md
@resources/INFRASTRUCTURE.md

## Overview

Maintain and optimize agent framework performance through surgical, experiment-driven interventions. This skill enforces anti-bloat principles, prioritizes architectural solutions over instructions, and ensures changes are tested rather than speculated.

**Evidence-Based Foundation**: This skill follows evidence-based best practices documented in `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md`, incorporating official Anthropic guidance on context engineering, subagent design, and effective AI agents.

## When to Use This Skill

Use agent-optimization when:

1. **Agent performance issues** - Agent violated standards or instructions
2. **Framework improvements** - Proposing new techniques or tools
3. **Bloat prevention** - Reviewing proposed instruction additions
4. **Architecture decisions** - Choosing between scripts/hooks/config/instructions
5. **Experiment evaluation** - Analyzing test results and metrics
6. **Component refinement** - Improving subagents, skills, commands, or hooks for conciseness and effectiveness
7. **Creating/updating components** - Establishing mandatory skill-first patterns for all subagents and slash commands

**Concrete trigger examples**:

- "Agent X didn't follow instruction Y - how do we fix this?"
- "Should we add these 50 lines to the agent instructions?"
- "I found a new prompting technique - should we adopt it?"
- "This agent keeps making the same mistake"
- "Evaluate whether this change actually improved performance"
- "Refine this subagent/skill/command to follow best practices"
- "Remove bloat from this agent instruction file"

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

### 5. Context Engineering Principles (Anthropic Official)

**Context as Finite Resource**:
- LLMs have "attention budget" that depletes with excessive tokens
- Target "smallest set of high-signal tokens" for desired outcomes
- Even with large context windows, context pollution degrades performance

**The Goldilocks Altitude**:
- Too Low: Overly complex, brittle hardcoded logic
- Too High: Vague guidance assuming shared context
- Just Right: Specific paired with flexible guidance through strong heuristics

**Examples Over Exhaustive Rules**:
- "Examples are the 'pictures' worth a thousand words"
- Use 2-3 canonical examples showing expected behavior
- More effective than exhaustive rule documentation

**What to AVOID** (from official best practices):
- ❌ Unnecessary background history that doesn't affect behavior
- ❌ FAQ sections answering questions the agent hasn't asked
- ❌ Excessive scene-setting and motivational preambles
- ❌ Negative instructions ("Don't do X") without saying what to do
- ❌ Vague instructions ("be concise" vs "limit to 2-3 sentences")
- ❌ Mixing instructions with context (use XML tags or headers to separate)

**Source**: See `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md` for complete evidence-based guidance with citations.

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

   **Before adding >5 lines, verify ALL**:

   - [ ] **Hierarchy Check**: Verified Q1-Q4 show NO architectural solution
   - [ ] **Bloat Estimate**: Calculated token cost vs writing code
   - [ ] **Modularity**: Can this be separate referenced doc?
   - [ ] **DRY Check**: Does similar guidance exist elsewhere?
   - [ ] **CRITICAL DRY**: Repeating _CORE.md or other agent? Use brief reference instead
   - [ ] **Complexity Budget**: File stays under 300 lines
   - [ ] **Justification**: Documented WHY code/config/hooks won't work
   - [ ] **Condensed**: Can this be expressed in bullet points vs paragraphs?

   **AXIOM: DO NOT REPEAT YOURSELF**:
   - Longer instructions NOT more effective (LLMs get lost in bloat)
   - If _CORE.md has it → REFERENCE (don't duplicate)
   - Example: "See _CORE.md Axiom #4" NOT 85 lines restating
   - Default to BULLET POINTS, not prose

   **HARD LIMITS**:
   - Adding >5 lines: Requires bloat justification
   - Adding >10 lines: STOP, create GitHub issue, get user approval
   - File >300 lines total: Architectural bloat, must refactor

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

## Component Refinement Workflow

### When to Refine Components

Use this workflow when:
- Component (subagent/skill/command/hook) shows signs of bloat (>500 lines)
- Instructions contain FAQ-style content or excessive examples
- Background context doesn't directly affect behavior
- Mixing instructions with context without clear separation
- Vague or negative instructions instead of specific directives

### Refinement Process

**1. Load Best Practices**:

Read `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md` to ensure current understanding of evidence-based principles.

**2. Audit Component**:

Review component against best practices checklist:
- [ ] Is context minimal and high-signal? (not comprehensive)
- [ ] Are instructions specific, not vague?
- [ ] Do I use 2-3 examples vs exhaustive rules?
- [ ] Is structure clear with XML tags or headers?
- [ ] Have I removed bloat (FAQs, background fluff, excessive examples)?
- [ ] Is component focused on one purpose?
- [ ] Does this follow "smallest set of high-signal tokens" principle?

**3. Identify Bloat Categories**:

Classify what to remove/refactor:
- **Background fluff**: History, motivation, philosophical preambles → DELETE or move to reference doc
- **FAQ content**: Answering questions not asked → DELETE
- **Excessive examples**: >3 examples → Reduce to 2-3 canonical cases
- **Negative instructions**: "Don't do X" → Replace with "Do Y instead"
- **Vague directives**: "Be concise" → Replace with specific metrics
- **Duplicate content**: Repeating _CORE.md or other files → Replace with reference
- **Mixed sections**: Instructions buried in context → Separate with XML tags/headers

**4. Refactor Component**:

Apply surgical changes:
- Extract bloat to separate reference document (if useful)
- Replace vague with specific instructions
- Consolidate duplicate content with references
- Add structure (XML tags, clear headers)
- Reduce to essential high-signal tokens

**5. Validate Effectiveness**:

Before/after comparison:
- Token count reduction (target: 20-50% reduction for bloated components)
- Clarity improvement (specific vs vague instruction count)
- Structure improvement (clear sections vs mixed content)

**6. Test Component**:

Create experiment log and test refined component:
- Does it still achieve intended behavior?
- Is performance improved, maintained, or degraded?
- Document outcome and iterate if needed

**Example Refinement**:

```markdown
❌ BEFORE (150 lines, bloated):
# Agent X

## Background
[50 lines of history and motivation]

## Instructions
When you do task Y, follow these steps:
1. Step one
2. Step two
[30 lines of detailed steps]

## FAQ
Q: What if X happens?
A: [Answer]
[40 lines of Q&A]

## Examples
[30 lines of 10 different examples]

✅ AFTER (40 lines, focused):
# Agent X

<background_information>
Essential context: [5 lines only]
</background_information>

<instructions>
Task Y workflow:
1. Use skill-name for [specific purpose]
2. Apply fail-fast principles (see _CORE.md Axiom #7)
3. Commit via git-commit skill

See @$ACADEMICOPS/references/task-y-details.md for edge cases.
</instructions>

<examples>
**Example 1**: [Canonical case]
**Example 2**: [Edge case]
</examples>
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

## Universal Pattern: Mandatory Skill-First Architecture

### The Problem

Agents often try to "figure out" instructions on their own by:
- Searching for documentation manually
- Guessing at workflows
- Attempting tasks without proper context
- Missing critical references and checklists

This wastes tokens, creates inconsistency, and leads to errors.

### The Solution: Mandatory Skill Invocation

**PRINCIPLE**: All subagents and slash commands MUST invoke their corresponding skill FIRST before attempting any work.

**Benefits**:
1. **Context efficiency**: Skills have built-in context that loads once
2. **Consistency**: Same workflow every time
3. **Documentation discovery**: Skills contain references and indices
4. **Prevents improvisation**: Agents follow established patterns instead of guessing
5. **Token efficiency**: Consolidated context vs scattered instructions

### Implementation Pattern

**For Slash Commands** (`.claude/commands/*.md`):

```markdown
---
description: [One-line description]
---

**MANDATORY FIRST STEP**: Invoke the `skill-name` skill IMMEDIATELY. The skill provides all context, workflows, and documentation needed for [task type].

**DO NOT**:
- Attempt to figure out instructions on your own
- Search for documentation manually
- Start work before loading the skill

The skill-name skill contains:
- [Key capability 1]
- [Key capability 2]
- [Key capability 3]

After the skill loads, follow its instructions precisely.

ARGUMENTS: $ARGUMENTS
```

**For Subagents** (`agents/*.md`):

```yaml
---
name: agent-name
description: "Clear one-sentence purpose"
tools: [list]
---

# Agent Name

**MANDATORY FIRST STEP**: Invoke the `skill-name` skill before proceeding with any task.

## Core Responsibilities

[Agent-specific authority and orchestration - keep minimal]

## Workflow

1. Load skill-name skill (MANDATORY)
2. Follow skill instructions for [task type]
3. [Any agent-specific orchestration]

See skill-name for complete workflow details.
```

### Required Components for All Skills

When creating skills to support this pattern, ensure they include:

1. **Documentation Index**: Clear references to all relevant docs
   ```markdown
   ## References
   - Core instructions: `@$ACADEMICOPS/core/_CORE.md`
   - Best practices: `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md`
   - Detailed guide: `@$ACADEMICOPS/references/specific-guide.md`
   ```

2. **Workflow Checklist**: Step-by-step process
   ```markdown
   ## Workflow
   1. [Step 1 with specifics]
   2. [Step 2 with specifics]
   3. [Step 3 with specifics]
   ```

3. **Critical Rules**: Key principles and constraints
   ```markdown
   ## Critical Rules
   **NEVER**: [List of prohibited actions]
   **ALWAYS**: [List of required actions]
   ```

4. **Quick Reference**: Condensed lookup for experienced users
   ```markdown
   ## Quick Reference
   - Pattern A: [Brief description]
   - Pattern B: [Brief description]
   ```

### Enforcement

When reviewing or creating components, verify:

- [ ] Slash command includes MANDATORY skill invocation instruction
- [ ] Subagent includes MANDATORY skill invocation as first step
- [ ] Supporting skill exists with documentation index
- [ ] Supporting skill includes workflow checklist
- [ ] Supporting skill includes critical rules section
- [ ] Supporting skill includes quick reference

**Rationale**: This pattern solves the dual problems of (1) agents trying to figure things out independently, and (2) difficulty discovering relevant documentation. Skills become the single entry point for all task-specific context.

## Universal Pattern: Skill Resources Symlinks

### The Problem

Skills don't receive SessionStart hooks, so they lack:
- Universal principles (axioms, fail-fast, DRY)
- Framework infrastructure knowledge ($ACADEMICOPS paths, repo structure)
- Repository-specific context

### The Solution: resources/ with Symlinks

**ALL skills** must include a `resources/` directory with symlinks to shared chunks:

```
skills/skill-name/
├── SKILL.md
└── resources/                    # NEW - Required for all skills
    ├── SKILL-PRIMER.md → ../../chunks/SKILL-PRIMER.md (symlink)
    ├── AXIOMS.md → ../../chunks/AXIOMS.md (symlink)
    └── INFRASTRUCTURE.md → ../../chunks/INFRASTRUCTURE.md (symlink - framework skills only)
```

### When to Include Each Chunk

**All skills MUST include**:
- `SKILL-PRIMER.md` - Explains skill execution context
- `AXIOMS.md` - Universal principles (fail-fast, DRY, standard tools, etc.)

**Framework-touching skills MUST include**:
- `INFRASTRUCTURE.md` - Repository structure, $ACADEMICOPS paths, environment variables

**Framework-touching skills** are those that:
- Read/write framework files (commands/, agents/, skills/, core/)
- Need to know about $ACADEMICOPS repository structure
- Work with multi-tier loading system

Examples: aops-trainer, skill-creator, skill-maintenance, claude-hooks, claude-md-maintenance, agent-initialization

**Non-framework skills** (skip INFRASTRUCTURE.md):
- General-purpose utilities that don't touch framework files
- Examples: pdf, archiver, strategic-partner, analyst

### Creating Symlinks

**In development** (bot repo - for skills in bot/skills/):
```bash
cd bot/skills/skill-name/
mkdir -p resources
cd resources
ln -s ../../../chunks/SKILL-PRIMER.md SKILL-PRIMER.md
ln -s ../../../chunks/AXIOMS.md AXIOMS.md
ln -s ../../../chunks/INFRASTRUCTURE.md INFRASTRUCTURE.md  # If framework-touching
```

**In installed skills** (~/.claude/skills/):
```bash
cd ~/.claude/skills/skill-name/
mkdir -p resources
cd resources
ln -s /home/nic/src/bot/chunks/SKILL-PRIMER.md SKILL-PRIMER.md
ln -s /home/nic/src/bot/chunks/AXIOMS.md AXIOMS.md
ln -s /home/nic/src/bot/chunks/INFRASTRUCTURE.md INFRASTRUCTURE.md  # If framework-touching
```

### Referencing in SKILL.md

Add at the top of every SKILL.md (after frontmatter, before first section):

```markdown
## Framework Context

@resources/SKILL-PRIMER.md
@resources/AXIOMS.md
@resources/INFRASTRUCTURE.md  # If framework-touching only
```

### DRY Compliance

This pattern maintains DRY because:
- ✅ Each principle exists in EXACTLY ONE file (`chunks/*.md`)
- ✅ Skills access via filesystem symlinks (not duplication)
- ✅ Updates to chunks/ automatically propagate to all skills
- ✅ No content copied between files

### Packaging and Installation

When packaging skills for distribution:
- Symlinks should be resolved to actual file contents
- Result: Self-contained skills with embedded context
- No runtime dependency on bot repo location

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

## Continuous Research & Self-Improvement

**Actively research** third-party approaches:

- code-conductor, aider, cursor
- Prompt engineering research
- Agent framework patterns
- LLM client documentation
- Official Anthropic updates on Claude Code and agent best practices

**When finding useful patterns**:

1. Document in GitHub issue
2. Propose MINIMAL adoption
3. Design experiment to test
4. Measure actual impact

**Integration philosophy**: Steal good ideas, adapt minimally, test rigorously.

### Updating Best Practices

As new learnings emerge from experiments and research:

1. **Update BEST-PRACTICES.md** with new evidence-based findings
   - Add new principles with citations
   - Remove disproven patterns with explanation
   - Keep document concise (follow its own principles)

2. **Update this skill** to reflect new patterns
   - Extract critical insights into skill instructions
   - Reference BEST-PRACTICES.md for details
   - Test refinements through experiments

3. **Propagate to components** systematically
   - Audit existing components against updated practices
   - Refine high-priority components first
   - Document improvements in experiment logs

**This skill is self-improving**: When you discover better approaches to agent optimization through experimentation, update BEST-PRACTICES.md and this skill accordingly.

## Critical Rules

**NEVER**:

- Add >5 lines without bloat justification
- Add >10 lines without GitHub issue + user approval
- Duplicate content from _CORE.md or other files
- Add instructions when scripts/hooks/config would work
- Claim something "will work" without testing
- Make >3 changes per intervention
- Skip GitHub documentation (diagnostics + solution design)
- Include FAQ-style content or extensive background that doesn't affect behavior
- Use vague instructions ("be concise") instead of specific directives ("2-3 sentences")
- Write prose paragraphs when bullet points suffice

**ALWAYS**:

- Search GitHub first (3+ searches)
- Work through Enforcement Hierarchy Decision Tree
- Document diagnostics before solutions
- Create experiment logs
- Test with real conversations
- Measure actual outcomes
- Update GitHub with results
- Follow "smallest set of high-signal tokens" principle (context engineering)
- Check BEST-PRACTICES.md when refining components

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

**Component refinement workflow**:

```
1. Load BEST-PRACTICES.md
2. Audit component against checklist
3. Identify bloat categories (FAQ, background, vague instructions)
4. Refactor surgically (extract/consolidate/specify)
5. Validate effectiveness (token reduction, clarity)
6. Test refined component with experiment log
```

**Anti-Bloat checklist** (before adding >5 lines):

- [ ] Tried scripts/hooks/config first
- [ ] Checked for existing content to reference
- [ ] Verified not repeating _CORE.md
- [ ] Calculated bloat cost (tokens wasted vs code written)
- [ ] Justified why architecture won't work
- [ ] Condensed to bullet points (not prose)
- [ ] File stays under 300 lines
- [ ] No FAQ content or excessive background
- [ ] Instructions specific, not vague
- [ ] Adding >10 lines: STOP, needs GitHub issue + approval

**Context engineering checklist** (component design):

- [ ] Context minimal and high-signal (not comprehensive)
- [ ] 2-3 canonical examples (not exhaustive)
- [ ] Specific directives (not vague like "be concise")
- [ ] Structured with XML tags or headers
- [ ] No negative instructions without alternatives
- [ ] References external docs instead of duplicating

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
