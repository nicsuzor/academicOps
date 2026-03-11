import {
    STATUS_FILLS,
    TYPE_BASE_SCALE,
    STATUS_TEXT,
    MUTED_FILL,
    MUTED_TEXT,
    INCOMPLETE_STATUSES,
    PRIORITY_BORDERS,
    ASSIGNEE_COLORS,
    ASSIGNEE_DEFAULT,
    TYPE_SHAPE,
    TYPE_BADGE,
    TYPE_CHARGE,
    EDGE_FORCE,
    FORCE_CONFIG
} from './constants';

export interface GraphNode {
    id: string;
    label: string;
    lines: string[];
    type: string;
    shape: string;
    status: string;
    priority: number;
    depth: number;
    maxDepth: number;
    w: number;
    h: number;
    fontSize: number;
    fill: string;
    textColor: string;
    borderColor: string;
    borderWidth: number;
    stakeholder: boolean;
    structural: boolean;
    dw: number;
    modified: number | null;
    badge: string;
    charge: number;
    parent: string | null;
    project: string | null;
    assignee: string | null;
    path: string | null;
    opacity: number;
    isLeaf: boolean;
    spotlight: boolean;
    x?: number;
    y?: number;
    layouts: Record<string, any>;
    fullTitle: string;
    _raw: any;

    // D3 physics mutation state
    fx?: number | null;
    fy?: number | null;
    vx?: number;
    vy?: number;

    // Layout-computed properties (mutated during rendering)
    _lr?: number;        // circle pack layout radius
    _lw?: number;        // treemap layout width
    _lh?: number;        // treemap layout height
    _isLeaf?: boolean;   // layout leaf state
    _isOverflow?: boolean; // layout overflow state
    _lastSelected?: boolean; // previous selection state for dirty-check optimisation
}

export interface GraphEdge {
    source: string | GraphNode;
    target: string | GraphNode;
    type: string;
    color: string;
    width: number;
    dash: string;
    strength: number;
    distance: number;
}

export interface PreparedGraph {
    nodes: GraphNode[];
    links: GraphEdge[];
    forceConfig: typeof FORCE_CONFIG;
    hasLayout: boolean;
    availableLayouts: string[];
}

function estimateTextWidth(text: string, fontSize: number): number {
    return text.length * fontSize * 0.56;
}

function wrapText(label: string, fontSize: number, maxWidth: number): string[] {
    if (estimateTextWidth(label, fontSize) <= maxWidth) {
        return [label];
    }
    const charsPerLine = Math.max(10, Math.floor(maxWidth / (fontSize * 0.56)));
    const lines: string[] = [];
    let current = "";

    for (const word of label.split(/\s+/)) {
        const test = current ? `${current} ${word}` : word;
        if (test.length > charsPerLine && current) {
            lines.push(current);
            current = word;
        } else {
            current = test;
        }
    }
    if (current) {
        lines.push(current);
    }
    return lines.slice(0, 3);
}

