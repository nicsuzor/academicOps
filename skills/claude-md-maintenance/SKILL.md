---
name: claude-md-maintenance
description: This skill maintains CLAUDE.md files across repositories by extracting
  substantive content to chunks, enforcing @reference patterns, and ensuring proper
  hierarchical organization. Use when CLAUDE.md files contain inline instructions,
  are too long, have duplication, or need refactoring to follow academicOps best practices.
permalink: aops/skills/claude-md-maintenance/skill
---

# CLAUDE.md Maintenance Skill

Maintain CLAUDE.md files across repositories following academicOps best practices. This skill ensures CLAUDE.md files remain concise, use proper @reference syntax, and organize content in the correct hierarchical tier.

## When to Use This Skill

Use this skill when:

1. **CLAUDE.md files are getting bloated** - Files over 50 lines or containing substantive inline instructions
2. **Instructions are in the wrong location** - Test instructions in root CLAUDE.md instead of `/tests/CLAUDE.md`
3. **Content is duplicated** - Same instructions appear in multiple CLAUDE.md files
4. **Migrating to @reference pattern** - Converting inline content to modular chunks
5. **Validating references** - Ensuring all @references resolve correctly
6. **Starting a new project** - Setting up proper CLAUDE.md structure from the beginning
7. **Auditing existing projects** - Reviewing CLAUDE.md files for compliance with best practices

**Concrete trigger examples**:

- "Clean up the CLAUDE.md files in this repository"
- "Extract inline instructions from CLAUDE.md to chunks"
- "Validate all references in CLAUDE.md files"
- "My CLAUDE.md is getting too long"
- "Move test instructions to the right location"
- "Check for duplicate content across CLAUDE.md files"

## Core Philosophy

### CLAUDE.md Best Practices

1. **No Substantive Content** - CLAUDE.md should contain ONLY @references, never full instructions
2. **Location Specificity** - Instructions go in the most specific directory (e.g., `/tests/CLAUDE.md` for test instructions)
3. **Modular Chunks** - Full instruction content lives in `/bots/prompts/<name>.md`
4. **Concise & DRY** - Target <20 lines, maximum 50 lines, no duplication
5. **Proper References** - Use correct @reference syntax for the appropriate tier

### Hierarchical Structure

The skill understands the 3-tier hierarchy for instruction chunks:

1. **Framework Tier** (`$ACADEMICOPS/bots/prompts/`)
   - Reusable across all projects
   - Generic Python, Git, Docker instructions
   - Best practices that apply everywhere

2. **User Tier** (`$ACADEMICOPS_PERSONAL/prompts/`)
   - Personal preferences and workflows
   - User-specific configurations
   - Cross-project but user-specific

3. **Project Tier** (`$CLAUDE_PROJECT_DIR/bots/prompts/`)
   - Project-specific instructions
   - Custom business logic
   - Domain-specific knowledge

## Workflow

### Step 1: Audit CLAUDE.md Files

Start by auditing existing CLAUDE.md files to identify issues:

```bash
scripts/audit_claude_files.py [directory]
```

The audit identifies:

- Substantive content that should be in chunks
- Wrong location (instructions in incorrect directory)
- Duplication across files
- Files that are too long
- Missing @reference syntax

**Example output**:

```
📄 CLAUDE.md:
  📝 substantive_content
     Line 10: Always use pytest for testing...
     → Extract to bots/prompts/testing_practices.md
  📏 too_long
     File has 87 lines (ideal: <20, acceptable: <50)
     → Extract content to chunks and use @references
```

### Step 2: Extract Substantive Content

Extract inline instructions to proper chunk files:

```bash
scripts/extract_chunks.py [path] [--dry-run]
```

This script:

- Identifies substantive content blocks
- Creates chunk files in the appropriate tier
- Replaces content with @reference syntax
- Preserves file structure and formatting

**Tier determination**:

- **Project-specific** content → `bots/prompts/PROJECT_<name>.md`
- **Reusable** content → `$ACADEMICOPS/bots/prompts/<name>.md`
- **Personal** preferences → `$ACADEMICOPS_PERSONAL/prompts/<name>.md`

### Step 3: Refactor to References

Convert remaining inline content to @references:

```bash
scripts/refactor_references.py [path] [--dry-run] [--consolidate]
```

This script:

- Identifies instruction patterns
- Finds existing chunks that match content
- Suggests new chunks for unmatched content
- Consolidates duplicate references with `--consolidate`

### Step 4: Validate References

Ensure all @references resolve correctly:

```bash
scripts/validate_references.py [path] [--fix]
```

Validates:

- All referenced files exist
- Paths are correct
- No circular references
- Environment variables resolve
- Suggests fixes with `--fix` flag

**Reference formats supported**:

- `@bots/prompts/chunk.md` - Project tier
- `@$ACADEMICOPS/bots/prompts/chunk.md` - Framework tier
- `@$ACADEMICOPS_PERSONAL/prompts/chunk.md` - User tier
- `@references/doc.md` - Reference documentation
- `@.claude/prompts/chunk.md` - Claude-specific

## Common Patterns

### Pattern 1: Initial Cleanup

For a repository with bloated CLAUDE.md files:

```bash
# 1. Audit to see issues
scripts/audit_claude_files.py .

# 2. Extract substantive content (dry run first)
scripts/extract_chunks.py . --dry-run

# 3. If looks good, extract for real
scripts/extract_chunks.py .

# 4. Refactor remaining content
scripts/refactor_references.py . --consolidate

# 5. Validate all references
scripts/validate_references.py .
```

### Pattern 2: Location-Specific CLAUDE.md

Move instructions to appropriate directories:

