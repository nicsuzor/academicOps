# CLAUDE.md Patterns and Anti-Patterns

This document describes common patterns and anti-patterns found in CLAUDE.md files, with examples of how to identify and fix them.

## Anti-Patterns to Avoid

### 1. Inline Instructions Anti-Pattern

**Problem**: Full instructions written directly in CLAUDE.md instead of using references.

**Symptoms**:
- CLAUDE.md files over 50 lines
- Detailed step-by-step instructions
- Multiple paragraphs of guidance
- Code examples inline

**Bad Example**:
```markdown
# CLAUDE.md

## Testing Guidelines

Always use pytest for testing. When writing tests, follow these rules:

1. Use real_bm fixture for all integration tests
2. Never mock internal code - only mock external services
3. Test files should match source file names with test_ prefix
4. Use descriptive test names that explain what is being tested
5. Each test should test one specific behavior

When debugging tests, use pytest -xvs flags for detailed output.
Tests should be deterministic and not rely on timing or order.
```

**Good Example**:
```markdown
# CLAUDE.md

@bots/prompts/PROJECT_testing_guidelines.md
```

### 2. Wrong Location Anti-Pattern

**Problem**: Instructions placed in root CLAUDE.md when they belong in subdirectories.

**Symptoms**:
- Root CLAUDE.md contains domain-specific instructions
- Test instructions not in `/tests/CLAUDE.md`
- Deployment instructions not in `/deploy/CLAUDE.md`
- Mixed concerns in single file

**Bad Structure**:
```
/CLAUDE.md          # Contains test, deploy, and dev instructions
/tests/             # No CLAUDE.md
/deploy/            # No CLAUDE.md
/src/               # No CLAUDE.md
```

**Good Structure**:
```
/CLAUDE.md           # Project overview references only
/tests/CLAUDE.md    # @bots/prompts/PROJECT_testing.md
/deploy/CLAUDE.md   # @bots/prompts/PROJECT_deployment.md
/src/CLAUDE.md      # @bots/prompts/PROJECT_development.md
```

### 3. Duplication Anti-Pattern

**Problem**: Same instructions repeated across multiple CLAUDE.md files.

**Symptoms**:
- Identical content in multiple files
- Copy-pasted instructions
- Maintenance burden when updating
- Inconsistent updates

**Bad Example**:
```markdown
# /CLAUDE.md
Use type hints for all functions.
Follow PEP 8 style guide.
Write docstrings for public APIs.

# /src/CLAUDE.md  
Use type hints for all functions.
Follow PEP 8 style guide.
Write docstrings for public APIs.

# /tests/CLAUDE.md
Use type hints for all functions.
Follow PEP 8 style guide.
Write docstrings for public APIs.
```

**Good Example**:
```markdown
# All three files reference:
@$ACADEMICOPS/bots/prompts/python_standards.md
```

### 4. Kitchen Sink Anti-Pattern

**Problem**: CLAUDE.md tries to contain everything, becoming a catch-all file.

**Symptoms**:
- Over 100 lines
- Multiple unrelated sections
- Mixes different concerns
- Hard to find specific guidance

**Bad Example**:
```markdown
# CLAUDE.md

## Python Development
[30 lines of Python guidelines...]

## Git Workflow
[20 lines of Git instructions...]

## Docker Setup
[25 lines of Docker config...]

## API Documentation
[40 lines of API specs...]

## Testing Strategy
[35 lines of test patterns...]
```

**Good Example**:
```markdown
# CLAUDE.md

## Development
@bots/prompts/PROJECT_overview.md
@$ACADEMICOPS/bots/prompts/python_standards.md

## Infrastructure
@bots/prompts/PROJECT_docker_setup.md
@bots/prompts/PROJECT_deployment.md

## Quality
@$ACADEMICOPS/bots/prompts/testing_practices.md
@$ACADEMICOPS/bots/prompts/code_review.md
```

### 5. Informal Notes Anti-Pattern

**Problem**: CLAUDE.md accumulates informal notes and reminders over time.

**Symptoms**:
- Shorthand notes like "remember to..."
- Incomplete thoughts
- Personal reminders
- Unstructured additions

**Bad Example**:
```markdown
# CLAUDE.md

Remember to use real_bm fixture
Don't forget about auth headers
TODO: document the API
NOTE: deployment needs AWS keys
btw tests are flaky sometimes
```

**Good Example**:
```markdown
# CLAUDE.md

@bots/prompts/PROJECT_test_fixtures.md
@bots/prompts/PROJECT_api_auth.md
@bots/prompts/PROJECT_deployment_requirements.md
@bots/prompts/PROJECT_known_issues.md
```

## Positive Patterns to Follow

### 1. Reference-Only Pattern

**Description**: CLAUDE.md contains only @references to chunks.

**Benefits**:
- Extremely concise
- Easy to scan
- No duplication
- Single source of truth

**Example**:
```markdown
# CLAUDE.md

@bots/prompts/PROJECT_overview.md
@$ACADEMICOPS/bots/prompts/development_standards.md
@$ACADEMICOPS_PERSONAL/prompts/my_workflow.md
```

### 2. Hierarchical Organization Pattern

**Description**: Use directory-specific CLAUDE.md files for location-appropriate content.

**Benefits**:
- Context-aware instructions
- Reduced cognitive load
- Better organization
- Easier maintenance

**Structure**:
```
/CLAUDE.md                    # Project-wide references
/src/CLAUDE.md               # Source code specific
/tests/CLAUDE.md             # Testing specific
/deploy/CLAUDE.md            # Deployment specific
/docs/CLAUDE.md              # Documentation specific
```

