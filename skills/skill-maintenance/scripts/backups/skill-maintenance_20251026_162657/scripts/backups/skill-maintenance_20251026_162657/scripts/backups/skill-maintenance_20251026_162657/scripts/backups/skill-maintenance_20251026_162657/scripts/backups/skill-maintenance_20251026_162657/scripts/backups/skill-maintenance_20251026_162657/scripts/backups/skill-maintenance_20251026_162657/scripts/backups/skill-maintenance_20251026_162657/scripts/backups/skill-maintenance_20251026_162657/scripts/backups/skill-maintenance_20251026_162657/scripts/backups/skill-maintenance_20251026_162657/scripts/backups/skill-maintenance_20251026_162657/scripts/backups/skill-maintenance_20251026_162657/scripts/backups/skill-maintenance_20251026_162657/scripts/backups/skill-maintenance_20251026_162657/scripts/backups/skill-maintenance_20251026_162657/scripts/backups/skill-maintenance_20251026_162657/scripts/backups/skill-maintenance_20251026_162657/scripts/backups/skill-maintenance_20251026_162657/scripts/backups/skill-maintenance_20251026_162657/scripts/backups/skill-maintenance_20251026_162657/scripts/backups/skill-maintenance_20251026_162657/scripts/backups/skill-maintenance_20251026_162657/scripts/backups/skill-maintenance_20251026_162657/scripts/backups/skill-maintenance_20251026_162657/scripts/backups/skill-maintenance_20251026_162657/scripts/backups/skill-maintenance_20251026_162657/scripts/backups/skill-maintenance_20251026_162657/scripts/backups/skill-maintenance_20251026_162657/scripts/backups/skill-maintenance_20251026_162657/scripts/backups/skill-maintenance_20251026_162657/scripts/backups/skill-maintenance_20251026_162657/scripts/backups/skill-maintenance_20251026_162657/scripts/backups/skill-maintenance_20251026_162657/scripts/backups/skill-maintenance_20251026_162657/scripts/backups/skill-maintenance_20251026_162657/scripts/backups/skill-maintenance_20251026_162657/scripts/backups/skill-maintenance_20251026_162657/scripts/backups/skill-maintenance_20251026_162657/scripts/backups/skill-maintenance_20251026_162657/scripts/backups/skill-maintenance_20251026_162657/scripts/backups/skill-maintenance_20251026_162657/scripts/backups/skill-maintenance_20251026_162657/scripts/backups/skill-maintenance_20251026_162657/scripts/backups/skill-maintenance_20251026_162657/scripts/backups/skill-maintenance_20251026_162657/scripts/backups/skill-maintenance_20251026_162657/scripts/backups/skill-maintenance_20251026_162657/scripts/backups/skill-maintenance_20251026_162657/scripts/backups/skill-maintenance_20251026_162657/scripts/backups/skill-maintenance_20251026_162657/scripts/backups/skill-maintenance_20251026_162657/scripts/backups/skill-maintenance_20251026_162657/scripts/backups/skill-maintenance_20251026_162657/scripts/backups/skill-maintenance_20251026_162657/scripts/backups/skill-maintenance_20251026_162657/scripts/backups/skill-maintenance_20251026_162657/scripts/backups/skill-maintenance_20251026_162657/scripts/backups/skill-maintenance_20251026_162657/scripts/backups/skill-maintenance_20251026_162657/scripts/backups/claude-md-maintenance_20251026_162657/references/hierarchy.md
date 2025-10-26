# CLAUDE.md Hierarchical Structure

This document explains the 3-tier hierarchy for organizing CLAUDE.md content and instruction chunks in the academicOps framework.

## Overview

The academicOps framework uses a 3-tier hierarchy to organize instructions and configuration:

1. **Framework Tier** - Shared across all projects
2. **User Tier** - Personal preferences across projects  
3. **Project Tier** - Specific to individual projects

Each tier has a specific purpose and location, allowing for maximum reusability while maintaining project-specific customization.

## Tier 1: Framework Tier

**Location**: `$ACADEMICOPS_BOT/bots/prompts/`

**Purpose**: Reusable instructions that apply to all projects using academicOps.

**Content Types**:
- Generic Python best practices
- Standard Git workflows
- Docker configuration patterns
- Testing methodologies
- Code quality standards
- General development workflows

**Examples**:
```markdown
@$ACADEMICOPS_BOT/bots/prompts/python_typing.md
@$ACADEMICOPS_BOT/bots/prompts/git_commit_standards.md
@$ACADEMICOPS_BOT/bots/prompts/docker_best_practices.md
```

**When to Use**:
- Instructions that would benefit any project
- Industry best practices
- Tool-specific guidance (pytest, mypy, ruff)
- Patterns that transcend specific domains

## Tier 2: User Tier

**Location**: `$ACADEMICOPS_PERSONAL/prompts/`

**Purpose**: Personal preferences and workflows that apply across a user's projects.

**Content Types**:
- Personal coding style preferences
- Custom workflows
- User-specific tool configurations
- Personal productivity patterns
- Preferred libraries and frameworks

**Examples**:
```markdown
@$ACADEMICOPS_PERSONAL/prompts/my_git_workflow.md
@$ACADEMICOPS_PERSONAL/prompts/preferred_testing_style.md
@$ACADEMICOPS_PERSONAL/prompts/personal_code_conventions.md
```

