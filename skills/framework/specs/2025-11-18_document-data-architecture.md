# Task Spec: Document Data Architecture and Path Resolution

**Created**: 2025-11-18
**Status**: Approved
**Priority**: P1 - Architecture Documentation
**Pattern**: #architecture #paths #cross-repo #documentation

## Problem Statement

The relationship between `$AOPS` (framework repository) and `$ACA_DATA` (user knowledge base) is underdocumented, leading to confusion about:
- Where files should live (framework vs user data)
- How skills access user data from any working directory
- What gets symlinked vs what stays in user's private repo
- How the remote environment problem (no ~/.claude/) should be handled

**Current state**:
- README.md documents both structures separately (lines 9-86 for $AOPS, lines 90-112 for $ACA_DATA)
- No clear explanation of how they interoperate
- Installation section mentions symlinks but doesn't explain data separation
- Remote environment .claude/ problem noted as "unsolved"

**User requirements** (from clarification):
```
$ACA_DATA='/home/nic/src/writing/data'  # User's private knowledge base
$AOPS='/home/nic/src/academicOps'       # Framework repository (may be public)

- Skills invoked from any directory must access single personal knowledge base
- Framework shouldn't contain user data (may be public repo)
- Remote environments: No ~/.claude/, need local <repo>/.claude/ copy (unsolved)
```

## Architecture Context

**Two-repository model**:

1. **Framework Repository** (`$AOPS`):
   - Contains: skills, hooks, commands, tests, documentation
   - Location: Any directory (e.g., `~/src/academicOps`)
   - Visibility: May be public (no user data)
   - Installation: Symlinks to `~/.claude/` (or `<repo>/.claude/` in remote)
   - Version control: Git repository

2. **User Data Repository** (`$ACA_DATA`):
   - Contains: bmem knowledge base, tasks, sessions, project data
   - Location: User's private repo (e.g., `~/src/writing/data`)
   - Visibility: Always private
   - Format: Obsidian-compatible bmem markdown
   - Access: Via `$ACA_DATA` environment variable from any directory

**Cross-repo access pattern**:
- Skills live in `$AOPS`, invoked via symlinks in `~/.claude/`
- Skills access user data via `$ACA_DATA` environment variable
- No assumptions about current working directory when skill invoked
- Enables: Work in project A, access same knowledge base as project B

**Known gap**: Remote environments without `~/.claude/` support

## Scope

### In Scope
1. Add "Architecture: Framework vs User Data" section to README.md
2. Document path resolution patterns for skill developers
3. Clarify what gets symlinked (framework) vs what stays in user repo (data)
4. Update STATE.md "Authoritative Facts" section with clear path architecture
5. Add environment variable validation recommendations
6. Document the remote environment problem and current status (unsolved)

### Out of Scope
- Solving remote environment .claude/ installation (user noted as unsolved)
- Changing actual directory structures (document as-is)
- Creating path resolution utilities (future task if needed)
- Modifying existing skills to use environment variables (separate task per skill)

## Success Criteria

**Functional Requirements**:
1. README.md clearly explains $AOPS vs $ACA_DATA separation
2. Skill developers understand how to access user data from framework code
3. Installation instructions clarify symlink vs environment variable setup
4. STATE.md documents authoritative path architecture

**Documentation Requirements**:

