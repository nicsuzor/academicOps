import * as d3 from 'd3';
import type { GraphNode } from '../../data/prepareGraphData';

function escapeHtml(str: string): string {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function statusOpacity(d: GraphNode) {
    if (['done', 'completed', 'cancelled'].includes(d.status)) return 0.15;
    if (d.status === 'active') return 0.9;
    return 0.35; // The baseline "Void" state
}

export function buildTaskCardNode(g: d3.Selection<SVGGElement, GraphNode, null, undefined>, d: GraphNode, isSelected = false) {
    const hw = d.w / 2;
    const hh = d.h / 2;

    // Add native tooltip to all nodes
    g.append("title").text(`${d.label} (${d.status})\nPriority: P${d.priority}\nProject: ${d.project || 'None'}`);

    if (isSelected) {
        g.classed("selected-node", true);
    } else {
        g.classed("selected-node", false);
    }

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

function projectHue(projectId: string): number {
    let hash = 0;
    const id = projectId || 'default';
    for (let i = 0; i < id.length; i++) {
        hash = (hash << 5) - hash + id.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash) % 360;
}

export function buildTreemapNode(g: d3.Selection<SVGGElement, any, null, undefined>, d: any, isSelected = false) {
    // expects d._lw and d._lh to be populated by the layout algo if using true sizes, else uses d.w/d.h
    const w = d._lw || d.w;
    const h = d._lh || d.h;
    const isParent = !d.isLeaf;
    const opacity = statusOpacity(d);

    if (isSelected) {
        g.classed("selected-node", true);
    } else {
        g.classed("selected-node", false);
    }

    // Base color logic: Project-based Hue
    const hue = projectHue(d.project || d.id);

    // Priority-based spectral colors for leaves (optional override or accent)
    const spectralHues = [
        "#ef4444", // 0 Critical (Red)
        "#f97316", // 1 High (Orange)
        "#f59e0b", // 2 Med (Amber)
        "#06b6d4", // 3 Low (Cyan)
        "#8b5cf6", // 4 Backlog (Purple)
    ];

    let cellColor: string;
    if (isParent) {
        // Parents get a stable project hue
        cellColor = `hsl(${hue}, 40%, 25%)`;
    } else {
        // Leaves get priority color if active, else project-based shade
        if (d.priority !== undefined && d.priority >= 0 && d.priority <= 2 && d.status !== 'done') {
            cellColor = spectralHues[d.priority];
        } else {
            const lightness = d.status === 'active' ? '35%' : '15%';
            cellColor = `hsl(${hue}, 35%, ${lightness})`;
        }
    }

    // Dim completed tasks
    if (d.status === "done" || d.status === "completed" || d.status === "cancelled") {
        cellColor = `hsl(${hue}, 10%, 15%)`;
    }

    // Helper to calculate contrast color for text
    const getContrastColor = (hex: string) => {
        if (!hex) return '#ffffff';
        // If HSL string
        if (hex.startsWith('hsl')) {
            const matches = hex.match(/hsl\(\d+,\s*\d+%,\s*(\d+)%/);
            if (matches && parseInt(matches[1]) > 60) return '#000000';
            return '#ffffff';
        }
        if (!hex.startsWith('#')) return '#ffffff';
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
        return (yiq >= 128) ? '#000000' : '#ffffff';
    };

    const textColor = getContrastColor(cellColor);

    // Add native tooltip
    g.append("title").text(`${d.label} (${d.status})\nPriority: P${d.priority}\nProject: ${d.project || 'None'}`);

    // Base solid background
    g.append("rect")
        .attr("x", -w / 2).attr("y", -h / 2).attr("width", w).attr("height", h)
        .attr("rx", 4)
        .attr("fill", cellColor).attr("fill-opacity", isParent ? 0.2 : 0.6)
        .attr("stroke", isSelected ? "#fff" : cellColor)
        .attr("stroke-width", isSelected ? 4 : 1)
        .style("transition", "all 0.2s ease");

    if (isParent && h > 20) {
        // Parent Header Bar
        const headerH = Math.min(28, h * 0.8);
        g.append("rect")
            .attr("x", -w / 2).attr("y", -h / 2)
            .attr("width", w).attr("height", headerH)
            .attr("rx", 4)
            .attr("fill", cellColor).attr("fill-opacity", 0.8);
    }

    // Operator grid pattern overlay for active tasks
    if (d.status !== "done" && d.status !== "completed" && d.status !== "cancelled" && !isParent) {
        g.append("rect")
            .attr("x", -w / 2).attr("y", -h / 2).attr("width", w).attr("height", h)
            .attr("rx", 4)
            .attr("fill", "url(#holographic-grid)").attr("pointer-events", "none")
            .attr("opacity", 0.3);
    }

    // Striped overlay for blocked tasks
    if (d.status === "blocked") {
        g.append("rect")
            .attr("x", -w / 2).attr("y", -h / 2).attr("width", w).attr("height", h)
            .attr("rx", 4)
            .attr("fill", "url(#striped-blocked)").attr("pointer-events", "none")
            .attr("opacity", 0.4);
    }

    // Double border for Critical (P0) priorities
    if (d.priority === 0 && !isParent) {
        g.append("rect")
            .attr("x", -w / 2 + 3).attr("y", -h / 2 + 3).attr("width", Math.max(0, w - 6)).attr("height", Math.max(0, h - 6))
            .attr("fill", "none")
            .attr("stroke", "#fff").attr("stroke-width", 1)
            .attr("stroke-dasharray", "2,2").attr("pointer-events", "none");
    }

    // Only attempt to render text if we have enough space. Small nodes collapse to solid colored boxes.
    if (w > 35 && h > 25) {
        const label = escapeHtml(d.label || '');
        const pad = 6;

        if (isParent) {
            // Parent nodes: Draw label in the header bar
            if (w > 40) {
                g.append("foreignObject")
                    .attr("x", -w / 2 + pad).attr("y", -h / 2 + 2)
                    .attr("width", Math.max(0, w - pad * 2)).attr("height", 24)
                    .style("pointer-events", "none")
                    .append("xhtml:div")
                    .style("display", "flex")
                    .style("align-items", "center")
                    .style("width", "100%")
                    .style("height", "100%")
                    .style("pointer-events", "none")
                    .html(`
                        <div style="font-size: 11px; font-weight: 700; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-transform: uppercase; letter-spacing: 0.05em;">
                            ${label}
                        </div>
                    `);
            }
        } else {
            // Leaf nodes: Draw title
            const fs = Math.max(8, Math.min(13, Math.min(w, h) * 0.28));
            const linesAvailable = Math.max(1, Math.floor((h - pad * 2) / (fs * 1.2)));

            const isBlocked = d.status === "blocked";

            g.append("foreignObject")
                .attr("x", -w / 2 + pad).attr("y", -h / 2 + pad)
                .attr("width", Math.max(0, w - pad * 2)).attr("height", Math.max(0, h - pad * 2))
                .style("pointer-events", "none")
                .append("xhtml:div")
                .style("display", "flex")
                .style("flex-direction", "column")
                .style("justify-content", "flex-start")
                .style("width", "100%")
                .style("height", "100%")
                .style("pointer-events", "none")
                .html(`
                    ${isBlocked && h > 40 ? `<div style="display: flex; justify-content: flex-end; margin-bottom: 2px;"><span class="material-symbols-outlined" style="font-size: ${fs + 2}px; color: #fff; background: var(--color-destructive); border-radius: 50%;">warning</span></div>` : ''}
                    <div style="font-size: ${fs}px; font-weight: 500; color: ${textColor}; line-height: 1.2; overflow: hidden; display: -webkit-box; -webkit-line-clamp: ${linesAvailable}; -webkit-box-orient: vertical; letter-spacing: -0.01em;">
                        ${label}
                    </div>
                `);
        }
    }
}
export function buildCirclePackNode(g: d3.Selection<SVGGElement, any, null, undefined>, d: any, isSelected = false) {
    const r = Math.max(d._lr || d.w / 2 || 5, 2);
    const opacity = statusOpacity(d);

    // Add native tooltip
    g.append("title").text(`${d.label} (${d.status})`);

    if (isSelected) {
        g.classed("selected-node", true);
    } else {
        g.classed("selected-node", false);
    }

    g.append("circle").attr("cx", 0).attr("cy", 0).attr("r", r)
        .attr("fill", d.fill).attr("fill-opacity", opacity)
        .attr("stroke", isSelected ? "#fff" : d.borderColor).attr("stroke-width", isSelected ? 4 : 1);

    if (d.status === "blocked" && d.dw >= 2) {
        g.insert("circle", ":first-child")
            .attr("cx", 0).attr("cy", 0).attr("r", r + 4)
            .attr("fill", "none").attr("stroke", "#ef4444")
            .attr("class", "danger-pulse");
    }

    if (r > 8) {
        const label = (d.label || '').substring(0, 24);
        const fs = Math.max(5, Math.min(12, r * 0.4));
        g.append("text").attr("class", "node-text")
            .attr("x", 0).attr("y", 0)
            .attr("text-anchor", "middle").attr("dominant-baseline", "central")
            .attr("font-size", fs + "px").attr("fill", d.textColor || "#fff").attr("opacity", 0.9)
            .text(label.length > 20 ? label.substring(0, 18) + '...' : label);
    }
}

export function buildArcNode(g: d3.Selection<SVGGElement, any, null, undefined>, d: any, isSelected = false) {
    const r = Math.max(4, (d.dw || 1) * 0.5 + 3);
    const opacity = statusOpacity(d);

    // Add native tooltip
    g.append("title").text(`${d.label} (${d.status})`);

    if (isSelected) {
        g.classed("selected-node", true);
    } else {
        g.classed("selected-node", false);
    }

    g.append("circle").attr("cx", 0).attr("cy", 0).attr("r", r)
        .attr("fill", d.fill).attr("fill-opacity", opacity)
        .attr("stroke", isSelected ? "#fff" : d.borderColor).attr("stroke-width", isSelected ? 4 : 1);
        
    g.append("text").attr("class", "node-text")
        .attr("x", 0).attr("y", r + 12)
        .attr("text-anchor", "middle").attr("font-size", "8px")
        .attr("fill", "#a3a3a3").attr("opacity", 0.8)
        .text((d.label || '').substring(0, 15));
}
