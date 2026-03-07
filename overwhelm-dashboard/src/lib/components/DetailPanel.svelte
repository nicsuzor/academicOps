<script lang="ts">
  import { selection, clearSelection } from '../stores/selection';
  import { graphData } from '../stores/graph';
  import { STATUS_FILLS, STATUS_TEXT } from '../data/constants';

  $: activeNodeId = $selection.activeNodeId;
  $: node = $graphData?.nodes.find(n => n.id === activeNodeId) || null;

  $: isFocusMode = $selection.focusNodeId !== null;

  function closePanel() {
    clearSelection();
  }

  function toggleFocus() {
    if (isFocusMode) {
      selection.update(s => ({ ...s, focusNodeId: null, focusNeighborSet: null }));
    } else if (node) {
      selection.update(s => ({ ...s, focusNodeId: node.id }));
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
  <div class="detail-panel">
    <div class="header">
      <h3>{node.label}</h3>
      <button class="close-btn" aria-label="Close" on:click={closePanel}>✕</button>
    </div>

    <div class="fields">
      <div class="field">
        <span class="label">Status</span>
        <span class="value badge indicator"
              style="background: {STATUS_FILLS[node.status] || '#f1f5f9'}; color: {STATUS_TEXT[node.status] || '#475569'}">
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
      <button class="btn btn-focus" class:active-focus={isFocusMode} on:click={toggleFocus}>
        {isFocusMode ? 'Exit Focus' : 'Focus'}
      </button>
      <button class="btn btn-edit" on:click={() => handleAction('edit')}>Edit</button>
      <button class="btn btn-complete" on:click={() => handleAction('complete')}>Done</button>
    </div>
  </div>
{/if}

<style>
  .detail-panel {
    position: absolute;
    top: 16px;
    right: 16px;
    z-index: 100;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 16px;
    width: 280px;
    box-sizing: border-box;
    color: #f8fafc;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
    background: rgba(255,255,255,0.1);
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
    background: rgba(255,255,255,0.1);
  }

  .actions {
    display: flex;
    gap: 8px;
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid rgba(255,255,255,0.1);
  }

  .btn {
    flex: 1;
    padding: 8px 0;
    border: none;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-focus { background: #7c3aed; color: white; }
  .btn-focus:hover, .btn-focus.active-focus { background: #6d28d9; }

  .btn-edit { background: #3b82f6; color: white; }
  .btn-edit:hover { background: #2563eb; }

  .btn-complete { background: #10b981; color: white; }
  .btn-complete:hover { background: #059669; }
</style>
