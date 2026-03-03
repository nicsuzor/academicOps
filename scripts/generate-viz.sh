#!/usr/bin/env bash
# generate-viz.sh - Generate all PKB visualizations
#
# All output goes to $AOPS_SESSIONS (default ~/.aops/sessions/):
#   graph.json            - Full PKB graph with task metadata and precomputed layouts
#   graph-*.svg           - SVG renders of each precomputed .dot layout
#   task-map.svg          - Task map (reachable from active leaves + ancestors)
#   task-map.html         - Interactive D3-force task map
#   attention-map.svg     - Under-connected important nodes
#
# Run periodically or from VSCode task. Replaces the old multi-command
# VSCode task with a single invocation.
#
# Usage:
#   ./scripts/generate-viz.sh              # All visualizations
#   ./scripts/generate-viz.sh --quick      # Graph + task map only (skip extras)
#   ./scripts/generate-viz.sh --ego <ID>   # Also generate ego-subgraph for <ID>
#   ./scripts/generate-viz.sh --renderer gt    # Use graph-tool (requires python3.14)
#   ./scripts/generate-viz.sh --renderer ogdf  # Use OGDF

set -euo pipefail

AOPS="${AOPS:-$(cd "$(dirname "$0")/.." && pwd)}"
AOPS_BIN="${AOPS_BIN:-$(command -v aops 2>/dev/null || echo aops)}"
GRAPH_DIR="${AOPS_SESSIONS:-${HOME}/.aops/sessions}"  # All output: graph JSONs + viz artifacts
VIZ_DIR="${GRAPH_DIR}"                                # Same directory now
LAYOUT="sfdp"
RENDERER="dot"  # dot (default), gt (graph-tool), ogdf
SPLINES=""
SEP=""
OVERLAP=""

# Parse arguments
QUICK=false
EGO_ID=""
EGO_DEPTH=2
ATTENTION_TOP=20

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick)
            QUICK=true
            shift
            ;;
        --ego)
            EGO_ID="$2"
            shift 2
            ;;
        --ego-depth)
            EGO_DEPTH="$2"
            shift 2
            ;;
        --attention-top)
            ATTENTION_TOP="$2"
            shift 2
            ;;
        --layout)
            LAYOUT="$2"
            shift 2
            ;;
        --renderer)
            RENDERER="$2"
            shift 2
            ;;
        --splines)
            SPLINES="$2"
            shift 2
            ;;
        --sep)
            SEP="$2"
            shift 2
            ;;
        --overlap)
            OVERLAP="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: generate-viz.sh [--quick] [--ego ID] [--ego-depth N] [--attention-top N] [--layout ENGINE] [--renderer dot|gt|ogdf] [--splines MODE] [--sep SEP] [--overlap MODE]"
            echo ""
            echo "Options:"
            echo "  --quick            Graph + task map only (skip attention map)"
            echo "  --ego ID           Also generate ego-subgraph centered on ID"
            echo "  --ego-depth N      Ego-subgraph depth in hops (default: 2)"
            echo "  --attention-top N  Number of top attention nodes (default: 20)"
            echo "  --layout ENGINE    Layout engine (default: sfdp)"
            echo "  --renderer TYPE    Renderer: dot (default), gt (graph-tool), ogdf"
            echo "  --splines MODE     Edge routing: true, curved, ortho, polyline, line, false"
            echo "  --sep SEP          Node separation (e.g. +2, +4)"
            echo "  --overlap MODE     Overlap removal: true, false, scale, prism, compress"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

mkdir -p "${GRAPH_DIR}" "${VIZ_DIR}"

# Step 1: Generate graph data (includes task metadata and precomputed layouts)
echo "==> Generating graph data..."
"${AOPS_BIN}" graph -f all -o "${GRAPH_DIR}/graph"

# Build density override args (shared across renderers)
DENSITY_ARGS=()
[ -n "${SPLINES}" ] && DENSITY_ARGS+=(--splines "${SPLINES}")
[ -n "${SEP}" ]     && DENSITY_ARGS+=(--sep "${SEP}")
[ -n "${OVERLAP}" ] && DENSITY_ARGS+=(--overlap "${OVERLAP}")

# Renderer dispatch helper
run_graph() {
    local extra_args=("$@")
    case "${RENDERER}" in
        gt)
            # graph-tool requires brew's python3.14
            local GT_PYTHON="/opt/homebrew/opt/python@3.14/bin/python3.14"
            if [ ! -x "${GT_PYTHON}" ]; then
                echo "    Error: python3.14 not found. Install: brew install graph-tool" >&2
                exit 1
            fi
            "${GT_PYTHON}" "${AOPS}/scripts/task_graph_gt.py" \
                "${GRAPH_DIR}/graph.json" \
                --filter reachable \
                --graphviz \
                ${DENSITY_ARGS[@]+"${DENSITY_ARGS[@]}"} \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
        ogdf)
            uv run python3 "${AOPS}/scripts/task_graph_ogdf.py" \
                "${GRAPH_DIR}/graph.json" \
                --filter reachable \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
        *)
            uv run python3 "${AOPS}/scripts/task_graph.py" \
                "${GRAPH_DIR}/graph.json" \
                --filter reachable \
                --layout "${LAYOUT}" \
                ${DENSITY_ARGS[@]+"${DENSITY_ARGS[@]}"} \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
    esac
}

# Step 2: Generate SVGs from precomputed layout .dot files
# Uses neato -n (fixed positions from aops export). Overrides splines to
# avoid expensive ortho routing. Skips files with errors (e.g. missing pos).
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

# Step 3: Generate task map SVG (reachable from active leaves)
echo "==> Generating task map (renderer: ${RENDERER})..."
run_graph -o "${VIZ_DIR}/task-map"

# Step 3b: Generate interactive D3 HTML
echo "==> Generating D3 interactive graph..."
uv run python3 "${AOPS}/scripts/task_graph_d3.py" \
    "${GRAPH_DIR}/graph.json" \
    --filter reachable \
    -o "${VIZ_DIR}/task-map.html"
echo "    Written ${VIZ_DIR}/task-map.html"

if [ "${QUICK}" = true ]; then
    echo "==> Quick mode, skipping extras."
else
    # Step 4: Generate attention map (unknown unknowns heat map)
    echo "==> Generating attention map..."
    run_graph -o "${VIZ_DIR}/attention-map" --attention-map --attention-top "${ATTENTION_TOP}"

    # Step 5: Generate ego-subgraph if requested
    if [ -n "${EGO_ID}" ]; then
        echo "==> Generating ego-subgraph for '${EGO_ID}' (depth ${EGO_DEPTH})..."
        run_graph -o "${VIZ_DIR}/ego-${EGO_ID}" --ego "${EGO_ID}" --depth "${EGO_DEPTH}"

        echo "==> Generating D3 ego-subgraph for '${EGO_ID}'..."
        uv run python3 "${AOPS}/scripts/task_graph_d3.py" \
            "${GRAPH_DIR}/graph.json" \
            --filter reachable \
            --ego "${EGO_ID}" --depth "${EGO_DEPTH}" \
            -o "${VIZ_DIR}/ego-${EGO_ID}.html"
        echo "    Written ${VIZ_DIR}/ego-${EGO_ID}.html"
    fi
fi

# Step 6: Commit graph layouts to sessions repo
echo "==> Committing graph layouts to sessions repo..."
if [ -d "${GRAPH_DIR}/.git" ]; then
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
