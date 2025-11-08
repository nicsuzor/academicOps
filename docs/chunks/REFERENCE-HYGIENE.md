---
title: Reference Hygiene
type: reference
entity_type: note
tags:
  - dry
  - references
  - documentation
  - anti-patterns
relations:
  - "[[AXIOMS]]"
  - "[[BEHAVIORAL-PATTERNS]]"
permalink: aops/chunks/reference-hygiene
---

# Reference Hygiene

Guidelines for using `@references` correctly to maintain DRY principles and avoid token waste.

## The @ Reference Mechanism

**How it works**:

- `@filename.md` or `@path/to/file.md` loads the ENTIRE file into context
- Happens automatically when Claude processes the instruction
- Content appears in full, not as summary or excerpt
- Multiple references to same file = same content loaded multiple times

**What this means**:

- Once you write `@docs/AXIOMS.md`, all axioms are in context
- Don't need to repeat, summarize, or highlight portions
- Trust the mechanism - it works

## The "Reference + Summary" Anti-Pattern

**Pattern**: Load content with `@reference`, then repeat portions of it

**Example violations**:

```markdown
❌ WRONG:

## Core Principles

@docs/AXIOMS.md

**Key axioms**:

1. DO ONE THING - Complete task, then stop
2. Fail-Fast - No defaults, no workarounds
3. DRY - One source of truth

[... continues repeating axiom content ...]
```

**Why this violates DRY (three ways)**:

1. **Technical duplication**: `@docs/AXIOMS.md` loads all axioms. The numbered list duplicates them.
2. **Arbitrary selection**: Who decided these are "key"? That choice isn't derived from axioms - it's editorial judgment.
3. **Token waste**: Content appears twice in context (once from @reference, once from summary).

**Additional violations if content is hook-loaded**:

4. **Triple redundancy**: SessionStart hook → @reference → summary = same content three times
5. **Distrust of infrastructure**: If hooks load it, why reference it again? Shows lack of confidence in own system.

## What "Arbitrary" Means

**Arbitrary** = Not directly derivable from axioms

**Examples**:

- ❌ Selecting 5 "key" principles from 17 axioms - by what axiom-derived criteria?
- ❌ Choosing to highlight certain axioms over others - based on what principle?
- ❌ Deciding something needs "emphasis" - according to which rule?

**Non-arbitrary**:

- ✅ "Load all axioms" - follows DRY, no selection bias
- ✅ "Reference BEHAVIORAL-PATTERNS.md when categorizing violations" - axiom-derived need
- ✅ "Enforcement hierarchy: Scripts > Hooks > Config > Instructions" - structural fact, not opinion

**Test**: Ask "by what axiom is this choice made?" If no clear answer → arbitrary → remove it.

## Hook-Loaded Content Redundancy

**Problem**: Some content is already loaded by SessionStart hook

**Currently hook-loaded** (via `hooks/load_instructions.py`):

- `${AOPS}/core/_CORE.md` (if exists)
- Git repository information

**Future hook-loaded** (if we populate core/):

- Any files in `${AOPS}/core/`
- Project-specific instructions from `docs/bots/` (if in project)

**Detection**:

1. Check what SessionStart hook loads
2. Don't @reference that same content in skill files
3. If content is both hook-loaded AND skill-needed, put in hook location only

**Example**:

```markdown
❌ WRONG (if axioms are hook-loaded): @docs/AXIOMS.md

**Follow these axioms...**

✅ CORRECT (if axioms are hook-loaded): [No reference needed - already in context from hook]

When agents violate axioms, categorize per @docs/chunks/BEHAVIORAL-PATTERNS.md
```

## Correct Patterns

### Pattern 1: Trust the Reference

**When**: Content exists in one canonical location

**Do**:

```markdown
✅ CORRECT:

## Behavioral Patterns

@docs/chunks/BEHAVIORAL-PATTERNS.md

When categorizing violations, use the patterns defined above.
```

**Don't**:

