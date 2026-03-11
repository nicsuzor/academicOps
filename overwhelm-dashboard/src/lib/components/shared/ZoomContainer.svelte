<script lang="ts">
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { graphData } from '../../stores/graph';
  import { viewSettings } from '../../stores/viewSettings';
  import { selection, clearSelection } from '../../stores/selection';
  import type { GraphNode } from '../../data/prepareGraphData';

  let svgElement: SVGSVGElement;
  let containerGroup: SVGGElement;

  let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown>;
  let svgSelection: d3.Selection<SVGSVGElement, unknown, null, undefined>;

  export let innerWidth = 1000;
  export let innerHeight = 800;

  // Set context so children know we have a zoom container if needed
  import { setContext } from 'svelte';
  setContext('zoom', {
    autoZoomToFit
  });

  onMount(() => {
    svgSelection = d3.select(svgElement);

    // Setup D3 Zoom
    zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.02, 10])
      .on("zoom", (e) => {
        d3.select(containerGroup).attr("transform", e.transform);
      });

    svgSelection.call(zoomBehavior);

    return () => {
      svgSelection.on('.zoom', null); // cleanup
    };
  });

  // Export so parent (+page.svelte) or child views can trigger it
  export function autoZoomToFit(nodesToFit?: GraphNode[], delay: number = 0, trimOutliers: boolean = true) {
    if (!svgSelection || !zoomBehavior) return;

    let ns = nodesToFit;
    if (!ns || ns.length === 0) {
      if (!$graphData || $graphData.nodes.length === 0) return;
      ns = $graphData.nodes.filter(n => typeof n.x === 'number' && typeof n.y === 'number' && n.x > -9000); // Exclude hidden/unpositioned
    }
    if (!ns || ns.length === 0) return;

    function doZoom() {
      let fitNodes = ns!;
      if (trimOutliers && fitNodes.length > 8) {
        const xs = fitNodes.map(n => n.x as number).sort((a, b) => a - b);
        const ys = fitNodes.map(n => n.y as number).sort((a, b) => a - b);

        const p5x = xs[Math.floor(xs.length * 0.05)];
        const p95x = xs[Math.ceil(xs.length * 0.95) - 1];
        const p5y = ys[Math.floor(ys.length * 0.05)];
        const p95y = ys[Math.ceil(ys.length * 0.95) - 1];

        const core = fitNodes.filter(n => typeof n.x === 'number' && typeof n.y === 'number' && n.x >= p5x && n.x <= p95x && n.y >= p5y && n.y <= p95y);
        if (core.length >= 4) {
          fitNodes = core;
        }
      }

      const xs = fitNodes.map(n => n.x as number);
      const ys = fitNodes.map(n => n.y as number);
      const x0 = Math.min(...xs) - 80;
      const x1 = Math.max(...xs) + 80;
      const y0 = Math.min(...ys) - 80;
      const y1 = Math.max(...ys) + 80;

      const dx = x1 - x0, dy = y1 - y0;
      if (dx === 0 || dy === 0) return;

      const W = svgElement.clientWidth || innerWidth;
      const H = svgElement.clientHeight || innerHeight;
      const zoomScale = Math.min(W / dx, H / dy) * 0.96; // Use 96% of space instead of 88%
      const cx = (x0 + x1) / 2;
      const cy = (y0 + y1) / 2;

      svgSelection.transition().duration(450).call(
        zoomBehavior.transform,
        d3.zoomIdentity.translate(W / 2, H / 2).scale(zoomScale).translate(-cx, -cy)
      );
    }

    if (delay > 0) {
      setTimeout(doZoom, delay);
    } else {
      doZoom();
    }
  }

  function handleZoomIn() {
    if (svgSelection && zoomBehavior) {
      svgSelection.transition().duration(250).call(zoomBehavior.scaleBy, 1.5);
    }
  }

  function handleZoomOut() {
    if (svgSelection && zoomBehavior) {
      svgSelection.transition().duration(250).call(zoomBehavior.scaleBy, 0.66);
    }
  }

  // Reactively auto-zoom when data or layout changes
  $: {
    if ($graphData && $viewSettings.viewMode) {
      // Trigger zoom on next tick so views have placed nodes
      setTimeout(() => autoZoomToFit(undefined, 0, true), 50);
    }
  }

  // Handle focus mode backgroud click to exit
  function handleSvgClick(e: MouseEvent) {
    if (e.target === svgElement) {
      clearSelection();
      if ($selection.focusNodeId) {
        selection.update(s => ({ ...s, focusNodeId: null, focusNeighborSet: null }));
        // zoom to fit all
        setTimeout(() => autoZoomToFit(undefined, 0, true), 50);
      }
    }
  }

