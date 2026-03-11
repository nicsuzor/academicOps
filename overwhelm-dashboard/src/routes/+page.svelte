<script lang="ts">
    import { onMount } from "svelte";
    import Sidebar from "$lib/components/Sidebar.svelte";
    import TaskEditorView from "$lib/components/views/TaskEditorView.svelte";
    import ZoomContainer from "$lib/components/shared/ZoomContainer.svelte";
    import Legend from "$lib/components/shared/Legend.svelte";
    import ViewConfigOverlay from "$lib/components/shared/ViewConfigOverlay.svelte";

    import TreemapView from "$lib/components/views/TreemapView.svelte";
    import CirclePackView from "$lib/components/views/CirclePackView.svelte";
    import ForceView from "$lib/components/views/ForceView.svelte";
    import ArcView from "$lib/components/views/ArcView.svelte";

    import DashboardView from "$lib/components/dashboard/DashboardView.svelte";
    import ThreadedTasksView from "$lib/components/views/ThreadedTasksView.svelte";

    import {
        prepareGraphData,
        type PreparedGraph,
        type GraphNode,
        type GraphEdge,
    } from "$lib/data/prepareGraphData";
    import { graphData } from "$lib/stores/graph";
    import {
        viewSettings,
        getLayoutFromViewSettings,
        getGraphLayoutKey,
    } from "$lib/stores/viewSettings";
    import { filters } from "$lib/stores/filters";
    import { selection } from "$lib/stores/selection";
    import { browser } from "$app/environment";

    export let data: any;

    let rawGraph: any = null;
    let loading = true;
    let errorMsg = "";
    let currentLayoutKey = "";

    async function fetchGraph(layoutKey: string) {
        if (!browser) return;
        if (layoutKey === currentLayoutKey && rawGraph) return;
        loading = true;
        errorMsg = "";
        try {
            const res = await fetch(`/api/graph?layout=${layoutKey}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            rawGraph = await res.json();
            currentLayoutKey = layoutKey;
            recomputeGraph();
        } catch (e: any) {
            errorMsg = `Failed to load graph (${layoutKey}): ` + e.message;
            console.error(e);
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        fetchGraph(getGraphLayoutKey($viewSettings));
    });

    $: {
        const key = getGraphLayoutKey($viewSettings);
        if (key !== currentLayoutKey) {
            fetchGraph(key);
        }
    }

    $: if (rawGraph) {
        // Only recompute if filters or settings change.
        // Selection is handled separately to avoid full graph object replacement.
        const _deps = [$filters, $viewSettings];
        recomputeGraph();
    }

    $: if ($selection && $graphData) {
        applyHighlightOpacity($graphData.nodes, $graphData.links);
    }
    $: focusNode = $selection.focusNodeId ? $graphData?.nodes.find(n => n.id === $selection.focusNodeId) : null;

    function recomputeGraph() {
        if (!rawGraph) return;

        const prepared = prepareGraphData(rawGraph);
        let fNodes = [...prepared.nodes];
        let fLinks = [...prepared.links];
        const isForce =
            $viewSettings.viewMode === "Force Atlas 2" ||
            $viewSettings.viewMode === "SFDP";

        // Filter out non-task items like contact, person, organization
        fNodes = fNodes.filter(n => !["contact", "person", "organization"].includes(n.type));

        if (!$filters.showActive) {
            fNodes = fNodes.filter(
                (n) => !["active", "inbox", "todo", "in_progress", "review"].includes(n.status),
            );
        }
        if (!$filters.showBlocked) {
            fNodes = fNodes.filter((n) => n.status !== "blocked");
        }
        if (!$filters.showCompleted) {
            fNodes = fNodes.filter(
                (n) => !["done", "completed", "cancelled", "historical", "deferred", "paused", "seed", "early-scaffold"].includes(n.status),
            );
        }
        if (isForce && $filters.project !== "ALL") {
            fNodes = fNodes.filter(
                (n) => n.project === $filters.project || n.type === "project" || n.type === "goal",
            );
        }
        if ($viewSettings.viewMode === "SFDP" && !$filters.showOrphans) {
            const nodesWithEdges = new Set<string>();
            fLinks.forEach((l) => {
                const sid = typeof l.source === "object" ? l.source.id : l.source;
                const tid = typeof l.target === "object" ? l.target.id : l.target;
                nodesWithEdges.add(sid);
                nodesWithEdges.add(tid);
            });
            fNodes = fNodes.filter((n) => nodesWithEdges.has(n.id) || !n.isLeaf);
        }
        if (!$filters.showDependencies) {
            fLinks = fLinks.filter((e) => e.type !== "depends_on");
        }
        if (!$filters.showReferences) {
            fLinks = fLinks.filter((e) => e.type !== "ref");
        }
        if (isForce && $viewSettings.topNLeaves < fNodes.length) {
            const parents = fNodes.filter((n) => !n.isLeaf);
            let leaves = fNodes.filter((n) => n.isLeaf).sort((a, b) => b.dw - a.dw);
            leaves = leaves.slice(0, $viewSettings.topNLeaves);
            fNodes = [...parents, ...leaves];
        }

        const survivingNodeIds = new Set(fNodes.map((n) => n.id));
        fLinks = fLinks.filter((l) => {
            const sid = typeof l.source === "object" ? l.source.id : l.source;
            const tid = typeof l.target === "object" ? l.target.id : l.target;
            return survivingNodeIds.has(sid) && survivingNodeIds.has(tid);
        });

        $graphData = { ...prepared, nodes: fNodes, links: fLinks };
    }

    function applyHighlightOpacity(nodes: GraphNode[], links: GraphEdge[]) {
        const active = $selection.activeNodeId;
        const isFocus = $selection.focusNodeId !== null;
        const focusSet = $selection.focusNeighborSet;
        const layout = getLayoutFromViewSettings($viewSettings);

        const parentMap = new Map();
        nodes.forEach(n => {
            if (n.parent) parentMap.set(n.id, n.parent);
        });

        // Helper to get all ancestors
        const getAncestors = (id: string) => {
            const ancestors = new Set<string>();
            let curr = parentMap.get(id);
            while (curr) {
                ancestors.add(curr);
                curr = parentMap.get(curr);
            }
            return ancestors;
        };

        nodes.forEach((n) => {
            if (["done", "completed", "cancelled"].includes(n.status)) {
                n.opacity = 0.4;
            } else if (n.status === "active") {
                n.opacity = 0.8;
            } else {
                n.opacity = 0.6;
            }

            if (isFocus && focusSet) {
                if (!focusSet.has(n.id)) n.opacity = 0.05;
                return;
            }

            if (active) {
                let isHighLighted = false;
                if (n.id === active) isHighLighted = true;

                // Is n a descendant of active?
                if (getAncestors(n.id).has(active)) isHighLighted = true;

                // Is n an ancestor of active?
                if (getAncestors(active).has(n.id)) isHighLighted = true;

                // Sibling logic for force/arc layouts
                const isActiveParentNode = nodes.find((act) => act.id === active)?.parent;
                if (isActiveParentNode && n.parent === isActiveParentNode && ["force", "arc"].includes(layout)) {
                    isHighLighted = true;
                }

                links.forEach((l) => {
                    const sid = typeof l.source === "object" ? l.source.id : l.source;
                    const tid = typeof l.target === "object" ? l.target.id : l.target;
                    // Highlight all connected nodes
                    if (sid === active && n.id === tid) isHighLighted = true;
                    if (tid === active && n.id === sid) isHighLighted = true;
                });

                if (!isHighLighted) n.opacity = 0.05; // Fade it deep
            }
        });

        links.forEach((l) => {
            if (isFocus && focusSet) {
                const sid = typeof l.source === "object" ? l.source.id : l.source;
                const tid = typeof l.target === "object" ? l.target.id : l.target;
                l.color = focusSet.has(sid) && focusSet.has(tid) ? l.color : "transparent";
            }
        });
    }

    $: activeLayout = getLayoutFromViewSettings($viewSettings);
</script>

{#if loading}
    <div class="col-span-12 flex items-center justify-center h-full text-primary font-mono text-xl animate-pulse">
        Initializing System...
    </div>
{:else if errorMsg}
    <div class="col-span-12 flex items-center justify-center h-full text-destructive font-mono text-lg">
        {errorMsg}
    </div>
{:else}
    {#if $viewSettings.theme === 'operator'}
        <!-- OPERATOR LAYOUT (12-Column Bento Grid) -->
        <!-- LEFT SIDEBAR: Navigation & Filters -->
        {#if $viewSettings.showSidebar}
            <aside class="col-span-3 border-r border-primary-border bg-background flex flex-col h-full overflow-y-auto custom-scrollbar transition-all">
                <Sidebar />
            </aside>
        {/if}

        {#if $viewSettings.mainTab === "Threaded Tasks"}
            <!-- THREADED TASKS & EDITOR OVERRIDE -->
            <section class="{$viewSettings.showSidebar ? 'col-span-9' : 'col-span-12'} flex flex-col h-full bg-background overflow-hidden transition-all">
                <ThreadedTasksView />
            </section>
        {:else}
            <!-- MAIN CONTENT: Graph or Dashboard -->
            <section class="{$viewSettings.showSidebar ? 'col-span-6' : 'col-span-9'} relative bg-surface flex flex-col h-full border-r border-primary-border overflow-hidden transition-all">
                <div class="absolute inset-0 grid-bg opacity-30 pointer-events-none"></div>

                <!-- Sub-Navigation for Graph Modes (Easy Access) -->
                {#if $viewSettings.mainTab === "Task Graph"}
                    <div class="absolute top-4 right-4 z-20 flex items-center gap-0 bg-black/90 backdrop-blur-lg border border-primary/40 p-0.5 shadow-[0_0_30px_rgba(0,0,0,0.8)]">
                        {#each ["Treemap", "Circle Pack", "Force Atlas 2", "SFDP", "Arc Diagram"] as mode}
                            <button
                                class="px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all cursor-pointer border border-transparent
                                {$viewSettings.viewMode === mode ? 'bg-primary text-black border-primary' : 'text-primary/50 hover:text-primary hover:bg-primary/5'}"
                                onclick={() => $viewSettings.viewMode = mode}
                            >
                                {mode}
                            </button>
                        {/each}
                    </div>
                {/if}

                <!-- Focus banner (Absolute Over Graph) -->
                {#if $selection.focusNodeId}
                    <div class="absolute top-4 left-4 z-20 flex items-center gap-3">
                        <button
                            class="px-3 py-1.5 bg-black/80 border border-primary/40 text-primary font-mono text-xs hover:bg-primary/20 transition-colors backdrop-blur-md cursor-pointer"
                            onclick={() =>
                                selection.update((s) => ({
                                    ...s,
                                    focusNodeId: null,
                                    focusNeighborSet: null,
                                }))}>← FULL VIEW</button>
                        <span class="px-3 py-1.5 bg-black/60 border border-primary/20 text-primary/70 font-mono text-xs backdrop-blur-md">
                            FOCUS: {focusNode?.fullTitle || $selection.focusNodeId}
                        </span>
                    </div>
                {/if}

                <!-- The Graph Area -->
                <div class="flex-1 relative z-0 h-full" class:blur-md={$viewSettings.mainTab === "Dashboard"} class:scale-105={$viewSettings.mainTab === "Dashboard"} style="transition: filter 0.5s ease, transform 0.5s ease;">
                    <ZoomContainer let:containerGroup let:innerWidth let:innerHeight>
                        {#if containerGroup}
                            {#if activeLayout === "treemap" || activeLayout === "tree"}
                                <TreemapView
                                    {containerGroup}
                                    width={innerWidth}
                                    height={innerHeight}
                                />
                            {:else if activeLayout === "circle_pack" || activeLayout === "circle"}
                                <CirclePackView {containerGroup} />
                            {:else if activeLayout === "force" || activeLayout === "fa2" || activeLayout === "sfdp"}
                                <ForceView {containerGroup} />
                            {:else if activeLayout === "arc"}
                                <ArcView {containerGroup} />
                            {/if}
                        {/if}
                    </ZoomContainer>
                </div>

                <!-- Legend -->
                <Legend />

                <!-- Graph Configuration Overlay -->
                <ViewConfigOverlay />

                <!-- Overlay Dashboard -->
                {#if $viewSettings.mainTab === "Dashboard"}
                    <div class="absolute inset-0 z-50 bg-background/90 backdrop-blur-lg overflow-y-auto custom-scrollbar">
                        <DashboardView {data} />
                    </div>
                {/if}
            </section>

            <!-- RIGHT SIDEBAR: Details / Editor -->
            <aside class="col-span-3 bg-background flex flex-col h-full overflow-y-auto custom-scrollbar">
                <TaskEditorView taskId={$selection.activeNodeId} onclose={() => selection.update(s => ({...s, activeNodeId: null}))} />
            </aside>
        {/if}
    {:else}
        <!-- HOLOGRAPHIC LAYOUT (Centralized Glassmorphism) -->
        <div class="w-full h-full flex flex-col items-center flex-1 px-4 md:px-12 py-8 relative">
            <div class="w-full max-w-7xl mb-8 flex flex-col md:flex-row justify-between items-end gap-6 z-10">
                <div class="text-left">
                    <span class="text-primary/60 text-xs font-bold tracking-[0.4em] uppercase mb-4 block">Neural Focus Protocol v4.2</span>
                    <div class="flex items-center gap-4">
                        <h1 class="text-slate-100 text-4xl md:text-5xl font-black leading-tight tracking-tighter glow-text uppercase">
                            {#if $viewSettings.mainTab === "Dashboard"}
                                Tactical <span class="text-primary italic">Overview</span>
                            {:else if $viewSettings.mainTab === "Task Graph"}
                                Active Focus <span class="text-primary italic">Path</span>
                            {:else if $viewSettings.mainTab === "Threaded Tasks"}
                                Deep Storage <span class="text-primary italic">Matrix</span>
                            {/if}
                        </h1>
                        <select
                            bind:value={$viewSettings.mainTab}
                            class="ml-4 bg-black/50 border border-primary/30 text-primary text-sm font-mono p-2 rounded outline-none cursor-pointer"
                        >
                            <option value="Dashboard">DASHBOARD</option>
                            <option value="Task Graph">TASK GRAPH</option>
                            <option value="Threaded Tasks">THREADED TASKS</option>
                        </select>
                    </div>
                </div>
                <div class="flex flex-col items-end gap-2">
                    {#if $viewSettings.mainTab === "Task Graph"}
                        <div class="flex gap-1 glass-card p-1 rounded-xl border border-primary/20">
                            {#each ["Treemap", "Circle Pack", "Force Atlas 2", "SFDP", "Arc Diagram"] as mode}
                                <button
                                    class="px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all cursor-pointer rounded-lg
                                    {$viewSettings.viewMode === mode ? 'bg-primary text-background shadow-[0_0_15px_rgba(var(--color-primary-rgb),0.4)]' : 'text-primary/60 hover:text-primary hover:bg-primary/10'}"
                                    onclick={() => $viewSettings.viewMode = mode}
                                >
                                    {mode}
                                </button>
                            {/each}
                        </div>
                    {/if}
                    <div class="flex gap-4">
                        <div class="px-6 py-3 glass-card rounded-xl text-center">
                            <p class="text-[10px] text-primary/60 uppercase font-bold tracking-widest mb-1">Graph Nodes</p>
                            <p class="text-3xl font-black text-white glow-text">{$graphData?.nodes?.length || 0}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Main Stage -->
            <section class="w-full max-w-7xl flex-1 relative min-h-[500px] flex items-center justify-center glass-panel rounded-2xl overflow-hidden shadow-2xl">
                {#if $viewSettings.mainTab === "Threaded Tasks"}
                    <div class="absolute inset-0 bg-black/40 backdrop-blur-md overflow-hidden flex flex-col">
                        <ThreadedTasksView />
                    </div>
                {:else}
                    <!-- Focus banner -->
                    {#if $selection.focusNodeId}
                        <div class="absolute top-6 left-6 z-20 flex items-center gap-3">
                            <button
                                class="px-4 py-2 glass-card text-primary font-mono text-xs hover:bg-primary/20 transition-colors cursor-pointer rounded-lg"
                                onclick={() =>
                                    selection.update((s) => ({
                                        ...s,
                                        focusNodeId: null,
                                        focusNeighborSet: null,
                                    }))}>← FULL VIEW</button>
                            <span class="px-4 py-2 glass-card text-primary/70 font-mono text-xs rounded-lg shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                                FOCUS: {focusNode?.fullTitle || $selection.focusNodeId}
                            </span>
                        </div>
                    {/if}

                    <div class="absolute inset-0 z-0">
                        <ZoomContainer let:containerGroup let:innerWidth let:innerHeight>
                            {#if containerGroup}
                                {#if activeLayout === "treemap" || activeLayout === "tree"}
                                    <TreemapView
                                        {containerGroup}
                                        width={innerWidth}
                                        height={innerHeight}
                                    />
                                {:else if activeLayout === "circle_pack" || activeLayout === "circle"}
                                    <CirclePackView {containerGroup} />
                                {:else if activeLayout === "force" || activeLayout === "fa2" || activeLayout === "sfdp"}
                                    <ForceView {containerGroup} />
                                {:else if activeLayout === "arc"}
                                    <ArcView {containerGroup} />
                                {/if}
                            {/if}
                        </ZoomContainer>
                    </div>

                    <!-- Overlay Dashboard -->
                    {#if $viewSettings.mainTab === "Dashboard"}
                        <div class="absolute inset-0 z-50 bg-black/60 backdrop-blur-xl overflow-y-auto custom-scrollbar p-8">
                            <DashboardView {data} />
                        </div>
                    {/if}

                    <!-- Task Editor Overlay -->
                    {#if $selection.activeNodeId}
                        <div class="absolute right-0 top-0 bottom-0 w-full max-w-2xl z-[60] bg-black/90 backdrop-blur-2xl border-l border-primary/20 shadow-2xl overflow-hidden shadow-primary/10">
                            <TaskEditorView taskId={$selection.activeNodeId} onclose={() => selection.update(s => ({...s, activeNodeId: null}))} />
                        </div>
                    {/if}
                {/if}
            </section>

            <!-- Bottom Data Grids -->
            {#if $viewSettings.mainTab !== "Dashboard"}
                <div class="w-full max-w-7xl grid grid-cols-1 md:grid-cols-3 gap-8 mb-8 shrink-0">
                    <!-- Dropped Threads (Context Recovery) -->
                    <div class="md:col-span-2 glass-panel p-8 rounded-2xl relative overflow-hidden">
                        <div class="absolute top-0 right-0 p-6 opacity-5 pointer-events-none">
                            <span class="material-symbols-outlined text-8xl">history</span>
                        </div>
                        <h3 class="flex items-center gap-2 text-primary font-bold tracking-widest uppercase text-xs mb-8">
                            <span class="material-symbols-outlined text-lg">dynamic_feed</span> Dropped Threads
                        </h3>
                        <div class="grid md:grid-cols-2 gap-4">
                            {#each (data?.dashboardData?.left_off?.abandoned || []).slice(0, 2) as thread}
                                <div class="glass-card p-5 rounded-xl border-l-2 border-primary group">
                                    <p class="text-[10px] font-bold text-primary/60 uppercase mb-2 truncate">{thread.project}</p>
                                    <h4 class="text-slate-100 font-bold mb-1 group-hover:text-primary transition-colors text-sm line-clamp-2">{thread.label}</h4>
                                    <p class="text-xs text-slate-500">{thread.status}</p>
                                    <button class="mt-4 flex items-center gap-2 text-[10px] font-black text-primary uppercase tracking-widest hover:gap-3 transition-all" onclick={() => { $viewSettings.mainTab = 'Threaded Tasks'; selection.update(s => ({...s, activeNodeId: thread.id})); }}>
                                        Resume Circuit <span class="material-symbols-outlined text-sm">bolt</span>
                                    </button>
                                </div>
                            {/each}
                            {#if (data?.dashboardData?.left_off?.abandoned || []).length === 0}
                                <div class="text-slate-500 italic text-sm">No dropped threads detected.</div>
                            {/if}
                        </div>
                    </div>

                    <!-- Blocker Radar -->
                    <div class="glass-panel p-8 rounded-2xl">
                        <h3 class="flex items-center gap-2 text-primary font-bold tracking-widest uppercase text-xs mb-8">
                            <span class="material-symbols-outlined text-lg">radar</span> Blocker Radar
                        </h3>
                        <div class="space-y-4 max-h-48 overflow-y-auto custom-scrollbar pr-2">
                            {#each ($graphData?.nodes || []).filter(n => n.status === 'blocked').slice(0, 4) as blocker}
                                <div class="flex items-center justify-between p-3 bg-primary/5 border border-primary/20 rounded-lg cursor-pointer hover:bg-primary/10 transition-colors" onclick={() => { selection.update(s => ({...s, focusNodeId: blocker.id})); }}>
                                    <span class="text-xs text-slate-100 font-bold truncate pr-2" title={blocker.label}>{blocker.label}</span>
                                    <span class="text-[10px] text-destructive font-mono shrink-0">BLOCKED</span>
                                </div>
                            {/each}
                            {#if ($graphData?.nodes || []).filter(n => n.status === 'blocked').length === 0}
                                <div class="text-slate-500 italic text-sm">No active blockers.</div>
                            {/if}
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    {/if}
{/if}

<style>
    :global(body) {
        margin: 0;
        padding: 0;
        overflow: hidden;
    }
</style>
