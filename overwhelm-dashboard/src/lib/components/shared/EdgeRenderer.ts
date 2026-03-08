import type { Selection } from 'd3';

export function routeContainmentEdges(linkSelection: Selection<any, any, any, any>) {
    // In tree/circle pack containment views, edges are hidden
    linkSelection.attr("d", null).attr("opacity", 0);
}

export function routeArcEdges(linkSelection: Selection<any, any, any, any>) {
    linkSelection.attr("d", (d: any) => {
        if (!d.source || !d.target) return null;
        const sx = d.source.x, sy = d.source.y;
        const tx = d.target.x, ty = d.target.y;
        if (sx == null || tx == null) return null;

        const dx = tx - sx;
        // quadratic bezier arc
        if (Math.abs(sy - ty) < 2) {
            // same row/depth: arch upward
            const rx = (sx + tx) / 2;
            const ry = sy - Math.abs(dx) * 0.3;
            return `M${sx},${sy} Q${rx},${ry} ${tx},${ty}`;
        }
        // different row: S-curve
        const my = (sy + ty) / 2;
        return `M${sx},${sy} C${sx},${my} ${tx},${my} ${tx},${ty}`;
    }).attr("opacity", (d: any) => d.type === "ref" ? 0.3 : 0.6);
}

export function routeForceEdges(linkSelection: Selection<any, any, any, any>) {
    linkSelection.attr("d", (d: any) => {
        if (!d.source || !d.target) return null;
        const sx = d.source.x, sy = d.source.y;
        const tx = d.target.x, ty = d.target.y;
        if (sx == null || tx == null) return null;
        return `M${sx},${sy} L${tx},${ty}`;
    }).attr("opacity", (d: any) => d.type === "ref" ? 0.4 : 0.7);
}

export function routeSfdpEdges(linkSelection: Selection<any, any, any, any>) {
    // Essentially identical to force in terms of visual routing
    routeForceEdges(linkSelection);
}
