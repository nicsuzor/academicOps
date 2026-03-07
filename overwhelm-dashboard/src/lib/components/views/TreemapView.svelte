<script lang="ts">
    import * as d3 from "d3";
    import { onMount } from "svelte";
    import { graphData } from "../../stores/graph";
    import { filters } from "../../stores/filters";
    import { toggleSelection, selection } from "../../stores/selection";
    import { buildTreemapNode } from "../shared/NodeShapes";
    import { routeContainmentEdges } from "../shared/EdgeRenderer";

    export let containerGroup: SVGGElement;

    let nodesLayer: SVGGElement;
    let edgesLayer: SVGGElement;

    $: {
        if (containerGroup && $graphData && nodesLayer && edgesLayer) {
            drawTreemap();
        }
    }

    function drawTreemap() {
        if (!$graphData) return;

        const data = $graphData;
        const nodes = data.nodes;

        // Treemap needs a single root. Create a virtual root if needed.
        const rootId = "__root__";
        const nodeIdSet = new Set(nodes.map(n => n.id));
        const treemapNodes = [
            { id: rootId, parent: "", type: "root" },
            ...nodes.map((n) => ({
                ...n,
                parent: (n.parent && nodeIdSet.has(n.parent)) ? n.parent : rootId,
            })),
        ];

        // Build hierarchy
        let root;
        try {
            root = d3
                .stratify<any>()
                .id((d) => d.id)
                .parentId((d) => d.parent)(treemapNodes);
        } catch (e) {
            console.warn("Stratify failed for Treemap", e);
            return;
        }

        root.sum((d) =>
            d.children?.length ? 0 : Math.max(1, d.dw || 1)
        ).sort((a, b) => (b.value || 0) - (a.value || 0));

        // Calculate layout
        d3
            .treemap<any>()
            .size([1600, 1000]) // Give it more breathing room
            .paddingOuter(16)
            .paddingTop(28)
            .paddingInner(8)
            .tile(d3.treemapSquarify.ratio(1.5))
            .round(true)(root);

        // Filter out virtual root
        const leavesAndParents = root
            .descendants()
            .filter((d) => d.data.id !== rootId && d.value! > 0);

        // Map computed coordinates back to node objects
        const layoutMap = new Map();
        leavesAndParents.forEach((d: any) => {
            layoutMap.set(d.data.id, {
                x: d.x0 + (d.x1 - d.x0) / 2,
                y: d.y0 + (d.y1 - d.y0) / 2,
                w: d.x1 - d.x0,
                h: d.y1 - d.y0,
                d3Node: d,
            });
        });

        // We mutate the store's node coordinates for zoom fit and hover calculations
        nodes.forEach((n) => {
            const l = layoutMap.get(n.id);
            if (l) {
                n.x = l.x;
                n.y = l.y;
                n.w = l.w;
                n.h = l.h;
            } else {
                // If it wasn't laid out (e.g. 0 value parent), hide it far away
                n.x = -9999;
                n.y = -9999;
            }
        });

        // Render nodes
        const nEls = d3
            .select(nodesLayer)
            .selectAll<SVGGElement, any>("g.node")
            .data(nodes.filter(n => (n.x || 0) > -9000), (d: any) => d.id)
            .join("g")
            .attr("class", "node")
            .attr("transform", (d) => `translate(${d.x},${d.y})`)
            .style("cursor", "pointer")
            .on("click", (e, d) => {
                e.stopPropagation();
                toggleSelection(d.id);
            })
            .on("mouseenter", (e, d) => {
                selection.update(s => ({ ...s, hoveredNodeId: d.id }));
            })
            .on("mouseleave", () => {
                selection.update(s => ({ ...s, hoveredNodeId: null }));
            });

        nEls.each(function (d) {
            const g = d3.select(this);
            g.selectAll("*").remove(); // clear

            // build node shape
            const layoutData = layoutMap.get(d.id);
            if (layoutData) {
                // temp override for builder to use actual screen width/height
                const tempD = { ...d, _lw: layoutData.w, _lh: layoutData.h };
                buildTreemapNode(g as any, tempD);
            }
        });

        // Treemap containment usually hides edges, we call routeContainmentEdges just to be clean
        const eEls = d3
            .select(edgesLayer)
            .selectAll("path")
            .data(data.links)
            .join("path");

        routeContainmentEdges(eEls);
    }
</script>

{#if containerGroup}
    <g bind:this={edgesLayer}></g>
    <g bind:this={nodesLayer}></g>
{/if}
