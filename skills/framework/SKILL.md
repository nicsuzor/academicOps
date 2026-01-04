---
name: framework
description: Categorical framework governance. Treats every change as a universal
  rule. Delegates user data operations to skills.
allowed-tools: Read,Grep,Glob,Edit,Write,Skill,AskUserQuestion
version: 4.2.0
permalink: skills-framework
---

# Framework Conventions Skill

**When to invoke**: Before modifying framework infrastructure OR when making any change that should become a generalizable pattern.

**What it provides**: Categorical analysis, conventions, delegation to appropriate skills, **compliance assessment**.

**What it doesn't do**: Ad-hoc one-off changes. Every action must be justifiable as a universal rule.

## Logical Derivation System

This framework is a **validated logical system**. Every component must be derivable from axioms and supporting documents.

### Authoritative Source Chain (Read in Order)

| Priority | Document          | Contains                                   |
| -------- | ----------------- | ------------------------------------------ |
| 1        | [[AXIOMS.md]]     | Inviolable principles                      |
| 2        | [[HEURISTICS.md]] | Empirically validated guidance (revisable) |
| 3        | [[VISION.md]]     | What we're building, success criteria      |
| 4        | [[ROADMAP.md]]    | Current status, done/planned/issues        |
| 5        | This skill        | Conventions derived from above             |
| 6        | [[README.md]]     | Feature inventory                          |
| 7        | [[INDEX.md]]      | File tree                                  |

Paths resolved in [[FRAMEWORK.md]] (injected at session start).

**Derivation rule**: Every convention in the [[academicOps]] framework MUST trace to an axiom or vision statement. If it can't, the convention is invalid.

### Compliance Assessment Protocol

When assessing any component for compliance:

1. **Trace to axiom**: Which axiom(s) justify this component's existence?
2. **Check placement**: Does INDEX.md define where this belongs?
3. **Verify uniqueness**: Is this information stated exactly once (DRY)?
4. **Confirm purpose**: Does VISION.md support this capability?

If ANY check fails → component is non-compliant → refactor or delete.

### HALT Protocol (MANDATORY)

**When you encounter something you cannot derive:**

1. **STOP** - Do not guess, do not work around
2. **STATE** - "I cannot determine [X] because [Y]"
3. **ASK** - Use AskUserQuestion to get clarification
4. **DOCUMENT** - Once resolved, add the rule to appropriate location

**Examples requiring HALT:**
- File doesn't fit any defined category
- Two axioms appear to conflict
- Placement is ambiguous (could go in multiple locations)
- New pattern with no existing convention

## Framework Introspection (MANDATORY - FIRST STEP)

**Before ANY action**, load the framework structure and verify consistency.

### Step 1: Load Authoritative Documents

Read these files in order (use Read tool):

1. `$AOPS/AXIOMS.md` - Inviolable principles
2. `$AOPS/HEURISTICS.md` - Empirically validated guidance
3. `$AOPS/INDEX.md` - Authoritative file tree
4. `$AOPS/VISION.md` - Goals and scope
5. `$AOPS/ROADMAP.md` - Current status

**Do NOT proceed until all 5 documents are loaded.** This ensures every action is informed by the complete framework state.

### Step 2: Run Consistency Checks

Before accepting ANY proposed change, verify ALL of:

| Check | Question | Failure = HALT |
|-------|----------|----------------|
| Axiom derivation | Which axiom(s) justify this change? | Cannot identify axiom |
| INDEX placement | Does INDEX.md define where this belongs? | Location not in INDEX |
| DRY compliance | Is this information stated exactly once? | Duplicate exists elsewhere |
| VISION alignment | Does VISION.md support this capability? | Outside stated scope |
| Namespace uniqueness | Does this name conflict with existing skill/command/hook/agent? | Name collision detected |

### Step 3: HALT Protocol on Inconsistency

If ANY check fails:

1. **STOP** - Do not proceed with the change
2. **REPORT** - State exactly which check failed and why
3. **ASK** - Use AskUserQuestion: "How should we resolve this inconsistency?"
4. **WAIT** - Do not attempt workarounds or auto-fixes

