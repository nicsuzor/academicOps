# lib/ - Git Submodules

This directory contains git submodules pointing to upstream repositories. academicOps is a **contributor**, not maintainer.

| Path | Upstream | Owner |
|------|----------|-------|
| `beads/` | steveyegge/beads | Steve Yegge |
| `gastown/` | steveyegge/gastown | Steve Yegge |
| `omcp/` | nicsuzor/omcp | Nic Suzor |

## Rules

1. **DO NOT create beads here** - beads belong in academicOps root, not in `lib/beads`
2. **DO NOT commit to these directories** - they track upstream; changes require PRs to upstream repos
3. **DO NOT push to upstream remotes** - academicOps has read-only consumer access

## Correct Patterns

- **Using beads**: Import from `lib/beads`, run `bd` commands - fine
- **Updating submodules**: `git submodule update --remote`
- **Contributing upstream**: Fork, branch, PR to upstream repo - not through academicOps
