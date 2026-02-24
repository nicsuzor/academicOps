#!/usr/bin/env bash
# repo_sync.sh - Check and sync git repositories defined in polecat.yaml
# Usage: repo_sync.sh [--check] [--quiet]
#   (default)  Fix dirty repos with ccommit, pull clean repos that are behind
#   --check    Just show status, don't fix anything
#   --quiet    Only show repos needing attention

set -euo pipefail

# Check dependencies
for cmd in git yq; do
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
POLECAT_YAML="${HOME}/.aops/polecat.yaml"
REPOS=()

if [[ -f "$POLECAT_YAML" ]]; then
    # Use yq to extract paths from polecat.yaml
    while IFS= read -r path; do
        # Expand ~ if it exists
        expanded_path="${path/#\~/$HOME}"
        if [[ -d "$expanded_path" ]]; then
            REPOS+=("$expanded_path")
        fi
    done < <(yq -r '.projects[].path' "$POLECAT_YAML")
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

check_repo() {
    local repo="$1"
    local name=$(basename "$repo")

    if [[ ! -d "$repo/.git" ]]; then
        [[ "$QUIET" == "false" ]] && echo -e "${RED}$name${NC}: not a git repo"
        return
    fi

    cd "$repo"

    # Fetch to check remote state
    [[ "$QUIET" == "false" ]] && echo -ne "  ${name}: fetching... "
    git fetch --quiet 2>/dev/null || true
    [[ "$QUIET" == "false" ]] && echo -ne "  ${name}: checking...  "

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
        local counts=$(git rev-list --left-right --count HEAD...@{u} 2>/dev/null || echo "0 0")
        local ahead_count=${counts%% *}
        local behind_count=${counts##* }
        [[ "$ahead_count" -gt 0 ]] && ahead="${ahead_count} ahead"
        [[ "$behind_count" -gt 0 ]] && behind="${behind_count} behind"
    fi

    # Decide action
    if [[ -n "$dirty" ]]; then
        # Dirty repo - needs ccommit
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
        # Ahead - needs push
        printf "  %-18s ${BLUE}%s${NC} (needs push)\n" "$name" "$ahead"
        NEEDS_FIX+=("$repo")
    else
        # All good
        [[ "$QUIET" == "false" ]] && printf "  %-18s ${GREEN}ok${NC}\n" "$name"
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

# If fixing and there are dirty repos, offer to run ccommit
if [[ "$FIX" == "true" && ${#NEEDS_FIX[@]} -gt 0 ]]; then
    if [[ "$QUIET" == "false" ]]; then
        echo -e "${BOLD}Repos needing attention:${NC}"
        for repo in "${NEEDS_FIX[@]}"; do
            echo "  - $(basename "$repo")"
        done
        echo ""
        echo -e "${BLUE}Running ccommit on each...${NC}"
        echo "(Claude will commit, pull, resolve conflicts, and push)"
        echo ""
    fi

    for repo in "${NEEDS_FIX[@]}"; do
        name=$(basename "$repo")
        [[ "$QUIET" == "false" ]] && echo -e "${BOLD}=== $name ===${NC}"
        cd "$repo"
        # Run ccommit (the claude alias)
        # Note: using 'claude' directly might depend on aliases.
        # In this environment, we should check if 'claude' or 'aops ccommit' is preferred.
        # The original script used 'claude'.
        claude --dangerously-skip-permissions -p "commit changed and new files, pull, fix conflicts, push" || {
            echo -e "${RED}ccommit failed for $name${NC}"
        }
        [[ "$QUIET" == "false" ]] && echo ""
    done

    [[ "$QUIET" == "false" ]] && echo -e "${GREEN}Done!${NC}"
elif [[ ${#NEEDS_FIX[@]} -gt 0 ]]; then
    echo -e "${YELLOW}${#NEEDS_FIX[@]} repo(s) need attention.${NC} Run with --fix to resolve."
else
    [[ "$QUIET" == "false" ]] && echo -e "${GREEN}All repos in sync!${NC}"
fi
