#!/bin/bash
# setup-machine.sh - Set up a new machine for academicOps
#
# Configures:
#   - ACA_DATA git hooks path
#   - Crontab for periodic sync + viz generation
#   - Validates required environment variables and tools
#
# Usage:
#   ./scripts/setup-machine.sh          # Interactive setup
#   ./scripts/setup-machine.sh --check  # Validate only, don't change anything

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

CHECK_ONLY=false
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=true

ERRORS=0

ok()   { echo -e "  ${GREEN}ok${NC}    $1"; }
warn() { echo -e "  ${YELLOW}warn${NC}  $1"; }
fail() { echo -e "  ${RED}FAIL${NC}  $1"; ERRORS=$((ERRORS + 1)); }

echo -e "${BOLD}academicOps machine setup${NC}"
echo ""

# --- 1. Check required environment variables ---
echo -e "${BOLD}Environment:${NC}"

if [[ -n "${ACA_DATA:-}" ]]; then
    ok "ACA_DATA=${ACA_DATA}"
else
    fail "ACA_DATA not set. Add 'export ACA_DATA=/path/to/brain' to your shell config."
fi

if [[ -n "${AOPS:-}" ]]; then
    ok "AOPS=${AOPS}"
else
    warn "AOPS not set (will default to /opt/nic/academicOps in scripts)"
fi

AOPS_SESSIONS="${AOPS_SESSIONS:-${HOME}/.aops/sessions}"
ok "AOPS_SESSIONS=${AOPS_SESSIONS}"

# --- 2. Check required tools ---
echo ""
echo -e "${BOLD}Tools:${NC}"

for cmd in git claude aops uv; do
    if command -v "$cmd" &>/dev/null; then
        ok "$cmd ($(command -v "$cmd"))"
    else
        fail "$cmd not found on PATH"
    fi
done

# --- 3. Check ACA_DATA git config ---
echo ""
echo -e "${BOLD}ACA_DATA git config:${NC}"

if [[ -n "${ACA_DATA:-}" && -d "${ACA_DATA}/.git" ]]; then
    hooks_path=$(git -C "${ACA_DATA}" config core.hooksPath 2>/dev/null || echo "")
    if [[ "$hooks_path" == ".githooks" ]]; then
        ok "core.hooksPath = .githooks"
    else
        if [[ "$CHECK_ONLY" == true ]]; then
            fail "core.hooksPath not set to .githooks (currently: '${hooks_path:-default}')"
        else
            echo -n "  Setting core.hooksPath = .githooks... "
            git -C "${ACA_DATA}" config core.hooksPath .githooks
            echo -e "${GREEN}done${NC}"
        fi
    fi

    if [[ -x "${ACA_DATA}/.githooks/post-commit" ]]; then
        ok "post-commit hook exists and is executable"
    else
        fail "post-commit hook missing or not executable at ${ACA_DATA}/.githooks/post-commit"
    fi

    # Check remote
    remote=$(git -C "${ACA_DATA}" remote get-url origin 2>/dev/null || echo "")
    if [[ -n "$remote" ]]; then
        ok "origin remote: ${remote}"
    else
        fail "No origin remote configured"
    fi
else
    if [[ -n "${ACA_DATA:-}" ]]; then
        fail "${ACA_DATA} is not a git repo"
    fi
fi

# --- 4. Check AOPS_SESSIONS ---
echo ""
echo -e "${BOLD}AOPS_SESSIONS:${NC}"

if [[ -d "${AOPS_SESSIONS}/.git" ]]; then
    ok "AOPS_SESSIONS is a git repo"
    remote=$(git -C "${AOPS_SESSIONS}" remote get-url origin 2>/dev/null || echo "")
    if [[ -n "$remote" ]]; then
        ok "origin remote: ${remote}"
    else
        warn "No origin remote (sessions won't sync across machines)"
    fi
else
    warn "AOPS_SESSIONS is not a git repo (viz/transcripts won't sync)"
fi

# --- 5. Crontab ---
echo ""
echo -e "${BOLD}Crontab:${NC}"

CRON_SCRIPT="${HOME}/dotfiles/scripts/repo-sync-cron.sh"
CRON_ENTRY="*/30 * * * * ${CRON_SCRIPT} >> /tmp/repo-sync-cron.log 2>&1"

if crontab -l 2>/dev/null | grep -q "repo-sync-cron"; then
    ok "repo-sync-cron already in crontab"
else
    if [[ "$CHECK_ONLY" == true ]]; then
        fail "repo-sync-cron not in crontab"
    else
        if [[ -x "${CRON_SCRIPT}" ]]; then
            echo -n "  Installing crontab entry... "
            # Preserve existing crontab entries
            (crontab -l 2>/dev/null || true; echo "${CRON_ENTRY}") | crontab -
            echo -e "${GREEN}done${NC}"
        else
            fail "Cron script not found at ${CRON_SCRIPT}"
            echo "  Copy repo-sync-cron.sh from academicOps docs or dotfiles."
        fi
    fi
fi

# --- Summary ---
echo ""
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}All checks passed!${NC}"
else
    echo -e "${RED}${BOLD}${ERRORS} issue(s) found.${NC}"
    [[ "$CHECK_ONLY" == true ]] && echo "Run without --check to fix automatically."
fi
