# academicOps Agent Behavioral Patterns

Categorization guide for agent violations and bugs in the academicOps framework. Group issues by underlying behavioral patterns, not surface symptoms.

## Purpose

When agents violate core axioms or instructions, categorize by the behavioral pattern that caused the violation. This enables:

- Recognizing systemic issues vs one-off mistakes
- Identifying enforcement gaps in the hierarchy (scripts > hooks > config > instructions)
- Tracking which patterns are recurring vs resolved
- Designing targeted interventions

## Core Behavioral Patterns

### Pattern 1: Defensive Behavior

**Symptom**: Agent tries to work around problems instead of failing fast.

**Examples**:

- Creating `_new` files instead of editing existing files
- Adding `try/except` blocks with fallback values
- Building workarounds for broken infrastructure
- Using `.get(key, default)` for required configuration
- Checking `if x is None: x = fallback` patterns

**Root Cause**: Agent doesn't trust fail-fast philosophy (Axiom #7, #8)

**Why It's Wrong**: Silent failures corrupt research data. Fail immediately so problems get fixed, not hidden.

**Enforcement Target**:

- Scripts: check_fail_fast.py detects defensive patterns
- Hooks: validate_tool.py blocks try/except with defaults
- Config: No permissions workarounds needed
- Instructions: _CORE.md Axiom #7 needs reinforcement

**Issue Labels**: `agent-behavior`, `fail-fast-violation`

### Pattern 2: Scope Creep

**Symptom**: Agent does more than requested, expands task beyond original ask.

**Examples**:

- User asks question → Agent launches into solution before answering
- User reports bug → Agent fixes it without asking
- User requests feature A → Agent also implements related features B and C
- Finding one problem → "Helpfully" fixing all similar problems

