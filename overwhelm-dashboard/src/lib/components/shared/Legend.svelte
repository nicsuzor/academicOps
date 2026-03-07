<script lang="ts">
  import { STATUS_FILLS } from '../../data/constants';
  let showLegend = true;

  function toggleLegend() {
    showLegend = !showLegend;
  }
</script>

{#if showLegend}
  <div class="legend" role="complementary" aria-label="Color Legend">
    <div class="legend-item">
      <div class="legend-box" style="background:{STATUS_FILLS.active || '#3b82f6'}"></div>
      <span>Active</span>
    </div>
    <div class="legend-item">
      <div class="legend-box" style="background:{STATUS_FILLS.blocked || '#ef4444'}"></div>
      <span>Blocked</span>
    </div>
    <div class="legend-item">
      <div class="legend-box" style="background:{STATUS_FILLS.done || '#22c55e'}"></div>
      <span>Done</span>
    </div>
    <div class="legend-item">
      <div class="legend-line" style="background:#3b82f6"></div>
      <span>Parent</span>
    </div>
    <div class="legend-item">
      <div class="legend-line" style="background:#ef4444"></div>
      <span>Dependency</span>
    </div>
    <div class="legend-item">
      <div class="legend-box" style="border: 1px solid #f59e0b; box-shadow: 0 0 4px #f59e0b; background: transparent"></div>
      <span>Recent (7d)</span>
    </div>
  </div>
{/if}

<button class="legend-toggle" on:click={toggleLegend}>
  {showLegend ? 'Hide Legend' : 'Show Legend'}
</button>

<style>
  .legend {
    position: absolute;
    bottom: 16px;
    left: 16px;
    z-index: 10;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 11px;
    color: #f8fafc;
    backdrop-filter: blur(8px);
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-family: var(--font-mono);
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .legend-box {
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }

  .legend-line {
    width: 14px;
    height: 3px;
    border-radius: 1.5px;
  }

  .legend-toggle {
    position: absolute;
    bottom: 16px;
    right: 16px;
    z-index: 10;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
    cursor: pointer;
    color: #f8fafc;
    font-weight: 500;
    font-family: inherit;
  }
</style>