Add to README.md after line 86:
```markdown
## Architecture: Framework vs User Data

academicOps uses a two-repository model separating framework code from user data:

**Framework Repository** (`$AOPS`):
- **Purpose**: Skills, hooks, commands, tests, documentation
- **Location**: Any directory (e.g., `~/src/academicOps`)
- **Visibility**: May be public - contains NO user data
- **Installation**: Symlinks to `~/.claude/` (local) or `<repo>/.claude/` (remote)

**User Data Repository** (`$ACA_DATA`):
- **Purpose**: bmem knowledge base, tasks, sessions, experiments
- **Location**: User's private repository (e.g., `~/src/writing/data`)
- **Visibility**: Always private
- **Format**: Obsidian-compatible bmem markdown
- **Access**: Via `$ACA_DATA` environment variable

**Why separate?**
- Framework can be version controlled and shared publicly
- User data stays private in personal repository
- Skills work across all projects by accessing single knowledge base
- Clear boundary between reusable infrastructure and personal content

**Path resolution for skill developers**:
- Framework files: Use `$AOPS/path/to/file` or relative paths from repo root
- User data files: Use `$ACA_DATA/path/to/file`
- Always use environment variables, never hardcode paths
- Validate environment variables exist before accessing

**Remote environments** (unsolved):
In remote environments without `~/.claude/` access, framework installation
to `<repo>/.claude/` is required but not yet automated. Manual symlink setup
currently necessary.
```

Update STATE.md "Authoritative Facts" section (after line 26):
```markdown
### Path Architecture

**Framework Repository** (`$AOPS`):
- Location: `/home/nic/src/academicOps` (or any directory)
- Contains: Skills, hooks, commands, tests, documentation
- NO user data (may be public repository)
- Installed via symlinks to `~/.claude/skills/`, `~/.claude/hooks/`, etc.

**User Data Repository** (`$ACA_DATA`):
- Location: `/home/nic/src/writing/data` (user's private repo)
- Contains: bmem knowledge base, tasks, sessions, project-specific data
- Always private
- Accessed via `$ACA_DATA` environment variable from any working directory

**Cross-repo access**:
- Skills invoked from Project A access same `$ACA_DATA` as skills in Project B
- No assumptions about current working directory
- Environment variables required: `$AOPS`, `$ACA_DATA`

**Key files**:
- Framework learning log: `$ACA_DATA/projects/aops/experiments/LOG.md`
- Task data: `$ACA_DATA/tasks/`
- bmem entities: `$ACA_DATA/` (following bmem directory structure)
- Session logs: `$ACA_DATA/sessions/`
```

**Testing Strategy**:
- Documentation review: Verify no contradictions between README.md and STATE.md
- Path audit: Check all documented paths match actual environment
- Environment variable validation: Test skills fail gracefully if $ACA_DATA unset

## Implementation Notes

**Key points to document**:
1. **Separation of concerns**: Framework (reusable) vs data (personal)
2. **Environment variables**: Required for cross-repo access
3. **Installation pattern**: Symlinks for framework, environment variable for data
4. **Remote environment gap**: Acknowledged as unsolved problem

**Consistency checks**:
- README.md "Installation" section should reference architecture explanation
- STATE.md should link to README.md for detailed architecture
- No hardcoded paths in documentation (use $AOPS and $ACA_DATA variables)

**Examples to include**:
```python
# WRONG: Hardcoded path
log_path = "/home/nic/src/writing/data/projects/aops/experiments/LOG.md"

# RIGHT: Environment variable
import os
from pathlib import Path

aca_data = os.getenv("ACA_DATA")
if not aca_data:
    raise EnvironmentError("ACA_DATA environment variable not set")

log_path = Path(aca_data) / "projects/aops/experiments/LOG.md"
```

## Dependencies

**Blocks**:
- Future skill development (clear pattern for path resolution)
- Remote environment installation improvements

**Blocked By**: None (documentation only)

**Related**:
- Task 1: Fix framework path references
- Task 2: Fix LOG.md references
- Both implement the architecture documented here

## Risks

**Low Risk**: Documentation clarification, no code changes

**Potential confusion**:
- Developers might not read architecture section before creating new components
- Mitigation: Add architecture reference to framework/SKILL.md workflow docs

## Success Metrics

- Zero ambiguity about where files should live (framework vs user data)
- Clear guidance for accessing user data from framework skills
- Future PRs demonstrate correct path resolution patterns
- No hardcoded paths in new framework components
