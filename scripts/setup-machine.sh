#!/bin/bash
# setup-machine.sh - Set up a new machine for academicOps
#
# Configures:
#   - ACA_DATA git hooks path
#   - Crontab for periodic sync + viz generation
#   - Polecat project config (local paths from master registry)
#   - CLI tools (pkb) from GitHub releases
#   - Claude Code plugins from marketplace
#   - Validates required environment variables and tools
#
# Usage:
#   ./scripts/setup-machine.sh          # Release install (from GitHub)
#   ./scripts/setup-machine.sh --check  # Validate only, don't change anything
#
# For development installs (local build), use: make install-dev

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

AOPS="${AOPS:-$(cd "$(dirname "$0")/.." && pwd)}"
AOPS_SESSIONS="${AOPS_SESSIONS:-${POLECAT_HOME:-${HOME}/.polecat}/sessions}"
MASTER_REGISTRY="${AOPS_SESSIONS}/polecat.yaml"

echo -e "${BOLD}academicOps machine setup${NC}"
echo ""

# --- 1. Check required environment variables ---
echo -e "${BOLD}Environment:${NC}"

if [[ -n "${ACA_DATA:-}" ]]; then
    ok "ACA_DATA=${ACA_DATA}"
else
    fail "ACA_DATA not set. Add 'export ACA_DATA=/path/to/brain' to your shell config."
fi

ok "AOPS=${AOPS}"
ok "AOPS_SESSIONS=${AOPS_SESSIONS}"

# --- 2. Check required tools ---
echo ""
echo -e "${BOLD}Tools:${NC}"

for cmd in git uv; do
    if command -v "$cmd" &>/dev/null; then
        ok "$cmd ($(command -v "$cmd"))"
    else
        fail "$cmd not found on PATH"
    fi
done

# Optional tools (warn only)
for cmd in claude pkb; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>/dev/null | head -1 || echo "unknown")
        ok "$cmd ($version)"
    else
        warn "$cmd not found (will attempt install)"
    fi
done

# --- 3. Install CLI tools (pkb) ---
echo ""
echo -e "${BOLD}CLI tools (pkb):${NC}"

INSTALL_BIN="${USER_OPT:+${USER_OPT}/bin}"
INSTALL_BIN="${INSTALL_BIN:-${HOME}/.local/bin}"

# Detect platform
PLATFORM=""
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)   PLATFORM="linux-x86_64" ;;
    Darwin-arm64)   PLATFORM="macos-aarch64" ;;
esac

if [[ "$CHECK_ONLY" == true ]]; then
    if command -v pkb &>/dev/null; then
        ok "pkb installed ($(pkb --version 2>/dev/null || echo 'unknown'))"
    else
        fail "pkb not installed. Run: make install-cli"
    fi
else
    if [[ -z "$PLATFORM" ]]; then
        fail "Cannot detect platform ($(uname -s)-$(uname -m)). Install manually: make install-cli PLATFORM=..."
    elif ! command -v gh &>/dev/null; then
        fail "gh (GitHub CLI) not found. Install it first, or use: make install-cli-dev"
    else
        echo -n "  Downloading pkb for ${PLATFORM}... "
        TMPDIR=$(mktemp -d)
        ARCHIVE="aops-claude-${PLATFORM}.tar.gz"
        if gh release download --repo nicsuzor/academicOps --pattern "${ARCHIVE}" --dir "${TMPDIR}" --clobber 2>/dev/null; then
            mkdir -p "${INSTALL_BIN}"
            tar xzf "${TMPDIR}/${ARCHIVE}" -C "${TMPDIR}"
            # Find and install binaries (may be at bin/ or aops-claude/bin/)
            for bin_name in pkb; do
                src=$(find "${TMPDIR}" -name "${bin_name}" -type f | head -1)
                if [[ -n "$src" ]]; then
                    cp "$src" "${INSTALL_BIN}/${bin_name}"
                    chmod +x "${INSTALL_BIN}/${bin_name}"
                fi
            done
            rm -rf "${TMPDIR}"
            echo -e "${GREEN}done${NC}"
            ok "Installed to ${INSTALL_BIN}"
            # Check PATH
            case ":${PATH}:" in
                *":${INSTALL_BIN}:"*) ;;
                *) warn "${INSTALL_BIN} is not on PATH. Add it to your shell config." ;;
            esac
        else
            rm -rf "${TMPDIR}"
            echo -e "${RED}failed${NC}"
            fail "Download failed. Check gh auth status or use: make install-cli-dev"
        fi
    fi
fi

# --- 4. Install Claude Code plugins ---
echo ""
echo -e "${BOLD}Claude Code plugins:${NC}"

if command -v claude &>/dev/null; then
    if [[ "$CHECK_ONLY" == true ]]; then
        if claude plugin list 2>/dev/null | grep -q "aops-core"; then
            ok "aops-core plugin installed"
        else
            fail "aops-core plugin not installed. Run: make install-claude"
        fi
    else
        echo -n "  Registering plugins... "
        if claude plugin marketplace add nicsuzor/academicOps 2>&1 | sed 's/^/    /' && \
           claude plugin marketplace update academicOps 2>&1 | sed 's/^/    /' && \
           claude plugin install aops-core@academicOps 2>&1 | sed 's/^/    /'; then
            ok "aops-core plugin installed"
        else
            fail "Plugin installation failed. Try: make install-claude"
        fi
    fi
