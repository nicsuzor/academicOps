#!/usr/bin/env bash
# repo-sync.sh - Check and sync git repositories defined in polecat.yaml
# Usage: repo-sync.sh [--check] [--quiet]
#   (default)  Fix dirty repos with plain git, pull clean repos that are behind
#   --check    Just show status, don't fix anything
#   --quiet    Only show repos needing attention

set -euo pipefail

# Check dependencies
for cmd in git uv; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' is required but not installed." >&2
        exit 1
    fi
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Build repo list from polecat.yaml
POLECAT_YAML="${POLECAT_HOME:-${HOME}/.polecat}/polecat.yaml"
REPOS=()

if [[ -f "$POLECAT_YAML" ]]; then
    # Use uv run python to extract paths from polecat.yaml (requires PyYAML)
    # If PyYAML is missing, it will fail gracefully.
    while IFS= read -r path; do
        # Expand ~ if it exists
        expanded_path="${path/#\~/$HOME}"
        if [[ -d "$expanded_path" ]]; then
            REPOS+=("$expanded_path")
        fi
    done < <(uv run --directory "${AOPS:-$(dirname "$(dirname "$0")")}" python -c "
import yaml, sys
try:
    with open(sys.argv[1]) as f:
        config = yaml.safe_load(f)
        for p in (config or {}).get('projects', {}).values():
            if 'path' in p:
                print(p['path'])
except ImportError:
    print('Error: PyYAML is required. Run: pip install PyYAML', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'Error parsing polecat.yaml: {e}', file=sys.stderr)
    sys.exit(1)
" "$POLECAT_YAML")
else
    echo -e "${YELLOW}Warning: ${POLECAT_YAML} not found.${NC}"
fi

# Always include AOPS_SESSIONS if defined (not in polecat.yaml but needs syncing)
if [[ -n "${AOPS_SESSIONS:-}" ]]; then
    expanded_sessions="${AOPS_SESSIONS/#\~/$HOME}"
    if [[ -d "$expanded_sessions" ]]; then
        REPOS+=("$expanded_sessions")
    fi
fi

if [[ ${#REPOS[@]} -eq 0 ]]; then
    echo -e "${YELLOW}Warning: No repositories configured.${NC}"
    exit 0
fi

# Parse args - default is to fix
FIX=true
QUIET=false
for arg in "$@"; do
    case $arg in
        --check) FIX=false ;;
        --quiet) QUIET=true ;;
    esac
done

# Track repos needing attention
NEEDS_FIX=()

_clear_stale_git_lock() {
    local repo="$1"
    local lockfile="$repo/.git/index.lock"
    [[ ! -f "$lockfile" ]] && return 0

    # If lsof available, check if a process holds the file
    if command -v lsof &>/dev/null; then
        lsof "$lockfile" &>/dev/null
        local lsof_rc=$?
        if [[ "$lsof_rc" -eq 0 ]]; then
            # Process holds the lock — leave it alone
            echo "  $(basename "$repo"): index.lock held by active process"
            return 1
        elif [[ "$lsof_rc" -ne 1 ]]; then
            # lsof error (not "no matches") — don't risk deleting
            echo "  $(basename "$repo"): lsof failed (rc=$lsof_rc), leaving index.lock" >&2
            return 1
        fi
        # lsof_rc == 1: no process holds it, safe to remove
    fi

    # No process holds it — stale lock, remove
    echo "  $(basename "$repo"): removing stale index.lock"
    rm -f "$lockfile"
    return 0
}

_plain_git_sync() {
    local repo="$1"
    local name=$(basename "$repo")
    local auto_commit="${2:-false}"

    cd "$repo"

    # Abort any stuck rebase from a previous failed run
    git rebase --abort 2>/dev/null || true

    # Stage tracked files only (avoid staging secrets/binaries)
    if [[ "$auto_commit" == "true" ]]; then
        git add -u
        if ! git diff --cached --quiet 2>/dev/null; then
            git commit -m "auto: sync $(date '+%Y-%m-%d %H:%M')" --quiet || return 1
        fi
    fi

    # Pull with rebase; on conflict, try auto-resolution then retry
    if ! git pull --rebase --quiet 2>/dev/null; then
        # Check for conflicts that can be auto-resolved
        local unmerged
        unmerged=$(git diff --name-only --diff-filter=U 2>/dev/null || true)
        if [[ -n "$unmerged" ]]; then
            # Try accepting theirs for all conflicting files (safe for auto-generated content)
            local resolved=true
            while IFS= read -r conflict_file; do
                if git checkout --theirs -- "$conflict_file" 2>/dev/null; then
                    git add "$conflict_file" 2>/dev/null
                else
                    resolved=false
                    break
                fi
            done <<< "$unmerged"

            if [[ "$resolved" == "true" ]]; then
                if git rebase --continue 2>/dev/null; then
                    echo -e "  ${YELLOW}$name: auto-resolved conflicts (accepted remote)${NC}"
                else
                    echo -e "${RED}$name: rebase --continue failed after auto-resolve${NC}"
                    git rebase --abort 2>/dev/null || true
                    return 1
                fi
            else
                echo -e "${RED}$name: rebase conflict — needs manual resolution${NC}"
                git rebase --abort 2>/dev/null || true
                return 1
            fi
        else
            echo -e "${RED}$name: rebase failed${NC}"
            git rebase --abort 2>/dev/null || true
            return 1
        fi
    fi

    # Only push if we are auto-committing or if we were clean and ahead
    if [[ "$auto_commit" == "true" ]] || [[ -z $(git status --porcelain 2>/dev/null) ]]; then
        git push --quiet 2>/dev/null || {
            echo -e "${RED}$name: push failed${NC}"
            return 1
        }
    fi
}

check_repo() {
    local repo="$1"
    local name=$(basename "$repo")

    if [[ ! -d "$repo/.git" ]]; then
        [[ "$QUIET" == "false" ]] && echo -e "${RED}$name${NC}: not a git repo"
        return
    fi

    cd "$repo"

    # Clear stale git locks before any operations
    if ! _clear_stale_git_lock "$repo"; then
        [[ "$QUIET" == "false" ]] && echo -e "${YELLOW}$name: git lock present — skipping${NC}"
        return 0
    fi

    # Fetch to check remote state
    [[ "$QUIET" == "false" ]] && echo -ne "  ${name}: fetching... "
    git fetch --quiet 2>/dev/null || true
    [[ "$QUIET" == "false" ]] && echo -ne "  ${name}: checking...  "

    # Get status
    local dirty=""
    local ahead=""
    local behind=""

    # Check for uncommitted changes
    if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
        dirty="dirty"
    fi

    # Check ahead/behind
    local tracking=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "")
    if [[ -n "$tracking" ]]; then
        local counts
        counts=$(git rev-list --left-right --count HEAD...@{u} 2>/dev/null || echo "0	0")
        read -r ahead_count behind_count <<< "$counts"
        [[ "$ahead_count" -gt 0 ]] && ahead="${ahead_count} ahead"
        [[ "$behind_count" -gt 0 ]] && behind="${behind_count} behind"
    fi

    # Decide action
    if [[ -n "$dirty" ]]; then
        # Dirty repo - needs sync
        printf "  %-18s ${YELLOW}%s${NC}" "$name" "dirty"
        [[ -n "$ahead" ]] && printf " ${BLUE}%s${NC}" "$ahead"
        [[ -n "$behind" ]] && printf " ${RED}%s${NC}" "$behind"
        echo ""
        NEEDS_FIX+=("$repo")
    elif [[ -n "$behind" ]]; then
        # Clean but behind - can pull
        if [[ "$FIX" == "true" ]]; then
            printf "  %-18s pulling %s... " "$name" "$behind"
            if git pull --quiet 2>/dev/null; then
                echo -e "${GREEN}done${NC}"
            else
                echo -e "${RED}failed${NC}"
                NEEDS_FIX+=("$repo")
            fi
        else
            printf "  %-18s ${RED}%s${NC}\n" "$name" "$behind"
        fi
    elif [[ -n "$ahead" ]]; then
        # Ahead - push if fixing, otherwise report
        if [[ "$FIX" == "true" ]]; then
            printf "  %-18s pushing %s... " "$name" "$ahead"
            if git push --quiet 2>/dev/null; then
                echo -e "${GREEN}done${NC}"
            else
                echo -e "${RED}failed${NC}"
                NEEDS_FIX+=("$repo")
            fi
        else
            printf "  %-18s ${BLUE}%s${NC} (needs push)\n" "$name" "$ahead"
            NEEDS_FIX+=("$repo")
        fi
    else
        # All good
        if [[ "$QUIET" == "false" ]]; then
            printf "  %-18s ${GREEN}ok${NC}\n" "$name"
        fi
    fi
}

# Main
if [[ "$QUIET" == "false" ]]; then
    echo -e "${BOLD}Checking repos...${NC}"
    echo ""
fi

for repo in "${REPOS[@]}"; do
    check_repo "$repo"
done

if [[ "$QUIET" == "false" ]]; then
    echo ""
fi

# If fixing and there are dirty repos, sync with plain git
if [[ "$FIX" == "true" && ${#NEEDS_FIX[@]} -gt 0 ]]; then
    if [[ "$QUIET" == "false" ]]; then
        echo -e "${BOLD}Repos needing attention:${NC}"
        for repo in "${NEEDS_FIX[@]}"; do
            echo "  - $(basename "$repo")"
        done
        echo ""
        echo -e "${BLUE}Syncing each with plain git...${NC}"
        echo ""
    fi

    # Resolve brain repo path for lint --fix
    brain_path="${ACA_DATA:-$HOME/brain}"
    brain_path="$(cd "$brain_path" 2>/dev/null && pwd || echo "")"

    for repo in "${NEEDS_FIX[@]}"; do
        name=$(basename "$repo")
        [[ "$QUIET" == "false" ]] && echo -e "${BOLD}=== $name ===${NC}"

        # Resolve brain repo path for lint --fix and auto-commit decision
        repo_realpath="$(cd "$repo" && pwd -P)"
        auto_commit=false
        if [[ "$repo_realpath" == "$brain_path" ]]; then
            auto_commit=true
            aops_bin="/opt/debian/lib/cargo/bin/aops"
            [[ ! -x "$aops_bin" ]] && aops_bin="${CARGO_HOME:-$HOME/.cargo}/bin/aops"
            [[ ! -x "$aops_bin" ]] && aops_bin="$(command -v aops 2>/dev/null || true)"
            if [[ -n "$aops_bin" && -x "$aops_bin" ]]; then
                [[ "$QUIET" == "false" ]] && echo "  Running aops lint --fix..."
                "$aops_bin" lint --fix 2>/dev/null || true
            fi
        fi

        # Sync with plain git (no Claude session spawned)
        _plain_git_sync "$repo" "$auto_commit" || {
            echo -e "${RED}sync failed for $name${NC}"
        }
        [[ "$QUIET" == "false" ]] && echo ""
    done

    [[ "$QUIET" == "false" ]] && echo -e "${GREEN}Done!${NC}"
elif [[ ${#NEEDS_FIX[@]} -gt 0 ]]; then
    echo -e "${YELLOW}${#NEEDS_FIX[@]} repo(s) need attention.${NC} Run with --fix to resolve."
else
    [[ "$QUIET" == "false" ]] && echo -e "${GREEN}All repos in sync!${NC}"
fi
