import * as d3 from 'd3';
import type { GraphNode } from '../../data/prepareGraphData';

function statusOpacity(d: GraphNode) {
    if (['done', 'completed', 'cancelled'].includes(d.status)) return 0.15;
    if (d.status === 'active') return 0.9;
    return 0.35; // The baseline "Void" state
}

export function buildTaskCardNode(g: d3.Selection<SVGGElement, GraphNode, null, undefined>, d: GraphNode) {
    const hw = d.w / 2;
    const hh = d.h / 2;

    if (d.spotlight && d.isLeaf) {
        const pad = 9;
        const rx = d.shape === 'pill' ? hh + pad : (d.shape === 'rounded' ? 14 : 8);
        g.insert("rect", ":first-child")
            .attr("x", -hw - pad).attr("y", -hh - pad)
            .attr("width", (hw + pad) * 2).attr("height", (hh + pad) * 2)
            .attr("rx", rx).attr("fill", "none")
            .attr("stroke", "#f59e0b").attr("class", "spotlight-ring");
        g.append("text")
            .attr("x", 0).attr("y", -hh - pad - 5)
            .attr("text-anchor", "middle").attr("font-size", "8px")
            .attr("font-weight", "700").attr("fill", "#f59e0b")
            .attr("letter-spacing", "0.6px").attr("pointer-events", "none")
            .text("★ START HERE");
    }

    const opacity = statusOpacity(d);

    if (d.shape === "pill") {
        g.append("rect").attr("x", -hw).attr("y", -hh).attr("width", d.w).attr("height", d.h)
            .attr("rx", hh).attr("ry", hh)
            .attr("fill", d.fill).attr("stroke", d.borderColor).attr("stroke-width", d.borderWidth)
            .attr("fill-opacity", opacity).attr("stroke-opacity", Math.max(opacity, 0.4));
    } else if (d.shape === "hexagon") {
        const c = Math.min(hh * 0.6, 12);
        const pts = `${-hw + c},${-hh} ${hw - c},${-hh} ${hw},${0} ${hw - c},${hh} ${-hw + c},${hh} ${-hw},${0}`;
        g.append("polygon").attr("points", pts)
            .attr("fill", d.fill).attr("stroke", d.borderColor).attr("stroke-width", d.borderWidth)
            .attr("fill-opacity", opacity).attr("stroke-opacity", Math.max(opacity, 0.4));
    } else {
        g.append("rect").attr("x", -hw).attr("y", -hh).attr("width", d.w).attr("height", d.h)
            .attr("rx", d.shape === "rounded" ? 10 : 4)
            .attr("fill", d.fill).attr("stroke", d.borderColor).attr("stroke-width", d.borderWidth)
            .attr("fill-opacity", opacity).attr("stroke-opacity", Math.max(opacity, 0.4));
    }

    if (d.status === "blocked" && d.dw >= 2) {
        g.insert("rect", ":first-child")
            .attr("x", -hw - 4).attr("y", -hh - 4).attr("width", d.w + 8).attr("height", d.h + 8)
            .attr("rx", hh + 4).attr("ry", hh + 4).attr("fill", "none").attr("stroke", "#ef4444")
            .attr("class", "danger-pulse");
    }

    const lh = d.fontSize + 4;
    const ty = -(d.lines.length * lh) / 2 + d.fontSize * 0.38 + (d.badge ? 6 : 0);

    d.lines.forEach((line, i) => {
        g.append("text").attr("class", "node-text")
            .attr("x", 0).attr("y", ty + i * lh)
            .attr("text-anchor", "middle").attr("dominant-baseline", "central")
            .attr("font-size", d.fontSize + "px")
            .attr("fill", d.textColor).text(line);
    });

    if (d.dw > 0) {
        const tw = d.dw.toFixed(1).length * 6 + 16;
        g.append("rect")
            .attr("x", -tw / 2).attr("y", hh + 4)
            .attr("width", tw).attr("height", 15)
            .attr("rx", 7).attr("fill", d.borderColor).attr("opacity", 0.15);
        g.append("text")
            .attr("class", "node-badge").attr("x", 0).attr("y", hh + 14.5)
            .attr("text-anchor", "middle").attr("font-size", "8px")
            .attr("fill", d.borderColor).text("⚖ " + d.dw.toFixed(1));
    }
}

export function buildTreemapNode(g: d3.Selection<SVGGElement, any, null, undefined>, d: any) {
    // expects d._lw and d._lh to be populated by the layout algo if using true sizes, else uses d.w/d.h
    const w = d._lw || d.w;
    const h = d._lh || d.h;
    const opacity = statusOpacity(d);

    g.append("rect")
        .attr("x", -w / 2).attr("y", -h / 2).attr("width", w).attr("height", h)
        .attr("fill", d.fill).attr("fill-opacity", opacity)
        .attr("stroke", d.borderColor).attr("stroke-width", 1.5);

    if (w > 30 && h > 16) {
        const label = d.label || '';
        const fs = Math.max(6, Math.min(11, Math.min(w, h) * 0.25));
        const pad = 3;
        g.append("foreignObject")
            .attr("x", -w / 2 + pad).attr("y", -h / 2 + pad)
            .attr("width", w - pad * 2).attr("height", h - pad * 2)
            .append("xhtml:div")
            .style("font-size", fs + "px")
            .style("font-family", "-apple-system, sans-serif")
            .style("color", d.textColor || "#fff")
            .style("line-height", "1.2")
            .style("overflow", "hidden")
            .style("word-wrap", "break-word")
            .style("overflow-wrap", "break-word")
            .style("hyphens", "auto")
            .style("width", "100%")
            .style("height", "100%")
            .style("pointer-events", "none")
            .text(label);
    }
}

export function buildCirclePackNode(g: d3.Selection<SVGGElement, any, null, undefined>, d: any) {
    const r = Math.max(d._lr || d.w / 2 || 5, 2);
    const opacity = statusOpacity(d);

    g.append("circle").attr("cx", 0).attr("cy", 0).attr("r", r)
        .attr("fill", d.fill).attr("fill-opacity", opacity)
        .attr("stroke", d.borderColor).attr("stroke-width", 1);

    if (d.status === "blocked" && d.dw >= 2) {
        g.insert("circle", ":first-child")
            .attr("cx", 0).attr("cy", 0).attr("r", r + 4)
            .attr("fill", "none").attr("stroke", "#ef4444")
            .attr("class", "danger-pulse");
    }

    if (r > 15) {
        const label = (d.label || '').substring(0, 18);
        const fs = Math.max(6, Math.min(10, r * 0.35));
        g.append("text").attr("class", "node-text")
            .attr("x", 0).attr("y", 0)
            .attr("text-anchor", "middle").attr("dominant-baseline", "central")
            .attr("font-size", fs + "px").attr("fill", d.textColor || "#fff").text(label);
    }
}

export function buildArcNode(g: d3.Selection<SVGGElement, any, null, undefined>, d: any) {
    const r = Math.max(4, (d.dw || 1) * 0.5 + 3);
    const opacity = statusOpacity(d);
    g.append("circle").attr("cx", 0).attr("cy", 0).attr("r", r)
        .attr("fill", d.fill).attr("fill-opacity", opacity)
        .attr("stroke", d.borderColor).attr("stroke-width", 1);
}
