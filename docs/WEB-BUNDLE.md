---
title: Web Bundle
type: framework-doc
permalink: docs-web-bundle
description: Using aOps on Claude Code Web and other limited environments
---

# Web Bundle

Use aOps in limited environments where only one repository is accessible.

## Environment Types

| Environment | Config Location | Features |
|-------------|-----------------|----------|
| **Full** (laptop, WSL, VM) | `~/.claude/` symlinks | All features, hooks, MCP |
| **Limited** (Claude Code Web) | Project `.claude/` bundle | Skills, commands, agents only |

## Full Environment Setup

Run `setup.sh` once to configure:

```bash
cd /path/to/academicOps
./setup.sh
```

This creates symlinks in `~/.claude/` pointing to the framework. All projects inherit these settings.

## Limited Environment Setup

### For academicOps itself

The repository's `.claude/` uses symlinks to parent directories:

```bash
python scripts/sync_web_bundle.py --self
```

Result:
```
.claude/
├── CLAUDE.md -> ../CLAUDE.md
├── agents -> ../agents
├── commands -> ../commands
├── settings.json -> ../config/claude/settings.json
└── skills -> ../skills
```

### For other projects

Bundle aOps into any project's `.claude/`:

```bash
python scripts/sync_web_bundle.py /path/to/writing
```

This copies (not symlinks) framework content:
```
writing/.claude/
├── .aops-bundle         # Marker file
├── CLAUDE.md            # Generated instructions
├── agents/              # Copied agent definitions
├── commands/            # Copied slash commands
├── settings.json        # Web-compatible (no hooks)
└── skills/              # Copied skill definitions
```

Commit this `.claude/` directory to enable aOps on Claude Code Web.

## What Works in Limited Environments

| Feature | Status | Notes |
|---------|--------|-------|
| Skills | Works | `Skill(skill="...")` loads bundled definitions |
| Commands | Works | `/command` invokes bundled slash commands |
| Agents | Works | Agent definitions available for Task tool |
| Hooks | Not available | Require $AOPS and Python environment |
| MCP servers | Not available | Require local setup |

## Keeping Bundles Fresh

### Automatic Updates (Recommended)

**Option 1: Git Hook (Local Auto-Sync)**

The sync script automatically installs a git post-commit hook that:
- Runs after each commit in the target project
- Only activates in full environments (where `$AOPS` is set)
- Automatically updates `.claude/` and commits changes

This happens automatically when you run:
```bash
python scripts/sync_web_bundle.py /path/to/writing
```

To skip hook installation, use `--no-hook`:
```bash
python scripts/sync_web_bundle.py /path/to/writing --no-hook
```

**Option 2: GitHub Actions (CI/CD Auto-Sync)**

For team projects or when working across multiple machines, add the GitHub Actions workflow:

1. Copy the template workflow to your project:
   ```bash
   mkdir -p /path/to/writing/.github/workflows
   cp templates/github-workflow-sync-aops.yml /path/to/writing/.github/workflows/
   ```

2. Commit and push the workflow:
   ```bash
   cd /path/to/writing
   git add .github/workflows/github-workflow-sync-aops.yml
   git commit -m "chore: add aOps bundle auto-sync workflow"
   git push
   ```

The workflow runs on every push to main/master and automatically updates the `.claude/` bundle.

### Manual Updates

Re-run sync periodically to update bundled projects:

```bash
# Update academicOps itself
python scripts/sync_web_bundle.py --self

# Update other projects
python scripts/sync_web_bundle.py /path/to/writing
python scripts/sync_web_bundle.py /path/to/buttermilk
```

The bundle includes a `.aops-bundle` marker. Re-syncing will overwrite existing bundles safely.

## Troubleshooting

**Skills not loading on Claude Code Web**

Check that `.claude/skills/` exists and contains skill files:
```bash
ls .claude/skills/
```

**"Hooks failed" messages**

Expected in limited environments. The bundled settings.json for other projects has no hooks. For academicOps itself, hook failures are logged but don't block operation.

**"$AOPS not set" errors**

This happens when full-environment hooks run without proper setup. In limited environments, use the bundled web settings which have no hooks.
