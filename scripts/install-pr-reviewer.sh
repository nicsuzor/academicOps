#!/usr/bin/env bash
# install-pr-reviewer.sh
#
# Install the PR reviewer bot into a target GitHub repository.
#
# The bot reviews PRs against framework axioms, reads repo-local rules
# (.agents/CORE.md), pushes fixes, and leaves review comments.
#
# USAGE
#   ./install-pr-reviewer.sh <target-repo-path>
#
# EXAMPLE
#   ./install-pr-reviewer.sh ~/src/mem
#
# PREREQUISITES
#   - Target repo must have GitHub Actions enabled
#   - Two secrets must be set in the target repo:
#       gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo <owner/repo>
#       gh secret set AOPS_BOT_GH_TOKEN --repo <owner/repo>
#
# WHAT GETS INSTALLED
#   .github/agents/pr-reviewer.agent.md  — axiom-driven review agent prompt
#   .github/workflows/pr-review.yml      — GitHub Actions workflow (manual + callable)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AOPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

AGENT_SRC="$AOPS_DIR/.github/agents/pr-reviewer.agent.md"
WORKFLOW_SRC="$AOPS_DIR/.github/workflows/pr-review.yml"

TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
    echo "Usage: $0 <target-repo-path>" >&2
    echo "Example: $0 ~/src/mem" >&2
    exit 1
fi

if [[ ! -d "$TARGET/.git" ]]; then
    echo "Error: $TARGET is not a git repository" >&2
    exit 1
fi

echo "Installing PR reviewer bot into: $TARGET"
echo ""

# Create target directories
mkdir -p "$TARGET/.github/agents"
mkdir -p "$TARGET/.github/workflows"

# Install agent prompt
dst_agent="$TARGET/.github/agents/pr-reviewer.agent.md"
SHARED_ERR="$AOPS_DIR/.github/agents/shared-error-handling.md"

if [[ ! -f "$AGENT_SRC" ]]; then
    echo "Error: source agent not found: $AGENT_SRC" >&2
    exit 1
fi
if [[ ! -f "$SHARED_ERR" ]]; then
    echo "Error: shared error handling file not found: $SHARED_ERR" >&2
    exit 1
fi

if [[ -f "$dst_agent" ]]; then
    echo "  [UPDATE]  .github/agents/pr-reviewer.agent.md"
else
    echo "  [INSTALL] .github/agents/pr-reviewer.agent.md"
fi
{ cat "$SHARED_ERR"; echo ""; cat "$AGENT_SRC"; } > "$dst_agent"

# Install workflow
dst_workflow="$TARGET/.github/workflows/pr-review.yml"
if [[ ! -f "$WORKFLOW_SRC" ]]; then
    echo "Error: source workflow not found: $WORKFLOW_SRC" >&2
    exit 1
fi
if [[ -f "$dst_workflow" ]]; then
    echo "  [UPDATE]  .github/workflows/pr-review.yml"
else
    echo "  [INSTALL] .github/workflows/pr-review.yml"
fi
cp "$WORKFLOW_SRC" "$dst_workflow"

# Resolve target repo slug (owner/repo) for secret operations
REPO_SLUG=$(cd "$TARGET" && gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || true)

# Set secrets from environment if available
if [[ -n "$REPO_SLUG" ]]; then
    echo ""
    echo "Configuring secrets for $REPO_SLUG..."

    EXISTING=$(gh secret list --repo "$REPO_SLUG" --json name -q '.[].name' 2>/dev/null || true)

    if echo "$EXISTING" | grep -q 'AOPS_BOT_GH_TOKEN'; then
        echo "  [OK]      AOPS_BOT_GH_TOKEN already set"
    elif [[ -n "${AOPS_BOT_GH_TOKEN:-}" ]]; then
        echo "$AOPS_BOT_GH_TOKEN" | gh secret set AOPS_BOT_GH_TOKEN --repo "$REPO_SLUG"
        echo "  [SECRET]  AOPS_BOT_GH_TOKEN set from environment"
    else
        echo "  [SKIP]    AOPS_BOT_GH_TOKEN not in environment — set manually:"
        echo "              gh secret set AOPS_BOT_GH_TOKEN --repo $REPO_SLUG"
    fi

    if echo "$EXISTING" | grep -q 'CLAUDE_CODE_OAUTH_TOKEN'; then
        echo "  [OK]      CLAUDE_CODE_OAUTH_TOKEN already set"
    elif [[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
        echo "$CLAUDE_CODE_OAUTH_TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo "$REPO_SLUG"
        echo "  [SECRET]  CLAUDE_CODE_OAUTH_TOKEN set from environment"
    else
        echo "  [SKIP]    CLAUDE_CODE_OAUTH_TOKEN not set — add manually:"
        echo "              gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo $REPO_SLUG"
    fi
else
    echo ""
    echo "  [WARN]    Could not resolve repo slug — set secrets manually"
fi

echo ""
echo "Done. Next steps:"
echo ""
echo "  1. Commit the installed files:"
echo "       cd $TARGET"
echo "       git add .github/agents/pr-reviewer.agent.md \\"
echo "               .github/workflows/pr-review.yml"
echo "       git commit -m 'ci: add PR reviewer bot (axiom-driven review agent)'"
echo ""
echo "  2. Push and trigger manually:"
echo "       git push"
echo "       gh workflow run 'Agent: PR Review' --repo ${REPO_SLUG:-<owner/repo>}"
echo ""
echo "  3. Optional: add .agents/CORE.md to your repo with local review rules."
echo ""
