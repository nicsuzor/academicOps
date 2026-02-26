#!/bin/bash
# setup-machine.sh - Set up a new machine for academicOps
#
# Configures:
#   - ACA_DATA git hooks path
#   - Crontab for periodic sync + viz generation
#   - Polecat project config (local paths from master registry)
#   - CLI tools (aops, pkb) from GitHub releases
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
AOPS_SESSIONS="${AOPS_SESSIONS:-${HOME}/.aops/sessions}"
MASTER_REGISTRY="${AOPS_SESSIONS}/projects.yaml"

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
for cmd in claude aops; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>/dev/null | head -1 || echo "unknown")
        ok "$cmd ($version)"
    else
        warn "$cmd not found (will attempt install)"
    fi
done

# --- 3. Install CLI tools (aops + pkb) ---
echo ""
echo -e "${BOLD}CLI tools (aops + pkb):${NC}"

INSTALL_BIN="${USER_OPT:+${USER_OPT}/bin}"
INSTALL_BIN="${INSTALL_BIN:-${HOME}/.local/bin}"

# Detect platform
PLATFORM=""
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)   PLATFORM="linux-x86_64" ;;
    Darwin-arm64)   PLATFORM="macos-aarch64" ;;
esac

if [[ "$CHECK_ONLY" == true ]]; then
    if command -v aops &>/dev/null; then
        ok "aops installed ($(aops --version 2>/dev/null || echo 'unknown'))"
    else
        fail "aops not installed. Run: make install-cli"
    fi
    if command -v pkb &>/dev/null; then
        ok "pkb installed"
    else
        fail "pkb not installed. Run: make install-cli"
    fi
else
    if [[ -z "$PLATFORM" ]]; then
        fail "Cannot detect platform ($(uname -s)-$(uname -m)). Install manually: make install-cli PLATFORM=..."
    elif ! command -v gh &>/dev/null; then
        fail "gh (GitHub CLI) not found. Install it first, or use: make install-cli-dev"
    else
        echo -n "  Downloading aops + pkb for ${PLATFORM}... "
        TMPDIR=$(mktemp -d)
        ARCHIVE="aops-claude-${PLATFORM}.tar.gz"
        if gh release download --repo nicsuzor/aops-dist --pattern "${ARCHIVE}" --dir "${TMPDIR}" --clobber 2>/dev/null; then
            mkdir -p "${INSTALL_BIN}"
            tar xzf "${TMPDIR}/${ARCHIVE}" -C "${TMPDIR}"
            # Find and install binaries (may be at bin/ or aops-claude/bin/)
            for bin_name in aops pkb; do
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
        echo "  Installing aops plugin from marketplace..."
        if claude plugin marketplace add nicsuzor/aops-dist 2>&1 | sed 's/^/    /' && \
           claude plugin marketplace update aops 2>&1 | sed 's/^/    /' && \
           claude plugin install aops-core@aops 2>&1 | sed 's/^/    /'; then
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

# --- 7. Generate polecat.yaml from master registry ---
echo ""
echo -e "${BOLD}Polecat config:${NC}"

POLECAT_YAML="${HOME}/.aops/polecat.yaml"

if [[ ! -f "${MASTER_REGISTRY}" ]]; then
    fail "Master project registry not found at ${MASTER_REGISTRY}"
    echo "  Pull AOPS_SESSIONS first: cd ${AOPS_SESSIONS} && git pull"
else
    ok "Master registry: ${MASTER_REGISTRY}"

    if [[ "$CHECK_ONLY" == true ]]; then
        if [[ -f "${POLECAT_YAML}" ]]; then
            ok "polecat.yaml exists"
        else
            fail "polecat.yaml not found at ${POLECAT_YAML}"
        fi
    else
        echo "  Generating ${POLECAT_YAML} from master registry..."
        mkdir -p "$(dirname "${POLECAT_YAML}")"

        # Parse master registry and discover local paths
        python3 -c "
import yaml
from pathlib import Path
import os

master = '$MASTER_REGISTRY'
output = '$POLECAT_YAML'

with open(master) as f:
    registry = yaml.safe_load(f)

projects = registry.get('projects', {})

# Common locations to search for repos
search_dirs = [
    Path.home() / 'src',
    Path.home(),
    Path('/opt/nic'),
    Path('/opt') / os.environ.get('USER', 'user'),
]

# Also check ACA_DATA for brain
aca_data = os.environ.get('ACA_DATA', '')

found = {}
missing = []

for abbrev, info in projects.items():
    repo_name = info.get('repo', abbrev)
    default_branch = info.get('default_branch', 'main')

    # Special case: brain is ACA_DATA
    if abbrev == 'brain' and aca_data:
        path = Path(aca_data)
        if path.exists():
            found[abbrev] = {'path': str(path), 'default_branch': default_branch}
            continue

    # Search common locations
    located = False
    for search_dir in search_dirs:
        candidate = search_dir / repo_name
        if candidate.exists() and (candidate / '.git').exists():
            found[abbrev] = {'path': str(candidate), 'default_branch': default_branch}
            located = True
            break

    if not located:
        missing.append((abbrev, repo_name))

# Write polecat.yaml
config = {'projects': {}}
for abbrev, info in found.items():
    config['projects'][abbrev] = {
        'path': info['path'],
        'default_branch': info['default_branch'],
    }

with open(output, 'w') as f:
    f.write('# Local polecat config - machine-specific paths\n')
    f.write('# Auto-generated by setup-machine.sh from projects.yaml\n')
    f.write('# Do NOT commit this file\n\n')
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print(f'  Found {len(found)} projects: {list(found.keys())}')
if missing:
    print(f'  Missing {len(missing)} projects: {[m[1] for m in missing]}')
    print(f'  (Clone them and re-run setup to add)')
"
        ok "polecat.yaml generated"
    fi
fi

# --- 8. Crontab ---
echo ""
echo -e "${BOLD}Crontab:${NC}"

QUICK_CRON_SCRIPT="${AOPS}/scripts/repo-sync-cron.sh"
QUICK_CRON_ENTRY="*/5 * * * * ${QUICK_CRON_SCRIPT} --quick >> /tmp/repo-sync-quick.log 2>&1"
FULL_CRON_ENTRY="0 * * * * ${QUICK_CRON_SCRIPT} >> /tmp/repo-sync-cron.log 2>&1"

if crontab -l 2>/dev/null | grep -q "repo-sync-cron"; then
    ok "repo-sync-cron already in crontab"
else
    if [[ "$CHECK_ONLY" == true ]]; then
        fail "repo-sync-cron not in crontab"
    else
        if [[ -x "${QUICK_CRON_SCRIPT}" ]]; then
            echo -n "  Installing crontab entries... "
            # Preserve existing crontab entries
            (crontab -l 2>/dev/null || true; echo "# aOps quick sync"; echo "${QUICK_CRON_ENTRY}"; echo "# aOps full maintenance"; echo "${FULL_CRON_ENTRY}") | crontab -
            echo -e "${GREEN}done${NC}"
        else
            fail "Cron script not found at ${QUICK_CRON_SCRIPT}"
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
