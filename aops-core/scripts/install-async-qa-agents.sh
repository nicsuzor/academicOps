#!/usr/bin/env bash
# install-async-qa-agents.sh
#
# Install the async QA review agents (hydrator-reviewer + custodiet-reviewer)
# into a target GitHub repository.
#
# These agents post advisory comments on PRs:
#   - hydrator-reviewer: identifies applicable workflows and quality gates
#   - custodiet-reviewer: detects scope drift and principle violations
#
# USAGE
#   ./install-async-qa-agents.sh <target-repo-path>
#
# EXAMPLE
#   ./install-async-qa-agents.sh ~/src/my-project
#
# PREREQUISITES
#   - Target repo must already have GitHub Actions enabled
#   - CLAUDE_CODE_OAUTH_TOKEN secret must be set in the target repo:
#       gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo <owner/repo>
#
# WHAT GETS INSTALLED
#   .github/agents/hydrator-reviewer.md   — workflow guidance agent prompt
#   .github/agents/custodiet-reviewer.md  — compliance reviewer agent prompt
#   .github/workflows/async-qa-review.yml — GitHub Actions trigger workflow
#
# INVOCATION (local, once installed)
#   Task(subagent_type='aops-core:hydrator-reviewer', prompt='PR #42 in owner/repo')
#   Task(subagent_type='aops-core:custodiet-reviewer', prompt='PR #42 in owner/repo')

set -euo pipefail

AOPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AGENTS_SRC="$AOPS_DIR/.github/agents"
WORKFLOW_SRC="$AOPS_DIR/.github/workflows/async-qa-review.yml"

TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
    echo "Usage: $0 <target-repo-path>" >&2
    echo "Example: $0 ~/src/my-project" >&2
    exit 1
fi

if [[ ! -d "$TARGET/.git" ]]; then
    echo "Error: $TARGET is not a git repository" >&2
    exit 1
fi

echo "Installing async QA agents into: $TARGET"
echo ""

# Create target directories
mkdir -p "$TARGET/.github/agents"
mkdir -p "$TARGET/.github/workflows"

# Install agent prompts
for agent in hydrator-reviewer custodiet-reviewer; do
    src="$AGENTS_SRC/$agent.md"
    dst="$TARGET/.github/agents/$agent.md"
    if [[ ! -f "$src" ]]; then
        echo "Error: source agent not found: $src" >&2
        exit 1
    fi
    if [[ -f "$dst" ]]; then
        echo "  [SKIP]    .github/agents/$agent.md (already exists)"
    else
        cp "$src" "$dst"
        echo "  [INSTALL] .github/agents/$agent.md"
    fi
done

# Install workflow
dst_workflow="$TARGET/.github/workflows/async-qa-review.yml"
if [[ -f "$dst_workflow" ]]; then
    echo "  [SKIP]    .github/workflows/async-qa-review.yml (already exists)"
else
    cp "$WORKFLOW_SRC" "$dst_workflow"
    echo "  [INSTALL] .github/workflows/async-qa-review.yml"
fi

echo ""
echo "Done. Next steps:"
echo ""
echo "  1. Ensure CLAUDE_CODE_OAUTH_TOKEN is set in the target repo:"
echo "       gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo <owner/repo>"
echo ""
echo "  2. Commit the installed files:"
echo "       cd $TARGET"
echo "       git add .github/agents/hydrator-reviewer.md \\"
echo "               .github/agents/custodiet-reviewer.md \\"
echo "               .github/workflows/async-qa-review.yml"
echo "       git commit -m 'ci: add async QA review agents (hydrator-reviewer + custodiet-reviewer)'"
echo ""
echo "  3. The agents will run automatically on the next PR open/sync/reopen."
echo ""
echo "  4. To invoke locally (requires aops task server + memory MCP):"
echo "       Task(subagent_type='aops-core:hydrator-reviewer', prompt='PR #<N> in <owner/repo>')"
echo "       Task(subagent_type='aops-core:custodiet-reviewer', prompt='PR #<N> in <owner/repo>')"
