---
name: skill-maintenance
description: This skill should be used for ongoing skill maintenance and evolution. It audits skills for outdated patterns, updates skills to current framework best practices, validates scripts and references, packages skills for distribution, and ensures deployment symlinks are correct. Use this when framework patterns evolve, skills need updates, or the entire skill ecosystem requires auditing.
---

# Skill Maintenance

## Overview

Maintain and evolve the academicOps skill ecosystem as framework patterns advance. This skill provides systematic maintenance to prevent skill rot, incorporate new patterns, validate functionality, and ensure skills remain current with evolving best practices.

## Core Principles

**Source of Truth**: `$ACADEMICOPS/skills/` is authoritative and version-controlled. Deployment at `~/.claude/skills/` must be symlinks, never independent copies. Packages in `$ACADEMICOPS/dist/skills/*.zip` are regenerated from source.

**Framework Evolution**: As academicOps evolves, skills must evolve alongside. Monitor changes to core patterns (CLAUDE.md, @references, enforcement hierarchy) and propagate updates to existing skills.

**Comprehensive Validation**: Every skill requires validation of SKILL.md structure, script executability, reference existence, asset formats, and cross-references to other skills or documentation.

## When to Use This Skill

Invoke skill-maintenance when:

1. **Framework patterns change** - New @reference system, updated enforcement hierarchy, revised axioms
2. **Skills show age** - Outdated patterns, missing current features, old architecture references
3. **Periodic audits needed** - Quarterly skill ecosystem health checks
4. **Pre-deployment validation** - Before packaging skills for distribution
5. **Deployment issues** - When ~/.claude/skills/ diverges from source symlinks

## Maintenance Workflows

### Audit Skills

Detect outdated patterns, missing features, and validation issues across skills.

**Single skill audit**:
```bash
python scripts/audit_skills.py skill-name
```

**Full ecosystem audit**:
```bash
python scripts/audit_skills.py --all
```

Output includes:
- Outdated pattern detection (pre-skills-first references)
- Missing framework features (@references, CLAUDE.md patterns)
- Validation issues (broken scripts, missing references)
- Improvement recommendations

### Update Skills

Apply framework evolution updates to skills systematically.

**Update single skill**:
```bash
python scripts/update_skill.py skill-name
```

**Update all skills**:
```bash
python scripts/update_skill.py --all
```

Updates include:
- SKILL.md pattern modernization
- Script validation and fixes
- Reference document updates
- Cross-reference corrections

**Interactive mode** (default): Review each proposed change before applying.
**Auto mode** (--auto flag): Apply all safe updates automatically.

### Validate Skills

Comprehensive validation of skill completeness and functionality.

**Validate single skill**:
```bash
python scripts/validate_skill.py skill-name
```

**Validate ecosystem**:
```bash
python scripts/validate_skill.py --all
```

Validation checks:
- SKILL.md frontmatter correctness
- Script executability and syntax
- Reference file existence
- Asset format validation
- Cross-skill reference resolution
- Bundled test execution

### Package Skills

Generate distribution packages from source skills.

**Package single skill**:
```bash
python scripts/package_skills.py skill-name
```

**Package all skills**:
```bash
python scripts/package_skills.py --all
```

Creates fresh .zip files in `$ACADEMICOPS/dist/skills/` with:
- Validated skill contents
- Proper directory structure
- Executable scripts preserved
- Clean packaging (no __pycache__, .pyc, etc.)

### Sync Deployment

Ensure deployment directory contains only symlinks to source.

```bash
python scripts/sync_deployment.py
```

Operations:
- Detect non-symlink skills in ~/.claude/skills/
- Report divergence from source
- Fix symlinks (with --fix flag)
- Clean orphaned deployments

## Script Capabilities

Detailed script descriptions in sections above. All scripts are located in `scripts/` directory.

## Change Tracking

Track framework evolution in `references/framework-changelog.md` with dates, patterns, affected skills, and migration steps.

## Common Maintenance Tasks

See workflow sections above for common patterns and batch operations.

## Error Recovery

When maintenance operations fail:

1. **Check backups** in `scripts/backups/` (created before updates)
2. **Review logs** in `scripts/logs/` for detailed errors  
3. **Manual intervention** for complex issues
4. **Report bugs** in framework-evolution tracking

## Integration Points

Works with skill-creator for standards, git-commit for version tracking, and CI/CD for automation.

## Performance Considerations

For large ecosystems, use parallel validation, incremental updates, and cached results.
