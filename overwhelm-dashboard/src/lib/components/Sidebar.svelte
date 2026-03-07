<script lang="ts">
  import { filters } from "../stores/filters";
  import { viewSettings } from "../stores/viewSettings";
  import { graphData } from "../stores/graph";

  const viewModes = ["Overview", "Force Atlas 2", "SFDP", "Arc Diagram"];

  $: isForce =
    $viewSettings.viewMode === "Force Atlas 2" ||
    $viewSettings.viewMode === "SFDP";
  $: isOverview = $viewSettings.viewMode === "Overview";

  $: availableProjects = $graphData
    ? Array.from(
        new Set($graphData.nodes.map((n) => n.project).filter((p) => p)),
      ).sort()
    : [];
</script>

<aside class="sidebar">
  <h2>Overwhelm</h2>
  <hr class="divider" />

  <div class="control-group">
    <label for="mainTab" class="bold-label">Navigation</label>
    <select id="mainTab" bind:value={$viewSettings.mainTab}>
      <option value="Dashboard">Dashboard</option>
      <option value="Task Graph">Task Graph</option>
    </select>
  </div>

  {#if $viewSettings.mainTab === "Task Graph"}
    <hr class="divider" />

    <div class="control-group">
      <label for="viewMode" class="bold-label">Graph View Mode</label>
      <select id="viewMode" bind:value={$viewSettings.viewMode}>
        {#each viewModes as mode}
          <option value={mode}>{mode}</option>
        {/each}
      </select>
    </div>
  {/if}

  {#if isOverview}
    <div class="control-group radio-group">
      <label class="bold-label">Overview Layout</label>
      <label>
        <input
          type="radio"
          bind:group={$viewSettings.overviewLayout}
          value="tree"
        />
        Treemap
      </label>
      <label>
        <input
          type="radio"
          bind:group={$viewSettings.overviewLayout}
          value="circle"
        />
        Circle Pack
      </label>
    </div>
  {/if}

  {#if $viewSettings.mainTab === "Task Graph"}
    <hr class="divider" />

    <h3>Filters</h3>
    <div class="control-group">
      {#if isForce}
        <label class="block-label">
          <span class="label-text">Project filter</span>
          <select bind:value={$filters.project}>
            <option value="ALL">ALL</option>
            {#each availableProjects as project}
              <option value={project}>{project}</option>
            {/each}
          </select>
        </label>
      {/if}

      <label class="check-label">
        <input type="checkbox" bind:checked={$filters.showActive} /> Active/Inbox
      </label>
      <label class="check-label">
        <input type="checkbox" bind:checked={$filters.showBlocked} /> Blocked (Red)
      </label>
      <label class="check-label">
        <input type="checkbox" bind:checked={$filters.showCompleted} /> Completed/Done
      </label>
      {#if $viewSettings.viewMode === "SFDP"}
        <label class="check-label">
          <input type="checkbox" bind:checked={$filters.showOrphans} /> Include orphans
        </label>
      {/if}
    </div>

    <hr class="divider" />

    <h3>Edges</h3>
    <div class="control-group">
      <label class="check-label">
        <input type="checkbox" bind:checked={$filters.showDependencies} /> Show dependencies
        (red)
      </label>
      <label class="check-label">
        <input type="checkbox" bind:checked={$filters.showReferences} /> Show references
        (dashed)
      </label>
    </div>

    {#if isForce}
      <hr class="divider" />
      <h3>Simulation</h3>

      <div class="control-group">
        <label class="block-label">
          <span class="label-text">Top N leaves (complexity)</span>
          <div class="slider-row">
            <input
              type="range"
              min="10"
              max="500"
              bind:value={$viewSettings.topNLeaves}
            />
            <span class="val">{$viewSettings.topNLeaves}</span>
          </div>
        </label>

        <label class="check-label">
          <input type="checkbox" bind:checked={$viewSettings.liveSimulation} /> Live
          Force Simulation
        </label>

        {#if $viewSettings.liveSimulation}
          <label class="block-label">
            <span class="label-text">Charge Strength</span>
            <div class="slider-row">
              <input
                type="range"
                min="0.1"
                max="3.0"
                step="0.1"
                bind:value={$viewSettings.chargeStrength}
              />
              <span class="val">{$viewSettings.chargeStrength.toFixed(1)}</span>
            </div>
          </label>
          <label class="block-label">
            <span class="label-text">Attraction Strength</span>
            <div class="slider-row">
              <input
                type="range"
                min="0.2"
                max="2.0"
                step="0.05"
                bind:value={$viewSettings.attractionStrength}
              />
              <span class="val"
                >{$viewSettings.attractionStrength.toFixed(2)}</span
              >
            </div>
          </label>
          <label class="block-label">
            <span class="label-text">Cluster Pull</span>
            <div class="slider-row">
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                bind:value={$viewSettings.clusterPull}
              />
              <span class="val">{$viewSettings.clusterPull.toFixed(2)}</span>
            </div>
          </label>
        {/if}
      </div>
    {/if}
  {/if}
</aside>
```

<style>
  .sidebar {
    width: 280px;
    height: 100vh;
    background: var(--bg-sidebar);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-right: 1px solid var(--border-subtle);
    padding: 24px 20px;
    box-sizing: border-box;
    overflow-y: auto;
    color: var(--text-primary);
    flex-shrink: 0;
    box-shadow: 4px 0 15px rgba(0, 0, 0, 0.2);
    z-index: 10;
  }

  h2 {
    margin-top: 0;
    margin-bottom: 20px;
    font-size: 22px;
    font-weight: 700;
    background: linear-gradient(135deg, var(--text-primary), var(--text-muted));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
  }

  h3 {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.1em;
    margin-bottom: 16px;
    margin-top: 0;
  }

  .divider {
    border: 0;
    height: 1px;
    background: var(--border-subtle);
    margin: 24px 0;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 24px;
  }

  .radio-group {
    gap: 8px;
    margin-top: 12px;
  }

  .bold-label {
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 4px;
    display: block;
    color: var(--text-secondary);
  }

  select {
    width: 100%;
    padding: 8px 12px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-subtle);
    font-size: 13px;
    background: var(--bg-input);
    color: var(--text-primary);
    outline: none;
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
  }

  select:focus {
    border-color: var(--border-accent);
    background: var(--bg-input-focus);
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
  }

  .check-label,
  .radio-group label {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    cursor: pointer;
    color: var(--text-secondary);
    transition: color var(--transition-fast);
  }

  .check-label:hover,
  .radio-group label:hover {
    color: var(--text-primary);
  }

  .check-label input,
  .radio-group input {
    margin: 0;
  }

  .block-label {
    display: block;
    margin-bottom: 4px;
  }

  .label-text {
    display: block;
    font-size: 13px;
    margin-bottom: 6px;
    color: #475569;
  }

  .slider-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 6px;
  }

  input[type="range"] {
    flex: 1;
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
  }

  input[type="range"]::-webkit-slider-runnable-track {
    width: 100%;
    height: 4px;
    background: var(--bg-input);
    border-radius: 2px;
  }

  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    height: 14px;
    width: 14px;
    border-radius: 50%;
    background: var(--accent-primary);
    cursor: pointer;
    margin-top: -5px;
    box-shadow: 0 0 8px rgba(129, 140, 248, 0.4);
    transition: transform var(--transition-fast);
  }

  input[type="range"]::-webkit-slider-thumb:hover {
    transform: scale(1.2);
  }

  .val {
    font-size: 12px;
    font-family: monospace;
    color: var(--text-muted);
    min-width: 30px;
    text-align: right;
  }
</style>