```markdown
❌ WRONG:

## Behavioral Patterns

@docs/chunks/BEHAVIORAL-PATTERNS.md

The key patterns are:

1. Defensive Behavior - agent works around problems
2. Scope Creep - agent does more than asked [... repeating content from the file ...]
```

### Pattern 2: Provide Context About WHEN, Not WHAT

**When**: You need to guide when/how to use referenced content

**Do**:

```markdown
✅ CORRECT:

@docs/chunks/BEHAVIORAL-PATTERNS.md

**Step 2**: Categorize the violation using the patterns above. Find the pattern that matches the symptom, then follow its enforcement recommendation.
```

This tells WHEN to use the content (step 2), not WHAT the content says.

**Don't**:

```markdown
❌ WRONG:

@docs/chunks/BEHAVIORAL-PATTERNS.md

**Defensive Behavior** is when agents work around problems. Use this when you see workarounds, fallbacks, or defensive code.
```

This repeats WHAT the referenced file already says.

### Pattern 3: Reference for Lookup, Don't Excerpt

**When**: Content is reference material to consult as needed

**Do**:

```markdown
✅ CORRECT:

For statistical test selection, see @references/test-selection-guide.md
```

Agent loads full file, finds what they need.

**Don't**:

```markdown
❌ WRONG:

Statistical test selection:

- Continuous outcome + normal distribution → t-test
- Continuous outcome + non-normal → Mann-Whitney U
- Binary outcome → Chi-square or Fisher's exact [... continues excerpting reference content ...]

For full details: @references/test-selection-guide.md
```

If you're excerpting "highlights", you're duplicating. Just reference the canonical source.

### Pattern 4: Multiple Small Chunks Over One Big Reference + Summary

**When**: Large file needs selective loading

**Do**:

```markdown
✅ CORRECT:

For context engineering: @docs/chunks/CONTEXT-ENGINEERING.md For subagent design: @docs/chunks/SUBAGENT-DESIGN.md For skill design: @docs/chunks/SKILL-DESIGN.md
```

Agent loads only what's needed for current task.

**Don't**:

```markdown
❌ WRONG:

@docs/BEST-PRACTICES.md

**Key practices**:

1. Context engineering - [summary]
2. Subagent design - [summary]
3. Skill design - [summary] [... continues summarizing the 700-line file ...]
```

This loads entire 700-line file, THEN adds summaries. Either chunk the source (preferred) or just reference it.

## Detection Heuristics for aops Skill

When reviewing documentation, check for:

**Red flags**:

1. **@reference followed by numbered/bulleted list** - Often a summary of referenced content
2. **Words like "key", "important", "main", "primary"** near @reference - Signals arbitrary selection
3. **@reference followed by section that repeats concepts from referenced file** - Check if content overlaps
4. **Same filename appears multiple times** in one skill - Each @reference loads full content
5. **Hook-loaded content also @referenced** - Check `hooks/load_instructions.py` for overlap

**Validation questions**:

1. Does content after @reference repeat what's in the referenced file?
2. Is the selection/summary based on axiom-derived criteria or arbitrary judgment?
3. Would removing the summary/list change what the agent understands? (If no → remove it)
4. Is this content already loaded by SessionStart hook?
5. Does the text trust the @reference mechanism, or hedge with "key points"?

**Test**: Remove everything after the @reference line. Does meaning change? If no → it was redundant.

## Common Justifications (and Rebuttals)

**"But it helps emphasize what's important"**

- REBUTTAL: Who decides what's important? That's arbitrary selection. Trust agents to read the full content.

**"But it provides quick reference"**

- REBUTTAL: The referenced file IS the quick reference. If it's too long, chunk it into smaller references.

**"But it saves agent time reading"**

- REBUTTAL: @reference loads full content regardless. You're not saving anything, just duplicating.

**"But it helps agents know what to focus on"**

- REBUTTAL: Tell them WHEN to use it, not WHAT it says. Example: "Use BEHAVIORAL-PATTERNS.md in step 2 of workflow" not "Behavioral patterns include..."