else
    warn "Claude Code not installed. Skipping plugin setup."
fi

# --- 5. Check ACA_DATA git config ---
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

    for hook in post-commit; do
        if [[ -x "${ACA_DATA}/.githooks/${hook}" ]]; then
            ok "${hook} hook exists and is executable"
        else
            fail "${hook} hook missing or not executable at ${ACA_DATA}/.githooks/${hook}"
        fi
    done

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

# --- 6. Check AOPS_SESSIONS ---
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

# --- 7. Verify project registry resolves on this machine ---
echo ""
echo -e "${BOLD}Project registry:${NC}"

if [[ ! -f "${MASTER_REGISTRY}" ]]; then
    fail "Project registry not found at ${MASTER_REGISTRY}"
    echo "  Pull AOPS_SESSIONS first: cd ${AOPS_SESSIONS} && git pull"
else
    ok "Registry: ${MASTER_REGISTRY}"

    LOCAL_OVERLAY="${POLECAT_HOME:-${HOME}/.polecat}/local.yaml"
    if [[ -f "${LOCAL_OVERLAY}" ]]; then
        ok "Local overlay: ${LOCAL_OVERLAY}"
    fi

    # Walk the registry; fail loud with the local.yaml block needed for any unresolved slug.
    AOPS="$AOPS" AOPS_SESSIONS="$AOPS_SESSIONS" \
    POLECAT_HOME="${POLECAT_HOME:-}" AOPS_SRC_DIR="${AOPS_SRC_DIR:-}" \
        uv run python - <<'PYEOF'
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ['AOPS'] + '/polecat')
from manager import load_config, resolve_project_path, get_local_overlay_path

config = load_config()
projects = config.get('projects', {}) or {}

resolved = {}
missing = {}
for slug, info in projects.items():
    repo = (info or {}).get('repo', slug)
    path = resolve_project_path(slug, repo)
    if path is None:
        missing[slug] = repo
    else:
        resolved[slug] = path

print(f'  Resolved {len(resolved)} project(s): {sorted(resolved)}')
if missing:
    print(f'  Unresolved {len(missing)} project(s): {sorted(missing)}')
    print(f'  Add to {get_local_overlay_path()}:')
    print('    paths:')
    for slug, repo in sorted(missing.items()):
        print(f'      {slug}: /absolute/path/to/{repo}')
    sys.exit(1)
PYEOF
    if [[ $? -ne 0 ]]; then
        fail "One or more projects could not be resolved"
    else
        ok "All projects resolved"
    fi
fi

# --- 7b. Verify ~/.env.local sets minimum env ---
echo ""
echo -e "${BOLD}env.local:${NC}"
if [[ -f "${HOME}/.env.local" ]]; then
    ok "${HOME}/.env.local exists"
    if grep -q '^export AOPS_SESSIONS=' "${HOME}/.env.local"; then
        ok "AOPS_SESSIONS exported"
    else
        warn "${HOME}/.env.local does not export AOPS_SESSIONS"
    fi
    if grep -q '^export AOPS_SRC_DIR=' "${HOME}/.env.local"; then
        ok "AOPS_SRC_DIR exported"
    else
        warn "${HOME}/.env.local does not export AOPS_SRC_DIR (default: ~/src)"
    fi
else
    warn "${HOME}/.env.local does not exist"
fi

# --- 8. Crontab ---
echo ""
echo -e "${BOLD}Crontab:${NC}"

CRON_SCRIPT="${AOPS}/scripts/repo-sync-cron.sh"
CRON_ENTRY="*/5 * * * * ${CRON_SCRIPT} >> /tmp/repo-sync-cron.log 2>&1"

if crontab -l 2>/dev/null | grep -q "repo-sync-cron"; then
    ok "repo-sync-cron already in crontab"
    if [[ "$CHECK_ONLY" != true ]]; then
        # Reinstall to ensure entry is up to date
        echo -n "  Updating crontab entry... "
        (crontab -l 2>/dev/null | grep -v "repo-sync-cron" | grep -v "# aOps"; echo "# aOps sync (transcript + repo sync every 5 min)"; echo "${CRON_ENTRY}") | crontab -
        echo -e "${GREEN}done${NC}"
    fi
else
    if [[ "$CHECK_ONLY" == true ]]; then
        fail "repo-sync-cron not in crontab"
    else
        if [[ -x "${CRON_SCRIPT}" ]]; then
            echo -n "  Installing crontab entry... "
            # Preserve existing crontab entries
            (crontab -l 2>/dev/null || true; echo "# aOps sync (transcript + repo sync every 5 min)"; echo "${CRON_ENTRY}") | crontab -
            echo -e "${GREEN}done${NC}"
        else
            fail "Cron script not found at ${CRON_SCRIPT}"
            echo "  Make sure you are running from the academicOps repository."
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