**When to Use**:
- Personal preferences that differ from defaults
- Custom workflows you use across projects
- User-specific optimizations
- Personal tool configurations

## Tier 3: Project Tier

**Location**: `$CLAUDE_PROJECT_DIR/bots/prompts/`

**Purpose**: Project-specific instructions and domain knowledge.

**Content Types**:
- Business logic and rules
- Domain-specific patterns
- Project architecture decisions
- Custom APIs and interfaces
- Project-specific workflows
- Local development setup

**Examples**:
```markdown
@bots/prompts/PROJECT_api_schema.md
@bots/prompts/PROJECT_business_rules.md
@bots/prompts/PROJECT_deployment_process.md
```

**When to Use**:
- Instructions specific to this project only
- Domain knowledge unique to the project
- Custom business logic
- Project-specific architecture patterns
- Local conventions that differ from standards

## Tier Selection Guidelines

### Determining the Correct Tier

Ask these questions in order:

1. **Is this specific to this project only?**
   - YES → Project Tier (`bots/prompts/PROJECT_*.md`)
   - NO → Continue

2. **Is this a personal preference or workflow?**
   - YES → User Tier (`$ACADEMICOPS_PERSONAL/prompts/*.md`)
   - NO → Continue

3. **Would this benefit all projects?**
   - YES → Framework Tier (`$ACADEMICOPS_BOT/bots/prompts/*.md`)
   - NO → Reconsider if it needs to be a chunk at all

### Content Examples by Tier

**Framework Tier Examples**:
- "Always use type hints for Python functions"
- "Follow conventional commit format"
- "Use pathlib instead of os.path"
- "Write tests before implementation (TDD)"

**User Tier Examples**:
- "Prefer 2-space indentation for YAML"
- "Use my custom git aliases"
- "Follow my personal naming conventions"
- "Use my preferred test organization pattern"

**Project Tier Examples**:
- "Use the company's internal authentication API"
- "Follow the project's specific database schema"
- "Apply domain-specific validation rules"
- "Use project-specific deployment pipeline"

## File Naming Conventions

### Framework Tier
- Generic, descriptive names
- No project prefixes
- Examples:
  - `python_typing.md`
  - `git_workflow.md`
  - `testing_practices.md`

### User Tier
- Optionally prefixed with "my_" or "personal_"
- Clear about being user-specific
- Examples:
  - `my_coding_style.md`
  - `personal_git_config.md`
  - `preferred_tools.md`

### Project Tier
- Prefixed with "PROJECT_" for clarity
- Project-specific terminology
- Examples:
  - `PROJECT_api_schema.md`
  - `PROJECT_business_rules.md`
  - `PROJECT_deployment.md`

## Migration Patterns

### Moving Up Tiers

When content becomes more generally useful:

```bash
# Project → Framework
mv bots/prompts/PROJECT_testing.md \
   $ACADEMICOPS_BOT/bots/prompts/testing_practices.md

# Update references
sed -i 's|@bots/prompts/PROJECT_testing.md|@$ACADEMICOPS_BOT/bots/prompts/testing_practices.md|g' CLAUDE.md
```

### Moving Down Tiers

When content needs more specificity:

```bash
# Framework → Project
cp $ACADEMICOPS_BOT/bots/prompts/python_dev.md \
   bots/prompts/PROJECT_python_dev.md

# Customize for project
# Update references
```

## Environment Variable Setup

Ensure these environment variables are set:

```bash
# Framework repository location
export ACADEMICOPS_BOT=/path/to/academicOps

# Personal configuration location
export ACADEMICOPS_PERSONAL=/path/to/personal

# Current project (usually auto-detected)
export CLAUDE_PROJECT_DIR=$(pwd)
```

Add to your shell profile (`~/.bashrc` or `~/.zshrc`) for persistence.

## Best Practices

1. **Start Specific, Generalize Later**
   - Begin with project tier
   - Move up as patterns prove reusable

2. **Keep Tiers Pure**
   - Don't mix project-specific and generic content
   - Split mixed content into separate chunks

3. **Use Clear Naming**
   - PROJECT_ prefix for project-specific
   - Descriptive names for framework tier
   - Personal prefixes for user tier

4. **Regular Review**
   - Periodically review project chunks for reusability
   - Move generalizable patterns up tiers
   - Consolidate duplicate content

5. **Document Decisions**
   - Comment why content is in a specific tier
   - Document migration history
   - Note dependencies between tiers

## Troubleshooting

### Reference Not Found

Check tier locations:
```bash
# Framework
ls $ACADEMICOPS_BOT/bots/prompts/

# User
ls $ACADEMICOPS_PERSONAL/prompts/

# Project
ls bots/prompts/
```

### Wrong Tier Symptoms

**Too High** (Framework when should be Project):
- Other projects can't use it
- Contains project-specific names/APIs
- Requires project context to understand

**Too Low** (Project when should be Framework):
- Duplicated across multiple projects
- Generic best practice
- No project-specific content

### Migration Checklist

When moving content between tiers:

- [ ] Content fits new tier's purpose
- [ ] File renamed appropriately
- [ ] All references updated
- [ ] Old file removed
- [ ] Tested in target environment
- [ ] Documentation updated
