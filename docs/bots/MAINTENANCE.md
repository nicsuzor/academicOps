# Supervisor Reference Maintenance Strategy

## The Problem

The supervisor agent references four critical files:

- `$ACADEMICOPS/docs/bots/skills-inventory.md` - Catalog of available skills
- `$ACADEMICOPS/docs/bots/dev-tools-reference.md` - Dev agent tool capabilities
- `$ACADEMICOPS/docs/bots/challenge-responses.md` - Decision-making frameworks
- `$ACADEMICOPS/docs/bots/delegation-architecture.md` - Three-level delegation patterns

These can become stale when:

- New skills are added
- Skills are modified (new features, changed delegation patterns)
- Tools/capabilities change
- Framework patterns evolve
- New challenge categories emerge

## Maintenance Strategy

### 1. Version-Controlled Source of Truth

**Status**: ✅ IMPLEMENTED

- All reference files are in git at `$ACADEMICOPS/docs/bots/`
- Changes tracked in repository history
- Can be reviewed in PRs

### 2. Explicit Update Triggers

**When to update references**:

#### A. Adding New Skill

**Trigger**: New skill created in `skills/[name]/SKILL.md`

**Required updates**:

- `skills-inventory.md`: Add skill entry with delegation patterns
- Check if new challenge category needed in `challenge-responses.md`

**Process**:

```
1. Create new skill
2. Document in skills-inventory.md:
   - Purpose
   - When supervisor should require it
   - Explicit delegation pattern
   - Key constraints
   - Success/failure signals
3. If skill introduces new failure modes, add to challenge-responses.md
```

#### B. Modifying Existing Skill

**Trigger**: Changes to `skills/[name]/SKILL.md` that affect:

- When to use the skill
- How to invoke it
- What constraints apply
- Expected outputs/reports

**Required updates**:

- `skills-inventory.md`: Update delegation pattern for that skill
- `challenge-responses.md`: If failure modes changed

**Process**:

```
1. Modify skill
2. Search skills-inventory.md for skill name
3. Update delegation pattern section
4. Update constraints if changed
5. Update success/failure signals if changed
```

#### C. New Tool Available to Dev Agent

**Trigger**: Dev agent gains new tool capability

**Required updates**:

- `dev-tools-reference.md`: Document new tool

**Process**:

```
1. Add tool to dev agent capabilities
2. Document in dev-tools-reference.md:
   - What it does
   - When dev uses it
   - Supervisor instruction patterns
   - Constraints
   - Add to tool availability summary table
```

#### D. New Challenge Category Discovered

**Trigger**: Supervisor encounters repeated challenge not covered by existing categories

**Required updates**:

- `challenge-responses.md`: Add new category

**Process**:

```
1. Identify recurring challenge through:
   - GitHub issues (multiple instances)
   - Experiment logs
   - User feedback
2. Add to challenge-responses.md:
   - Challenge category name
   - Analysis checklist
   - Decision tree
   - Response patterns
   - Escalation criteria
   - Anti-patterns
3. Add to response time guidelines table
```

#### E. Framework Pattern Evolution

**Trigger**: Changes to core framework patterns (axioms, enforcement hierarchy, architectural decisions)

**Required updates**:

- `delegation-architecture.md`: If delegation patterns change
- `challenge-responses.md`: If decision-making principles change
- All references: If terminology changes

**Process**:

```
1. Document framework change (via experiment log)
2. Grep all reference files for affected patterns
3. Update each file systematically
4. Create git commit linking to experiment/issue
```

### 3. Automated Validation (Future Enhancement)

**Script**: `scripts/validate_supervisor_references.py` (TO BE CREATED)

**What it checks**:

