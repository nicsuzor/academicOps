<script lang="ts">
    import * as d3 from "d3";
    import { onMount } from "svelte";
    import { graphData } from "../../stores/graph";
    import { filters } from "../../stores/filters";
    import { toggleSelection, selection } from "../../stores/selection";
    import { buildTreemapNode } from "../shared/NodeShapes";
    import { routeTreemapEdges } from "../shared/EdgeRenderer";

    export let containerGroup: SVGGElement;
    export let width = 2000;
    export let height = 1000;

    let nodesLayer: SVGGElement;
    let edgesLayer: SVGGElement;

    let layoutComputed = false;
    let lastGraphData: any = null;

    $: {
        if (containerGroup && $graphData && nodesLayer && edgesLayer && $selection && width && height) {
            const dataChanged = $graphData !== lastGraphData;
            if (dataChanged) {
                computeTreemapLayout();
                lastGraphData = $graphData;
                layoutComputed = true;
            }
            if (layoutComputed) {
                renderTreemapNodes();
            }
        }
    }

    let activeSynthNodes: any[] = [];

    function computeTreemapLayout() {
        if (!$graphData) return;

        const data = $graphData;
        const nodes = data.nodes;

        const rootId = "__root__";
        const nodeIdSet = new Set(nodes.map(n => n.id));
        const treemapNodes = [
            { id: rootId, parent: "", type: "root", label: "ROOT" },
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
                .parentId((d) => d.parent)(treemapNodes);
        } catch (e) {
            console.warn("Stratify failed for Treemap", e);
            return;
        }

        const computeSum = (d: any) => {
            if (d.children?.length) return 0;
            if (["done", "completed", "cancelled"].includes(d.status)) return 0.1;
            return Math.max(2, d.dw || 1);
        };

        root.sum(computeSum).sort((a, b) => (a.data.priority ?? 5) - (b.data.priority ?? 5));

        const canvasW = 3000;
        const aspect = (height && width) ? height / width : 0.5;
        const canvasH = canvasW * aspect;

        const treemap = d3.treemap<any>()
            .size([canvasW, canvasH])
            .paddingInner(12)
            .paddingOuter(14)
            .paddingTop(36)
            .tile(d3.treemapSquarify.ratio(1.3))
            .round(true);

        treemap(root);

        const MIN_TASK_AREA = 12000; // More aggressive rollup threshold
        const partialDisplayMap = new Map<string, any[]>();
        const synthNodes: any[] = [];
        const hNodeMap = new Map<string, d3.HierarchyNode<any>>();

        root.descendants().forEach(d => hNodeMap.set(d.data.id, d));

        root.descendants().forEach(d => {
            if (d.children && d.children.length > 0 && d.depth > 0) {
                const w = d.x1 - d.x0;
                const h = d.y1 - d.y0;
                const area = w * h;
                const capacity = Math.max(0, Math.floor(area / MIN_TASK_AREA));

                const sortedChildren = [...d.children].sort((a, b) => {
                    const pa = a.data.priority ?? 5;
                    const pb = b.data.priority ?? 5;
                    if (pa !== pb) return pa - pb;
                    return (b.value || 0) - (a.value || 0);
                });

                if (capacity <= 1 || (h > w * 1.4)) {
                    partialDisplayMap.set(d.data.id, []);
                } else if (d.children.length > capacity) {
                    const displayCount = Math.max(1, capacity - 1);
                    const toDisplay = sortedChildren.slice(0, displayCount).map(c => ({...c.data, _weight: 1.0}));
                    const overflowNode = {
                        id: d.data.id + "__overflow__",
                        label: "[...]",
                        status: "active",
                        priority: 9,
                        project: d.data.project,
                        _weight: 1.0,
                        _isOverflow: true
                    };
                    toDisplay.push(overflowNode);
                    synthNodes.push(overflowNode);
                    partialDisplayMap.set(d.data.id, toDisplay);
                } else {
                    partialDisplayMap.set(d.data.id, d.children.map(c => ({...c.data, _weight: 1.0})));
                }
            }
        });

        // RE-LAYOUT with pruned tree
        const prunedRoot = d3.hierarchy(root.data, d => {
            if (partialDisplayMap.has(d.id)) return partialDisplayMap.get(d.id);
            const hNode = hNodeMap.get(d.id);
            return hNode && hNode.children ? hNode.children.map(c => c.data) : null;
        });

        prunedRoot.sum(d => d._weight || (d.children ? 0 : 1)).sort((a, b) => {
            if (a.data._isOverflow) return 1;
            if (b.data._isOverflow) return -1;
            const pa = a.data.priority ?? 5;
            const pb = b.data.priority ?? 5;
            if (pa !== pb) return pa - pb;
            return (b.value || 0) - (a.value || 0);
        });

        treemap(prunedRoot);

        const layoutMap = new Map();
        prunedRoot.descendants().forEach((d: any) => {
            if (d.data.id === rootId) return;
            layoutMap.set(d.data.id, {
                x: d.x0 + (d.x1 - d.x0) / 2,
                y: d.y0 + (d.y1 - d.y0) / 2,
                w: d.x1 - d.x0,
                h: d.y1 - d.y0,
                depth: d.depth,
                isLeaf: !d.children || d.children.length === 0,
                d3Node: d,
            });
        });

        nodes.forEach((n) => {
            const l = layoutMap.get(n.id);
            if (l) {
                n.x = l.x; n.y = l.y; n.w = l.w; n.h = l.h;
                n.depth = l.depth;
                n._isLeaf = l.isLeaf;
                n._isOverflow = false;
            } else {
                n.x = -9999; n.y = -9999;
            }
        });

        activeSynthNodes = [];
        synthNodes.forEach(s => {
            const l = layoutMap.get(s.id);
            if (l) {
                s.x = l.x; s.y = l.y; s.w = l.w; s.h = l.h;
                s.depth = l.depth;
                s._isLeaf = true;
                s._isOverflow = true;
                activeSynthNodes.push(s);
            }
        });
    }

    function renderTreemapNodes() {
        const data = $graphData;
        if (!data) return;

        const visibleNodes = [...data.nodes, ...activeSynthNodes]
            .filter(n => (n.x || 0) > -9000)
            .sort((a, b) => (a.depth || 0) - (b.depth || 0));

        const nEls = d3
            .select(nodesLayer)
            .selectAll<SVGGElement, any>("g.node")
            .data(visibleNodes, (d: any) => d.id)
            .join("g")
            .attr("class", "node")
            .attr("transform", (d) => `translate(${d.x},${d.y})`)
            .style("cursor", (d) => d._isOverflow ? "default" : "pointer")
            .on("click", (e, d) => {
                if (d._isOverflow) return;
                e.stopPropagation();
                toggleSelection(d.id);
            })
            .on("mouseenter", (e, d) => {
                if (d._isOverflow) return;
                selection.update(s => ({ ...s, hoveredNodeId: d.id }));
            })
            .on("mouseleave", () => {
                selection.update(s => ({ ...s, hoveredNodeId: null }));
            });

        const activeNodeId = $selection.activeNodeId;
        const hoveredNodeId = $selection.hoveredNodeId;

        nEls.each(function (d) {
            const g = d3.select(this);
            const isSelected = d.id === activeNodeId;
            const isHovered = d.id === hoveredNodeId;

            const lastSelected = d._lastSelected;
            if (g.selectAll("*").empty() || lastSelected !== isSelected) {
                g.selectAll("*").remove();
                const tempD = { ...d, _lw: d.w, _lh: d.h, isLeaf: d._isLeaf };
                buildTreemapNode(g as any, tempD, isSelected);
                d._lastSelected = isSelected;
            }

            g.classed("hovered-node", isHovered);
        });

        const eEls = d3
            .select(edgesLayer)
            .selectAll("path")
            .data(data.links)
            .join("path");

        routeTreemapEdges(eEls);
    }
</script>

{#if containerGroup}
    <g bind:this={edgesLayer}></g>
    <g bind:this={nodesLayer}></g>
{/if}
