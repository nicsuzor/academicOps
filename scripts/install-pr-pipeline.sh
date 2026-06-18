#!/usr/bin/env bash
# install-pr-pipeline.sh
#
# Script the §9 satellite-repo install of the academicOps PR pipeline.
# Writes trigger-enforcer.yml + trigger-qa.yml (byte-identical across repos,
# calling agent-enforcer/agent-qa @pipeline-v1 on pull_request) and a
# LANG-preset ci.yml (posts the required test-status commit status).
# Removes stale pr-review.yml / merge-prep.yml if present.
#
# Does NOT touch secrets (human task — see post-install checklist below).
# Does NOT verify runtime (see post-install checklist → template aops-da9b4f5a).
#
# USAGE
#   ./install-pr-pipeline.sh <target-repo-path> --lang python|rust|node
#
# EXAMPLE
#   ./install-pr-pipeline.sh ~/src/zotmcp --lang python
#
# WHAT GETS INSTALLED
#   .github/workflows/trigger-enforcer.yml  — fires agent-enforcer @pipeline-v1 on PR
#   .github/workflows/trigger-qa.yml        — fires agent-qa @pipeline-v1 on PR
#   .github/workflows/ci.yml               — LANG-preset mechanical CI (posts test-status)
#
# WHAT GETS REMOVED (stale v1 files)
#   .github/workflows/pr-review.yml         — old portable reviewer shim
#   .github/workflows/merge-prep.yml        — old merge-prep shim
#
# PREREQUISITES (human-touch, NOT done by this script)
#   Two secrets must be set on the target repo:
#     AOPS_BOT_GH_TOKEN      — bot PAT scoped to this repo (statuses, reviews, push)
#     CLAUDE_CODE_OAUTH_TOKEN — OAuth token for the Claude agent
#   See template aops-da9b4f5a for the secrets gate + runtime verification steps.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Arg parsing ────────────────────────────────────────────────────────────────

TARGET=""
LANG_ARG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang)
      LANG_ARG="${2:-}"
      shift 2
      ;;
    -*)
      echo "Unknown flag: $1" >&2
      exit 1
      ;;
    *)
      if [[ -n "$TARGET" ]]; then
        echo "Error: unexpected argument '$1'" >&2
        exit 1
      fi
      TARGET="$1"
      shift
      ;;
  esac
done

if [[ -z "$TARGET" ]] || [[ -z "$LANG_ARG" ]]; then
  echo "Usage: $0 <target-repo-path> --lang python|rust|node" >&2
  echo "Example: $0 ~/src/zotmcp --lang python" >&2
  exit 1
fi

case "$LANG_ARG" in
  python|rust|node) ;;
  *)
    echo "Error: --lang must be one of: python, rust, node (got '$LANG_ARG')" >&2
    exit 1
    ;;
esac

if [[ ! -d "$TARGET/.git" ]]; then
  echo "Error: $TARGET is not a git repository" >&2
  exit 1
fi

echo "Installing PR pipeline into: $TARGET (lang=$LANG_ARG)"
echo ""

mkdir -p "$TARGET/.github/workflows"

# ── Write trigger-enforcer.yml (byte-identical across repos) ───────────────────

ENFORCER_DST="$TARGET/.github/workflows/trigger-enforcer.yml"
if [[ -f "$ENFORCER_DST" ]]; then
  echo "  [UPDATE]  .github/workflows/trigger-enforcer.yml"
else
  echo "  [INSTALL] .github/workflows/trigger-enforcer.yml"
fi

cat > "$ENFORCER_DST" << 'EOF'
name: "Trigger: Enforcer"

on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]

# Caller must grant at least the union of permissions any nested job requests.
# Without this block, default-restrictive repo settings drop the token and GitHub
# rejects the workflow at graph-build time (startup_failure — RCA aops-31798611).
permissions:
  contents: write
  pull-requests: write
  statuses: write
  issues: write
  id-token: write

