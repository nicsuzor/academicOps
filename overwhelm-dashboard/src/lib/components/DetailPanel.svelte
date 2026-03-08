<script lang="ts">
  import { selection, clearSelection } from "../stores/selection";
  import { graphData } from "../stores/graph";
  import { STATUS_FILLS, STATUS_TEXT } from "../data/constants";

  $: activeNodeId = $selection.activeNodeId;
  $: node = $graphData?.nodes.find((n) => n.id === activeNodeId) || null;

  $: isFocusMode = $selection.focusNodeId !== null;

  function closePanel() {
    clearSelection();
  }

  function toggleFocus() {
    if (isFocusMode) {
      selection.update((s) => ({
        ...s,
        focusNodeId: null,
        focusNeighborSet: null,
      }));
    } else if (node) {
      // Build ego-network neighbor set so applyHighlightOpacity can dim non-neighbors
      const neighbors = new Set<string>([node.id]);
      $graphData?.links.forEach((l) => {
        const sid = typeof l.source === "object" ? (l.source as { id: string }).id : l.source;
        const tid = typeof l.target === "object" ? (l.target as { id: string }).id : l.target;
        if (sid === node.id) neighbors.add(tid);
        if (tid === node.id) neighbors.add(sid);
      });
      selection.update((s) => ({ ...s, focusNodeId: node.id, focusNeighborSet: neighbors }));
    }
  }

  function handleAction(actionType: string) {
    if (!node) return;
    console.log(`Action: ${actionType} on Node: ${node.id}`);
    alert(`Triggered ${actionType} on ${node.id}`);
  }
</script>

{#if node}
  <div class="flex flex-col h-full bg-background-dark font-mono border-l border-primary/30 relative">
    <div class="p-3 border-b border-primary/30 bg-surface-dark/50 backdrop-blur-sm flex items-center justify-between">
      <h2 class="text-xs font-bold tracking-[0.2em] text-primary">NODE INSPECTOR</h2>
      <button class="text-primary hover:text-white transition-colors" on:click={closePanel}>✕</button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-6">
      <div class="space-y-1">
        <span class="text-[10px] text-primary/60 tracking-widest">ID: {node.id.split('-').pop()}</span>
        <h3 class="text-lg font-bold text-primary font-display">{node.label}</h3>
      </div>

      <div class="grid grid-cols-2 gap-4 text-xs">
        <div class="flex flex-col gap-1 border border-primary/20 p-2 bg-black/50">
          <span class="text-[10px] text-primary/60">STATUS</span>
          <span class="font-bold flex items-center gap-2">
            <span class="w-2 h-2 rounded-full" style="background: {STATUS_FILLS[node.status] || '#f1f5f9'}"></span>
            {node.status.toUpperCase()}
          </span>
        </div>

        <div class="flex flex-col gap-1 border border-primary/20 p-2 bg-black/50">
          <span class="text-[10px] text-primary/60">TYPE</span>
          <span class="font-bold text-primary">{node.type?.toUpperCase() || 'UNKNOWN'}</span>
        </div>

        <div class="flex flex-col gap-1 border border-primary/20 p-2 bg-black/50">
          <span class="text-[10px] text-primary/60">PRIORITY</span>
          <span class="font-bold text-primary">P{node.priority}</span>
        </div>

        <div class="flex flex-col gap-1 border border-primary/20 p-2 bg-black/50">
          <span class="text-[10px] text-primary/60">WEIGHT ⚖️</span>
          <span class="font-bold text-primary">{node.dw.toFixed(1)}</span>
        </div>

        <div class="flex flex-col gap-1 border border-primary/20 p-2 bg-black/50 col-span-2">
          <span class="text-[10px] text-primary/60">PROJECT</span>
          <span class="font-bold text-primary">{node.project || 'NONE'}</span>
        </div>
      </div>

      <div class="space-y-2 pt-4 border-t border-primary/20">
        <h4 class="text-[10px] font-bold tracking-widest text-primary/60">METRICS</h4>
        <div class="flex justify-between items-center text-xs">
          <span class="text-primary/70">Depth</span>
          <span class="text-primary">{node.depth} / {node.maxDepth}</span>
        </div>
        {#if node.assignee}
          <div class="flex justify-between items-center text-xs">
            <span class="text-primary/70">Assignee</span>
            <span class="text-primary">{node.assignee}</span>
          </div>
        {/if}
      </div>
    </div>

    <!-- Actions Footer -->
    <div class="p-4 border-t border-primary/30 bg-black/80 flex flex-col gap-2">
      <button
        class="w-full py-2 border {isFocusMode ? 'border-primary bg-primary/20' : 'border-primary/50'} text-primary text-xs font-bold tracking-widest hover:bg-primary hover:text-black transition-colors"
        on:click={toggleFocus}
      >
        {isFocusMode ? "EXIT FOCUS MODE" : "ISOLATE NODE"}
      </button>
      <div class="grid grid-cols-2 gap-2">
        <button
          class="py-2 border border-primary/50 text-primary/70 text-xs font-bold tracking-widest hover:border-primary hover:text-primary transition-colors"
          on:click={() => handleAction("edit")}
        >
          EDIT
        </button>
        <button
          class="py-2 bg-primary/10 border border-primary text-primary text-xs font-bold tracking-widest hover:bg-primary hover:text-black transition-colors"
          on:click={() => handleAction("complete")}
        >
          COMPLETE
        </button>
      </div>
    </div>
  </div>
{:else}
  <div class="flex flex-col h-full bg-background-dark font-mono border-l border-primary/30 items-center justify-center text-primary/30 p-8 text-center">
    <span class="material-symbols-outlined text-4xl mb-2">radar</span>
    <span class="text-xs tracking-widest">AWAITING TARGET ACQUISITION</span>
  </div>
{/if}
