# Framework Evolution Changelog

Track significant framework pattern changes that affect skills.

## 2024-01-24: Skills-First Architecture

**Pattern**: Transition from agent-heavy to skills-first architecture
**Affected**: All skills created before this date
**Migration Steps**:
1. Extract procedural knowledge from agents to skills
2. Convert agents to orchestrators that call skills
3. Remove duplicate instructions from agents
4. Ensure skills are atomic and composable

## 2024-01-23: @reference Pattern System

**Pattern**: New @reference system for just-in-time context loading
**Affected**: Skills with large reference documents
**Migration Steps**:
1. Move detailed docs to references/ directory
2. Add @reference annotations in SKILL.md
3. Keep SKILL.md under 5k words
4. Ensure references are loaded only when needed

## 2024-01-22: Enforcement Hierarchy

**Pattern**: Scripts > Hooks > Config > Instructions
**Affected**: All skills with deterministic operations
**Migration Steps**:
1. Move deterministic operations to scripts/
2. Use hooks for framework-level enforcement
3. Configuration for user preferences
4. Instructions only for guidance

## 2024-01-21: Imperative Form Standard

**Pattern**: All skill instructions use imperative/infinitive form
**Affected**: All skills using second-person language
**Migration Steps**:
1. Remove "you should/must/will" patterns
2. Convert to verb-first instructions
3. Use objective, instructional language
4. Focus on WHAT and HOW

## 2024-01-20: YAML Frontmatter Requirements

**Pattern**: Strict YAML frontmatter format for skills
**Affected**: Skills with incomplete or incorrect frontmatter
**Migration Steps**:
1. Ensure name field matches directory name
2. Description starts with "This skill"
3. Description is 50+ characters
4. Valid YAML syntax with --- delimiters

## 2024-01-19: Atomic Skills Principle

**Pattern**: Skills do ONE thing well
**Affected**: Mega-skills trying to do multiple things
**Migration Steps**:
1. Break large skills into atomic components
2. Each skill has single clear purpose
3. Skills compose together for complex tasks
4. No dependencies between skills

## 2024-01-18: Universal Portability

**Pattern**: Skills work in ANY repository
**Affected**: Skills with hardcoded paths or assumptions
**Migration Steps**:
1. Remove all hardcoded paths
2. Use relative paths or environment variables
3. Document patterns instead of specific files
4. Test skill in different contexts

## Pattern Detection Guide

Use these patterns in audit_skills.py to detect outdated code:

### Pre-Skills-First Patterns
- References to `.claude/agents`
- Agent-specific language: "agent should"
- Embedded procedural knowledge in agents

### Old Reference System
- References to `docs/_CHUNKS`
- Large embedded documentation in SKILL.md
- Missing references/ directory usage

### Second-Person Language
- Pattern: `[Yy]ou (should|must|will|can)`
- Should be imperative form instead

### Old Path References
- `/home/*/projects/*` hardcoded paths
- Project-specific file references
- Missing environment variable usage

## Update Priority

When updating skills, apply changes in this order:

1. **Critical**: Fix broken references and paths
2. **High**: Convert to imperative form
3. **Medium**: Apply enforcement hierarchy
4. **Low**: Optimize reference loading

## Validation Checklist

After updates, ensure:
- [ ] YAML frontmatter valid
- [ ] Scripts executable
- [ ] References exist
- [ ] No hardcoded paths
- [ ] Imperative form used
- [ ] Skills are atomic
- [ ] Works universally
