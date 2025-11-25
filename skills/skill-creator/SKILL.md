---
name: skill-creator
description: Create and maintain skills following evidence-based anti-bloat principles. Use when creating new skills or updating existing skills.
license: Complete terms in LICENSE.txt
permalink: aops/skills/skill-creator/skill
---

# Skill Creator

## Framework Context

@resources/AXIOMS.md

## Overview

Skills are modular packages extending agent capabilities with specialized workflows, tools, and domain knowledge.

**Read First** (mandatory references):

- `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md` - Evidence-based component design
- `@$ACADEMICOPS/docs/bots/skill-invocation-guide.md` - How skills are invoked
- `@resources/AXIOMS.md` - Universal principles (fail-fast, DRY, standard tools)

## Skill Creation Workflow

### 1. Understanding with Examples

Identify concrete use cases:

- "What functionality should this skill support?"
- "Give examples of how this skill would be used"
- "What would trigger this skill?"

Skip only when usage patterns are crystal clear.

### 2. Planning Reusable Contents

Analyze examples to identify bundled resources:

**Structure**:

- `scripts/` - Executable code (Python/Bash) for deterministic/repeated tasks
- `references/` - Documentation loaded as needed (schemas, APIs, policies)
- `assets/` - Output files (templates, boilerplate, icons)

**Examples**:

- PDF rotation → Repeated code → `scripts/rotate_pdf.py`
- Frontend webapp → Boilerplate → `assets/hello-world/` template
- BigQuery → Schema discovery → `references/schema.md`

### 3. Initialize Skill

```bash
scripts/init_skill.py <skill-name> --path <output-directory>
```

Generates SKILL.md template, example resource directories, and placeholder files.

**MANDATORY Post-Initialization**:

Create `resources/` directory with framework symlinks:

```bash
cd <skill-dir>/resources
ln -s ../../../AXIOMS.md AXIOMS.md
```

Add to SKILL.md header:

```markdown
## Framework Context

@resources/AXIOMS.md
```

**Framework Context**: Skills that work with framework files (agents/, skills/, commands/) should include AXIOMS.md for foundational principles. General utility skills can skip this.

### 4. Edit SKILL.md

**Writing Style**: Imperative/infinitive form (verb-first), not second person. Objective: "To accomplish X, do Y" not "you do X."

**Content**:

1. Purpose (2-3 sentences)
2. Trigger conditions
3. Workflow with bundled resources
4. 1-2 concrete examples

**Anti-Bloat Checklist** (before adding >5 lines):

- [ ] No existing content to reference? (DRY check)
- [ ] Not repeating chunks/ or BEST-PRACTICES.md?
- [ ] Bullet points, not prose?
- [ ] Specific instructions, not vague? ("2-3 sentences" not "be concise")
- [ ] File stays <300 lines?
- [ ] No FAQ or excessive background?
- [ ] Adding >10 lines? STOP → GitHub issue + approval

**DRY Principle**: Reference, don't duplicate. Example: "See AXIOMS.md #7" NOT 85 lines explaining fail-fast.

### 5. Package Skill

```bash
scripts/package_skill.py <path/to/skill-folder>
```

Validates (YAML, naming, structure) then packages to .zip. Fix errors if validation fails.

### 6. Iterate

Test on real tasks → Notice inefficiencies → Update → Test again. Follow anti-bloat checklist for updates.

## Cross-Repo Structure

**Repositories**:

- **academicOps** (`$ACADEMICOPS`): Framework (PUBLIC), used as submodule
- **Personal Repo**: User's repo with aOps submodule (e.g., `./aops/`)

**Three-Tier Loading**: SessionStart loads framework → personal → project instructions.

**Symlinks**:

- Development (aops/skills/): `ln -s ../../../chunks/FILE.md`
- Installed (~/.claude/skills/): `ln -s $ACADEMICOPS/chunks/FILE.md`

## Skill Maintenance

**Update This Skill When**:

- New patterns discovered
- Creation failures observed
- Framework changes
- Anti-bloat violations

**How to Update**:

1. Document in GitHub issue
2. Create experiment log (`experiments/YYYY-MM-DD_name.md`)
3. Single change (<10 lines)
4. Test with real creation
5. Measure: success/failure/partial
6. Keep/revert/iterate

**Success Metrics**:

- Pass validation first try
- Follow anti-bloat checklist
- Use resources/ symlinks correctly

**Never assume** changes work - test, document, measure.

## Quick Reference

**Mandatory Steps**:

1. `scripts/init_skill.py <name> --path <dir>`
2. Create `resources/` + symlinks
3. Reference framework context at top
4. Imperative/infinitive style
5. Pass anti-bloat checklist
6. `scripts/package_skill.py <folder>`

**Key References**:

- `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md`
- `@$ACADEMICOPS/docs/bots/skill-invocation-guide.md`
- `@resources/AXIOMS.md`