### 3. Tier-Appropriate Pattern

**Description**: Place content in the correct tier based on reusability.

**Benefits**:
- Maximum reuse
- Minimal duplication
- Clear ownership
- Easy sharing

**Decision Tree**:
```
Is it project-specific?
  YES → bots/prompts/PROJECT_*.md
  NO → Is it a personal preference?
    YES → $ACADEMICOPS_PERSONAL/prompts/*.md
    NO → $ACADEMICOPS/bots/prompts/*.md
```

### 4. Descriptive Naming Pattern

**Description**: Use clear, descriptive names for chunks.

**Benefits**:
- Self-documenting
- Easy to find
- Clear purpose
- Better organization

**Good Names**:
- `PROJECT_api_authentication.md`
- `python_type_hints.md`
- `git_commit_standards.md`
- `docker_multi_stage_builds.md`

**Bad Names**:
- `instructions.md`
- `notes.md`
- `config.md`
- `misc.md`

### 5. Progressive Enhancement Pattern

**Description**: Start simple, add complexity only when needed.

**Benefits**:
- Avoid over-engineering
- Grow organically
- Easy to understand
- Maintainable

**Evolution**:
```markdown
# Version 1: Single reference
@bots/prompts/PROJECT_setup.md

# Version 2: Add standards
@bots/prompts/PROJECT_setup.md
@$ACADEMICOPS/bots/prompts/python_standards.md

# Version 3: Add personal preferences
@bots/prompts/PROJECT_setup.md
@$ACADEMICOPS/bots/prompts/python_standards.md
@$ACADEMICOPS_PERSONAL/prompts/my_dev_workflow.md
```

## Migration Strategies

### From Inline to Chunks

**Step 1**: Identify substantive content
```bash
scripts/audit_claude_files.py .
```

**Step 2**: Extract to chunks
```bash
scripts/extract_chunks.py CLAUDE.md
```

**Step 3**: Verify references
```bash
scripts/validate_references.py .
```

### From Monolithic to Hierarchical

**Step 1**: Create subdirectory CLAUDE.md files
```bash
touch tests/CLAUDE.md src/CLAUDE.md deploy/CLAUDE.md
```

**Step 2**: Move relevant references
```bash
# Manually move test-related references to tests/CLAUDE.md
# Move source-related to src/CLAUDE.md
# Move deployment-related to deploy/CLAUDE.md
```

**Step 3**: Cleanup root CLAUDE.md
```bash
# Keep only project-wide references in root
scripts/refactor_references.py . --consolidate
```

### From Duplication to DRY

**Step 1**: Find duplicates
```bash
scripts/audit_claude_files.py . | grep duplication
```

**Step 2**: Extract to shared chunk
```bash
# Create shared chunk in appropriate tier
echo "Content" > $ACADEMICOPS/bots/prompts/shared_pattern.md
```

**Step 3**: Replace with references
```bash
scripts/refactor_references.py . --consolidate
```

## Detection Patterns

### Regex Patterns for Issues

**Inline Instructions**:
```regex
^(Always|Never|Must|Should|Do not|Don't)\s+
^(When|If|Before|After)\s+.+:
^[A-Z][A-Z\s]+:$
^-\s+(Use|Create|Check|Verify|Ensure)\s+
```

**Informal Notes**:
```regex
^(TODO|NOTE|FIXME|XXX|HACK):
^(remember|don't forget|btw|fyi)
\.\.\.$
```

**Duplication Indicators**:
```regex
# Lines appearing in multiple files
# Content >50 chars repeated
```

### File Size Thresholds

- **Ideal**: < 20 lines
- **Acceptable**: 20-50 lines  
- **Warning**: 50-100 lines
- **Critical**: > 100 lines

## Tools Integration

### With audit_claude_files.py

Detects:
- Substantive content blocks
- Wrong location patterns
- Duplication across files
- File size violations
- Missing references

### With extract_chunks.py

Handles:
- Content extraction
- Tier determination
- Reference generation
- File updates
- Chunk creation

### With refactor_references.py

Performs:
- Pattern matching
- Existing chunk detection
- Reference consolidation
- Duplicate removal
- File cleanup

### With validate_references.py

Verifies:
- Reference syntax
- File existence
- Path correctness
- Circular dependencies
- Environment variables

## Success Metrics

**Well-Structured CLAUDE.md**:
- [ ] Under 50 lines (ideally <20)
- [ ] Only @references, no inline content
- [ ] No duplication across files
- [ ] Appropriate directory placement
- [ ] Clear tier organization
- [ ] All references valid
- [ ] Descriptive chunk names
- [ ] No informal notes

## Common Fixes

### Fix: File Too Long
```bash
scripts/extract_chunks.py CLAUDE.md
scripts/refactor_references.py CLAUDE.md --consolidate
```

### Fix: Duplication
```bash
scripts/audit_claude_files.py . | grep duplication
# Create shared chunk
# Update all files to reference shared chunk
```

### Fix: Wrong Location
```bash
# Move content to appropriate directory
mkdir -p tests
echo "@bots/prompts/PROJECT_testing.md" > tests/CLAUDE.md
# Remove from root CLAUDE.md
```

### Fix: Broken References
```bash
scripts/validate_references.py . --fix
# Follow suggestions to fix paths
```

### Fix: Informal Notes
```bash
scripts/extract_chunks.py CLAUDE.md
# Formalize extracted content in chunks
```
