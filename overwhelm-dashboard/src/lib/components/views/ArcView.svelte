<script lang="ts">
  import * as d3 from 'd3';
  import { graphData } from '../../stores/graph';
  import { toggleSelection, selection } from '../../stores/selection';
  import { viewSettings } from '../../stores/viewSettings';
  import { buildArcNode } from '../shared/NodeShapes';
  import { routeArcEdges } from '../shared/EdgeRenderer';
  import type { GraphNode, GraphEdge } from '../../data/prepareGraphData';

  export let containerGroup: SVGGElement;

  let nodesLayer: SVGGElement;
  let edgesLayer: SVGGElement;

  let layoutComputed = false;
  let lastGraphData: any = null;
  let lastArcScale: number | undefined = undefined;

  $: {
    if (containerGroup && $graphData && nodesLayer && edgesLayer && $selection && $viewSettings) {
      const dataChanged = $graphData !== lastGraphData;
      const settingsChanged = $viewSettings.arcVerticalSpacing !== lastArcScale;

      if (dataChanged || settingsChanged) {
        computeArcLayout();
        lastGraphData = $graphData;
        lastArcScale = $viewSettings.arcVerticalSpacing;
        layoutComputed = true;
      }
      if (layoutComputed) {
        renderArcNodes();
      }
    }
  }

  function computeArcLayout() {
    if (!$graphData) return;

    const nodes = [...$graphData.nodes];

    // Sort nodes for better Arc diagram logic: by depth, then priority, then status
    nodes.sort((a, b) => {
        if ((a.depth || 0) !== (b.depth || 0)) return (a.depth || 0) - (b.depth || 0);
        const pa = a.priority ?? 5;
        const pb = b.priority ?? 5;
        if (pa !== pb) return pa - pb;
        const statusOrder: Record<string, number> = { "active": 0, "blocked": 1, "waiting": 2, "review": 3, "done": 4, "completed": 4, "cancelled": 5 };
        const sa = statusOrder[a.status] ?? 10;
        const sb = statusOrder[b.status] ?? 10;
        return sa - sb;
    });

    // We do simple mapping: depth maps to Y bands. x maps to sorted index within depth
    const maxDepth = Math.max(...nodes.map(n => n.depth || 0), 1);
    const hBand = (1200 / (maxDepth + 1)) * ($viewSettings.arcVerticalSpacing || 1.0);

    const nodesByDepth = new Map<number, GraphNode[]>();

    nodes.forEach(n => {
        const d = n.depth || 0;
        if (!nodesByDepth.has(d)) nodesByDepth.set(d, []);
        nodesByDepth.get(d)!.push(n);
    });

    nodesByDepth.forEach((depthNodes, depth) => {
        const count = depthNodes.length;
        const xStep = 1200 / (count + 1);
        depthNodes.forEach((n, i) => {
            n.x = xStep * (i + 1) + 100;
            n.y = (depth * hBand) + 100 + (Math.random() * 10 - 5);
        });
    });
  }

  function renderArcNodes() {
    const data = $graphData;
    if (!data) return;

    const nodes = data.nodes;
    const links = data.links;

    const eEls = d3.select(edgesLayer).selectAll<SVGPathElement, GraphEdge>("path")
      .data(links)
      .join("path")
      .attr("fill", "none")
      .attr("stroke", d => d.color)
      .attr("stroke-width", d => d.width)
      .attr("stroke-dasharray", d => d.dash || null)
      .attr("marker-end", "url(#ar)");

    routeArcEdges(eEls);

    const nEls = d3.select(nodesLayer).selectAll<SVGGElement, GraphNode>("g.node")
      .data(nodes, d => d.id)
      .join("g")
      .attr("class", "node")
      .attr("transform", d => `translate(${d.x},${d.y})`)
      .style("cursor", "pointer")
      .on("click", (e, d) => { e.stopPropagation(); toggleSelection(d.id); })
      .on("mouseenter", (e, d) => {
        selection.update(s => ({ ...s, hoveredNodeId: d.id }));
      })
      .on("mouseleave", () => {
        selection.update(s => ({ ...s, hoveredNodeId: null }));
      });

    const activeNodeId = $selection.activeNodeId;

    nEls.each(function(d) {
      const g = d3.select(this);
      const isSelected = d.id === activeNodeId;

      const lastSelected = (d as any)._lastSelected;
      if (g.selectAll("*").empty() || lastSelected !== isSelected) {
          g.selectAll("*").remove();
          buildArcNode(g as any, d, isSelected);
          (d as any)._lastSelected = isSelected;
      }
    });
  }
</script>

{#if containerGroup}
  <g bind:this={edgesLayer}></g>
  <g bind:this={nodesLayer}></g>
{/if}
