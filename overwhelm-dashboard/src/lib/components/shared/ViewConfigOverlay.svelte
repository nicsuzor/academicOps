<script lang="ts">
    import { viewSettings, getLayoutFromViewSettings } from "../../stores/viewSettings";
    import { filters } from "../../stores/filters";
    import { graphData } from "../../stores/graph";

    $: layout = getLayoutFromViewSettings($viewSettings);
    $: isForce = layout === "force";
    $: isCircle = layout === "circle_pack";
    $: isArc = layout === "arc";
    $: isTreemap = layout === "treemap";

    $: availableProjects = $graphData
        ? Array.from(new Set($graphData.nodes.map((n) => n.project).filter((p) => p))).sort()
        : [];

    let expanded = false;
</script>

<div class="absolute bottom-4 left-4 z-30 flex flex-col items-start gap-2 font-mono">
    {#if expanded}
        <div class="glass-card p-4 rounded-xl border border-primary/20 flex flex-col gap-4 min-w-[280px] animate-in slide-in-from-bottom-2 fade-in duration-200 shadow-2xl overflow-y-auto max-h-[80vh] custom-scrollbar">
            <div class="flex items-center justify-between border-b border-primary/10 pb-2">
                <h3 class="text-[10px] font-bold tracking-[0.2em] text-primary/80 uppercase">
                    {#if isForce}Simulation_Config{:else if isCircle}Circle_Pack_Config{:else if isArc}Arc_Diagram_Config{:else}Treemap_Config{/if}
                </h3>
                <button class="text-primary/40 hover:text-primary transition-colors cursor-pointer" onclick={() => expanded = false}>
                    <span class="material-symbols-outlined text-sm">close</span>
                </button>
            </div>

            <!-- VIEW-SPECIFIC CONTROLS -->
            {#if isForce}
                <label class="flex items-center justify-between cursor-pointer group">
                    <span class="text-[10px] font-bold text-primary/60 uppercase">Live_Simulation</span>
                    <input type="checkbox" bind:checked={$viewSettings.liveSimulation} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm cursor-pointer" />
                </label>

                {#if $viewSettings.liveSimulation}
                    <div class="space-y-3 pt-1 border-t border-primary/5">
                        <div class="space-y-1">
                            <div class="flex justify-between text-[9px] text-primary/50 uppercase">
                                <span>Repulsion</span>
                                <span>{$viewSettings.chargeStrength.toFixed(1)}x</span>
                            </div>
                            <input type="range" min="0.1" max="3.0" step="0.1" bind:value={$viewSettings.chargeStrength} class="w-full h-1 bg-primary/10 rounded-lg appearance-none cursor-pointer accent-primary" />
                        </div>
                        <div class="space-y-1">
                            <div class="flex justify-between text-[9px] text-primary/50 uppercase">
                                <span>Link_Distance</span>
                                <span>{$viewSettings.linkDistance.toFixed(1)}x</span>
                            </div>
                            <input type="range" min="0.1" max="3.0" step="0.1" bind:value={$viewSettings.linkDistance} class="w-full h-1 bg-primary/10 rounded-lg appearance-none cursor-pointer accent-primary" />
                        </div>
                        <div class="space-y-1">
                            <div class="flex justify-between text-[9px] text-primary/50 uppercase">
                                <span>Gravity</span>
                                <span>{$viewSettings.gravity.toFixed(2)}</span>
                            </div>
                            <input type="range" min="0.01" max="0.5" step="0.01" bind:value={$viewSettings.gravity} class="w-full h-1 bg-primary/10 rounded-lg appearance-none cursor-pointer accent-primary" />
                        </div>
                    </div>
                {/if}

                <div class="space-y-1 pt-1 border-t border-primary/5">
                    <div class="flex justify-between text-[9px] text-primary/50 uppercase">
                        <span>Max_Visible_Nodes</span>
                        <span>{$viewSettings.topNLeaves}</span>
                    </div>
                    <input type="range" min="10" max="500" step="10" bind:value={$viewSettings.topNLeaves} class="w-full h-1 bg-primary/10 rounded-lg appearance-none cursor-pointer accent-primary" />
                </div>
            {/if}

            {#if isCircle}
                <div class="space-y-1">
                    <div class="flex justify-between text-[9px] text-primary/50 uppercase">
                        <span>Rollup_Threshold</span>
                        <span>{$viewSettings.circleRollupThreshold}px</span>
                    </div>
                    <input type="range" min="5" max="50" step="1" bind:value={$viewSettings.circleRollupThreshold} class="w-full h-1 bg-primary/10 rounded-lg appearance-none cursor-pointer accent-primary" />
                </div>
            {/if}

            {#if isArc}
                <div class="space-y-1">
                    <div class="flex justify-between text-[9px] text-primary/50 uppercase">
                        <span>Vertical_Scale</span>
                        <span>{$viewSettings.arcVerticalSpacing.toFixed(1)}x</span>
                    </div>
                    <input type="range" min="0.5" max="3.0" step="0.1" bind:value={$viewSettings.arcVerticalSpacing} class="w-full h-1 bg-primary/10 rounded-lg appearance-none cursor-pointer accent-primary" />
                </div>
            {/if}

            <!-- GLOBAL VISIBILITY TOGGLES -->
            <div class="space-y-3 pt-3 border-t border-primary/20">
                <h4 class="text-[9px] font-black text-primary/40 uppercase tracking-widest">Visibility_Matrix</h4>
                <div class="flex flex-col gap-2">
                    <label class="flex items-center gap-2 cursor-pointer group">
                        <input type="checkbox" bind:checked={$filters.showActive} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm cursor-pointer" />
                        <span class="text-[10px] font-bold group-hover:text-primary transition-colors">ACTIVE_TASKS</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer group">
                        <input type="checkbox" bind:checked={$filters.showBlocked} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm cursor-pointer" />
                        <span class="text-[10px] font-bold group-hover:text-primary transition-colors text-destructive">BLOCKED_ITEMS</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer group">
                        <input type="checkbox" bind:checked={$filters.showCompleted} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm cursor-pointer" />
                        <span class="text-[10px] font-bold group-hover:text-primary transition-colors">COMPLETED_DUMP</span>
                    </label>
                </div>
            </div>

            <!-- EDGE CONTROLS -->
            <div class="space-y-3 pt-3 border-t border-primary/20">
                <h4 class="text-[9px] font-black text-primary/40 uppercase tracking-widest">Neural_Edges</h4>
                <div class="flex flex-col gap-2">
                    <label class="flex items-center gap-2 cursor-pointer group">
                        <input type="checkbox" bind:checked={$filters.showDependencies} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm cursor-pointer" />
                        <span class="text-[10px] font-bold group-hover:text-primary transition-colors">DEPENDENCIES</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer group">
                        <input type="checkbox" bind:checked={$filters.showReferences} class="text-primary bg-black border-primary/30 focus:ring-primary rounded-sm cursor-pointer" />
                        <span class="text-[10px] font-bold group-hover:text-primary transition-colors">REFERENCES</span>
                    </label>
                </div>
            </div>

            <!-- FOCUS ISOLATION -->
            <div class="space-y-1 pt-3 border-t border-primary/20">
                <span class="text-[9px] text-primary/50 uppercase block mb-1 font-black">Isolated_Project</span>
                <select bind:value={$filters.project} class="w-full bg-black/50 border border-primary/20 text-primary text-[10px] font-mono py-1.5 px-2 rounded outline-none focus:border-primary/50 transition-colors cursor-pointer">
                    <option value="ALL">ALL_ACTIVE_WORK</option>
                    {#each availableProjects as project}
                        <option value={project}>{project.toUpperCase()}</option>
                    {/each}
                </select>
            </div>
        </div>
    {/if}

    <button
        class="glass-card px-3 py-2 rounded-lg border border-primary/30 flex items-center gap-2 hover:bg-primary/10 transition-all cursor-pointer group shadow-lg"
        onclick={() => expanded = !expanded}
    >
        <span class="material-symbols-outlined text-primary group-hover:rotate-90 transition-transform duration-300">
            {#if isForce}settings_input_component{:else if isCircle}radio_button_checked{:else if isArc}architecture{:else}view_quilt{/if}
        </span>
        <span class="text-[10px] font-black uppercase tracking-widest text-primary">
            {#if isForce}Force{:else if isCircle}Pack{:else if isArc}Arc{:else}Tree{/if}_Config
        </span>
    </button>
</div>

<style>
    input[type=range]::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 12px;
        height: 12px;
        background: var(--color-primary);
        cursor: pointer;
        border-radius: 50%;
        box-shadow: 0 0 10px rgba(var(--color-primary-rgb), 0.5);
    }
</style>