```bash
# Create location-specific CLAUDE.md files
echo "@bots/prompts/PROJECT_testing.md" > tests/CLAUDE.md
echo "@bots/prompts/PROJECT_python_dev.md" > src/CLAUDE.md
echo "@bots/prompts/PROJECT_deployment.md" > deploy/CLAUDE.md

# Extract test content from root
scripts/extract_chunks.py CLAUDE.md

# Move to tests/CLAUDE.md reference
scripts/refactor_references.py .
```

### Pattern 3: Cross-Repository Reuse

Share chunks across repositories:

```bash
# Extract reusable content to framework tier
ACADEMICOPS=/path/to/academicOps scripts/extract_chunks.py .

# This creates chunks in $ACADEMICOPS/bots/prompts/
# Other repositories can reference with:
# @$ACADEMICOPS/bots/prompts/python_typing.md
```

### Pattern 4: Formalize Shorthand Notes

Convert informal notes to proper chunks:

```bash
# CLAUDE.md contains: "remember to use real_bm fixture"
# Extract and formalize:
scripts/extract_chunks.py CLAUDE.md

# Creates: bots/prompts/PROJECT_testing_fixtures.md
# With proper content:
# "Test Fixture Requirements
#  
#  Always use real_bm fixture for integration tests..."
```

## Anti-Patterns to Avoid

### ❌ Inline Instructions

**Bad**:

```markdown
# CLAUDE.md

Always use pytest for testing. Never mock internal code. Use real_bm fixture for all tests.
```

**Good**:

```markdown
# CLAUDE.md

@bots/prompts/testing_practices.md
```

### ❌ Wrong Location

**Bad** (in root CLAUDE.md):

```markdown
When writing tests, use pytest...
```

**Good** (in tests/CLAUDE.md):

```markdown
@bots/prompts/PROJECT_test_guidelines.md
```

### ❌ Duplication

**Bad** (same content in multiple files):

```markdown
# /CLAUDE.md

Use type hints for all functions...

# /src/CLAUDE.md

Use type hints for all functions...
```

**Good** (single reference):

```markdown
# Both files reference:

@$ACADEMICOPS/bots/prompts/python_typing.md
```

### ❌ Overly Long Files

**Bad** (100+ line CLAUDE.md):

```markdown
# CLAUDE.md

[100 lines of instructions...]
```

**Good** (concise references):

```markdown
# CLAUDE.md

@bots/prompts/PROJECT_overview.md @bots/prompts/PROJECT_development.md @$ACADEMICOPS/bots/prompts/python_best_practices.md
```

## Script Reference

### audit_claude_files.py

**Usage**: `scripts/audit_claude_files.py [directory]`

**Purpose**: Scan and report issues in CLAUDE.md files

**Options**:

- `directory` - Directory to audit (default: current directory)

**Exit codes**:

- 0 - No issues found
- 1 - Issues found

### extract_chunks.py

**Usage**: `scripts/extract_chunks.py [path] [--dry-run]`

**Purpose**: Extract substantive content to chunk files

**Options**:

- `path` - CLAUDE.md file or directory to process
- `--dry-run` - Show what would be extracted without writing files

**Creates**:

- Chunk files in appropriate tier directories
- Updated CLAUDE.md with @references

### refactor_references.py

**Usage**: `scripts/refactor_references.py [path] [--dry-run] [--consolidate]`

**Purpose**: Convert inline content to @references

**Options**:

- `path` - CLAUDE.md file or directory to process
- `--dry-run` - Show changes without writing
- `--consolidate` - Remove duplicate references

**Actions**:

- Identifies instruction patterns
- Matches with existing chunks
- Suggests new chunks
- Updates files with references

### validate_references.py

**Usage**: `scripts/validate_references.py [path] [--fix]`

**Purpose**: Validate all @references resolve correctly

**Options**:

- `path` - CLAUDE.md file or directory to validate
- `--fix` - Show suggested fixes for broken references

**Checks**:

- File existence
- Path correctness
- Environment variable resolution
- Circular references

**Exit codes**:

- 0 - All references valid
- 1 - Invalid references found

## Success Metrics

A well-maintained CLAUDE.md structure has:

1. **All CLAUDE.md files <50 lines** (ideally <20)
2. **No inline instructions** - only @references
3. **No duplication** - shared content in single chunks
4. **100% valid references** - all @references resolve
5. **Proper location** - instructions in most specific directory
6. **Clear hierarchy** - correct tier for each chunk

## Troubleshooting

### Environment Variables Not Set

If references to `$ACADEMICOPS` or `$ACADEMICOPS_PERSONAL` fail:

```bash
export ACADEMICOPS=/path/to/academicOps
export ACADEMICOPS_PERSONAL=/path/to/personal
export CLAUDE_PROJECT_DIR=$(pwd)
```

### References Not Resolving

Check reference syntax:

- Project: `@bots/prompts/chunk.md`
- Framework: `@$ACADEMICOPS/bots/prompts/chunk.md`
- Personal: `@$ACADEMICOPS_PERSONAL/prompts/chunk.md`

### Chunks in Wrong Tier

Review tier criteria:

- **Project**: Specific to this repository
- **Framework**: Reusable across all projects
- **Personal**: User preferences across projects

## Integration with Other Tools

This skill works with:

- **skill-migration** - Extract instructions from agent files
- **aops-trainer** - Maintain agent instruction quality
- **git-commit** - Validate CLAUDE.md changes before commit

## Remember

**"Instructions belong in chunks, not CLAUDE.md."** Keep CLAUDE.md files lean and focused on references. Extract substantive content to properly organized chunks for reusability and maintainability.

**When in doubt, extract it out.** If content is more than a simple reference, it belongs in a chunk file.
