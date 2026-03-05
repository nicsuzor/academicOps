#!/usr/bin/env bash
# generate-viz.sh - Generate PKB visualizations
#
# All output goes to $AOPS_SESSIONS (default $POLECAT_HOME/sessions/):
#   graph-*.json          - Per-layout graph data (fa2, treemap, etc.)
#   graph-*.dot           - DOT layout files
#   graph-*.svg           - SVG renders of each .dot layout
#
# Run periodically or from VSCode task.
#
# Usage:
#   ./scripts/generate-viz.sh              # All visualizations
#   ./scripts/generate-viz.sh --quick      # Graph + SVGs only (skip extras)

set -euo pipefail

AOPS_BIN="${AOPS_BIN:-$(command -v aops 2>/dev/null || echo aops)}"
GRAPH_DIR="${AOPS_SESSIONS:-${POLECAT_HOME:-$HOME/.polecat}/sessions}"

# Parse arguments
QUICK=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick)
            QUICK=true
            shift
            ;;
        -h|--help)
            echo "Usage: generate-viz.sh [--quick]"
            echo ""
            echo "Options:"
            echo "  --quick  Graph + SVGs only (skip extras)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "${GRAPH_DIR}"

# Step 0: Generate dashboard synthesis
echo "==> Generating dashboard synthesis..."
uv run python3 "${SCRIPT_DIR}/synthesize_dashboard.py" 2>&1 || echo "Warning: synthesis generation failed"

# Step 1: Generate graph data (per-layout JSONs + .dot files)
echo "==> Generating graph data..."
"${AOPS_BIN}" graph -f all -o "${GRAPH_DIR}/graph"

# Step 1b: Generate SFDP layout (scalable force-directed with Manhattan routing)
echo "==> Generating SFDP layout..."
if command -v sfdp >/dev/null 2>&1; then
    uv run python3 "${SCRIPT_DIR}/task_graph_sfdp.py" \
        "${GRAPH_DIR}/graph.json" \
        -o "${GRAPH_DIR}/graph-sfdp.json" \
        --dot-output "${GRAPH_DIR}/graph-sfdp.dot" \
        --timeout 600 2>&1 || echo "Warning: SFDP layout generation failed"
else
    echo "    Skipped (sfdp not found — install graphviz)"
fi

# Step 2: Generate SVGs from precomputed layout .dot files
# Uses neato -n (fixed positions from aops export). Skips files with errors.
echo "==> Generating SVGs from layout .dot files..."
DOT_COUNT=0
DOT_FAIL=0
for dotfile in "${GRAPH_DIR}"/graph*.dot; do
    [ -f "${dotfile}" ] || continue
    svgfile="${dotfile%.dot}.svg"
    dotbase="$(basename "${dotfile}")"
    echo -n "    ${dotbase} -> ${dotbase%.dot}.svg ... "
    if timeout 120 neato -n -Tsvg -Gsplines=false "${dotfile}" -o "${svgfile}" 2>/dev/null; then
        echo "ok ($(du -h "${svgfile}" | cut -f1))"
        DOT_COUNT=$((DOT_COUNT + 1))
    else
        rm -f "${svgfile}"
        echo "SKIP (missing positions or timeout)"
        DOT_FAIL=$((DOT_FAIL + 1))
    fi
done
echo "    Generated ${DOT_COUNT} SVG(s), ${DOT_FAIL} skipped"

# Step 3: Commit graph layouts to sessions repo
echo "==> Committing graph layouts to sessions repo..."
if [ -d "${GRAPH_DIR}/.git" ]; then
    # Resolve conflicts in graph files (freshly generated version wins)
    echo "    Checking for graph file conflicts..."
    conflicted_files=$(git -C "${GRAPH_DIR}" diff --name-only --diff-filter=U | grep -E "graph.*\.(dot|svg|json|graphml)" || true)
    if [[ -n "$conflicted_files" ]]; then
        echo "$conflicted_files" | xargs -r git -C "${GRAPH_DIR}" add 2>/dev/null || true
    fi

    git -C "${GRAPH_DIR}" add -f graph*.dot graph*.svg graph.graphml graph-*.json 2>/dev/null || true
    if ! git -C "${GRAPH_DIR}" diff --cached --quiet 2>/dev/null; then
        git -C "${GRAPH_DIR}" commit -m "update graph layouts $(date +%Y-%m-%d)" --no-gpg-sign 2>/dev/null || true
        git -C "${GRAPH_DIR}" push 2>/dev/null && echo "    Pushed to remote" || echo "    Push failed (will retry next run)"
    else
        echo "    No changes to commit"
    fi
else
    echo "    Skipped (${GRAPH_DIR} is not a git repo)"
fi

echo "==> Done."