**"But this is standard technical writing practice"**

- REBUTTAL: Standard practice for humans reading sequentially. Agents see full referenced content immediately. Different medium, different rules.

## Enforcement Checklist

When reviewing any documentation with @references:

- [ ] Each @reference appears only once per file
- [ ] No content after @reference repeats/summarizes the referenced file
- [ ] No arbitrary selections ("key", "important", "main")
- [ ] Guidance focuses on WHEN/HOW to use referenced content, not WHAT it contains
- [ ] Referenced content not also loaded by SessionStart hook
- [ ] If file >300 lines, considered chunking instead of summarizing

## Examples: Before and After

### Example 1: Axioms

```markdown
❌ BEFORE (DRY violation):

## Core Principles

@docs/AXIOMS.md

**Key framework principles**:

1. **MINIMAL** - Actively fight bloat
2. **Enforcement Hierarchy** - Scripts > Hooks > Config > Instructions
3. **Experiment-Driven** - Test changes, don't speculate
4. **DRY via Chunks** - Extract reusable content
5. **Fail-Fast** - No workarounds, fix root cause
```

**Violations**:

- @reference loads all axioms, list duplicates some
- "Key" is arbitrary - not axiom-derived selection
- If hook loads AXIOMS.md, this is triple redundancy

```markdown
✅ AFTER (DRY compliant):

Follow core axioms from @docs/AXIOMS.md throughout all workflows.
```

Or if axioms are hook-loaded, even simpler:

```markdown
✅ AFTER (if hook-loaded):

[No reference needed - axioms already in context from SessionStart]
```

### Example 2: Behavioral Patterns

```markdown
❌ BEFORE (DRY violation):

@docs/chunks/BEHAVIORAL-PATTERNS.md

**Common patterns**:

- Defensive Behavior: Agent works around problems instead of failing fast
- Scope Creep: Agent does more than requested
- DRY Violations: Agent duplicates content
- Authority Violations: Wrong agent doing wrong work
```

**Violation**: Summarizing content that @reference already loaded.

```markdown
✅ AFTER (DRY compliant):

@docs/chunks/BEHAVIORAL-PATTERNS.md

**Step 2: Categorize by pattern** Identify which behavioral pattern from above matches the violation symptom.
```

Context about WHEN to use (step 2), not WHAT the patterns are.

### Example 3: Reference Material

```markdown
❌ BEFORE (DRY violation):

For statistical analysis, see @references/statistical-analysis.md

**Quick reference**:

- T-test: Continuous, normal distribution, compare means
- Mann-Whitney: Continuous, non-normal, compare distributions
- Chi-square: Categorical, test independence [... continues with 20 more tests ...]
```

**Violation**: Excerpting reference content.

```markdown
✅ AFTER (DRY compliant):

For statistical test selection: @references/statistical-analysis.md
```

Trust the reference. If file is too long, chunk it.

## Relationship to Other Principles

**DRY (Axiom 8)**:

- Reference hygiene IS DRY enforcement
- One canonical source, many references
- No duplication via summary/excerpt

**Fail-Fast (Axiom 5-6)**:

- Trust infrastructure (hooks, @references)
- Don't hedge with "just in case" summaries
- If reference mechanism broken, fix it, don't work around

**Use Standard Tools (Axiom 9)**:

- @reference IS the standard mechanism
- Don't reinvent with manual summaries
- Trust the tool

**Arbitrary Selection**:

- Violates Axiom 0: "NO OTHER TRUTHS"
- Can't decide anything not directly derivable from axioms
- "Key principles" selection = arbitrary = forbidden

## Summary

**Core principle**: @reference loads content. Trust it. Don't repeat it.

**When you see @reference**:

- Content is now in full context
- Don't summarize what's already loaded
- Don't highlight "key points" arbitrarily
- Provide context on WHEN/HOW to use, not WHAT it contains

**The aops skill's job**: Detect and remove all "Reference + Summary" violations.
