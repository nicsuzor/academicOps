#!/usr/bin/env bash
# generate-viz.sh - Generate all PKB visualizations
#
# Graph JSON files are written to $ACA_DATA (default ~/brain):
#   graph.json            - Full PKB graph (used by overwhelm dashboard)
#   knowledge-graph.json  - Same graph (dashboard "Knowledge Base" view)
#
# Visualization artifacts go to $AOPS_SESSIONS (default ~/.aops/sessions/):
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
GRAPH_DIR="${ACA_DATA:-${HOME}/brain}"          # Graph JSONs (dashboard reads from here)
VIZ_DIR="${AOPS_SESSIONS:-${HOME}/.aops/sessions}"  # SVG/HTML artifacts
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

mkdir -p "${GRAPH_DIR}" "${VIZ_DIR}"

# Step 1: Generate graph data
# - mcp-index: rich task metadata (status, priority, downstream_weight, etc.)
# - json: full PKB graph with all nodes + wikilink edges (but sparse metadata)
echo "==> Generating graph data..."
"${AOPS_BIN}" graph -f mcp-index -o "${GRAPH_DIR}/mcp-index.json"
"${AOPS_BIN}" graph -f json -o "${GRAPH_DIR}/pkb-raw.json"

# Step 1b: Build dashboard graph files from the raw data
python3 -c "
import json, sys, os

graph_dir = sys.argv[1]
idx = json.load(open(os.path.join(graph_dir, 'mcp-index.json')))
raw = json.load(open(os.path.join(graph_dir, 'pkb-raw.json')))

tasks = idx.get('tasks', {})

# Build lookup for precomputed layout coordinates from pkb-raw.json
raw_by_id = {n['id']: n for n in raw.get('nodes', []) if 'id' in n}

# -- graph.json: task-only graph with rich metadata --
nodes, edges, seen_edges = [], [], set()
for tid, t in tasks.items():
    raw_node = raw_by_id.get(t['id'], {})
    node = {
        'id': t['id'], 'label': t.get('title', t['id']),
        'path': t.get('path', ''), 'tags': t.get('tags', []),
        'node_type': t.get('type', 'task'), 'status': t.get('status', 'inbox'),
        'priority': t.get('priority', 2), 'project': t.get('project', ''),
        'depth': t.get('depth', 0), 'downstream_weight': t.get('downstream_weight', 0),
        'stakeholder_exposure': t.get('stakeholder_exposure', False),
        'leaf': t.get('leaf', True), 'assignee': t.get('assignee', ''),
    }
    if 'x' in raw_node and 'y' in raw_node:
        node['x'] = raw_node['x']
        node['y'] = raw_node['y']
    nodes.append(node)
    for cid in t.get('children', []):
        key = (cid, t['id'], 'parent')
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({'source': cid, 'target': t['id'], 'type': 'parent'})
    for did in t.get('depends_on', []):
        key = (t['id'], did, 'depends_on')
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({'source': t['id'], 'target': did, 'type': 'depends_on'})
    for sid in t.get('soft_depends_on', []):
        key = (t['id'], sid, 'soft_depends_on')
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({'source': t['id'], 'target': sid, 'type': 'soft_depends_on'})

task_ids = {n['id'] for n in nodes}
edges = [e for e in edges if e['source'] in task_ids and e['target'] in task_ids]
with open(os.path.join(graph_dir, 'graph.json'), 'w') as f:
    json.dump({'nodes': nodes, 'edges': edges}, f)
print(f'    graph.json: {len(nodes)} nodes, {len(edges)} edges')

