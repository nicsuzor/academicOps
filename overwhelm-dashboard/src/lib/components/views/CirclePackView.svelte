<script lang="ts">
    import * as d3 from "d3";
    import { graphData } from "../../stores/graph";
    import { toggleSelection, selection } from "../../stores/selection";
    import { buildCirclePackNode } from "../shared/NodeShapes";
    import { routeContainmentEdges } from "../shared/EdgeRenderer";

    export let containerGroup: SVGGElement;

    let nodesLayer: SVGGElement;
    let edgesLayer: SVGGElement;

    $: {
        if (containerGroup && $graphData && nodesLayer && edgesLayer) {
            drawCirclePack();
        }
    }

    function drawCirclePack() {
        if (!$graphData) return;

        const data = $graphData;
        const nodes = data.nodes;

        const rootId = "__root__";
        const nodeIdSet = new Set(nodes.map(n => n.id));
        const packNodes = [
            { id: rootId, parent: "", type: "root" },
            ...nodes.map((n) => ({
                ...n,
                parent: (n.parent && nodeIdSet.has(n.parent)) ? n.parent : rootId,
            })),
        ];

        let root;
        try {
            root = d3
                .stratify<any>()
                .id((d) => d.id)
                .parentId((d) => d.parent)(packNodes);
        } catch (e) {
            console.warn("Stratify failed for Circle Pack", e);
            return;
        }

        root.sum((d) =>
            d.children?.length ? 0 : Math.max(1, d.dw || 1),
        ).sort((a, b) => (b.value || 0) - (a.value || 0));

        d3.pack<any>().size([1600, 1600]).padding(6)(root);

        const leavesAndParents = root
            .descendants()
            .filter((d) => d.data.id !== rootId && d.value! > 0);

        const layoutMap = new Map();
        leavesAndParents.forEach((d: any) => {
            layoutMap.set(d.data.id, {
                x: d.x,
                y: d.y,
                r: d.r,
                d3Node: d,
            });
        });

        nodes.forEach((n) => {
            const l = layoutMap.get(n.id);
            if (l) {
                n.x = l.x - 800; // center at 0
                n.y = l.y - 800;
            } else {
                n.x = -9999;
                n.y = -9999;
            }
        });

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
            g.selectAll("*").remove();

            const layoutData = layoutMap.get(d.id);
            if (layoutData) {
                const tempD = { ...d, _lr: layoutData.r };
                buildCirclePackNode(g as any, tempD);
            }
        });

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