**Root Cause**: Agent violates "DO ONE THING" (Axiom #1) and "ANSWER DIRECT QUESTIONS" (Axiom #2)

**Why It's Wrong**: Interruptions are impossible when agent expands scope. User loses control.

**Enforcement Target**:

- Scripts: None needed (behavioral, not detectable)
- Hooks: None needed
- Config: None needed
- Instructions: Axiom #1, #2 need emphasis, examples

**Issue Labels**: `agent-behavior`, `scope-creep`

### Pattern 3: DRY Violations

**Symptom**: Agent duplicates content across multiple files.

**Examples**:

- Repeating core axioms in agent-specific files
- Duplicating workflow descriptions in multiple agents
- Creating similar scripts with minor differences
- Copying documentation instead of referencing

**Root Cause**: Agent doesn't recognize existing content or doesn't understand DRY principle (Axiom #10)

**Why It's Wrong**: Creates maintenance burden, divergence, confusion about authoritative source.

**Enforcement Target**:

- Scripts: check_duplication.py detects repeated content
- Hooks: validate_tool.py warns on large file additions (check if exists elsewhere)
- Config: None needed
- Instructions: #111 modular documentation architecture

**Issue Labels**: `agent-behavior`, `dry-violation`, `documentation`

### Pattern 4: Authority Violations

**Symptom**: Wrong agent doing wrong work, bypassing required agents.

**Examples**:

- Trainer agent fixing code bugs directly (should invoke developer agent)
- Developer agent committing without code-review agent
- General agent performing specialized work (should invoke skill)
- Agent modifying files outside its domain

**Root Cause**: Agent boundaries unclear, agent doesn't know when to delegate.

**Why It's Wrong**: Bypasses quality gates, violates separation of concerns, breaks agent specialization.

**Enforcement Target**:

- Scripts: check_agent_authority.py (future)
- Hooks: None needed
- Config: Permissions can restrict file access by agent
- Instructions: Agent definitions need clearer boundaries

**Issue Labels**: `agent-behavior`, `authority-violation`, `agent-chaining`

### Pattern 5: Axiom Violations (Specific)

Each core axiom can be violated in specific ways. Document separately:

#### Axiom #1: DO ONE THING - Already covered by Scope Creep

#### Axiom #2: ANSWER DIRECT QUESTIONS

**Violations**:

- Launching into solutions before answering
- Assuming user wants fix when they asked question
- Providing context before answer

**Example**:

```
User: "Where are client errors handled?"
❌ Agent: "Let me search the codebase and also check for related issues and fix any bugs I find..."
✅ Agent: "Client errors are handled in src/services/process.ts:712"
```

#### Axiom #3: Namespace Separation

**Violations**:

- Putting agent instructions in docs/ (human documentation space)
- Putting human documentation in agents/ (AI instruction space)
- Mixing imperative (agent) and descriptive (human) language

#### Axiom #4: Data Boundaries

**Violations**:

- Leaking private repo content to public bot/ repo
- Posting sensitive client data to public GitHub

#### Axiom #7: Fail-Fast Philosophy (Code)

**Violations**: See Defensive Behavior pattern

#### Axiom #8: Fail-Fast Philosophy (Agents)

**Violations**:

- Working around broken hooks instead of reporting
- Attempting recovery when infrastructure fails
- Continuing with workarounds instead of stopping

#### Axiom #10: DRY

**Violations**: See DRY Violations pattern

#### Axiom #11: Use Standard Tools

**Violations**:

- Creating custom implementations of solved problems
- Reinventing wheels (secrets detection, CLI parsing, validation)
- Not searching for existing libraries before writing code

**Example**: Issue #141 - custom sanitization script instead of DataFog

#### Axiom #13: VERIFY FIRST

**Violations**:

- Assuming state instead of checking
- Guessing file paths instead of reading
- Making changes without reading current content

#### Axiom #14: NO EXCUSES

**Violations**:

- Closing issues without confirmation
- Claiming success without verification
- Rationalizing failures instead of fixing

### Pattern 6: Infrastructure Violations

**Symptom**: Agent doesn't properly use framework infrastructure.

**Examples**:

- Hardcoding paths instead of using environment variables
- Not using hooks when available
- Bypassing permission system
- Not loading required instruction files

**Root Cause**: Agent doesn't understand framework architecture or tries to shortcut.

**Why It's Wrong**: Breaks portability, bypasses enforcement, creates technical debt.

**Enforcement Target**:

- Scripts: check_infrastructure_use.py
- Hooks: Already enforces infrastructure
- Config: Already enforces permissions
- Instructions: Better infrastructure documentation needed

**Issue Labels**: `infrastructure`, `agent-behavior`

## Error Categorization

For non-behavioral errors (bugs in code, not agent violations):

### Environment Errors

- Missing dependencies
- Wrong paths
- Environment variables not set
- Python/Node version incompatibilities

### Integration Errors

- Tool compatibility (gh, git, uv, pytest)
- API failures
- Version mismatches

### Hook/Script Errors

- Logic bugs in validation scripts
- Edge cases not handled
- Performance issues

### Permission Issues

- Tool blocked inappropriately
- Tool allowed when should be blocked
- Permission configuration errors

## Categorization Workflow

When documenting an agent violation or bug:

1. **Identify the symptom**: What did the agent do wrong?
2. **Recognize the pattern**: Which behavioral pattern caused this?
3. **Determine root cause**: Why did this pattern manifest?
4. **Select enforcement layer**: Scripts > Hooks > Config > Instructions
5. **Label appropriately**: Use pattern-based labels
6. **Link related issues**: Same pattern = related issues

## Issue Granularity

**Create SEPARATE issues when**:

- Different behavioral patterns (scope creep vs defensive behavior)
- Different root causes requiring different solutions
- Different enforcement layers needed

**CONSOLIDATE into ONE issue when**:

- Same behavioral pattern with multiple instances
- Same root cause in different contexts
- Same enforcement solution applies

**Example**:

- Issue A: "Agent creates _new files" (Defensive Behavior pattern)
- Issue B: "Agent uses try/except fallbacks" (Defensive Behavior pattern)
- **Should be**: ONE issue "Defensive Behavior: Agent doesn't trust fail-fast" with both examples

## Pattern Evolution

Patterns change over time:

**Track pattern frequency**:

- First occurrence → New pattern, document thoroughly
- Recurring (2-3 times) → Systemic issue, needs enforcement
- Frequent (>3 times) → Enforcement failed, escalate hierarchy

**Pattern lifecycle**:

1. **Discovery**: First instance observed
2. **Documentation**: Pattern identified, categorized
3. **Intervention**: Enforcement added (instructions)
4. **Escalation**: If recurring, move to hooks/scripts
5. **Resolution**: Pattern no longer observed
6. **Monitoring**: Watch for recurrence

## Related Issues

- #111: Modular documentation architecture (DRY enforcement)
- #116: TRAINER.md complexity budget (pattern bloat)
- #141: Axiom #11 violations (Use Standard Tools)
- #142: Skill complexity budget (enforcement layer choice)

## Quick Reference

| Pattern              | Axiom Violated | Enforcement Layer      | Labels                |
| -------------------- | -------------- | ---------------------- | --------------------- |
| Defensive Behavior   | #7, #8         | Scripts > Hooks        | `fail-fast-violation` |
| Scope Creep          | #1, #2         | Instructions           | `scope-creep`         |
| DRY Violations       | #10            | Scripts > Instructions | `dry-violation`       |
| Authority Violations | N/A            | Instructions > Config  | `authority-violation` |
| Use Standard Tools   | #11            | Scripts > Skills       | `reinvented-wheel`    |
| Infrastructure       | N/A            | Scripts > Config       | `infrastructure`      |