# -- knowledge-graph.json: full PKB graph enriched with task metadata --
task_by_path = {t.get('path', ''): t for t in tasks.values() if t.get('path')}
raw_nodes = raw.get('nodes', [])
enriched = []
for n in raw_nodes:
    t = task_by_path.get(n.get('path', ''))
    if t:
        enriched.append({**n, 'node_type': t.get('type', 'task'),
            'status': t.get('status', 'inbox'), 'priority': t.get('priority', 2),
            'project': t.get('project', ''), 'depth': t.get('depth', 0),
            'downstream_weight': t.get('downstream_weight', 0),
            'stakeholder_exposure': t.get('stakeholder_exposure', False),
            'assignee': t.get('assignee', ''), 'label': t.get('title', n.get('label', ''))})
    else:
        enriched.append({**n, 'node_type': 'note'})
raw_edges = raw.get('edges', [])
with open(os.path.join(graph_dir, 'knowledge-graph.json'), 'w') as f:
    json.dump({'nodes': enriched, 'edges': raw_edges}, f)
print(f'    knowledge-graph.json: {len(enriched)} nodes, {len(raw_edges)} edges')
" "${GRAPH_DIR}"

# Also keep a copy in VIZ_DIR for the rendering scripts below
cp "${GRAPH_DIR}/graph.json" "${VIZ_DIR}/tasks.json"

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
                "${VIZ_DIR}/tasks.json" \
                --filter reachable \
                --graphviz \
                ${DENSITY_ARGS[@]+"${DENSITY_ARGS[@]}"} \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
        ogdf)
            uv run python3 "${AOPS}/scripts/task_graph_ogdf.py" \
                "${VIZ_DIR}/tasks.json" \
                --filter reachable \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
        *)
            uv run python3 "${AOPS}/scripts/task_graph.py" \
                "${VIZ_DIR}/tasks.json" \
                --filter reachable \
                --layout "${LAYOUT}" \
                ${DENSITY_ARGS[@]+"${DENSITY_ARGS[@]}"} \
                ${extra_args[@]+"${extra_args[@]}"}
            ;;
    esac
}

# Step 2: Generate task map SVG (reachable from active leaves)
echo "==> Generating task map (renderer: ${RENDERER})..."
run_graph -o "${VIZ_DIR}/task-map"

# Step 2b: Generate interactive D3 HTML
echo "==> Generating D3 interactive graph..."
uv run python3 "${AOPS}/scripts/task_graph_d3.py" \
    "${VIZ_DIR}/tasks.json" \
    --filter reachable \
    -o "${VIZ_DIR}/task-map.html"
echo "    Written ${VIZ_DIR}/task-map.html"

if [ "${QUICK}" = true ]; then
    echo "==> Quick mode, skipping extras."
    exit 0
fi

# Step 3: Generate attention map (unknown unknowns heat map)
echo "==> Generating attention map..."
run_graph -o "${VIZ_DIR}/attention-map" --attention-map --attention-top "${ATTENTION_TOP}"

# Step 4: Generate ego-subgraph if requested
if [ -n "${EGO_ID}" ]; then
    echo "==> Generating ego-subgraph for '${EGO_ID}' (depth ${EGO_DEPTH})..."
    run_graph -o "${VIZ_DIR}/ego-${EGO_ID}" --ego "${EGO_ID}" --depth "${EGO_DEPTH}"

    echo "==> Generating D3 ego-subgraph for '${EGO_ID}'..."
    uv run python3 "${AOPS}/scripts/task_graph_d3.py" \
        "${VIZ_DIR}/tasks.json" \
        --filter reachable \
        --ego "${EGO_ID}" --depth "${EGO_DEPTH}" \
        -o "${VIZ_DIR}/ego-${EGO_ID}.html"
    echo "    Written ${VIZ_DIR}/ego-${EGO_ID}.html"
fi

# Step 5: Sync sessions repo and generate recent transcripts
if [ -d "${VIZ_DIR}/.git" ]; then
    echo "==> Syncing sessions repo..."
    git -C "${VIZ_DIR}" pull --ff-only --quiet 2>/dev/null || echo "    Warning: sessions repo sync failed (offline or conflict)"
fi
echo "==> Generating recent transcripts..."
uv run python3 "${AOPS}/aops-core/scripts/transcript.py" --recent

echo "==> Done."
