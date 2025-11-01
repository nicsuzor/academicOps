# CLAUDE.md Transformation Examples

Real-world examples of CLAUDE.md file transformations from problematic to properly structured.

## Example 1: Bloated Root CLAUDE.md

### Before (150+ lines)

```markdown
# CLAUDE.md

## Project Overview
This is the AcademicOps automation framework for research computing...
[10 lines of project description]

## Python Development Standards

Always use type hints for all function parameters and return values.
Follow PEP 8 style guidelines strictly. Use Black for formatting.
Use pathlib instead of os.path for file operations.
Never use bare except clauses - always catch specific exceptions.
Use Pydantic for data validation at boundaries.
Prefer f-strings over .format() or % formatting.
Write comprehensive docstrings with Args, Returns, Raises sections.
[... 30 more lines of Python guidelines]

## Testing Requirements

Use pytest exclusively for all testing needs.
Always use the real_bm fixture for integration tests.
Never mock internal code - only mock external services.
Write tests before implementation (TDD).
Each test should test exactly one behavior.
Use descriptive test names that explain what is being tested.
Run tests with pytest -xvs for debugging.
Maintain test coverage above 80%.
[... 25 more lines of testing guidelines]

## Git Workflow

Follow conventional commit format for all commits.
Create feature branches from main.
Squash commits before merging.
Always write descriptive commit messages.
Never commit directly to main.
Use git rebase to keep history clean.
Sign commits with GPG when possible.
[... 20 more lines of Git instructions]

## Docker Configuration

Use multi-stage builds to minimize image size.
Always specify exact versions in FROM statements.
Use .dockerignore to exclude unnecessary files.
Run containers as non-root user.
Use health checks for production containers.
[... 15 more lines of Docker guidelines]

## API Design

Follow RESTful principles for all endpoints.
Use proper HTTP status codes.
Version APIs using URL path (/v1/, /v2/).
Implement pagination for list endpoints.
Use JSON for request/response bodies.
[... 20 more lines of API guidelines]
```

### After (12 lines)

```markdown
# CLAUDE.md

## Project
@bots/prompts/PROJECT_overview.md

## Development Standards
@$ACADEMICOPS/bots/prompts/python_best_practices.md
@$ACADEMICOPS/bots/prompts/testing_standards.md
@$ACADEMICOPS/bots/prompts/git_workflow.md

## Infrastructure
@bots/prompts/PROJECT_docker_config.md
@bots/prompts/PROJECT_api_design.md
```

### Chunks Created

**bots/prompts/PROJECT_overview.md**:
```markdown
# AcademicOps Project Overview

This is the AcademicOps automation framework for research computing...
[Project-specific description]
```

**$ACADEMICOPS/bots/prompts/python_best_practices.md**:
```markdown
# Python Development Standards

## Type Hints
Always use type hints for all function parameters and return values...
[Full Python guidelines, reusable across projects]
```

## Example 2: Test Instructions in Wrong Location

### Before (root CLAUDE.md)

```markdown
# CLAUDE.md

## General Instructions
Follow Python best practices...

## Testing
When writing tests, always use pytest.
Use the real_bm fixture for all integration tests.
Test files must be in tests/ directory.
Mock only external services, never internal code.
Test names should be descriptive.
Run with pytest -xvs for debugging.
Each test should be independent.
No test should depend on another test.
Clean up test data after each test.
Use parametrize for testing multiple inputs.
```

### After

**Root CLAUDE.md**:
```markdown
# CLAUDE.md

@bots/prompts/PROJECT_overview.md
@$ACADEMICOPS/bots/prompts/python_best_practices.md
```

**tests/CLAUDE.md** (new file):
```markdown
# tests/CLAUDE.md

@$ACADEMICOPS/bots/prompts/pytest_standards.md
@bots/prompts/PROJECT_test_fixtures.md
```

**bots/prompts/PROJECT_test_fixtures.md**:
```markdown
# Project Test Configuration

## Required Fixtures
Always use the real_bm fixture for integration tests in this project.

## Project-Specific Testing Rules
- Mock only external services, never internal code
- Test data cleanup is handled by fixtures
```

## Example 3: Duplicate Content Across Files

### Before

**/CLAUDE.md**:
```markdown
Use type hints for all Python functions.
Follow PEP 8 style guide.
Use pathlib for file operations.
Write comprehensive docstrings.
[Project specific instructions...]
```

**/src/CLAUDE.md**:
```markdown
Use type hints for all Python functions.
Follow PEP 8 style guide.
Use pathlib for file operations.
Write comprehensive docstrings.
[Source specific instructions...]
```

**/tests/CLAUDE.md**:
```markdown
Use type hints for all Python functions.
Follow PEP 8 style guide.
Use pathlib for file operations.
Write comprehensive docstrings.
[Test specific instructions...]
```

### After

**/CLAUDE.md**:
```markdown
@$ACADEMICOPS/bots/prompts/python_standards.md
@bots/prompts/PROJECT_overview.md
```

**/src/CLAUDE.md**:
```markdown
@$ACADEMICOPS/bots/prompts/python_standards.md
@bots/prompts/PROJECT_source_guidelines.md
```

**/tests/CLAUDE.md**:
```markdown
@$ACADEMICOPS/bots/prompts/python_standards.md
@bots/prompts/PROJECT_test_guidelines.md
```

**$ACADEMICOPS/bots/prompts/python_standards.md** (shared):
```markdown
# Python Development Standards

Use type hints for all Python functions.
Follow PEP 8 style guide.
Use pathlib for file operations.
Write comprehensive docstrings.
```