**Example HALT output:**
```
FRAMEWORK INTROSPECTION FAILED

Check failed: DRY compliance
Issue: Proposed content duplicates information in $AOPS/README.md lines 45-52
Options:
1. Reference existing content instead of duplicating
2. Move authoritative content to new location
3. Proceed anyway (requires explicit user approval)
```

---

## Categorical Imperative (MANDATORY)

Per AXIOMS.md #1: Every action must be justifiable as a universal rule derived from these AXIOMS.

### Before ANY Change

1. **State the rule**: What generalizable principle justifies this action?
2. **Check rule exists**: Is this in AXIOMS, this skill, or documented elsewhere?
3. **If no rule exists**: Propose the rule. Get user approval. Document it.
4. **Ad-hoc actions are PROHIBITED**: If you can't generalize it, don't do it.

### File Boundaries (ENFORCED)

| Location | Action | Reason |
|----------|--------|--------|
| `$AOPS/*` | Direct modification OK | Public framework files |
| `$ACA_DATA/*` | **MUST delegate to skill** | User data requires repeatable processes |

**Rationale**: If we need to operate on user data, we build a skill for it. One-off scripts and manual changes are prohibited. This ensures every process is generalizable and repeatable.

### When Operating on User Data

1. **Identify the operation category**: What type of work is this?
2. **Find existing skill**: Does a skill already handle this? (remember, tasks, analyst, etc.)
3. **If skill exists**: Invoke it with `FRAMEWORK SKILL CHECKED` token
4. **If NO skill exists**: Create one first, THEN invoke it

### Creating Skills for New Operations

When no skill handles a needed user data operation:

1. **Use this skill** to create the new skill (skill creation is a framework operation)
2. Follow "Adding a Skill" pattern in Component Patterns section
3. Skill must be generalizable (not one-off)
4. Then invoke the new skill to do the actual work

**This is recursive**: Creating a skill uses the framework skill. The framework skill provides the patterns. Skill creation happens in `$AOPS/skills/` (framework files = direct modification OK).

**Example**: Need to persist framework learning?
1. Invoke `framework` skill
2. Framework skill delegates to `remember` skill for knowledge persistence
3. Future retrieval uses memory server for semantic search

- ❌ Wrong: Directly delete files in `$ACA_DATA/`
- ✅ Right: Create skill via framework, then invoke it


## Framework Paths

See [[INDEX.md]] for complete file tree. Paths are resolved in [[FRAMEWORK.md]] (injected at session start).

## Core Conventions (with Axiom Derivations)

Each convention traces to its source axiom. If a convention lacks derivation, it's invalid.


### Single Source of Truth

Each piece of information exists in exactly ONE location:

| Information | Authoritative Location |
|-------------|------------------------|
| Principles | `$AOPS/AXIOMS.md` |
| File tree | `$AOPS/INDEX.md` |
| Feature inventory | `$AOPS/README.md` |
| User context | `$ACA_DATA/CORE.md` |
| Work style | `$ACA_DATA/ACCOMMODATIONS.md` |
| Framework vision | `$AOPS/VISION.md` |
| Framework status | `$AOPS/ROADMAP.md` |
| Workflows | `$AOPS/WORKFLOWS.md` |

**Pattern**: Reference, don't repeat.

### Mandatory Critic Review

Before presenting any plan or conclusion to the user, invoke the critic agent:

```
Task(subagent_type="critic", model="opus", prompt="
Review this plan/conclusion for errors and hidden assumptions:

[PLAN OR CONCLUSION SUMMARY]

Check for: logical errors, unstated assumptions, missing verification, overconfident claims.
")
```

If critic returns **REVISE** or **HALT**, address issues before proceeding.

### Skills are Read-Only

Skills in `skills/` MUST NOT contain dynamic data. All mutable state goes in `$ACA_DATA/`.

### Trust Version Control

- Never create backup files (`.bak`, `_old`, etc.)
- Edit directly, git tracks changes
- Commit AND push after completing work

### Markdown Format Convention

