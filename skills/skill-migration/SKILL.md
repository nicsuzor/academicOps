---
name: skill-migration
description: This skill should be used when extracting automation workflows from agent definitions or documentation files to create new, portable, reusable skills. It analyzes agent files and documentation, identifies automatable workflows, creates atomic skills from them, and cleans up source files by removing migrated content. Use this when migrating from agent-based instructions to skill-based atomic workflows.
---

# Skill Migration

## Overview

Extract automation workflows from agent definitions and documentation to create portable, reusable skills. This skill transforms embedded procedural knowledge into atomic, composable skills that work across any repository or project, then cleans up source files to maintain lean, efficient agents.

## Migration Philosophy

**Goal**: Transform agents from procedural instruction manuals into orchestrators of atomic skills.

**Before Migration**:
- Agents contain embedded procedural knowledge
- Workflows are duplicated across multiple agent files
- Instructions are repository-specific
- Documentation mixes agent rules with human guides

**After Migration**:
- Skills contain atomic, reusable workflows
- Agents chain skills together for complex tasks
- Skills work universally across projects
- Clean separation: agents orchestrate, skills execute

## When to Use This Skill

Use skill-migration when:

1. **User provides task description** - "Create a skill that does X based on our Y documentation"
2. **Consolidating duplicated workflows** - Same procedure appears in multiple agents
3. **Making workflows portable** - Want to use a workflow across different projects
4. **Cleaning up agent bloat** - Agent files have grown too large with procedural details
5. **Creating automation library** - Building collection of reusable automation skills

**Concrete trigger examples**:
- "Create a commit skill from our code-review agent"
- "Extract the test-writing workflow into a reusable skill"
- "Make a skill for our Hydra configuration standards"
- "Turn our git workflow documentation into skills"

## Migration Workflow

Follow this workflow in order. Each step builds on previous ones.

### Step 1: Understand the Target Workflow

**Objective**: Clearly understand what automation workflow to extract and what it should do.

**Process**:

1. **Ask clarifying questions** to understand scope:
   - What specific workflow or task should the skill automate?
   - Which agent files or documentation contain this workflow?
   - Should the skill handle a single atomic task or a broader workflow?
   - What repositories/projects should this skill work in? (Answer should be: ALL)

2. **Identify source files** containing the workflow:
   - Agent definitions in `agents/*.md`
   - Documentation in `docs/*.md` or project-specific `docs/agents/*.md`
   - Old/deprecated documentation in `docs/_UNUSED/` or `.claude/agents.backup/`

3. **Define success criteria** - What makes a successful skill?
   - Skill works in any repository (not hardcoded paths)
   - Skill is atomic (does ONE thing well)
   - Skill is reusable (can be composed with other skills)
   - Source files are cleaner after migration

**Example**:
```
User: "Create a skill for git commits"

Questions to ask:
- Should this handle the full commit workflow or just message generation?
- Should it include code review or is that separate?
- What commit message format/standards should it use?
- Which files have our current commit instructions? (e.g., code-review agent, git docs)
```

### Step 2: Analyze Source Files

**Objective**: Extract relevant workflow content from source files and understand what needs to be migrated.

**Process**:

1. **Read all identified source files** using Read tool
   - Load agent definitions
   - Load documentation files
   - Load any deprecated/backup files that might have useful content

2. **Identify workflow sections** to extract:
   - Step-by-step procedures
   - Decision trees and conditionals
   - Tool usage patterns
   - Validation criteria
   - Examples and templates
   - Common patterns and anti-patterns

3. **Note dependencies**:
   - What tools does the workflow use?
   - What external files/configs does it reference?
   - What other workflows does it depend on?
   - Can these dependencies be generalized?

4. **Identify repository-specific content** that needs generalization:
   - Hardcoded paths (e.g., `/home/user/projects/X` → use relative paths or env vars)
   - Specific file names (e.g., `config.yaml` → explain pattern)
   - Project-specific conventions (document as examples, not requirements)

**Example Analysis**:

From code-review agent (`agents/REVIEW.md`):
- **Workflow**: Load validation rules → Build checklist → Execute validation → Generate report → Commit if approved
- **Dependencies**: Validation rule files in `docs/_CHUNKS/`, git tools
- **Repository-specific**: References to `bot/docs/_CHUNKS/` (needs generalization)
- **Reusable**: Checklist pattern, validation gate pattern, commit message format

