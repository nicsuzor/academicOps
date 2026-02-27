# Repository Sync Setup

AcademicOps uses multiple git repositories that need to stay in sync across machines. This document describes the recommended setup.

## Repositories

| Repo                                          | Purpose                               | Env var         |
| --------------------------------------------- | ------------------------------------- | --------------- |
| `$ACA_DATA` (e.g. `~/brain`)                  | Personal knowledge base, tasks, notes | `ACA_DATA`      |
| `$AOPS_SESSIONS` (default `~/.aops/sessions`) | Session transcripts and summaries     | `AOPS_SESSIONS` |
| `~/dotfiles`                                  | Shell config, scripts                 | -               |

## Sync Layers

### 1. Agent auto-commit (PostToolUse hook)

The `autocommit_state.py` hook automatically commits and pushes `$ACA_DATA` changes after state-modifying tool calls (MCP task/memory operations, Write/Edit to `$ACA_DATA`).

This covers agent-driven changes but **does not cover** changes from CLI tools (e.g. `aops new`), Obsidian, or manual edits.

### 2. Session-start sync (SessionStart hook)

`session_env_setup.py` runs on every Claude/Gemini session start:

1. **Commits and pushes** any pending local changes (catches CLI/manual edits)
2. **Pulls** remote changes from other machines

### 3. Hourly cron backup

A cron job runs `repo-sync.sh` hourly to catch anything missed between sessions.

### 4. Post-commit auto-push

A git hook at `$ACA_DATA/.githooks/post-commit` pushes to origin after every commit. Requires:

```bash
git config core.hooksPath .githooks
```

## Setup

### Prerequisites

- `$ACA_DATA` set in shell config (e.g. `export ACA_DATA=/opt/nic/brain` in `.zshrc.local`)
- Claude CLI installed and on PATH (for conflict resolution via Haiku)
- Git SSH keys configured for all repos

### Example: repo-sync.sh

Place in `~/dotfiles/scripts/repo-sync.sh`:

```bash
#!/bin/bash
# repo-sync.sh - Check and sync git repositories
# Usage: repos [--check] [--quiet]
#   (default)  Fix dirty repos with ccommit, pull clean repos that are behind
#   --check    Just show status, don't fix anything
#   --quiet    Only show repos needing attention

set -euo pipefail

REPOS=(
    "$HOME/dotfiles"
    "$HOME/writing"
    "$HOME/src/academicOps"
)
# Add env-configured repos if set
[[ -n "${ACA_DATA:-}" ]] && REPOS+=("$ACA_DATA")
[[ -n "${AOPS_SESSIONS:-}" ]] && REPOS+=("$AOPS_SESSIONS")

# Parse args
FIX=true
QUIET=false
for arg in "$@"; do
    case $arg in
        --check) FIX=false ;;
        --quiet) QUIET=true ;;
    esac
done

check_repo() {
    local repo="$1"
    local name=$(basename "$repo")

    if [[ ! -d "$repo/.git" ]]; then
        [[ "$QUIET" == "false" ]] && echo "$name: not a git repo"
        return
    fi

    cd "$repo"
    git fetch --quiet 2>/dev/null || true

    local dirty=""
    local behind=""

    [[ -n $(git status --porcelain 2>/dev/null) ]] && dirty="dirty"

    local tracking=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "")
    if [[ -n "$tracking" ]]; then
        local counts=$(git rev-list --left-right --count HEAD...@{u} 2>/dev/null || echo "0 0")
        local behind_count=$(echo "$counts" | awk '{print $2}')
        [[ "$behind_count" -gt 0 ]] && behind="${behind_count} behind"
    fi

    if [[ -n "$dirty" ]]; then
        echo "  $name: dirty"
        if [[ "$FIX" == "true" ]]; then
            # Uses Claude Haiku to commit, resolve conflicts, push
            claude --model haiku --dangerously-skip-permissions \
                -p "commit changed and new files, pull, fix conflicts, push" || true
        fi
    elif [[ -n "$behind" ]]; then
        if [[ "$FIX" == "true" ]]; then
            echo "  $name: pulling $behind..."
            git pull --quiet 2>/dev/null || echo "  $name: pull failed"
        else
            echo "  $name: $behind"
        fi
    else
        [[ "$QUIET" == "false" ]] && echo "  $name: ok"
    fi
}

for repo in "${REPOS[@]}"; do
    check_repo "$repo"
done
```

### Example: cron wrapper

Place in `~/dotfiles/scripts/repo-sync-cron.sh`:

```bash
#!/bin/bash
# Hourly cron wrapper - sources env and runs repo-sync
set -euo pipefail

# Source exports from shell config
if [[ -f "$HOME/.zshrc.local" ]]; then
    eval "$(grep '^export ' "$HOME/.zshrc.local")"
fi

export ACA_DATA="${ACA_DATA:-/opt/nic/brain}"
export AOPS_SESSIONS="${AOPS_SESSIONS:-$HOME/.aops/sessions}"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH"

echo "$(date '+%Y-%m-%d %H:%M:%S') repo-sync-cron starting"
"$(dirname "$0")/repo-sync.sh" --quiet 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') repo-sync-cron done"
```

### Example: crontab

```
0 * * * * /home/debian/dotfiles/scripts/repo-sync-cron.sh >> /tmp/repo-sync-cron.log 2>&1
```

Install with:

```bash
crontab -e
# or:
echo '0 * * * * ~/dotfiles/scripts/repo-sync-cron.sh >> /tmp/repo-sync-cron.log 2>&1' | crontab -
```

### Example: post-commit hook

Place at `$ACA_DATA/.githooks/post-commit`:

```bash
#!/usr/bin/env bash
# Auto-push after every commit. Runs in background, never blocks.
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
[ -z "$BRANCH" ] && exit 0
(git push origin "$BRANCH" 2>/dev/null || true) &
```

Then enable custom hooks path:

```bash
cd $ACA_DATA
git config core.hooksPath .githooks
chmod +x .githooks/post-commit
```

## New Machine Checklist

1. Clone all repos
2. Set `export ACA_DATA=/path/to/brain` in shell config
3. Run `git config core.hooksPath .githooks` in `$ACA_DATA`
4. Install aops plugin in Claude Code
5. Install crontab entry
6. Verify: `repos --check`