jobs:
  enforce:
    uses: nicsuzor/academicOps/.github/workflows/agent-enforcer.yml@pipeline-v1
    with:
      pr_number: ${{ github.event.pull_request.number }}
      ref:       ${{ github.event.pull_request.head.ref }}
      sha:       ${{ github.event.pull_request.head.sha }}
    secrets:
      AOPS_BOT_GH_TOKEN: ${{ secrets.AOPS_BOT_GH_TOKEN }}
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
EOF

# ── Write trigger-qa.yml (byte-identical across repos) ────────────────────────

QA_DST="$TARGET/.github/workflows/trigger-qa.yml"
if [[ -f "$QA_DST" ]]; then
  echo "  [UPDATE]  .github/workflows/trigger-qa.yml"
else
  echo "  [INSTALL] .github/workflows/trigger-qa.yml"
fi

cat > "$QA_DST" << 'EOF'
name: "Trigger: QA"

on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]

# Mirror enforcer permissions union (RCA aops-31798611). QA never commits so
# contents: read is sufficient; the rest must match the callee's declared job permissions.
permissions:
  contents: read
  pull-requests: write
  statuses: write
  id-token: write

jobs:
  qa:
    uses: nicsuzor/academicOps/.github/workflows/agent-qa.yml@pipeline-v1
    with:
      pr_number: ${{ github.event.pull_request.number }}
      ref:       ${{ github.event.pull_request.head.ref }}
      sha:       ${{ github.event.pull_request.head.sha }}
    secrets:
      AOPS_BOT_GH_TOKEN: ${{ secrets.AOPS_BOT_GH_TOKEN }}
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
EOF

# ── Write ci.yml (LANG-preset, posts test-status) ────────────────────────────
#
# The §9 naming contract requires a commit status named "test-status".
# GITHUB_TOKEN with statuses: write is sufficient — no extra secret needed.

CI_DST="$TARGET/.github/workflows/ci.yml"
if [[ -f "$CI_DST" ]]; then
  echo "  [UPDATE]  .github/workflows/ci.yml (lang=$LANG_ARG)"
else
  echo "  [INSTALL] .github/workflows/ci.yml (lang=$LANG_ARG)"
fi

case "$LANG_ARG" in

  python)
    cat > "$CI_DST" << 'EOF'
name: "CI"

on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]

permissions:
  contents: read
  statuses: write

jobs:
  test:
    name: Pytest
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - name: Post test-status pending
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SHA: ${{ github.event.pull_request.head.sha }}
          REPO: ${{ github.repository }}
        run: |
          gh api "repos/$REPO/statuses/$SHA" \
            -f state=pending \
            -f context=test-status \
            -f description="Tests running…"

      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.ref }}

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --frozen --no-install-project

      - name: Run tests
        run: uv run pytest --tb=short -q

      - name: Post test-status result
        if: always()
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SHA: ${{ github.event.pull_request.head.sha }}
          REPO: ${{ github.repository }}
          OUTCOME: ${{ job.status }}
        run: |
          if [[ "$OUTCOME" == "success" ]]; then
            gh api "repos/$REPO/statuses/$SHA" \
              -f state=success -f context=test-status -f description="Tests passed"
          else
            gh api "repos/$REPO/statuses/$SHA" \
              -f state=failure -f context=test-status -f description="Tests failed"
          fi
EOF
    ;;

  rust)
    cat > "$CI_DST" << 'EOF'
name: "CI"

on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]

permissions:
  contents: read
  statuses: write

jobs:
  test:
    name: Cargo Test
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - name: Post test-status pending
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SHA: ${{ github.event.pull_request.head.sha }}
          REPO: ${{ github.repository }}
        run: |
          gh api "repos/$REPO/statuses/$SHA" \
            -f state=pending \
            -f context=test-status \
            -f description="Tests running…"

      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.ref }}

      - uses: dtolnay/rust-toolchain@stable

      - name: Run tests
        run: cargo test

      - name: Post test-status result
        if: always()
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SHA: ${{ github.event.pull_request.head.sha }}
          REPO: ${{ github.repository }}
          OUTCOME: ${{ job.status }}
        run: |
          if [[ "$OUTCOME" == "success" ]]; then
            gh api "repos/$REPO/statuses/$SHA" \
              -f state=success -f context=test-status -f description="Tests passed"
          else
            gh api "repos/$REPO/statuses/$SHA" \
              -f state=failure -f context=test-status -f description="Tests failed"
          fi