function hexToRgb(hex: string): [number, number, number] {
    const h = hex.replace(/^#/, '');
    if (h.length === 3) {
        return [
            parseInt(h[0] + h[0], 16),
            parseInt(h[1] + h[1], 16),
            parseInt(h[2] + h[2], 16)
        ];
    }
    return [
        parseInt(h.substring(0, 2), 16),
        parseInt(h.substring(2, 4), 16),
        parseInt(h.substring(4, 6), 16)
    ];
}

function rgbToHex(r: number, g: number, b: number): string {
    return '#' + [r, g, b].map(x => {
        const hex = x.toString(16);
        return hex.length === 1 ? '0' + hex : hex;
    }).join('');
}

function interpolateColor(colorA: string, colorB: string, t: number): string {
    t = Math.max(0, Math.min(1, t));
    const [ra, ga, ba] = hexToRgb(colorA);
    const [rb, gb, bb] = hexToRgb(colorB);

    const r = Math.round(ra + (rb - ra) * t);
    const g = Math.round(ga + (gb - ga) * t);
    const b = Math.round(ba + (bb - ba) * t);

    return rgbToHex(r, g, b);
}

function classifyEdge(sourceId: string, targetId: string, nodeById: Map<string, any>): string {
    const source = nodeById.get(sourceId) || {};
    if (source.parent === targetId) return 'parent';
    if (source.depends_on?.includes(targetId)) return 'depends_on';
    if (source.soft_depends_on?.includes(targetId)) return 'soft_depends_on';
    return 'link';
}

export function prepareGraphData(
    graph: { nodes?: any[]; edges?: any[] },
    structuralIds: Set<string> = new Set()
): PreparedGraph {
    const rawNodes = graph.nodes || [];
    const rawEdges = graph.edges || [];

    const nodeById = new Map<string, any>(rawNodes.map(n => [n.id, n]));
    const nodeIds = new Set(rawNodes.map(n => n.id));

    // Sanitize orphan parents: if a node's parent isn't in the graph, clear it
    rawNodes.forEach(n => {
        if (n.parent && !nodeIds.has(n.parent)) {
            n.parent = null;
        }
    });

    const parentIdsInGraph = new Set<string>();
    rawNodes.forEach(n => {
        if (n.parent) parentIdsInGraph.add(n.parent);
    });

    const validEdges = rawEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
    const maxDepth = Math.max(0, ...rawNodes.map(n => n.depth || 0));

    const weights = rawNodes.map(n => n.downstream_weight || 0);
    let maxWeight = Math.max(1, ...weights);
    if (maxWeight === 0) maxWeight = 1;

    const targetWeight = new Map<string, number>(
        rawNodes.map(n => [n.id, n.downstream_weight || 0])
    );

    const d3Nodes: GraphNode[] = [];
    for (const node of rawNodes) {
        const nid = node.id;
        const nodeType = node.node_type || "task";
        const status = (node.status || "inbox").toLowerCase();
        const priority = typeof node.priority === 'number' ? node.priority : 2;
        const dw = node.downstream_weight || 0;
        const stakeholder = node.stakeholder_exposure || false;
        const depth = node.depth || 0;
        const isStructural = structuralIds.has(nid);

        let label = node.title || node.label || nid;
        // Strip redundant type prefixes (e.g. "Epic: ...", "Project: ...")
        label = label.replace(/^(Epic|Project|Task|Goal|Note|Memory):\s*/i, '');
        const fullTitle = label;
        if (label.length > 60) label = label.substring(0, 57) + "...";

        // Skip file-system recency extraction as we are in browser JS.
        // Must rely on node.modified if passed in.
        const modified = node.modified || null;

        let typeScale = TYPE_BASE_SCALE[nodeType] ?? 1.0;
        if (['done', 'completed', 'cancelled'].includes(status)) {
            typeScale *= 0.6;
        }
        const weightFactor = dw > 0 ? 1 + Math.log1p(dw) * 0.3 : 1.0;
        const scale = typeScale * weightFactor;

        const baseFont = 10;
        const fontSize = Math.max(8, Math.min(16, Math.round(baseFont * scale)));

        const maxTextW = 160 * scale;
        const lines = wrapText(label, fontSize, maxTextW);
        const lineWidths = lines.map(line => estimateTextWidth(line, fontSize));
        const textW = lineWidths.length > 0 ? Math.max(...lineWidths) : 40;

        const padX = 16 * typeScale;
        const padY = 10 * typeScale;
        const nodeW = Math.max(textW + padX * 2, 55 * typeScale);
        const nodeH = Math.max(lines.length * (fontSize + 4) + padY * 2, 30 * typeScale);

        let fill: string;
        let textCol: string;

        if (isStructural) {
            fill = "#e2e8f0";
            textCol = "#94a3b8";
        } else {
            const weightNorm = Math.min(Math.log1p(dw) / Math.log1p(maxWeight), 1.0);
            const baseFill = STATUS_FILLS[status] || "#f1f5f9";
            const desaturation = Math.max(0, 0.4 - weightNorm * 0.4);
            fill = interpolateColor(baseFill, MUTED_FILL, desaturation);
            const baseText = STATUS_TEXT[status] || "#475569";
            textCol = interpolateColor(baseText, MUTED_TEXT, desaturation);
        }

        let opacity = 1.0;
        if (!isStructural && dw === 0) {
            const hasEdges = validEdges.some(e => e.source === nid || e.target === nid);
            if (!hasEdges) opacity = 0.5;
        }

        const isIncomplete = INCOMPLETE_STATUSES.has(status);
        let borderColor = PRIORITY_BORDERS[priority] || "#cbd5e1";

        // In Python we extracted assignee from frontmatter. Here we assume it's passed down.
        const assignee = node.assignee || null;
        if (assignee && isIncomplete) {
            borderColor = ASSIGNEE_COLORS[assignee] || ASSIGNEE_DEFAULT;
        }

        let borderWidth = 1.5 + Math.min(Math.log1p(dw) * 0.5, 2.5);
        if (priority <= 1 && isIncomplete) {
            borderWidth = Math.max(borderWidth, 3);
        }

        const shape = TYPE_SHAPE[nodeType] || "rect";
        const badge = TYPE_BADGE[nodeType] || "";

        d3Nodes.push({
            id: nid,
            label,
            fullTitle,
            lines,
            type: nodeType,
            shape,
            status,
            priority,
            depth,
            maxDepth,
            w: Math.round(nodeW * 10) / 10,
            h: Math.round(nodeH * 10) / 10,
            fontSize,
            fill,
            textColor: textCol,
            borderColor,
            borderWidth: Math.round(borderWidth * 10) / 10,
            stakeholder,
            structural: isStructural,
            dw: Math.round(dw * 10) / 10,
            modified,
            badge,
            charge: TYPE_CHARGE[nodeType] ?? -100,
            parent: node.parent || null,
            project: node.project || null,
            assignee,
            path: node.path || null,
            opacity,
            isLeaf: !parentIdsInGraph.has(nid),
            spotlight: Boolean(node.spotlight),
            x: node.x,
            y: node.y,
            layouts: node.layouts || {},
            _raw: node
        });
    }

    const d3Links: GraphEdge[] = [];
    for (const edge of validEdges) {
        let etype = edge.type || classifyEdge(edge.source, edge.target, nodeById);
        if (['soft_depends_on', 'link', 'wikilink'].includes(etype)) {
            etype = 'ref';
        }

        const force = EDGE_FORCE[etype as keyof typeof EDGE_FORCE] || EDGE_FORCE.ref;

        let color: string;
        let width: number;
        let dash: string;

        if (etype === 'parent') {
            color = "#f2aa0d"; // Amber for containment/parent
            width = 3.0;
            dash = "";
        } else if (etype === 'depends_on') {
            color = "#FF2A6D"; // Neon Red/Pink for dependencies
            width = 2.5;
            dash = "";
            const tw = targetWeight.get(edge.target) || 0;
            if (tw > 0 && maxWeight > 0) {
                const critRatio = Math.min(Math.log1p(tw) / Math.log1p(maxWeight), 1.0);
                if (critRatio > 0.5) {
                    width = 2.0 + critRatio * 2.0;
                    color = "#ff4d85"; // Lighter pink/red
                }
            }
        } else {
            color = "#a3a3a3"; // Lighter grey for references
            width = 1.5;
            dash = "4,3";
        }

        // Flip parent direction so arrows point parent -> child
        let linkSource = edge.source;
        let linkTarget = edge.target;
        if (etype === 'parent') {
            linkSource = edge.target;
            linkTarget = edge.source;
        }

        d3Links.push({
            source: linkSource,
            target: linkTarget,
            type: etype,
            color,
            width: Math.round(width * 10) / 10,
            dash,
            strength: force.strength,
            distance: force.distance
        });
    }

    const hasLayout = rawNodes.some(n =>
        n.x !== undefined ||
        n.layouts?.forceatlas2 ||
        n.layouts?.fa2
    );

    const availableLayouts = new Set<string>();
    rawNodes.forEach(n => {
        if (n.layouts) {
            Object.keys(n.layouts).forEach(k => availableLayouts.add(k));
        }
    });

    return {
        nodes: d3Nodes,
        links: d3Links,
        forceConfig: FORCE_CONFIG,
        hasLayout,
        availableLayouts: Array.from(availableLayouts).sort()
    };
}