```python
def validate_skills_inventory():
    """Ensure skills-inventory.md matches actual skills."""
    actual_skills = glob("skills/*/SKILL.md")
    documented_skills = parse_skills_from_inventory()

    # Check for missing skills
    missing = actual_skills - documented_skills
    if missing:
        error(f"Skills not documented: {missing}")

    # Check for obsolete entries
    obsolete = documented_skills - actual_skills
    if obsolete:
        warning(f"Documented skills don't exist: {obsolete}")

    # Validate delegation patterns are syntactically correct
    for skill in documented_skills:
        pattern = extract_delegation_pattern(skill)
        if not validate_task_syntax(pattern):
            error(f"{skill}: Invalid Task() syntax")

def validate_dev_tools():
    """Check dev-tools-reference matches actual tool availability."""
    # Parse DEVELOPER.md or built-in tool list
    actual_tools = get_dev_agent_tools()
    documented_tools = parse_tools_from_reference()

    missing = actual_tools - documented_tools
    obsolete = documented_tools - actual_tools

    if missing:
        error(f"Tools not documented: {missing}")
    if obsolete:
        warning(f"Documented tools don't exist: {obsolete}")

def validate_cross_references():
    """Check that @references and links resolve."""
    all_refs = extract_references_from_files(
        "docs/bots/*.md"
    )

    for ref in all_refs:
        if not file_exists(ref):
            error(f"Broken reference: {ref}")

def validate_examples():
    """Check that example Task() calls are valid."""
    examples = extract_code_blocks(
        "docs/bots/*.md",
        lang="Task"
    )

    for example in examples:
        if not validate_task_syntax(example):
            error(f"Invalid Task() example: {example[:50]}...")
```

**Usage**:

```bash
# Run validation
python scripts/validate_supervisor_references.py

# Auto-fix issues where possible
python scripts/validate_supervisor_references.py --fix

# Report only (no errors, just warnings)
python scripts/validate_supervisor_references.py --report
```

**Integration**:

- Run in pre-commit hook when reference files change
- Run in CI on PRs
- Run periodically (monthly audit)

### 4. Documentation-as-Code Pattern

**Enforce**: Reference files are YAML-parseable or have structured sections

**Example - skills-inventory.md structure**:

```markdown
## Core Development Skills

### test-writing

**Purpose**: [one-line description]

**When supervisor should require**: [trigger conditions]

**Explicit delegation pattern**:
```

Task(subagent_type="dev", prompt=" [structured pattern] ")

```
**Key constraints to enforce**:
- MUST: [requirement]
- FORBIDDEN: [anti-pattern]

**Success signals**: [what good looks like]
**Failure signals**: [what bad looks like]
```

This structure allows:

- Automated parsing to check completeness
- Validation that required sections exist
- Linting for consistency

### 5. Maintenance Checklist in skill-maintenance Skill

Update the skill-maintenance skill to include supervisor reference maintenance:

**Add to skill-maintenance/SKILL.md**:

````markdown
### Audit Supervisor References

Check supervisor references for completeness and accuracy.

**Single reference audit**:

```bash
python scripts/audit_supervisor_refs.py [ref-name]
```
````

**Full reference audit**:

```bash
python scripts/audit_supervisor_refs.py --all
```

Checks:

- Skills-inventory matches actual skills in skills/
- Dev-tools-reference matches actual tools
- Challenge-responses covers common failure modes
- Cross-references resolve
- Examples are syntactically valid
- No obsolete patterns

**Update workflow**:

1. Framework change identified (new skill, tool, pattern)
2. Update relevant reference file(s)
3. Run audit: `python scripts/audit_supervisor_refs.py --all`
4. Fix any issues
5. Commit with reference to change trigger (issue/experiment)

````
### 6. Change Documentation Pattern

**When updating references, create experiment log**:

**File**: `experiments/YYYY-MM-DD_supervisor-ref-[description].md`

