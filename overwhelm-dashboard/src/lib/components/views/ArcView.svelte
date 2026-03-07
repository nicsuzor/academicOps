<script lang="ts">
  import * as d3 from 'd3';
  import { graphData } from '../../stores/graph';
  import { toggleSelection } from '../../stores/selection';
  import { buildArcNode } from '../shared/NodeShapes';
  import { routeArcEdges } from '../shared/EdgeRenderer';
  import type { GraphNode, GraphEdge } from '../../data/prepareGraphData';

  export let containerGroup: SVGGElement;

  let nodesLayer: SVGGElement;
  let edgesLayer: SVGGElement;

  $: {
    if (containerGroup && $graphData && nodesLayer && edgesLayer) {
      drawArcDiagram();
    }
  }

  function drawArcDiagram() {
    if (!$graphData) return;

    const nodes = $graphData.nodes;
    const links = $graphData.links;

    // We do simple mapping: depth maps to Y bands. x maps to precomputed .x (flattened horizontally)

    // Use the 2nd and 98th percentile for domain bound normalization so stray outliers don't crush width
    const validX = nodes.map(n => n.x as number).filter(x => typeof x === 'number' && !isNaN(x)).sort((a,b) => a-b);
    let minX = 0, maxX = 1000;
    if (validX.length > 4) {
      minX = validX[Math.floor(validX.length * 0.02)];
      maxX = validX[Math.floor(validX.length * 0.98)] || minX + 1;
    }
    if (maxX === minX) maxX += 1;

    const mapX = d3.scaleLinear().domain([minX, maxX]).range([50, 1150]).clamp(true);

    const maxDepth = Math.max(...nodes.map(n => n.depth || 0));
    const hBand = 1500 / (maxDepth + 1);

    nodes.forEach(d => {
      d.y = ((d.depth || 0) * hBand) + (Math.random() * 20 - 10) + 100; // Small randomness jitter to avoid overlaps perfectly on line
      d.x = mapX((d.layouts?.arc?.x || d.x || 0) as number);
    });

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
      .on("click", (e, d) => { e.stopPropagation(); toggleSelection(d.id); });

    nEls.each(function(d) {
      const g = d3.select(this);
      g.selectAll("*").remove();
      buildArcNode(g, d);
    });
  }
</script>

{#if containerGroup}
  <g bind:this={edgesLayer}></g>
  <g bind:this={nodesLayer}></g>
{/if}