EOF
    ;;

  node)
    cat > "$CI_DST" << 'EOF'
name: "CI"

on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]

permissions:
  contents: read
  statuses: write

jobs:
  test:
    name: npm test
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - name: Post test-status pending
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SHA: ${{ github.event.pull_request.head.sha }}
          REPO: ${{ github.repository }}
        run: |
          gh api "repos/$REPO/statuses/$SHA" \
            -f state=pending \
            -f context=test-status \
            -f description="Tests running…"

      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.ref }}

      - uses: actions/setup-node@v4
        with:
          node-version: "lts/*"

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Post test-status result
        if: always()
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SHA: ${{ github.event.pull_request.head.sha }}
          REPO: ${{ github.repository }}
          OUTCOME: ${{ job.status }}
        run: |
          if [[ "$OUTCOME" == "success" ]]; then
            gh api "repos/$REPO/statuses/$SHA" \
              -f state=success -f context=test-status -f description="Tests passed"
          else
            gh api "repos/$REPO/statuses/$SHA" \
              -f state=failure -f context=test-status -f description="Tests failed"
          fi
EOF
    ;;

esac

# ── Remove stale v1 workflow files ────────────────────────────────────────────

for stale in "pr-review.yml" "merge-prep.yml"; do
  stale_path="$TARGET/.github/workflows/$stale"
  if [[ -f "$stale_path" ]]; then
    rm "$stale_path"
    echo "  [REMOVE]  .github/workflows/$stale (stale v1 file)"
  fi
done

# ── Resolve target repo slug for checklist output ─────────────────────────────

REPO_SLUG=$(cd "$TARGET" && gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || true) # allow-fallback: gh may be absent or target repo not yet pushed; caller sees <owner/repo> placeholder
REPO_DISPLAY="${REPO_SLUG:-<owner/repo>}" # allow-fallback: display-only placeholder when gh cannot resolve the slug

# ── Post-install checklist ────────────────────────────────────────────────────

echo ""
echo "Done. Post-install checklist:"
echo ""
echo "  1. Commit the installed files:"
echo "       cd $TARGET"
echo "       git add .github/workflows/trigger-enforcer.yml \\"
echo "               .github/workflows/trigger-qa.yml \\"
echo "               .github/workflows/ci.yml"
echo "       git commit -m 'ci: install academicOps §9 PR pipeline (enforcer + qa + $LANG_ARG CI)'"
echo ""
echo "  2. Secrets gate (HUMAN TASK — do not skip):"
echo "       Confirm these secrets exist on $REPO_DISPLAY and are unexpired:"
echo "         AOPS_BOT_GH_TOKEN      — bot PAT scoped to this repo"
echo "         CLAUDE_CODE_OAUTH_TOKEN — Claude agent OAuth token"
echo "       gh secret list --repo $REPO_DISPLAY"
echo "       NOTE: 'gh secret list' shows existence only, NOT validity."
echo "       The #1 failure mode is a stale/wrong-scope AOPS_BOT_GH_TOKEN —"
echo "       checkout fails with 'fatal: could not read Username'."
echo "       Only the user can rotate the token; do not broker the secret value."
echo ""
echo "  3. Push and open a PR to verify all three workflows trigger:"
echo "       git push"
echo "       (Open a test PR — trigger-enforcer.yml, trigger-qa.yml, and ci.yml"
echo "        must all appear in the Actions tab and post their statuses:"
echo "        enforcer-status, qa-status, test-status)"
echo ""
echo "  4. Optionally add enforcer-status, qa-status, test-status as required"
echo "       checks in branch protection for $REPO_DISPLAY."
echo ""
echo "  Full verification steps and secrets rotation guide:"
echo "    → Template aops-da9b4f5a in the academicOps PKB"
echo ""
echo "  This script does NOT set secrets and does NOT verify runtime."
echo "  Steps 2 (secrets gate) and 3 (runtime verify) require human touch."
