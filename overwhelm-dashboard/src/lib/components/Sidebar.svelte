<script lang="ts">
  import { filters } from "../stores/filters";
  import { viewSettings } from "../stores/viewSettings";
  import { graphData } from "../stores/graph";

  const viewModes = ["Treemap", "Circle Pack", "Force Atlas 2", "SFDP", "Arc Diagram"];

  $: isForce =
    $viewSettings.viewMode === "Force Atlas 2" ||
    $viewSettings.viewMode === "SFDP";

  $: availableProjects = $graphData
    ? Array.from(
        new Set($graphData.nodes.map((n) => n.project).filter((p) => p)),
      ).sort()
    : [];
</script>

<div class="flex flex-col h-full bg-background-dark font-mono text-primary/80">
  <div class="p-3 border-b border-primary/30 bg-surface-dark/50 backdrop-blur-sm">
    <div class="flex items-center justify-between">
      <h2 class="text-xs font-bold tracking-[0.2em] text-primary">SYSTEM CONTROL</h2>
      <span class="text-[10px] font-mono opacity-60 animate-pulse">ACTIVE</span>
    </div>
  </div>

  <div class="flex-1 overflow-y-auto p-4 space-y-6 grid-bg custom-scrollbar">

    <div class="space-y-2">
      <label for="mainTab" class="block text-[10px] font-bold tracking-widest text-primary/60">NAVIGATION</label>
      <select id="mainTab" bind:value={$viewSettings.mainTab} class="w-full bg-black/50 border border-primary/30 text-primary text-xs py-1.5 px-2 focus:ring-1 focus:ring-primary focus:border-primary">
        <option value="Dashboard">DASHBOARD</option>
        <option value="Task Graph">TASK GRAPH</option>
        <option value="Threaded Tasks">THREADED TASKS</option>
      </select>
    </div>

    {#if $viewSettings.mainTab === "Task Graph"}
      <div class="h-px bg-primary/20 w-full"></div>

      <div class="space-y-2">
        <label for="viewMode" class="block text-[10px] font-bold tracking-widest text-primary/60">GRAPH VIEW MODE</label>
        <select id="viewMode" bind:value={$viewSettings.viewMode} class="w-full bg-black/50 border border-primary/30 text-primary text-xs py-1.5 px-2 focus:ring-1 focus:ring-primary focus:border-primary">
          {#each viewModes as mode}
            <option value={mode}>{mode.toUpperCase()}</option>
          {/each}
        </select>
      </div>
    {/if}

    {#if $viewSettings.mainTab === "Task Graph"}
      <div class="h-px bg-primary/20 w-full"></div>

      <div class="space-y-3">
        <h3 class="text-[10px] font-bold tracking-widest text-primary/60">FILTERS</h3>

        {#if isForce}
          <div class="space-y-1">
            <span class="block text-[10px] text-primary/50">PROJECT</span>
            <select bind:value={$filters.project} class="w-full bg-black/50 border border-primary/30 text-primary text-xs py-1 px-2 focus:ring-1 focus:ring-primary">
              <option value="ALL">ALL</option>
              {#each availableProjects as project}
                <option value={project}>{project}</option>
              {/each}
            </select>
          </div>
        {/if}

        <div class="flex flex-col gap-2 pt-2">
          <label class="flex items-center gap-2 cursor-pointer group">
            <input type="checkbox" bind:checked={$filters.showActive} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm" />
            <span class="text-xs group-hover:text-primary transition-colors">ACTIVE/INBOX</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer group">
            <input type="checkbox" bind:checked={$filters.showBlocked} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm" />
            <span class="text-xs group-hover:text-primary transition-colors">BLOCKED (RED)</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer group">
            <input type="checkbox" bind:checked={$filters.showCompleted} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm" />
            <span class="text-xs group-hover:text-primary transition-colors">COMPLETED/DONE</span>
          </label>
          {#if $viewSettings.viewMode === "SFDP"}
            <label class="flex items-center gap-2 cursor-pointer group">
              <input type="checkbox" bind:checked={$filters.showOrphans} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm" />
              <span class="text-xs group-hover:text-primary transition-colors">INCLUDE ORPHANS</span>
            </label>
          {/if}
        </div>
      </div>

      <div class="h-px bg-primary/20 w-full"></div>

      <div class="space-y-3">
        <h3 class="text-[10px] font-bold tracking-widest text-primary/60">EDGES</h3>
        <div class="flex flex-col gap-2">
          <label class="flex items-center gap-2 cursor-pointer group">
            <input type="checkbox" bind:checked={$filters.showDependencies} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm" />
            <span class="text-xs group-hover:text-primary transition-colors">DEPENDENCIES</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer group">
            <input type="checkbox" bind:checked={$filters.showReferences} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm" />
            <span class="text-xs group-hover:text-primary transition-colors">REFERENCES</span>
          </label>
        </div>
      </div>

      {#if isForce}
        <div class="h-px bg-primary/20 w-full"></div>

        <div class="space-y-4">
          <h3 class="text-[10px] font-bold tracking-widest text-primary/60">SIMULATION</h3>

          <div class="space-y-1">
            <span class="block text-[10px] text-primary/50">TOP N LEAVES ({$viewSettings.topNLeaves})</span>
            <input type="range" min="10" max="500" bind:value={$viewSettings.topNLeaves} class="w-full accent-primary" />
          </div>

          <label class="flex items-center gap-2 cursor-pointer group">
            <input type="checkbox" bind:checked={$viewSettings.liveSimulation} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm" />
            <span class="text-xs group-hover:text-primary transition-colors">LIVE SIMULATION</span>
          </label>

          {#if $viewSettings.liveSimulation}
            <div class="space-y-1">
              <span class="block text-[10px] text-primary/50">CHARGE STRENGTH ({$viewSettings.chargeStrength.toFixed(1)})</span>
              <input type="range" min="0.1" max="3.0" step="0.1" bind:value={$viewSettings.chargeStrength} class="w-full accent-primary" />
            </div>
          {/if}
        </div>
      {/if}
    {/if}
  </div>
</div>
