#!/usr/bin/env bash
# generate-viz.sh - Generate all PKB visualizations
#
# Produces (in $AOPS_SESSIONS, default ~/.aops/sessions/):
#   tasks.json        - Full graph JSON from fast-indexer
#   task-map.svg      - Task map (reachable from active leaves + ancestors)
#   task-map.html     - Interactive D3-force task map
#   attention-map.svg - Under-connected important nodes
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
OUT_DIR="${AOPS_SESSIONS:-${HOME}/.aops/sessions}"
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
            echo "  --quick            Graph + task map only (skip attention map and transcripts)"
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

mkdir -p "${OUT_DIR}"

# Step 1: Generate graph JSON from fast-indexer
echo "==> Generating graph JSON..."
"${AOPS_BIN}" graph -f json -o "${OUT_DIR}/tasks.json"
echo "    Written ${OUT_DIR}/tasks.json"

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
                "${OUT_DIR}/tasks.json" \
                --filter reachable \
                --graphviz \
                ${DENSITY_ARGS[@]+"${DENSITY_ARGS[@]}"} \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
        ogdf)
            uv run python3 "${AOPS}/scripts/task_graph_ogdf.py" \
                "${OUT_DIR}/tasks.json" \
                --filter reachable \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
        *)
            uv run python3 "${AOPS}/scripts/task_graph.py" \
                "${OUT_DIR}/tasks.json" \
                --filter reachable \
                --layout "${LAYOUT}" \
                ${DENSITY_ARGS[@]+"${DENSITY_ARGS[@]}"} \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
    esac
}

# Step 2: Generate task map SVG (reachable from active leaves)
echo "==> Generating task map (renderer: ${RENDERER})..."
run_graph -o "${OUT_DIR}/task-map"

# Step 2b: Generate interactive D3 HTML
echo "==> Generating D3 interactive graph..."
uv run python3 "${AOPS}/scripts/task_graph_d3.py" \
    "${OUT_DIR}/tasks.json" \
    --filter reachable \
    -o "${OUT_DIR}/task-map.html"
echo "    Written ${OUT_DIR}/task-map.html"

if [ "${QUICK}" = true ]; then
    echo "==> Quick mode, skipping extras."
    exit 0
fi

# Step 3: Generate attention map (unknown unknowns heat map)
echo "==> Generating attention map..."
run_graph -o "${OUT_DIR}/attention-map" --attention-map --attention-top "${ATTENTION_TOP}"

# Step 4: Generate ego-subgraph if requested
if [ -n "${EGO_ID}" ]; then
    echo "==> Generating ego-subgraph for '${EGO_ID}' (depth ${EGO_DEPTH})..."
    run_graph -o "${OUT_DIR}/ego-${EGO_ID}" --ego "${EGO_ID}" --depth "${EGO_DEPTH}"

    echo "==> Generating D3 ego-subgraph for '${EGO_ID}'..."
    uv run python3 "${AOPS}/scripts/task_graph_d3.py" \
        "${OUT_DIR}/tasks.json" \
        --filter reachable \
        --ego "${EGO_ID}" --depth "${EGO_DEPTH}" \
        -o "${OUT_DIR}/ego-${EGO_ID}.html"
    echo "    Written ${OUT_DIR}/ego-${EGO_ID}.html"
fi

# Step 5: Sync sessions repo and generate recent transcripts
if [ -d "${OUT_DIR}/.git" ]; then
    echo "==> Syncing sessions repo..."
    git -C "${OUT_DIR}" pull --ff-only --quiet 2>/dev/null || echo "    Warning: sessions repo sync failed (offline or conflict)"
fi
echo "==> Generating recent transcripts..."
uv run python3 "${AOPS}/aops-core/scripts/transcript.py" --recent

echo "==> Done."
