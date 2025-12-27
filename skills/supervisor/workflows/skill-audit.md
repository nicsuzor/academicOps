---
name: skill-audit
description: Review skills for content separation - actionable instructions vs background/explanatory content
required-skills:
  - framework
scope:
  - Auditing skill files for content separation
  - Ensuring SKILL.md contains only agent instructions
  - Moving explanatory content to specs or references
  - Enforcing skill file size limits
---

# Skill Audit Workflow Template

This workflow reviews all skills to ensure content separation: SKILL.md files should contain ONLY actionable agent instructions. Background, explanations, and rationale belong in specs or references.

## Content Separation Principle

**SKILL.md should contain:**
- ✅ Direct instructions for agents
- ✅ Step-by-step workflows
- ✅ Subagent prompt templates
- ✅ Quality gates and checklists
- ✅ Tool invocation patterns

**SKILL.md should NOT contain:**
- ❌ Background explanations ("why we do this")
- ❌ Historical context
- ❌ Detailed rationale
- ❌ Tutorial-style content
- ❌ Reference documentation (belongs in `references/`)
- ❌ Design decisions (belong in specs)

---

## ITERATION UNIT

One audit cycle = review one skill → identify violations → report findings

Each cycle:
1. Read SKILL.md
2. Check for inlined explanatory content
3. Check file size (<500 lines)
4. Check for content that belongs elsewhere
5. Report findings with specific file:line references

---

## QUALITY GATE

For each skill reviewed:

- [ ] File size under 500 lines
- [ ] No multi-paragraph explanations
- [ ] No "why we do this" sections
- [ ] No historical context
- [ ] References point to `references/` subdirectory
- [ ] Templates in `templates/` subdirectory if present

---

## PHASE 1: DISCOVERY

### Find All Skills

```
Task(subagent_type="Explore", prompt="
Find all skill files in the framework.

Search: $AOPS/skills/*/SKILL.md

Report:
- Total skill count
- List of all skill paths
- Any skills without SKILL.md (violations)
")
```

### Create Audit Checklist

Populate TodoWrite with all skills to review.

---

## PHASE 2: PARALLEL REVIEW

### Spawn Review Agents

Spawn 4 parallel agents, each reviewing a subset of skills:

```
Task(subagent_type="general-purpose", prompt="
Audit these skills for content separation violations:

Skills to review:
1. {skill_path_1}
2. {skill_path_2}
...

**FIRST**: Invoke Skill(skill='framework') to load conventions.

For each SKILL.md, check:

1. **File Size**
   - Count total lines
   - VIOLATION if >500 lines

2. **Explanatory Content**
   - Look for paragraphs explaining 'why' instead of 'how'
   - Look for background context sections
   - Look for historical notes
   - VIOLATION if found - quote the content with line numbers

3. **Inlined References**
   - Look for detailed reference material that should be in references/
   - Look for long code examples (>20 lines)
   - VIOLATION if found

4. **Missing Subdirectories**
   - Check if skill has templates that should be in templates/
   - Check if skill has references that should be in references/
   - VIOLATION if inlined instead of separated

5. **Content Actionability Test**
   - For each major section, ask: 'Is this telling an agent WHAT TO DO?'
   - If a section is purely informational, it's a VIOLATION

Return structured report:
- Skill: {path}
- Line count: {n}
- Violations:
  - Type: {violation_type}
  - Lines: {start}-{end}
  - Content: {quoted_content}
  - Recommendation: {what_to_do}
- Overall: PASS or FAIL
")
```

---

## PHASE 3: CONSOLIDATE FINDINGS

### Aggregate Reports

Collect all agent reports and consolidate:

```
## Skill Audit Summary

### Skills Passing: {count}
{list of passing skills}

### Skills Failing: {count}

#### {skill_name}
- Line count: {n} (OVER LIMIT / OK)
- Violations:
  1. {violation_type} at lines {n}-{m}
     Content: "{quoted}"
     Fix: {recommendation}
```

### Prioritize Fixes

If violations found, ask user how to proceed:

```
AskUserQuestion(questions=[{
  "question": "How should we handle the skill violations?",
  "header": "Fix Strategy",
  "options": [
    {"label": "Fix all now", "description": "Refactor all failing skills in this session"},
    {"label": "Fix critical only", "description": "Only fix skills >500 lines or with major violations"},
    {"label": "Report only", "description": "Just provide the report, I'll fix manually"},
    {"label": "Fix one", "description": "Fix the worst offender as an example"}
  ],
  "multiSelect": false
}])
```

---

## PHASE 4: REFACTORING (If Requested)

### For Each Skill to Fix

```
Task(subagent_type="general-purpose", prompt="
Refactor this skill for content separation:

Skill: {skill_path}
Violations: {list_of_violations}

**FIRST**: Invoke Skill(skill='framework') to load conventions.

Refactoring steps:

1. **Extract Explanatory Content**
   - Create spec file if rationale/design content found
   - Move to: $ACA_DATA/projects/aops/specs/{skill-name}.md
   - Replace with brief link: 'See [[specs/{skill-name}.md]] for rationale'

2. **Extract References**
   - Create references/ subdirectory if needed
   - Move detailed reference content to references/{topic}.md
   - Replace with: 'See [[references/{topic}.md]]'

3. **Extract Templates**
   - Create templates/ subdirectory if needed
   - Move template content to templates/{name}.md
   - Reference from SKILL.md

4. **Trim to Essentials**
   - Remove redundant explanations
   - Condense multi-paragraph sections to bullet points
   - Keep only actionable instructions

5. **Verify Under Limit**
   - Count lines after refactoring
   - Must be <500 lines

Report:
- Files created: {list}
- Lines removed from SKILL.md: {count}
- Final line count: {n}
- Skill now PASSES / still FAILS
")
```

---

## COMPLETION CRITERIA

Skill audit complete when:
- All skills reviewed
- Findings consolidated into report
- User decision on fixes obtained
- Requested fixes applied
- Changes committed and pushed

---

## Violation Detection Patterns

### Pattern: Explanation Paragraph

Look for:
```markdown
## Why We Do This

The reason for this approach is that historically we found...
```

**Fix**: Move to spec, replace with link.

### Pattern: Inlined Reference

Look for:
```markdown
## Complete API Reference

### Method: get_item(key)
Parameters:
- key: The item key
Returns:
- The item value
...
(continues for 100+ lines)
```

**Fix**: Move to `references/api.md`.

### Pattern: Historical Context

Look for:
```markdown
Originally this was implemented differently, but in v2.0 we changed...
```

**Fix**: Delete (git has history) or move to spec if architecturally relevant.

### Pattern: Tutorial Content

Look for:
```markdown
Let's walk through an example step by step. First, you'll want to understand...
```

**Fix**: Convert to terse workflow steps or move to separate guide.

---

## Example Invocation

```
/supervise skill-audit Review all skills in $AOPS/skills/ and ensure SKILL.md files contain only actionable agent instructions
```