</script>

<div class="zoom-wrapper" bind:clientWidth={innerWidth} bind:clientHeight={innerHeight}>
  <!-- svelte-ignore a11y-click-events-have-key-events // handled role in SVG -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <svg
    bind:this={svgElement}
    onclick={handleSvgClick}
    role="application"
  >
    <defs>
      <!-- Original Edge Markers -->
      <marker id="ap" viewBox="0 -4 8 8" refX="12" refY="0" markerWidth="4" markerHeight="4" orient="auto">
        <path d="M0,-3L8,0L0,3" fill="var(--color-primary)"/>
      </marker>
      <marker id="ad" viewBox="0 -4 8 8" refX="12" refY="0" markerWidth="4" markerHeight="4" orient="auto">
        <path d="M0,-3L8,0L0,3" fill="var(--color-destructive)"/>
      </marker>
      <marker id="ar" viewBox="0 -4 8 8" refX="12" refY="0" markerWidth="4" markerHeight="4" orient="auto">
        <path d="M0,-3L8,0L0,3" fill="#a3a3a3"/>
      </marker>

      <!-- Holographic/Spectral Patterns -->
      <pattern id="holographic-grid" width="10" height="10" patternUnits="userSpaceOnUse">
        <rect width="10" height="10" fill="none" />
        <path d="M 10 0 L 0 0 0 10" fill="none" stroke="var(--color-primary)" stroke-width="0.5" stroke-opacity="0.1" />
      </pattern>

      <!-- Operator Blocked Striped Pattern -->
      <pattern id="striped-blocked" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="none" />
        <line x1="0" y1="0" x2="0" y2="8" stroke="var(--color-destructive)" stroke-width="4" stroke-opacity="0.2" />
      </pattern>
    </defs>

    <g bind:this={containerGroup} class="container-group">
      <slot {containerGroup} {innerWidth} {innerHeight}></slot>
    </g>
  </svg>
  
  <div class="absolute bottom-4 right-4 z-20 flex flex-col gap-2 glass-card p-1 rounded-xl border border-primary/20 shadow-xl bg-black/60 backdrop-blur">
    <button class="p-2 text-primary/70 hover:text-primary hover:bg-primary/20 rounded-lg transition-colors cursor-pointer flex items-center justify-center" title="Zoom In" onclick={handleZoomIn}>
      <span class="material-symbols-outlined text-sm">zoom_in</span>
    </button>
    <button class="p-2 text-primary/70 hover:text-primary hover:bg-primary/20 rounded-lg transition-colors cursor-pointer flex items-center justify-center" title="Zoom Out" onclick={handleZoomOut}>
      <span class="material-symbols-outlined text-sm">zoom_out</span>
    </button>
    <button class="p-2 text-primary/70 hover:text-primary hover:bg-primary/20 rounded-lg transition-colors cursor-pointer flex items-center justify-center" title="Fit to Screen" onclick={() => autoZoomToFit(undefined, 0, false)}>
      <span class="material-symbols-outlined text-sm">fit_screen</span>
    </button>
  </div>
</div>

<style>
  .zoom-wrapper {
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: transparent;
    position: relative;
    cursor: grab;
  }
  .zoom-wrapper:active {
    cursor: grabbing;
  }

  svg {
    width: 100%;
    height: 100%;
    display: block;
  }
</style>
