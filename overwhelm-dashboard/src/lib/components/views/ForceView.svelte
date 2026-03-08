<script lang="ts">
    import * as d3 from "d3";
    import { onMount, onDestroy } from "svelte";
    import { graphData } from "../../stores/graph";
    import { viewSettings } from "../../stores/viewSettings";
    import { filters } from "../../stores/filters";
    import { selection, toggleSelection } from "../../stores/selection";
    import { buildTaskCardNode } from "../shared/NodeShapes";
    import { routeForceEdges } from "../shared/EdgeRenderer";
    import type { GraphNode, GraphEdge } from "../../data/prepareGraphData";

    export let containerGroup: SVGGElement;

    let nodesLayer: SVGGElement;
    let edgesLayer: SVGGElement;
    let hullLayer: SVGGElement;

    let simulation: d3.Simulation<GraphNode, GraphEdge> | null = null;

    // Track cleanup and frame loop
    let frameId = 0;

    $: {
        if (
            containerGroup &&
            $graphData &&
            nodesLayer &&
            edgesLayer &&
            hullLayer
        ) {
            if (!simulation || $viewSettings.liveSimulation) {
                // Reset when settings deeply change, handled via function call instead of basic reactivity
                // to prevent overwhelming physics restarts.
                drawForceAndStartPhysics();
            } else {
                // Just a fast unlinked layout
                drawStaticForce();
            }
        }
    }

    // Flashlight Hover Effect Logic
    $: if (nodesLayer && edgesLayer && $graphData) {
        const hoveredId = $selection.hoveredNodeId;
        const nEls = d3.select(nodesLayer).selectAll(".node");
        const eEls = d3.select(edgesLayer).selectAll("path");

        if (hoveredId) {
            const neighbors = new Set<string>([hoveredId]);
            $graphData.links.forEach((l: any) => {
                const sid = l.source.id || l.source;
                const tid = l.target.id || l.target;
                if (sid === hoveredId) neighbors.add(tid);
                if (tid === hoveredId) neighbors.add(sid);
            });

            nEls.classed("dimmed", (d: any) => !neighbors.has(d.id)).classed(
                "illuminated",
                (d: any) => neighbors.has(d.id),
            );

            eEls.classed("dimmed", (l: any) => {
                const sid = l.source.id || l.source;
                const tid = l.target.id || l.target;
                return sid !== hoveredId && tid !== hoveredId;
            }).classed("illuminated", (l: any) => {
                const sid = l.source.id || l.source;
                const tid = l.target.id || l.target;
                return sid === hoveredId || tid === hoveredId;
            });
        } else {
            nEls.classed("dimmed", false).classed("illuminated", false);
            eEls.classed("dimmed", false).classed("illuminated", false);
        }
    }

    function projectColor(projectId: string) {
        let hash = 0;
        for (let i = 0; i < projectId.length; i++) {
            hash = (hash << 5) - hash + projectId.charCodeAt(i);
            hash |= 0;
        }
        const hue = Math.abs(hash) % 360;
        return `hsl(${hue}, 55%, 52%)`;
    }

    function updateHulls() {
        if (!$graphData || !hullLayer) return;

        const projectNodes = new Map<string, [number, number][]>();
        $graphData.nodes.forEach((n) => {
            if (
                typeof n.x !== "number" ||
                typeof n.y !== "number" ||
                n.x < -9000
            )
                return;
            const p = n.project;
            if (!p) return;
            if (!projectNodes.has(p)) projectNodes.set(p, []);
            projectNodes.get(p)!.push([n.x, n.y]);
        });

        const hullData: any[] = [];
        projectNodes.forEach((pts, pid) => {
            if (pts.length < 3) return;
            const hull = d3.polygonHull(pts);
            if (!hull) return;
            // Expand hull
            const cx = d3.mean(hull, (p) => p[0]) || 0;
            const cy = d3.mean(hull, (p) => p[1]) || 0;
            const expanded = hull.map(([x, y]) => {
                const dx = x - cx,
                    dy = y - cy;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                return [x + (dx / dist) * 40, y + (dy / dist) * 40];
            });
            hullData.push({ id: pid, points: expanded, cx, cy });
        });

        d3.select(hullLayer)
            .selectAll(".hull-path")
            .data(hullData, (d: any) => d.id)
            .join("path")
            .attr("class", "hull-path")
            .attr(
                "d",
                (d) =>
                    "M" + d.points.map((p: any) => p.join(",")).join("L") + "Z",
            )
            .attr("fill", (d) => projectColor(d.id))
            .attr("fill-opacity", 0.05)
            .attr("stroke", (d) => projectColor(d.id))
            .attr("stroke-opacity", 0.22)
            .attr("stroke-width", 1.5)
            .attr("stroke-dasharray", "5,3")
            .style("pointer-events", "none");

        d3.select(hullLayer)
            .selectAll(".hull-label")
            .data(hullData, (d: any) => d.id)
            .join("text")
            .attr("class", "hull-label")
            .attr("x", (d) => Number(d3.mean(d.points, (p: any) => p[0]) || 0))
            .attr(
                "y",
                (d) => Number(d3.min(d.points, (p: any) => p[1]) || 0) - 5,
            )
            .attr("text-anchor", "middle")
            .attr("font-size", "9px")
            .attr("font-weight", "700")
            .attr("fill", (d) => projectColor(d.id))
            .attr("opacity", 0.55)
            .attr("letter-spacing", "0.5px")
            .style("pointer-events", "none")
            .style("user-select", "none")
            .text((d) =>
                d.id.replace(/_/g, " ").toUpperCase().substring(0, 22),
            );
    }

    function bindDragAndClick(nEls: any) {
        nEls.style("cursor", "crosshair")
            .on("click", (e: any, d: any) => {
                e.stopPropagation();
                toggleSelection(d.id);
            })
            .on("mouseenter", (e: any, d: any) => {
                selection.update((s) => ({ ...s, hoveredNodeId: d.id }));
            })
            .on("mouseleave", (e: any, d: any) => {
                selection.update((s) => ({ ...s, hoveredNodeId: null }));
            })
            .call(
                d3
                    .drag<SVGGElement, GraphNode>()
                    .on("start", (e, d) => {
                        if ($viewSettings.liveSimulation && simulation) {
                            simulation.alphaTarget(0.1).restart();
                        }
                        d.fx = d.x;
                        d.fy = d.y;
                    })
                    .on("drag", (e, d) => {
                        d.fx = e.x;
                        d.fy = e.y;
                        if (!$viewSettings.liveSimulation) {
                            d.x = e.x;
                            d.y = e.y;
                            tickVisuals();
                        }
                    })
                    .on("end", (e, d) => {
                        if ($viewSettings.liveSimulation && simulation) {
                            simulation.alphaTarget(0);
                        }
                        d.fx = null;
                        d.fy = null;
                    }),
            );
    }

    function drawStaticForce() {
        if (!$graphData) return;
        if (simulation) {
            simulation.stop();
            simulation = null;
        }

        const data = $graphData;
        // Map initial precomputed FA2 layout
        data.nodes.forEach((d) => {
            d.x =
                d.layouts?.forceatlas2?.x ||
                d.layouts?.fa2?.x ||
                d.x ||
                Math.random() * 500;
            d.y =
                d.layouts?.forceatlas2?.y ||
                d.layouts?.fa2?.y ||
                d.y ||
                Math.random() * 500;
        });

        const nEls = d3
            .select(nodesLayer)
            .selectAll<SVGGElement, GraphNode>("g.node")
            .data(data.nodes, (d) => d.id)
            .join("g")
            .attr("class", "node")
            .attr("transform", (d) => `translate(${d.x},${d.y})`);

        nEls.each(function (d) {
            const g = d3.select(this) as any;
            g.selectAll("*").remove();
            buildTaskCardNode(g, d);
        });

        bindDragAndClick(nEls);

        const eEls = d3
            .select(edgesLayer)
            .selectAll<SVGPathElement, GraphEdge>("path")
            .data(data.links)
            .join("path")
            .attr("fill", "none")
            .attr("stroke", (d) => d.color)
            .attr("stroke-width", (d) => d.width)
            .attr("stroke-dasharray", (d) => d.dash || null)
            .attr("marker-end", "url(#ar)")
            .attr("stroke-linecap", "round")
            .attr("stroke-linejoin", "round")
            .attr("opacity", 0.3)
            .attr("class", "force-edge");

        routeForceEdges(eEls);
        updateHulls();
    }

    function tickVisuals() {
        d3.select(nodesLayer)
            .selectAll<SVGGElement, GraphNode>("g.node")
            .attr("transform", (d) => `translate(${d.x},${d.y})`);

        routeForceEdges(
            d3.select(edgesLayer).selectAll<SVGPathElement, GraphEdge>("path"),
        );
        updateHulls();
    }

    function drawForceAndStartPhysics() {
        if (!$graphData) return;

        // Setup elements
        drawStaticForce();

        // Start Simulation
        if (simulation) simulation.stop();

        const fc = $graphData.forceConfig;
        const cw = 1200,
            ch = 800; // Expected center bounds

        simulation = d3
            .forceSimulation<GraphNode, GraphEdge>($graphData.nodes)
            .force(
                "link",
                d3
                    .forceLink<GraphNode, GraphEdge>($graphData.links)
                    .id((d) => d.id)
                    .distance((d) => d.distance * (fc.linkDistMult || 1.0))
                    .strength((d) => d.strength),
            )
            .force(
                "charge",
                d3
                    .forceManyBody<GraphNode>()
                    .strength(
                        (d) =>
                            (d.charge || -100) *
                            (fc.chargeMult || 1.0) *
                            $viewSettings.chargeStrength,
                    )
                    .distanceMax(fc.chargeDistanceMax || 280),
            )
            .force(
                "collide",
                d3
                    .forceCollide<GraphNode>()
                    .radius(
                        (d) =>
                            Math.max(d.w / 2, d.h / 2) +
                            (fc.collisionPadding || 2),
                    )
                    .strength(fc.collisionStrength || 0.4)
                    .iterations(fc.collisionIterations || 3),
            )
            .force("center", d3.forceCenter(cw / 2, ch / 2).strength(0.05))
            .alphaDecay(fc.alphaDecay || 0.04)
            .velocityDecay(fc.velocityDecay || 0.55);

        // Warm up ticks
        const warmup = fc.warmupTicks || 80;
        for (let i = 0; i < warmup; i++) {
            simulation.tick();
        }

        // Live loop
        simulation.on("tick", tickVisuals);
    }

    onDestroy(() => {
        if (simulation) simulation.stop();
        cancelAnimationFrame(frameId);
    });
</script>

{#if containerGroup}
    <g bind:this={hullLayer} class="hull-layer"></g>
    <g bind:this={edgesLayer}></g>
    <g bind:this={nodesLayer}></g>
{/if}

<style>
    /* Flashlight depth-of-field state classes */
    :global(.node) {
        transition:
            opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1),
            filter 0.3s ease;
    }
    :global(.node.dimmed) {
        opacity: 0.15 !important;
        filter: grayscale(0.8) brightness(0.6);
    }
    :global(.node.illuminated) {
        opacity: 1 !important;
        filter: drop-shadow(0 0 16px var(--color-primary));
    }
    :global(path.force-edge) {
        transition:
            opacity 0.3s ease,
            stroke-width 0.3s ease,
            stroke 0.3s ease;
    }
    :global(path.force-edge.dimmed) {
        opacity: 0.05 !important;
    }
    :global(path.force-edge.illuminated) {
        opacity: 1 !important;
        stroke: var(--color-primary) !important;
        stroke-width: 2px !important;
    }
</style>
