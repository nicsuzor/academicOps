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
      selection.update((s) => ({ ...s, focusNodeId: node.id }));
    }
  }

  function handleAction(actionType: string) {
    if (!node) return;
    // Real implementation would talk back to python/backend via API or iframe postMessage.
    // For now, simply console.log for the standalone dashboard version.
    console.log(`Action: ${actionType} on Node: ${node.id}`);
    alert(`Triggered ${actionType} on ${node.id}`);
  }
</script>

{#if node}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="monolith-backdrop" on:click={closePanel}></div>
  <div class="detail-panel glass-surface">
    <div class="header">
      <h3>{node.label}</h3>
      <button class="close-btn" aria-label="Close" on:click={closePanel}
        >✕</button
      >
    </div>

    <div class="fields">
      <div class="field">
        <span class="label">Status</span>
        <span
          class="value badge indicator"
          style="background: {STATUS_FILLS[node.status] ||
            '#f1f5f9'}; color: {STATUS_TEXT[node.status] || '#475569'}"
        >
          {node.status}
        </span>
      </div>

      {#if node.type}
        <div class="field">
          <span class="label">Type</span>
          <span class="value badge">{node.type}</span>
        </div>
      {/if}

      {#if node.project}
        <div class="field">
          <span class="label">Project</span>
          <span class="value">{node.project}</span>
        </div>
      {/if}

      <div class="field">
        <span class="label">Priority</span>
        <span class="value">P{node.priority}</span>
      </div>

      <div class="field">
        <span class="label">Weight ⚖️</span>
        <span class="value">{node.dw.toFixed(1)}</span>
      </div>

      {#if node.assignee}
        <div class="field">
          <span class="label">Assignee</span>
          <span class="value">{node.assignee}</span>
        </div>
      {/if}

      <div class="field">
        <span class="label">Depth</span>
        <span class="value">{node.depth} / {node.maxDepth}</span>
      </div>
    </div>

    <div class="actions">
      <button
        class="btn btn-focus"
        class:active-focus={isFocusMode}
        on:click={toggleFocus}
      >
        {isFocusMode ? "Exit Focus" : "Focus"}
      </button>
      <button class="btn btn-edit" on:click={() => handleAction("edit")}
        >Edit</button
      >
      <button class="btn btn-complete" on:click={() => handleAction("complete")}
        >Done</button
      >
    </div>
  </div>
{/if}

<style>
  .monolith-backdrop {
    position: fixed;
    inset: 0;
    z-index: 99;
    background: rgba(5, 5, 5, 0.4);
    backdrop-filter: blur(40px) brightness(0.3);
    -webkit-backdrop-filter: blur(40px) brightness(0.3);
  }

  .detail-panel {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 100;
    width: 400px;
    padding: 24px;
    box-sizing: border-box;
    /* Removed custom background/border/blur since glass-surface handles it, but we can boost the box-shadow */
    box-shadow:
      0 20px 50px rgba(0, 0, 0, 0.5),
      0 0 0 1px rgba(255, 255, 255, 0.05);
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.4;
    word-break: break-word;
    padding-right: 12px;
  }

  .close-btn {
    background: none;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    font-size: 16px;
    padding: 0;
    margin: -4px -4px 0 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
  }

  .close-btn:hover {
    color: #f8fafc;
    background: rgba(255, 255, 255, 0.1);
  }

  .fields {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 12px;
  }

  .label {
    color: #94a3b8;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    font-weight: 600;
  }

  .value {
    font-weight: 500;
    text-align: right;
  }

  .badge {
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: rgba(255, 255, 255, 0.1);
  }

  .actions {
    display: flex;
    gap: 12px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid var(--border-subtle);
  }

  .btn {
    flex: 1;
    padding: 10px 0;
    background: transparent;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 700;
    font-family: var(--font-display);
    text-transform: uppercase;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  /* Neon fill on hover */
  .btn-focus {
    border-color: var(--neon-magenta);
    color: var(--neon-magenta);
  }
  .btn-focus:hover,
  .btn-focus.active-focus {
    background: var(--neon-magenta);
    color: var(--color-void);
    box-shadow: 0 0 15px var(--neon-magenta);
  }

  .btn-edit {
    border-color: var(--neon-cyan);
    color: var(--neon-cyan);
  }
  .btn-edit:hover {
    background: var(--neon-cyan);
    color: var(--color-void);
    box-shadow: 0 0 15px var(--neon-cyan);
  }

  .btn-complete {
    border-color: var(--accent-success);
    color: var(--accent-success);
  }
  .btn-complete:hover {
    background: var(--accent-success);
    color: var(--color-void);
    box-shadow: 0 0 15px var(--accent-success);
  }
</style>
