#!/usr/bin/env bash
# install-brain-workflows.sh
#
# Install PKB consolidation workflows into a brain ($ACA_DATA) repository.
#
# Installs three GitHub Actions workflows:
#   - sleep-cycle.yml      — periodic consolidation (every 6h)
#   - pkb-quality-review.yml — weekly quality assessment
#   - transcript-extraction.yml — transcript mining (every 6h)
#
# USAGE
#   ./install-brain-workflows.sh <brain-repo-path>
#
# EXAMPLE
#   ./install-brain-workflows.sh ~/brain
#
# PREREQUISITES
#   - Target repo must have GitHub Actions enabled
#   - Secrets required in the target repo:
#       gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo <owner/repo>
#       gh secret set AOPS_DIST_PAT --repo <owner/repo>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AOPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TEMPLATE_DIR="$AOPS_DIR/templates/github-workflows"

TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
    echo "Usage: $0 <brain-repo-path>" >&2
    echo "Example: $0 ~/brain" >&2
    exit 1
fi

if [[ ! -d "$TARGET/.git" ]]; then
    echo "Error: $TARGET is not a git repository" >&2
    exit 1
fi

echo "Installing PKB consolidation workflows into: $TARGET"
echo ""

# Create target directory
mkdir -p "$TARGET/.github/workflows"

# Install each workflow template
WORKFLOWS=(
    "sleep-cycle.yml"
    "pkb-quality-review.yml"
    "transcript-extraction.yml"
)

for wf in "${WORKFLOWS[@]}"; do
    src="$TEMPLATE_DIR/$wf"
    dst="$TARGET/.github/workflows/$wf"

    if [[ ! -f "$src" ]]; then
        echo "  [ERROR]   Source not found: $src" >&2
        continue
    fi

    if [[ -f "$dst" ]]; then
        echo "  [UPDATE]  .github/workflows/$wf"
    else
        echo "  [INSTALL] .github/workflows/$wf"
    fi
    cp "$src" "$dst"
done

# Resolve target repo slug
REPO_SLUG=$(cd "$TARGET" && gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || true)

# Check secrets
if [[ -n "$REPO_SLUG" ]]; then
    echo ""
    echo "Checking secrets for $REPO_SLUG..."

    EXISTING=$(gh secret list --repo "$REPO_SLUG" --json name -q '.[].name' 2>/dev/null || true)

    for secret in CLAUDE_CODE_OAUTH_TOKEN AOPS_DIST_PAT; do
        if echo "$EXISTING" | grep -q "$secret"; then
            echo "  [OK]      $secret already set"
        else
            echo "  [SKIP]    $secret not set — add manually:"
            echo "              gh secret set $secret --repo $REPO_SLUG"
        fi
    done
else
    echo ""
    echo "  [WARN]    Could not resolve repo slug — set secrets manually"
fi

echo ""
echo "Done. Next steps:"
echo ""
echo "  1. Commit the installed workflows:"
echo "       cd $TARGET"
echo "       git add .github/workflows/sleep-cycle.yml \\"
echo "               .github/workflows/pkb-quality-review.yml \\"
echo "               .github/workflows/transcript-extraction.yml"
echo "       git commit -m 'ci: add PKB consolidation workflows'"
echo ""
echo "  2. Push to enable the scheduled workflows:"
echo "       git push"
echo ""
echo "  3. Test manually:"
echo "       gh workflow run 'Sleep Cycle' --repo ${REPO_SLUG:-<owner/repo>}"
echo ""
echo "  Schedule:"
echo "    - Sleep cycle:     every 6h at :17"
echo "    - Quality review:  weekly Monday 3:23 AM"
echo "    - Transcript extraction: every 6h at :47"
echo ""
