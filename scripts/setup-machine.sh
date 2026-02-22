#!/bin/bash
# setup-machine.sh - Set up a new machine for academicOps
#
# Configures:
#   - ACA_DATA git hooks path
#   - Crontab for periodic sync + viz generation
#   - Polecat project config (local paths from master registry)
#   - Rust CLI tools (aops, pkb)
#   - Claude Code plugins and MCP servers
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

# --- 3. Install Rust CLI tools ---
echo ""
echo -e "${BOLD}Rust CLI tools:${NC}"

MEM_REPO="${HOME}/src/mem"
if [[ ! -d "$MEM_REPO" ]]; then
    # Try common locations
    for candidate in /opt/nic/mem /opt/*/mem; do
        if [[ -d "$candidate/Cargo.toml" ]] || [[ -d "$candidate" && -f "$candidate/Cargo.toml" ]]; then
            MEM_REPO="$candidate"
            break
        fi
    done
fi

if [[ -f "${MEM_REPO}/Cargo.toml" ]]; then
    if [[ "$CHECK_ONLY" == true ]]; then
        if command -v aops &>/dev/null; then
            ok "aops installed ($(aops --version 2>/dev/null || echo 'unknown'))"
        else
            fail "aops not installed. Run: cargo install --path ${MEM_REPO}"
        fi
    else
        echo -n "  Installing aops + pkb from ${MEM_REPO}... "
        if cargo install --path "${MEM_REPO}" --quiet 2>/dev/null; then
            echo -e "${GREEN}done${NC}"
        else
            echo -e "${RED}failed${NC}"
            fail "cargo install --path ${MEM_REPO} failed"
        fi
    fi
else
    warn "mem repo not found (checked ${MEM_REPO}). Clone it to install aops/pkb."
fi

# --- 4. Install Claude Code plugins ---
echo ""
echo -e "${BOLD}Claude Code plugins:${NC}"

if command -v claude &>/dev/null; then
    DOTFILES_SETUP="${HOME}/dotfiles/scripts/setup-ai-tools.sh"
    if [[ -x "${DOTFILES_SETUP}" ]]; then
        if [[ "$CHECK_ONLY" == true ]]; then
            ok "setup-ai-tools.sh available at ${DOTFILES_SETUP}"
        else
            echo "  Running setup-ai-tools.sh..."
            bash "${DOTFILES_SETUP}" 2>&1 | sed 's/^/    /'
        fi
    else
        warn "setup-ai-tools.sh not found at ${DOTFILES_SETUP}"
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