### Step 3: Design the Skill

**Objective**: Plan how the extracted workflow becomes a portable, atomic skill.

**Process**:

1. **Define skill scope** - Make it atomic:
   - ONE primary workflow or capability
   - Clear input/output contract
   - No dependencies on other skills (can use tools, but not other skills)

2. **Choose skill structure** (from skill-creator patterns):
   - **Workflow-Based**: For sequential processes (e.g., commit workflow, test workflow)
   - **Task-Based**: For collections of related operations (e.g., git operations)
   - **Reference/Guidelines**: For standards (e.g., code standards, commit message format)

3. **Plan resources** needed:
   - **scripts/**: Deterministic operations that get rewritten repeatedly
   - **references/**: Detailed documentation too long for SKILL.md
   - **assets/**: Templates, boilerplate code, examples

4. **Generalize repository-specific content**:
   - Replace hardcoded paths with patterns or conventions
   - Document expected file structures instead of specific files
   - Use relative paths or environment variables
   - Provide examples from multiple contexts

**Example Design**:

Skill: `git-commit`
- **Scope**: Create standardized git commits with proper messages and metadata
- **Structure**: Workflow-based (decision tree → compose message → execute commit)
- **Resources**:
  - `scripts/`: None needed (git operations are simple)
  - `references/commit-message-guide.md`: Detailed commit message standards
  - `assets/`: None needed
- **Generalization**:
  - Don't assume specific validation files exist
  - Provide commit message template that works anywhere
  - Document how to add project-specific commit standards

### Step 4: Create the Skill

**Objective**: Build the actual skill following skill-creator best practices.

**Process**:

1. **Initialize skill** using skill-creator:
   ```bash
   # Use the skill-creator's init_skill.py script
   uv run python .claude/skill-creator/scripts/init_skill.py <skill-name> --path .claude
   ```

2. **Write SKILL.md** with imperative/infinitive form:
   - Clear description in YAML frontmatter
   - Overview explaining what the skill enables
   - Workflow or task sections with specific instructions
   - Examples showing concrete usage
   - References to bundled resources
   - NO second-person ("you should") - use objective instructions

3. **Create bundled resources**:
   - Write scripts for deterministic operations
   - Create reference docs for detailed information
   - Add assets for templates or boilerplate

4. **Remove example files** not needed:
   - Delete unused `scripts/example.py`
   - Delete unused `references/api_reference.md`
   - Delete unused `assets/example_asset.txt`

5. **Add real examples** from analyzed source files:
   - Include actual patterns found in documentation
   - Show both correct and incorrect usage
   - Provide decision trees from agent definitions

**Writing Style Requirements**:
- Imperative/infinitive form (verb-first): "Execute the command" not "You should execute"
- Objective, instructional language: "To accomplish X, do Y" not "If you want X"
- Clear, specific procedures: "Run `git status` to check" not "Check the status somehow"
- Focus on WHAT and HOW, assume the reader (AI) needs explicit instructions

### Step 5: Clean Up Source Files

**Objective**: Remove migrated content from source files to keep them lean and prevent duplication.

**CRITICAL**: This step maintains the fail-fast philosophy for agents (Axiom #8). Once content is migrated to a skill, it MUST be removed from source files. Keeping duplicate instructions violates DRY and creates confusion about the authoritative source.

**Process**:

1. **Identify content to remove** from source files:
   - Procedural workflows now in the skill
   - Detailed instructions now in skill resources
   - Examples and patterns now in skill
   - **Keep**: High-level orchestration instructions for agents
   - **Keep**: Pointers to use the new skill
   - **Remove**: Detailed how-to content

2. **Edit source files** to remove migrated content:
   - Delete entire sections that moved to skill
   - Replace with reference to new skill: "Use the <skill-name> skill for X"
   - Simplify agent instructions to orchestration level
   - Update any cross-references

3. **Verify no duplication**:
   - Grep for key phrases from skill in source files
   - Ensure instructions exist in ONLY one place (the skill)
   - Check that removed content is fully represented in skill

4. **Update agent frontmatter** if needed:
   - Remove tools if agent no longer uses them directly
   - Update description if responsibilities changed

**Example Cleanup**:

Before (in `agents/REVIEW.md`):
```markdown
## Commit Process

1. Run git status to see untracked files
2. Run git diff to see changes
3. Draft commit message:
   - Summarize changes (1-2 sentences)
   - Focus on "why" not "what"
   - End with:
     🤖 Generated with [Claude Code](...)
     Co-Authored-By: Claude <noreply@anthropic.com>
4. Add files: git add .
5. Commit with heredoc format...
[20 more lines of detailed instructions]
```

After (in `agents/REVIEW.md`):
```markdown
## Commit Process

After validating code, use the `git-commit` skill to create and execute the commit with proper formatting and metadata.
```

### Step 6: Validate and Package

**Objective**: Ensure the skill works correctly and package it for distribution.

**Process**:

1. **Test the skill** manually:
   - Invoke the skill in a test scenario
   - Verify it works without repository-specific knowledge
   - Test in multiple contexts if possible
   - Confirm bundled resources load correctly

2. **Validate with skill-creator tools**:
   ```bash
   # Validate skill structure
   uv run python .claude/skill-creator/scripts/quick_validate.py .claude/<skill-name>
   ```

3. **Package the skill**:
   ```bash
   # Creates validated .zip file for distribution
   uv run python .claude/skill-creator/scripts/package_skill.py .claude/<skill-name>
   ```

4. **Verify cleanup**:
   - Re-read modified source files
   - Confirm removed content is in skill
   - Check for no duplication
   - Ensure agents reference the skill

### Step 7: Document the Migration

**Objective**: Create record of what was migrated and why for future reference.

**Process**:

1. **Create migration summary**:
   - List source files modified
   - List content sections removed
   - Describe how skill generalizes the workflow
   - Note any dependencies or prerequisites

2. **Update agent instructions** if needed:
   - Add skill invocation examples
   - Update workflow to use skill
   - Document when to use the skill

3. **Report to user**:
   - Skill created at X location
   - Package file created (if packaged)
   - Source files cleaned: list files
   - Next steps: test the skill, distribute if needed

**Example Report**:
```
Migration complete for `git-commit` skill:

Created:
- .claude/git-commit/SKILL.md - Main workflow instructions
- .claude/git-commit/references/commit-standards.md - Detailed message format guide
- .claude/git-commit.zip - Packaged skill for distribution

Modified source files (content removed):
- agents/REVIEW.md - Removed detailed commit workflow (lines 120-147)
- docs/git-workflow.md - Removed commit message format section (lines 45-89)

The skill is now portable and can be used in any repository. Source files reference the skill for commit operations.

Next steps:
1. Test the skill: Try invoking it with a commit scenario
2. Distribute: Share git-commit.zip with other projects
3. Monitor: Watch for agents correctly using the skill vs. attempting old patterns
```

## Helper Scripts

This skill includes helper scripts to automate parts of the migration workflow:

### scripts/extract_workflow.py

Analyzes source files to identify extractable workflow sections. Uses heuristics to find:
- Numbered lists (step-by-step procedures)
- Sections with specific headers (e.g., "## Workflow", "## Process")
- Repeated patterns across multiple files
- Code examples and templates

Usage:
```bash
uv run python .claude/skill-migration/scripts/extract_workflow.py agents/REVIEW.md
```

Output: JSON with extracted sections, suggested skill name, and confidence scores.

### scripts/generalize_content.py

Transforms repository-specific content into generalized patterns:
- Replaces hardcoded paths with relative patterns
- Identifies project-specific file references
- Suggests environment variable replacements
- Flags content that needs manual review

Usage:
```bash
uv run python .claude/skill-migration/scripts/generalize_content.py --input extracted_workflow.json --output generalized.md
```

### scripts/cleanup_sources.py

Assists with removing migrated content from source files:
- Identifies sections in source files that match skill content
- Generates Edit tool commands to remove content
- Suggests replacement text (skill references)
- Creates backup before modification

Usage:
```bash
uv run python .claude/skill-migration/scripts/cleanup_sources.py --skill .claude/git-commit --sources agents/REVIEW.md docs/git-workflow.md
```

## Migration Patterns

### Pattern 1: Simple Workflow Extraction

**Use when**: Single procedural workflow in one file

**Example**: Extract commit message formatting from code-review agent

**Steps**:
1. Understand: "Create skill for commit message format"
2. Analyze: Read agents/REVIEW.md, find commit message section
3. Design: Reference-based skill with message template
4. Create: Simple SKILL.md with examples, no scripts needed
5. Cleanup: Remove commit message format from REVIEW.md, add skill reference
6. Validate: Test message format in different repos

### Pattern 2: Consolidating Duplicate Workflows

**Use when**: Same workflow appears in multiple files

**Example**: Test-writing patterns in test-cleaner agent, supervisor agent, and test documentation

**Steps**:
1. Understand: "Consolidate test-writing workflows"
2. Analyze: Read all three files, identify common and unique content
3. Design: Workflow-based skill with decision tree for different test types
4. Create: SKILL.md with comprehensive workflow, references/ for detailed patterns
5. Cleanup: Remove test workflow from ALL three files, replace with skill reference
6. Validate: Ensure skill covers all use cases from original files

### Pattern 3: Documentation to Skill

**Use when**: Documentation has automatable workflows

**Example**: Git workflow documentation into git-operations skill

**Steps**:
1. Understand: "Turn git docs into reusable skill"
2. Analyze: Read docs/git-workflow.md, identify operations vs. explanation
3. Design: Task-based skill (one section per git operation)
4. Create: SKILL.md with task sections, scripts/ for complex operations
5. Cleanup: Keep high-level git concepts in docs, remove how-to procedures
6. Validate: Test each operation in skill works independently

### Pattern 4: Agent to Multiple Skills

**Use when**: Large agent does multiple distinct things

**Example**: Code-review agent → validation-rules skill + git-commit skill + checklist-pattern skill

**Steps**:
1. Understand: "Break code-review into atomic skills"
2. Analyze: Identify distinct responsibilities (validation, commit, reporting)
3. Design: THREE separate atomic skills
4. Create: One skill at a time, follow full workflow for each
5. Cleanup: Replace agent content with references to all three skills
6. Validate: Verify agent can orchestrate skills to achieve original behavior

## Anti-Patterns to Avoid

**Don't create repository-specific skills**:
- ❌ Skill assumes specific file paths exist
- ❌ Skill requires specific project structure
- ✅ Skill explains patterns and works anywhere

**Don't create mega-skills**:
- ❌ One skill does validation + commit + reporting
- ✅ Three atomic skills, each doing one thing

**Don't leave duplicate content**:
- ❌ Remove content from source but forget to add to skill
- ❌ Keep detailed instructions in both source and skill
- ✅ Content exists in ONLY one place (the skill)

**Don't skip generalization**:
- ❌ Copy exact agent instructions including hardcoded paths
- ✅ Transform to general patterns that work anywhere

**Don't forget cleanup**:
- ❌ Create skill but leave original instructions in place
- ✅ Remove migrated content, add skill reference

## Success Criteria

A successful skill migration achieves:

1. **Portable skill**: Works in any repository, no hardcoded assumptions
2. **Atomic scope**: Skill does ONE thing well, composable with others
3. **Clean sources**: Original files are leaner, no duplication
4. **Clear authority**: Skill is THE authoritative source for its workflow
5. **Complete coverage**: All use cases from original content work in skill
6. **Proper structure**: Follows skill-creator best practices
7. **Validated**: Passes skill-creator validation, tested in practice

## Quick Reference

**Common skill-migration command sequence**:

```bash
# 1. Understand - talk with user about what to migrate

# 2. Analyze - read source files
# (Use Read tool on identified files)

# 3. Design - plan the skill
# (Use helper script to extract workflows)
uv run python .claude/skill-migration/scripts/extract_workflow.py <source-file>

# 4. Create - build the skill
uv run python .claude/skill-creator/scripts/init_skill.py <skill-name> --path .claude
# (Edit SKILL.md and create resources)

# 5. Cleanup - remove from sources
uv run python .claude/skill-migration/scripts/cleanup_sources.py --skill .claude/<skill-name> --sources <files...>

# 6. Validate and package
uv run python .claude/skill-creator/scripts/package_skill.py .claude/<skill-name>

# 7. Document - report to user
```

**Key files**:
- `.claude/skill-creator/SKILL.md` - How to create skills
- `.claude/skill-migration/SKILL.md` - This file, how to migrate to skills
- `agents/*.md` - Source files for workflow extraction
- `docs/*.md` - Documentation with automatable content
