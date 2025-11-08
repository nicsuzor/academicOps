# Repository Structure

**Authoritative source**: `aOps/paths.toml` and `aOps/README.md`

## Monorepo with Submodule

aOps is a **submodule** of the main writing repository:

```
${ACA}                      # User's home repo (PRIVATE, nicsuzor/writing)
└── ${AOPS}/               # Automation framework (PUBLIC, nicsuzor/academicOps, submodule)
    ├── skills/            # Reusable workflows
    ├── hooks/             # Claude Code automation hooks
    ├── scripts/           # Utility scripts
    ├── config/            # Configuration files
    ├── docs/              # Documentation
    └── resources/         # External references
```

Current paths:
- `${ACA}` = `/home/nic/src/writing/`
- `${AOPS}` = `/home/nic/src/writing/aOps/`

## Data Boundaries

- `aOps/` = PUBLIC (GitHub, nicsuzor/academicOps)
- Everything else = PRIVATE (nicsuzor/writing)

**Axiom #2**: Project-specific content belongs ONLY in project repository.
**Axiom #3**: Projects must work independently without cross-dependencies.

## Project Dependencies

Projects in `${ACA}/projects/` may have dependencies (see @docs/chunks/PROJECT-CATALOG.md for details).

- Changes to shared dependencies require testing ALL dependents
- Breaking changes require user approval

## GitHub Issue Management

- ALL agent training issues → `nicsuzor/academicOps`
- Project-specific issues → project repos
- Always search before creating new issues
- Tag with `prompts` label for agent instruction issues

## Scope Detection

**Before ANY work**, verify repository context:

```bash
# Check if in aOps submodule
pwd | grep -q '/aOps' && echo "In aOps (PUBLIC)" || echo "In main repo (PRIVATE)"

# Verify git remote for GitHub operations
git remote -v
```