**Content**:
```markdown
# Experiment: Supervisor Reference Update - [Description]

**Date**: YYYY-MM-DD
**Trigger**: [New skill X / Framework pattern Y changed / etc.]
**Issue**: #[NUMBER]
**Files Modified**:
- docs/bots/skills-inventory.md
- [other files]

## Change Description

[What changed and why]

## Files Updated

### skills-inventory.md
- Added: [skill name] entry
- Modified: [skill name] delegation pattern
- Removed: [obsolete entry]

### challenge-responses.md
- Added: Category [N]: [challenge name]
- Modified: Response pattern for [category]

## Validation

- [ ] Ran `python scripts/audit_supervisor_refs.py --all`
- [ ] All skills documented
- [ ] All tools documented
- [ ] Examples syntactically valid
- [ ] Cross-references resolve

## Testing

[How change was validated - e.g., supervisor used new skill successfully]

## Outcome

SUCCESS - References updated and validated
````

This creates audit trail and searchable history.

### 7. Periodic Audit Schedule

**Monthly**: Run full validation

```bash
python scripts/audit_supervisor_refs.py --all --report > reports/supervisor-refs-$(date +%Y-%m).txt
```

**Quarterly**: Human review of references

- Read through each file
- Check for clarity and completeness
- Look for emergent patterns not yet documented
- Update based on observed supervisor behavior

**After major framework changes**: Full audit and update cycle

### 8. GitHub Issue Integration

**Label**: `maintenance:supervisor-refs`

**Issue template**: `.github/ISSUE_TEMPLATE/supervisor-ref-update.md`

```markdown
---
name: Supervisor Reference Update
about: Track updates needed to supervisor reference files
title: "[MAINT] Update supervisor refs for [change]"
labels: maintenance:supervisor-refs
---

## Change Trigger

[What changed - new skill, modified tool, pattern evolution, etc.]

## Required Updates

- [ ] skills-inventory.md - [what needs updating]
- [ ] dev-tools-reference.md - [what needs updating]
- [ ] challenge-responses.md - [what needs updating]
- [ ] delegation-architecture.md - [what needs updating]

## Validation

- [ ] Audit script passes
- [ ] Examples tested
- [ ] Cross-references resolve

## Related

- Issue/Experiment: #[NUMBER]
- Commit: [SHA]
```

**Workflow**:

1. Framework change occurs (new skill, etc.)
2. Create maintenance issue
3. Update references
4. Run validation
5. Close issue with commit link

### 9. Integration with aops-bug Skill

When aops-bug skill is used to log agent violations or infrastructure issues, check if supervisor references need updating.

**Add to aops-bug workflow**:

```markdown
## Step X: Check If Supervisor References Need Update

After logging violation/bug:

Q: Does this reveal gap in supervisor's knowledge? ├─ New skill needed → Create issue with label `maintenance:supervisor-refs` ├─ Challenge category missing → Update challenge-responses.md ├─ Tool capability changed → Update dev-tools-reference.md └─ Delegation pattern unclear → Update skills-inventory.md or delegation-architecture.md

If yes, create maintenance issue linked to bug issue.
```

## Summary: Keeping References Current

**Proactive maintenance**:

1. ✅ Update reference files when making changes (new skills, tools, patterns)
2. ✅ Document updates in experiment logs with clear triggers
3. ✅ Create GitHub issues with `maintenance:supervisor-refs` label
4. ✅ Link reference updates to triggering changes (issues, experiments, commits)

**Reactive maintenance**:

1. ⏳ Run validation scripts (TO BE CREATED)
2. ⏳ Monthly automated audits
3. ✅ Quarterly human reviews
4. ✅ Post-mortem updates when supervisor struggles

**Validation**:

1. ⏳ Automated validation script checks completeness (TO BE CREATED)
2. ⏳ Pre-commit hooks catch missing updates (TO BE CREATED)
3. ✅ Experiment logs document updates
4. ✅ Git history tracks evolution

**Status Legend**:

- ✅ Already in place or manual process defined
- ⏳ Requires tooling to be built (scripts)

## Next Steps to Implement Full Strategy

1. **Create validation script**: `scripts/validate_supervisor_references.py`
2. **Create audit script**: `scripts/audit_supervisor_refs.py`
3. **Add pre-commit hook**: Validate references when changed
4. **Update skill-maintenance skill**: Include supervisor reference maintenance
5. **Create GitHub issue template**: `supervisor-ref-update.md`
6. **Add to aops-bug workflow**: Check for reference gaps
7. **Schedule first audit**: Run validation and document any issues

This creates a multi-layered maintenance approach combining automation, documentation, and human oversight.
