---
title: Web Bundle
type: reference
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

This creates symlinks in `~/.claude/` pointing to the framework. Claude Code automatically loads these settings for all projects on the machine.

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
| Hooks | Not available | See note below |
| MCP servers | Not available | Require local setup |

**Why hooks don't work**: Claude Code Web and similar limited environments don't provide shell access to run Python scripts. Hooks require the `$AOPS` environment variable and a Python environment with dependencies. This is expected behavior - the bundled `settings.json` intentionally excludes hook definitions to avoid spurious error messages.

## Keeping Bundles Fresh

### Sync Strategies

Choose the sync strategy that fits your workflow:

| Strategy | When to Use | Sync Trigger | Overhead |
|----------|-------------|--------------|----------|
| **Git Hook** | Local development, single machine | Every commit | Low |
| **Push Workflow** | Teams, CI integration | Every push to main | Medium |
| **Nightly Workflow** | Minimal overhead, infrequent updates | Nightly at 3am UTC | Very Low |

### Option 1: Git Hook (Local Auto-Sync)

Best for: Individual developers working on a single machine.

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

### Option 2: Push Workflow (CI/CD Auto-Sync)

Best for: Team projects or working across multiple machines.

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

### Option 3: Nightly Workflow (Less Invasive)

Best for: Projects that don't need immediate updates, reducing CI overhead.

This workflow only syncs when aOps has new commits:

1. Copy the nightly workflow template:
   ```bash
   mkdir -p /path/to/writing/.github/workflows
   cp templates/github-workflow-sync-aops-nightly.yml /path/to/writing/.github/workflows/sync-aops-nightly.yml
   ```

2. Commit and push:
   ```bash
   cd /path/to/writing
   git add .github/workflows/sync-aops-nightly.yml
   git commit -m "chore: add nightly aOps bundle sync workflow"
   git push
   ```

Features:
- Runs at 3am UTC daily (configurable via cron)
- Checks if aOps has updates before syncing
- Tracks version in `.claude/.aops-version`
- Uses `[skip ci]` to prevent workflow loops
- Manual trigger available via workflow_dispatch

### Version Tracking

All sync methods now write the aOps commit SHA to `.claude/.aops-version`. This enables:
- Nightly workflow to skip sync when already up-to-date
- Easy verification of which aOps version a project uses
- Debugging when issues arise

Check your current aOps version:
```bash
cat .claude/.aops-version
```

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

### Verifying Your Bundle

Check that the bundle is properly installed:
```bash
# Verify marker file exists
cat .claude/.aops-bundle

# Check bundle version
cat .claude/.aops-version

# List available skills
ls .claude/skills/
```

### Common Issues

**Skills not loading on Claude Code Web**

1. Verify `.claude/skills/` exists and contains skill files
2. Check that files are actual copies, not broken symlinks
3. Re-run sync: `python scripts/sync_web_bundle.py /path/to/project`

**"Hooks failed" messages**

This is **expected behavior** in limited environments. Hooks require:
- Shell access to run Python scripts
- The `$AOPS` environment variable set
- Python with installed dependencies

The bundled `settings.json` for other projects excludes hooks entirely. For academicOps itself on Claude Code Web, hook failures are logged but don't block operation.

**"$AOPS not set" errors**

This occurs when full-environment hooks run without proper setup. Solutions:
1. Run `./setup.sh` to configure the full environment, OR
2. Use the bundled web settings which have no hooks

**Bundle seems outdated**

Force a fresh sync:
```bash
# Remove existing bundle
rm -rf .claude/

# Re-sync
python scripts/sync_web_bundle.py /path/to/project

# Verify new version
cat .claude/.aops-version
```

**GitHub Actions workflow not triggering**

1. Ensure workflow file is in `.github/workflows/`
2. Check repository has Actions enabled
3. Verify the workflow has correct trigger events
