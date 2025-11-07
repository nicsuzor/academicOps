---
name: agent-optimization
description: This skill should be used when reviewing and improving agents, skills,
  hooks, permissions, and configurations. It enforces an experiment-driven, anti-bloat
  approach with enforcement hierarchy of Scripts, Hooks, Config, then Instructions.
  The skill prevents adding repetitive or overly specific instructions, understands
  how different enforcement mechanisms fit together, and makes strategic decisions
  about where to intervene. Use this skill when agent performance issues arise, when
  evaluating new techniques, or when maintaining the agent framework. Always test
  before claiming something works. Specific to academicOps framework.
permalink: aops/skills/aops-trainer/skill
---

# Agent Optimization

You are responsible for agent performance in the @nicsuzor/academicOps project.

## Framework Context

@resources/SKILL-PRIMER.md @resources/AXIOMS.md @resources/INFRASTRUCTURE.md

## Overview

Maintain and optimize agent framework performance through surgical, experiment-driven interventions. This skill enforces anti-bloat principles, prioritizes architectural solutions over instructions, and ensures changes are tested rather than speculated.

**Evidence-Based Foundation**: This skill follows evidence-based best practices documented in `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md`, incorporating guidance on context engineering, subagent design, and effective AI agents.

## Information Architecture

**CRITICAL**: Understanding where content belongs prevents architectural bloat and maintains DRY principles.

### Document Types & Their Purpose

**ARCHITECTURE.md** - Timeless structural specification:

- Three-tier repository system (framework/personal/project)
- File structure for each tier
- Component specifications (what agents/skills/hooks/chunks ARE)
- Architectural patterns (enforcement hierarchy, skill-first, DRY via chunks)
- **NEVER includes**: Testing procedures, installation steps, coding standards, process workflows, metrics, status, progress indicators, temporal labels (NEW), line counts

**chunks/AXIOMS.md** - Universal principles:

- Core axioms (fail-fast, DRY, explicit configuration)
- Behavioral rules (no workarounds, verify first)
- Tool failure protocol
- Specific coding standards (no `.get(key, default)`)
- **WHY it belongs here**: Universal across all contexts, loaded by all agents

**docs/bots/BEST-PRACTICES.md** - Evidence-based agent design:

- Context engineering principles
- Instruction writing guidelines
- What works/doesn't work (with citations)
- Component design patterns
- **WHY it belongs here**: Meta-level guidance for building agents

**README.md** - User-facing capabilities guide:

- What tools exist and what they do
- Quick reference: which tool when
- Component tree (auto-generated)
- Brief purpose statement
- **NEVER includes**: Agent instructions, implementation details, process workflows

**Skills** - Process workflows:

- HOW to execute specific tasks
- Step-by-step procedures
- Tool invocation sequences
- Checklists and validation
- Example: aops-trainer contains the experiment workflow, not ARCHITECTURE.md

**Core instruction files** (core/_CORE.md, agents/_.md, commands/_.md):

- Runtime instructions for agents
- Task-specific orchestration
- When to invoke which skills
- **References** universal content, doesn't duplicate it

**Installation/testing docs** (INSTALL.md, TESTING.md):

- Setup procedures
- Test execution commands
- Environment configuration
- NOT in ARCHITECTURE.md

### Content Placement Decision Tree

When creating or editing content, ask:

1. **Is this a timeless structural fact?**
   - YES → ARCHITECTURE.md
   - NO → Continue

2. **Is this a universal principle applicable everywhere?**
   - YES → chunks/AXIOMS.md
   - NO → Continue

3. **Is this guidance on how to design agents/instructions?**
   - YES → docs/bots/BEST-PRACTICES.md
   - NO → Continue

4. **Is this a step-by-step process workflow?**
   - YES → Skill (or script if automatable)
   - NO → Continue

5. **Is this user-facing "what can I do" information?**
   - YES → README.md
   - NO → Continue

6. **Is this setup/installation/testing procedure?**
   - YES → INSTALL.md or TESTING.md
   - NO → Consider if it should exist at all

### Common Mistakes to Avoid

❌ **Putting process in ARCHITECTURE.md**:

