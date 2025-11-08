# Agent Behavioral Patterns

Categorization guide for agent violations and bugs. Group issues by underlying behavioral patterns, not surface symptoms.

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

**Root Cause**: Agent doesn't trust fail-fast philosophy

**Why It's Wrong**: Silent failures corrupt research data. Fail immediately so problems get fixed, not hidden.

**Enforcement Target**:

- Scripts: check_fail_fast.py detects defensive patterns
- Hooks: validate_tool.py blocks try/except with defaults
- Config: No permissions workarounds needed
- Instructions: Core axioms need reinforcement

**Issue Labels**: `agent-behavior`, `fail-fast-violation`

### Pattern 2: Scope Creep

**Symptom**: Agent does more than requested, expands task beyond original ask.

**Examples**:

- User asks question → Agent launches into solution before answering
- User reports bug → Agent fixes it without asking
- User requests feature A → Agent also implements related features B and C
- Finding one problem → "Helpfully" fixing all similar problems

**Root Cause**: Agent violates "DO ONE THING" and "ANSWER DIRECT QUESTIONS" axioms

**Why It's Wrong**: Interruptions are impossible when agent expands scope. User loses control.

**Enforcement Target**:

- Scripts: None needed (behavioral, not detectable)
- Hooks: None needed
- Config: None needed
- Instructions: Axioms need emphasis, examples

**Issue Labels**: `agent-behavior`, `scope-creep`

### Pattern 3: DRY Violations

**Symptom**: Agent duplicates content across multiple files.

**Examples**:

- Repeating core axioms in skill-specific files
- Duplicating workflow descriptions in multiple skills
- Creating similar scripts with minor differences
- Copying documentation instead of referencing

**Root Cause**: Agent doesn't recognize existing content or doesn't understand DRY principle

**Why It's Wrong**: Creates maintenance burden, divergence, confusion about authoritative source.

**Enforcement Target**:

- Scripts: check_duplication.py detects repeated content
- Hooks: validate_tool.py warns on large file additions
- Config: None needed
- Instructions: Modular documentation architecture

**Issue Labels**: `agent-behavior`, `dry-violation`, `documentation`

### Pattern 4: Authority Violations

**Symptom**: Wrong agent doing wrong work, bypassing required agents/skills.

**Examples**:

- General agent performing specialized work (should invoke skill)
- Agent modifying files outside its domain
- Bypassing quality gates or required workflows

**Root Cause**: Agent boundaries unclear, agent doesn't know when to delegate.

**Why It's Wrong**: Bypasses quality gates, violates separation of concerns, breaks specialization.

**Enforcement Target**:

- Scripts: check_agent_authority.py (future)
- Hooks: None needed
- Config: Permissions can restrict file access
- Instructions: Skill definitions need clearer boundaries

**Issue Labels**: `agent-behavior`, `authority-violation`

### Pattern 5: Use Standard Tools Violations

**Symptom**: Agent creates custom implementations of solved problems.

**Examples**:

- Creating custom implementations instead of using existing libraries
- Reinventing wheels (secrets detection, CLI parsing, validation)
- Not searching for existing libraries before writing code

**Why It's Wrong**: Creates maintenance burden, introduces bugs, wastes time.

**Enforcement Target**:

- Scripts: check_standard_tools.py
- Hooks: None needed
- Config: None needed
- Instructions: "Use Standard Tools" axiom needs examples

**Issue Labels**: `agent-behavior`, `reinvented-wheel`

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

## Quick Reference

| Pattern              | Enforcement Layer      | Labels                |
| -------------------- | ---------------------- | --------------------- |
| Defensive Behavior   | Scripts > Hooks        | `fail-fast-violation` |
| Scope Creep          | Instructions           | `scope-creep`         |
| DRY Violations       | Scripts > Instructions | `dry-violation`       |
| Authority Violations | Instructions > Config  | `authority-violation` |
| Use Standard Tools   | Scripts > Skills       | `reinvented-wheel`    |
| Infrastructure       | Scripts > Config       | `infrastructure`      |