## Example 4: Informal Notes to Formal Chunks

### Before

```markdown
# CLAUDE.md

Remember to use real_bm fixture
Don't forget auth headers in API calls
TODO: document the deployment process
NOTE: CI/CD needs AWS credentials
btw the database migrations are in alembic/
sometimes tests fail due to race conditions
make sure to validate email formats
```

### After

```markdown
# CLAUDE.md

@bots/prompts/PROJECT_test_configuration.md
@bots/prompts/PROJECT_api_authentication.md
@bots/prompts/PROJECT_deployment_process.md
@bots/prompts/PROJECT_database_migrations.md
@bots/prompts/PROJECT_known_issues.md
@bots/prompts/PROJECT_data_validation.md
```

**bots/prompts/PROJECT_test_configuration.md**:
```markdown
# Test Configuration

## Required Fixtures
All integration tests must use the real_bm fixture to ensure proper database state and configuration loading.
```

**bots/prompts/PROJECT_known_issues.md**:
```markdown
# Known Issues and Workarounds

## Test Race Conditions
Some tests may fail intermittently due to race conditions in async operations.
Workaround: Use proper async fixtures and await all operations.
```

## Example 5: Mixed Tiers to Proper Hierarchy

### Before (all in project tier)

```markdown
# bots/prompts/PROJECT_everything.md

## Python Standards
Use type hints everywhere...
Follow PEP 8...

## Our API Schema  
Our specific endpoints...
Our authentication flow...

## My Personal Preferences
I prefer 2-space indents in YAML...
I like to organize tests by feature...
```

### After (properly separated)

**Framework Tier** (`$ACADEMICOPS/bots/prompts/python_standards.md`):
```markdown
# Python Standards
Use type hints everywhere...
Follow PEP 8...
```

**Project Tier** (`bots/prompts/PROJECT_api.md`):
```markdown
# Project API Schema
Our specific endpoints...
Our authentication flow...
```

**User Tier** (`$ACADEMICOPS_PERSONAL/prompts/my_preferences.md`):
```markdown
# Personal Development Preferences
I prefer 2-space indents in YAML...
I like to organize tests by feature...
```

**Updated CLAUDE.md**:
```markdown
@$ACADEMICOPS/bots/prompts/python_standards.md
@bots/prompts/PROJECT_api.md
@$ACADEMICOPS_PERSONAL/prompts/my_preferences.md
```

## Example 6: Complete Repository Transformation

### Repository Structure Before

```
/
├── CLAUDE.md (200+ lines of mixed content)
├── src/
│   └── (no CLAUDE.md)
├── tests/
│   └── (no CLAUDE.md)
├── deploy/
│   └── (no CLAUDE.md)
└── docs/
    └── (no CLAUDE.md)
```

### Repository Structure After

```
/
├── CLAUDE.md (8 lines, references only)
├── bots/
│   └── prompts/
│       ├── PROJECT_overview.md
│       ├── PROJECT_api_schema.md
│       ├── PROJECT_business_rules.md
│       └── PROJECT_deployment.md
├── src/
│   └── CLAUDE.md (3 lines, references only)
├── tests/
│   └── CLAUDE.md (3 lines, references only)
├── deploy/
│   └── CLAUDE.md (2 lines, references only)
└── docs/
    └── CLAUDE.md (2 lines, references only)
```

### Transformation Commands

```bash
# 1. Initial audit
scripts/audit_claude_files.py .

# 2. Extract chunks from root
scripts/extract_chunks.py CLAUDE.md

# 3. Create subdirectory CLAUDE.md files
echo "@$ACADEMICOPS/bots/prompts/python_standards.md" > src/CLAUDE.md
echo "@bots/prompts/PROJECT_source_structure.md" >> src/CLAUDE.md

echo "@$ACADEMICOPS/bots/prompts/pytest_standards.md" > tests/CLAUDE.md
echo "@bots/prompts/PROJECT_test_fixtures.md" >> tests/CLAUDE.md

echo "@bots/prompts/PROJECT_deployment.md" > deploy/CLAUDE.md

echo "@bots/prompts/PROJECT_api_docs.md" > docs/CLAUDE.md

# 4. Refactor and consolidate
scripts/refactor_references.py . --consolidate

# 5. Validate all references
scripts/validate_references.py .

# 6. Final audit to confirm
scripts/audit_claude_files.py .
```

### Final Root CLAUDE.md

```markdown
# CLAUDE.md

@bots/prompts/PROJECT_overview.md
@$ACADEMICOPS/bots/prompts/development_standards.md
@$ACADEMICOPS/bots/prompts/code_quality.md
@$ACADEMICOPS_PERSONAL/prompts/my_workflow.md
@bots/prompts/PROJECT_getting_started.md
```

## Measurement of Success

### Before Metrics
- Total lines in CLAUDE.md files: 500+
- Files over 50 lines: 5
- Duplicate content blocks: 12
- Inline instructions: 95%
- Invalid references: N/A

### After Metrics
- Total lines in CLAUDE.md files: 45
- Files over 50 lines: 0
- Duplicate content blocks: 0
- Inline instructions: 0%
- Invalid references: 0

### Benefits Achieved
- 91% reduction in CLAUDE.md line count
- 100% elimination of duplication
- Clear separation of concerns
- Reusable chunks across projects
- Easy to maintain and update
- Fast context loading for Claude
