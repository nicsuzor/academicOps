#!/usr/bin/env bash
# generate-viz.sh - Generate all PKB visualizations
#
# Produces (in $AOPS_SESSIONS, default ~/.aops/sessions/):
#   tasks.json        - Full graph JSON from fast-indexer
#   task-map.svg      - Task map (reachable from active leaves + ancestors)
#   attention-map.svg - Under-connected important nodes
#
# Run periodically or from VSCode task. Replaces the old multi-command
# VSCode task with a single invocation.
#
# Usage:
#   ./scripts/generate-viz.sh              # All visualizations
#   ./scripts/generate-viz.sh --quick      # Graph + task map only (skip extras)
#   ./scripts/generate-viz.sh --ego <ID>   # Also generate ego-subgraph for <ID>

set -euo pipefail

AOPS="${AOPS:-/Users/suzor/src/academicOps}"
AOPS_BIN="${AOPS_BIN:-aops}"
OUT_DIR="${AOPS_SESSIONS:-${HOME}/.aops/sessions}"
LAYOUT="sfdp"

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
        -h|--help)
            echo "Usage: generate-viz.sh [--quick] [--ego ID] [--ego-depth N] [--attention-top N] [--layout ENGINE]"
            echo ""
            echo "Options:"
            echo "  --quick            Graph + task map only (skip attention map and transcripts)"
            echo "  --ego ID           Also generate ego-subgraph centered on ID"
            echo "  --ego-depth N      Ego-subgraph depth in hops (default: 2)"
            echo "  --attention-top N  Number of top attention nodes (default: 20)"
            echo "  --layout ENGINE    Graphviz layout engine (default: sfdp)"
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

# Step 2: Generate task map (reachable from active leaves)
echo "==> Generating task map..."
uv run python3 "${AOPS}/scripts/task_graph.py" \
    "${OUT_DIR}/tasks.json" \
    -o "${OUT_DIR}/task-map" \
    --filter reachable \
    --layout "${LAYOUT}"

if [ "${QUICK}" = true ]; then
    echo "==> Quick mode, skipping extras."
    exit 0
fi

# Step 3: Generate attention map (unknown unknowns heat map)
echo "==> Generating attention map..."
uv run python3 "${AOPS}/scripts/task_graph.py" \
    "${OUT_DIR}/tasks.json" \
    -o "${OUT_DIR}/attention-map" \
    --attention-map \
    --attention-top "${ATTENTION_TOP}" \
    --layout "${LAYOUT}" \
    --single

# Step 4: Generate ego-subgraph if requested
if [ -n "${EGO_ID}" ]; then
    echo "==> Generating ego-subgraph for '${EGO_ID}' (depth ${EGO_DEPTH})..."
    uv run python3 "${AOPS}/scripts/task_graph.py" \
        "${OUT_DIR}/tasks.json" \
        -o "${OUT_DIR}/ego-${EGO_ID}" \
        --ego "${EGO_ID}" \
        --depth "${EGO_DEPTH}" \
        --layout "${LAYOUT}" \
        --single
fi

# Step 5: Sync sessions repo and generate recent transcripts
if [ -d "${OUT_DIR}/.git" ]; then
    echo "==> Syncing sessions repo..."
    git -C "${OUT_DIR}" pull --ff-only --quiet 2>/dev/null || echo "    Warning: sessions repo sync failed (offline or conflict)"
fi
echo "==> Generating recent transcripts..."
uv run python3 "${AOPS}/aops-core/scripts/transcript.py" --recent

echo "==> Done."