All framework markdown files use properly formatted markdown with relative wikilinks:

1. **Frontmatter**: Required fields: `title`, `permalink`, `type`, `tags`
2. **Links**: Use relative wikilinks with paths: `[[folder/file.md]]` or `[[../sibling/file.md]]`
3. **Graph connectivity**: Links create Obsidian graph edges; consistent linking builds navigable documentation

```markdown
# In skills/analyst/SKILL.md:
[[instructions/dbt-workflow.md]]     # ✅ Relative path within skill
[[../framework/SKILL.md]]            # ✅ Relative to sibling skill
[[AXIOMS.md]]                        # ✅ Root-level reference
```

## Documentation Structure

See [[INDEX.md]] for complete file tree and document purposes.

### Documentation Rules

1. **AXIOMS.md is pure** - Principles only. No enforcement, examples, or implementation.
2. **VISION.md is grounded** - Academic support framework, not autonomous research.
3. **ROADMAP.md is simple** - Just lists: Done, In Progress, Planned, Issues.
4. **README.md has the inventory** - Every skill/command/hook with one-line purpose and how to invoke.
5. **No other core docs** - specs/ and experiments/ handle implementation details; episodic observations go to GitHub Issues.

### Feature Inventory Format (README.md)

Each capability listed with:
- Name
- Purpose (one line)
- Invocation (how to use it)
- Test (how it's verified)

## Anti-Bloat Rules

### File Limits

- Skill files: 500 lines max
- Documentation chunks: 300 lines max
- Approaching limit = Extract and reference

### Prohibited Bloat

1. Multi-line summaries after references (brief inline OK)
2. Historical context ("What's Gone", migration notes)
3. Meta-instructions ("How to use this file")
4. Duplicate explanations across files

### File Creation

New files PROHIBITED unless:
1. Clear justification (existing files insufficient)
2. Integration test validates purpose
3. Test passes before commit

## Component Patterns

**Testing requirement**: All framework tests must be **e2e against production code with live data**. No unit tests, no mocks of internal code. See `references/testing-with-live-data.md`.

### Adding a Skill

1. Create `skills/<name>/SKILL.md`
2. Follow YAML frontmatter format (see existing skills)
3. Keep under 500 lines
4. Add e2e test (NOT unit test - test real behavior with real data)

### Adding a Command

1. Create `commands/<name>.md`
2. Define YAML frontmatter (name, description, tools)
3. Commands are slash-invoked: `/name`
4. **Name must not match any skill name** - Claude Code treats same-named commands as model-only (user gets "can only be invoked by Claude" error)

### Adding a Hook

1. **Read [[references/hooks_guide.md]] first** - contains architecture principles
2. Create hook in `hooks/` directory
3. Triggers: PreToolUse, PostToolUse, UserPromptSubmit, SessionStart, Stop
4. Hooks inject context/instructions - they NEVER call LLM APIs directly

### Script Design

Scripts are SIMPLE TOOLS that agents call via Bash:

**Allowed**: Mechanical data transformation (chunking, merging)
**Prohibited**: File reading, pattern matching, filtering, reasoning

Agents orchestrate. Scripts are utilities.

### Workflows

Step-by-step guides for common framework operations:

- [[workflows/01-design-new-component.md]] - Adding hooks, skills, scripts, commands
- [[workflows/02-debug-framework-issue.md]] - Investigating framework problems (**includes Deep Root Cause Analysis - MANDATORY for "why didn't X work?" questions**)
- [[workflows/03-experiment-design.md]] - Creating framework experiments
- [[workflows/04-monitor-prevent-bloat.md]] - Keeping framework lean
- [[workflows/06-develop-specification.md]] - Writing specs for new features

## Framework Project Data (`$AOPS/`)

Per [[AXIOMS]] #28 (Current State Machine): `$ACA_DATA` contains ONLY semantic memory (current state). Episodic memory (observations) lives in **GitHub Issues** (nicsuzor/academicOps repo).

### Storage Classification

| Type | Memory | Location | Rule |
|------|--------|----------|------|
| Vision/Strategy | SEMANTIC | `VISION.md`, `ROADMAP.md` | Current state. Edit in place. |
| Specifications | SEMANTIC | `specs/` | Timeless. One per feature. See [[AXIOMS]] #29 |
| Bug investigations | EPISODIC | GitHub Issue (label: `bug`) | Synthesize → close when fixed |
| Experiment observations | EPISODIC | GitHub Issue (label: `experiment`) | Synthesize → close |
| Development logs | EPISODIC | GitHub Issue (label: `devlog`) | Synthesize patterns → close |
| Decision rationales | EPISODIC | GitHub Issue (label: `decision`) | Synthesize → close |
| Session transcripts | ARCHIVE | `~/writing/sessions/` | Raw data (too large for Issues) |

### Creating Episodic Content

When you have an observation, investigation, or time-bound record:

1. **Create GitHub Issue** in nicsuzor/academicOps repo
2. **Apply label**: `bug`, `experiment`, `devlog`, `decision`, or `learning`
3. **Add observations** as Issue comments over time
4. **Synthesize** when patterns emerge → update HEURISTICS.md or specs/
5. **Close Issue** with link to synthesized content

```bash
# Example: Create a bug investigation Issue
gh issue create --repo nicsuzor/academicOps --title "Bug: [description]" --label "bug" --body "## Investigation\n\n[details]"
```


### Before Creating Content

1. **Is this semantic (timeless truth)?** → `$ACA_DATA` (specs/, HEURISTICS.md)
2. **Is this episodic (observation)?** → GitHub Issue
3. **Is this raw archive?** → `~/writing/sessions/` or git history

### Synthesis Workflow

Episodic → Semantic:
1. Observations accumulate in GitHub Issue(s)
2. Pattern emerges across multiple observations
3. Create/update semantic doc (HEURISTICS.md entry or spec)
4. Close Issue(s) with link: "Synthesized to HEURISTICS.md H[n]"
5. Closed Issues remain searchable via GitHub

## Compliance Refactoring Workflow

When bringing components into compliance with this logical system:

### Step 1: Assess Current State

For each component (file, convention, pattern):
1. Can its existence be derived from AXIOMS + VISION?
2. Is it in the location defined by INDEX.md?
3. Is its information unique (not duplicated elsewhere)?

### Step 2: Classify the Issue

| Issue Type | Action |
|------------|--------|
| No axiom derivation | Delete or propose new axiom (HALT, ask user) |
| Wrong location | Move to correct location per INDEX.md |
| Duplicated content | Consolidate to single authoritative source |
| Missing from INDEX | Add to INDEX.md or delete if invalid |
| Ambiguous placement | **HALT** - ask user to clarify |

### Step 3: Incremental Change

- Fix ONE issue at a time
- Commit after each fix
- Verify no regressions (run tests)
- Update ROADMAP.md if significant

### Step 4: Document the Rule

If you discovered a new pattern:
1. Propose the generalizable rule
2. Get user approval
3. Add to this skill with axiom derivation
4. Never apply ad-hoc fixes without rules

## Reference Documentation

Detailed guides for specific framework topics:

- [[references/hooks_guide.md]] - Hook system architecture and patterns
- [[references/script-design-guide.md]] - Script design principles
- [[references/e2e-test-harness.md]] - Test harness infrastructure
- [[references/claude-code-config.md]] - Claude Code configuration
- [[references/strategic-partner-mode.md]] - Strategic collaboration mode

## Before You Modify

1. **Check existing patterns** - Similar component exists?
2. **Verify paths** - Right location per conventions?
3. **Validate scope** - Single responsibility?
4. **Plan test** - How will you verify it works?
5. **Trace to axiom** - Which principle justifies this?

## After Framework Sessions

**VISION.md and ROADMAP.md ARE the framework's memory.** Without them being current, agents cannot understand what the framework is, what's working, or what needs attention.

After any significant framework work, check if updates are needed:
- **VISION.md**: End state. Update when direction changes (rare).
- **ROADMAP.md**: Current status. Update after features added, bugs fixed, or blockers identified.