- Testing procedures → Belongs in TESTING.md or skill
- Installation steps → Belongs in INSTALL.md
- Experiment workflow → Belongs in aops-trainer skill
- Anti-bloat checklist → Belongs in aops-trainer skill (it's a process)
- **Checklists with "before doing X"** → Process, not structure
- **"ALL changes require" workflows** → Process, not structure
- **Step-by-step procedures** → Process, not structure

**Process vs Principle distinction**:

- ✅ PRINCIPLE: "Enforcement hierarchy: Scripts > Hooks > Config > Instructions" (describes WHAT the pattern is)
- ❌ PROCESS: "Pre-addition checklist: [ ] Tried scripts first?" (describes HOW to apply it)
- ✅ PRINCIPLE: "Experiment-driven development" (describes WHAT the approach is)
- ❌ PROCESS: "ALL changes require: 1. GitHub issue 2. Experiment log..." (describes HOW to do it)

❌ **Putting coding standards in ARCHITECTURE.md**:

- "No `.get(key, default)`" → Belongs in chunks/AXIOMS.md (universal principle)
- "Use uv run python" → Belongs in chunks/AXIOMS.md (universal tool)
- Specific line limits → Belongs in skill that enforces them

❌ **Putting temporal/metric content in ARCHITECTURE.md**:

- "(NEW)" labels → Remove, architecture is timeless
- "(97 lines)" counts → Remove, metrics change
- "All tests passing ✅" → Remove, status changes
- "down from 113" → Remove, progress doesn't belong in specification

❌ **Duplicating universal content**:

- If chunks/AXIOMS.md has it → Reference it, don't copy
- If docs/bots/BEST-PRACTICES.md explains it → Link to it
- One source, many references (DRY)

### Validation Questions

Before modifying any documentation file:

1. Does this content already exist elsewhere? (DRY check)
2. Is this content timeless or will it change? (If changes → wrong file)
3. Am I describing structure or process? (Structure → ARCHITECTURE, Process → Skill)
4. Would this make sense to a user in 2 years? (If no → remove temporal aspects)
5. Is this the authoritative source for this concept? (If no → reference instead)

### Universal Chunking Principle

**CHUNK EVERYTHING**: No documentation file should exceed ~200 lines. When files grow large, modularize into topic-focused chunks.

**Why chunking matters**:

- **Token efficiency**: Agents load only relevant topics via @references
- **Maintainability**: Smaller files easier to update and keep current
- **DRY enforcement**: Each chunk has single responsibility, clear purpose
- **Discoverability**: Topic-focused files easier to find and navigate
- **Context pollution prevention**: Avoid loading 700-line files when 50 lines needed

**Chunking strategies**:

1. **Topic-based splitting** - Extract major sections into separate files
   - Example: BEST-PRACTICES.md (705 lines) → CONTEXT-ENGINEERING.md, SUBAGENT-DESIGN.md, SKILL-DESIGN.md, COMMAND-DESIGN.md, HOOK-DESIGN.md, TOOL-DESIGN.md, ANTI-PATTERNS.md
   - Original becomes index with @references

2. **Reference over duplicate** - Create topic file, reference from multiple locations
   - Example: chunks/AXIOMS.md loaded by both agents (via _CORE.md) and skills (via resources/)
   - One source, many references

3. **Progressive detail** - Index file has summaries, topic files have details
   - Index: What each topic covers + @reference
   - Topic files: Complete guidance on specific subject
   - Agents load index, then specific topics as needed

**Hard limits**:

- Documentation files >200 lines → CHUNK IT
- Reference files (chunks/, docs/bots/) >300 lines → CHUNK IT
- Any file approaching size limit → Plan chunking strategy BEFORE adding content

**When chunking, preserve**:

- Cross-references between chunks
- Navigation (index file with all @references)
- Authoritative source designation (which file is canonical for what)

**Example chunk structure**:

```
docs/bots/
├── BEST-PRACTICES.md          # Index (137 lines)
├── CONTEXT-ENGINEERING.md     # Topic chunk (~120 lines)
├── SUBAGENT-DESIGN.md         # Topic chunk (~60 lines)
├── SKILL-DESIGN.md            # Topic chunk (~80 lines)
├── COMMAND-DESIGN.md          # Topic chunk (~130 lines)
├── HOOK-DESIGN.md             # Topic chunk (~35 lines)
├── TOOL-DESIGN.md             # Topic chunk (~40 lines)
└── ANTI-PATTERNS.md           # Topic chunk (~75 lines)
```

Total content preserved, but modular and loadable on-demand.

### ARCHITECTURE.md Specific Guidance

**Canonical structure** (in order):

1. **Core Concepts** - Foundational ideas (chunks system, environment variables, namespace separation)
2. **Instruction Loading System** - How three tiers compose (SessionStart loading, skill resources)
3. **File Structure** - What exists where (three trees: framework/personal/project)
4. **Component Specifications** - Technical requirements for each component type
5. **Design Principles** - High-level patterns (DRY, enforcement hierarchy, skill-first) - BRIEF, no checklists
6. **References** - Pointers to other docs

**When refactoring ARCHITECTURE.md**, remove ALL:

- Checklists (especially "Pre-addition checklist", "Before adding >5 lines")
- "ALL changes require" procedural lists
- Testing commands and procedures
- Installation procedures
- Detailed "how to" workflows (those belong in skills)
- Temporal markers (NEW, line counts, status updates)

**Keep ONLY**:

- Structural specifications (what exists, where it lives)
- Component requirements (what makes something valid)
- Pattern names and brief descriptions (not enforcement procedures)
- References to where process details live

## Writing Effective Agent Instructions

**Meta-learnings from empirical testing of this skill's effectiveness**

### Specificity Over Generality

**What doesn't work**:

- General guidance: "Process content doesn't belong in ARCHITECTURE.md"
- Abstract principles: "Distinguish between structure and process"
- Vague directives: "Be concise"

**What works**:

- Concrete examples with ✅/❌ markers
- Explicit removal lists: "Remove ALL: checklists, 'ALL changes require' lists"
- File-specific sections: "ARCHITECTURE.md Specific Guidance"
- Show the distinction: "✅ PRINCIPLE: X vs ❌ PROCESS: Y"

**Experiment evidence**: ARCHITECTURE.md refactoring attempts

- Attempt 1 (general guidance): Removed 2/5 violations (40% success)
- Attempt 2 (specific examples + explicit lists): Removed 5/5 violations (100% success)

### Examples Are More Powerful Than Rules

**Principle alone fails**:

```
"Distinguish between principles and process implementations"
→ Agent couldn't identify "ALL changes require..." as process
```

**Principle + Example succeeds**:

```
Process vs Principle distinction:
- ✅ PRINCIPLE: "Experiment-driven development"
- ❌ PROCESS: "ALL changes require: 1. GitHub issue 2. Experiment log..."
→ Agent correctly removed process, kept principle
```

**Pattern**: Show 2-3 canonical examples rather than explaining exhaustively. Examples teach pattern recognition better than rules.

### Anticipate Common Confusions

When agents might confuse two similar concepts, explicitly contrast them:

**Example from this skill**:

- PRINCIPLE: "Anti-bloat enforcement" (describes WHAT the pattern is)
- PROCESS: "Pre-addition checklist" (describes HOW to apply it)

Without this distinction shown, agents keep checklists thinking they're part of the principle.

**Checklist for instruction writing**:

1. What will agents confuse with what? (principle vs implementation, structure vs process)
2. Can you show both side-by-side with ✅/❌ markers?
3. What specific strings should agents search for? (Give them: "checklists", "ALL...require", "before doing X")

### Component-Specific Guidance Beats Generic Rules

**Generic guidance** (less effective):

- "Testing procedures don't belong in architecture documents"
- Agents may interpret differently for different files

**Component-specific guidance** (more effective):

```
### ARCHITECTURE.md Specific Guidance

When refactoring ARCHITECTURE.md, remove ALL:
- Checklists (especially "Pre-addition checklist")
- "ALL changes require" procedural lists
- Testing commands
```

**Pattern**: If multiple files follow similar patterns but have file-specific nuances, create a section per file type.

### Explicit "Remove ALL" Lists Work

Agents respond better to explicit removal lists than inference:

**Inference-based** (requires agent reasoning):

- "Process content doesn't belong" → Agent must figure out what that means

**Explicit list** (direct action):

- "Remove ALL: Checklists, 'ALL changes require', Testing commands, Installation procedures"
- Agent searches for these patterns and removes them

### Progressive Refinement Based on Failure Analysis

**Workflow for improving agent instructions**:

1. **Test with minimal instruction** → Agent fails
2. **Analyze failure**: What specific confusion occurred?
3. **Add targeted guidance**:
   - If confusion about concept X vs Y → Add ✅/❌ examples
   - If missed specific patterns → Add explicit removal list
   - If file-specific → Add component-specific section
4. **Re-test** → Measure improvement
5. **Iterate** until success rate acceptable

**Evidence**: This skill improved via 2-iteration cycle

- Iteration 1: Added Information Architecture (general)
- Iteration 2: Added Process vs Principle examples + ARCHITECTURE.md section (specific)
- Result: 40% → 100% success rate

### What NOT to Do

❌ **Don't assume agents understand context you have**:

- You know "ALL changes require: 1. 2. 3..." is a process
- Agent sees "changes" and "require" and might think it's a rule about the system
- Solution: Show the distinction explicitly

❌ **Don't rely on agents inferring from principles**:

- Principle: "DRY - don't repeat yourself"
- Agent may not realize chunks/AXIOMS.md content shouldn't be in ARCHITECTURE.md
- Solution: Explicit DRY check in validation questions

❌ **Don't write instructions for yourself**:

- Write for an agent that has ZERO context about your intent
- What seems obvious to you is not obvious to LLMs
- Test your assumptions with experiments

### Template for High-Impact Instructions

```markdown
## [Task Name]

**Purpose**: [One sentence - what this achieves]

**When to use**: [Explicit trigger conditions]

**Canonical structure** (if applicable):

1. [Step 1]
2. [Step 2]

**Common mistakes**: ❌ [Mistake pattern] → [Correct alternative] ❌ [Mistake pattern] → [Correct alternative]

**Examples**: ✅ CORRECT: [Concrete example] ❌ WRONG: [Concrete counter-example]

**Explicit removal/addition lists** (if applicable):

- Remove ALL: [Item 1], [Item 2], [Item 3]
- Keep ONLY: [Item 1], [Item 2]

**Validation**: [How to verify task completed correctly]
```

**Why this template works**:

- Purpose prevents scope creep
- Canonical structure gives clear path
- Common mistakes show ✅/❌ distinctions
- Examples enable pattern recognition
- Explicit lists enable direct action
- Validation enables self-checking

## When to Use This Skill

Use agent-optimization when:

1. **Agent performance issues** - Agent violated standards or instructions
2. **Framework improvements** - Proposing new techniques or tools
3. **Bloat prevention** - Reviewing proposed instruction additions
4. **Architecture decisions** - Choosing between scripts/hooks/config/instructions
5. **Experiment evaluation** - Analyzing test results and metrics
6. **Component refinement** - Improving subagents, skills, commands, or hooks for conciseness and effectiveness
7. **Creating/updating components** - Establishing mandatory skill-first patterns for all subagents and slash commands
8. **Instruction tree maintenance** - Keeping README.md documentation synchronized with repository structure

**Concrete trigger examples**:

- "Agent X didn't follow instruction Y - how do we fix this?"
- "Should we add these 50 lines to the agent instructions?"
- "I found a new prompting technique - should we adopt it?"
- "This agent keeps making the same mistake"
- "Evaluate whether this change actually improved performance"
- "Refine this subagent/skill/command to follow best practices"
- "Remove bloat from this agent instruction file"
- "Update README instruction tree after adding new skill"

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
2. Step two [30 lines of detailed steps]

## FAQ

Q: What if X happens? A: [Answer] [40 lines of Q&A]

## Examples

[30 lines of 10 different examples]

✅ AFTER (40 lines, focused):

# Agent X

<background_information> Essential context: [5 lines only] </background_information>

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

## Instruction Tree Maintenance

### When to Update Instruction Tree

Update README.md instruction tree documentation when:

- New agent files added to `agents/`
- New skills added to `skills/`
- New slash commands added to `commands/`
- New hooks added to `hooks/`
- Components removed or renamed
- After any structural changes to repository
- **Component descriptions updated or missing**

### Description Maintenance Workflow

**When descriptions need updating**:

- New component created without description in frontmatter
- Existing component modified but description stale
- Description vague or doesn't match actual behavior
- After refactoring that changes component responsibilities

**How to extract and verify descriptions**:

1. **Check current state**: Run `python scripts/generate_instruction_tree.py` to see which components lack descriptions
2. **Read component code**: Understand actual behavior and purpose
3. **Add/update frontmatter**:
   - Agents: Add `description:` field to YAML frontmatter in `agents/*.md`
   - Skills: Add `description:` field to YAML frontmatter in `skills/*/SKILL.md`
   - Commands: Add `description:` field to YAML frontmatter in `commands/*.md`
   - Hooks: Update first line of module docstring in `hooks/*.py`
4. **Validate extraction**: Run `python scripts/generate_instruction_tree.py` again to verify description appears
5. **Verify accuracy**: Ensure description matches actual component behavior

**Description quality criteria**:

- **Concise**: One sentence, 10-20 words
- **Specific**: What does it DO, not general platitudes
- **Accurate**: Matches current behavior, not aspirational
- **Unique**: Distinguishable from other components (if similar descriptions → architectural smell)

**Reference**: The `scripts/generate_instruction_tree.py` script automatically extracts descriptions from:

- YAML frontmatter `description:` field (agents, skills, commands)
- Python module docstring first line (hooks)

### Architectural Analysis Using Descriptions

**Purpose**: Use component descriptions to identify architectural problems that manifest as description similarities.

**Overlap detection** - Components with similar descriptions:

- **Symptom**: Multiple components have nearly identical description keywords
- **Example**: Three skills all described as "workflow automation" or "task management"
- **Problem**: Unclear boundaries, duplicate functionality, user confusion about which to use
- **Action**: Propose consolidation or clearer differentiation

**Fragmentation detection** - Related functionality split across components:

- **Symptom**: Descriptions that are complementary halves of same workflow
- **Example**: "Creates tasks" (one component) + "Updates task status" (another) + "Archives tasks" (third)
- **Problem**: Related functionality scattered, forces users to learn multiple components
- **Action**: Evaluate whether consolidation into single workflow makes sense

**Confusion detection** - Vague or overlapping responsibilities:

- **Symptom**: Descriptions using vague terms like "manages", "handles", "processes"
- **Example**: "Manages agent configurations" overlaps with "Handles agent settings"
- **Problem**: Unclear which component owns what, leads to missed responsibilities
- **Action**: Sharpen descriptions OR clarify actual responsibilities via refactoring

**Workflow for architectural analysis**:

1. **Generate descriptions**: Run `python scripts/generate_instruction_tree.py` and review README.md
2. **Identify patterns**: Look for keyword clusters (grep for "manage", "workflow", "task", etc.)
3. **Flag similarities**: Note any 3+ components with similar description terms
4. **Investigate root cause**: Read component code to understand actual vs described behavior
5. **Document findings**: Create GitHub issue with evidence of overlap/fragmentation/confusion
6. **Propose solution**: Consolidate, differentiate, or refactor as appropriate

**Examples of architectural problems to catch**:

```markdown
❌ OVERLAP DETECTED:

- skill-creator: "Guide for creating effective skills"
- skill-maintenance: "Ongoing skill maintenance and evolution"
- aops-trainer: "Reviewing and improving skills" → All three mention "skills" - are responsibilities clear?

❌ FRAGMENTATION DETECTED:

- email-fetch: "Fetches emails from Outlook"
- email-parse: "Extracts tasks from email content"
- email-archive: "Archives processed emails" → Three skills for email workflow - should be one?

❌ CONFUSION DETECTED:

- agent-config: "Manages agent configurations"
- settings-handler: "Handles framework settings" → What's difference between "manage" and "handle"? Between "agent configurations" and "framework settings"?
```

### Maintenance Workflow

**1. Validate Current State**:

```bash
python scripts/validate_instruction_tree.py
```

- Exit code 0: Tree is current, no action needed
- Exit code 1: Tree is stale, shows what changed

**2. Regenerate Tree** (if stale):

```bash
python scripts/generate_instruction_tree.py
```

- Scans repository for all components
- Extracts descriptions from frontmatter/docstrings
- Generates updated markdown tree
- Updates README.md between markers `<!-- INSTRUCTION_TREE_START -->` and `<!-- INSTRUCTION_TREE_END -->`

**3. Review Changes**:

```bash
git diff README.md
```

Verify generated tree accurately reflects repository structure and descriptions.

**4. Architectural Review** (during regeneration):

- Scan generated descriptions for similar keywords
- Flag potential overlap/fragmentation/confusion
- Create GitHub issues for architectural smells

**5. Commit**:

Use git-commit skill to validate and commit documentation update.

### Integration with Component Creation

When creating/updating components:

1. Implement component (agent/skill/command/hook)
2. **Add description to frontmatter/docstring** (mandatory)
3. Test component functionality
4. **Regenerate instruction tree** (mandatory)
5. **Review descriptions for architectural smells**
6. Commit component + updated README together

This ensures documentation never falls out of sync with code, and architectural problems surface early.

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

   **NEVER**: [List of prohibited actions] **ALWAYS**: [List of required actions]
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

@resources/SKILL-PRIMER.md @resources/AXIOMS.md @resources/INFRASTRUCTURE.md # If framework-touching only
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
5. Push to remote [... 85 more lines of detailed steps ...]
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
4. Include attribution footer [Agent still forgets sometimes]
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

**Bad**: "I think adding retry logic would help agents handle API failures better. Let me add 50 lines of retry instructions."

**Good**: "Agent failed on API timeout (Issue #123).

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
