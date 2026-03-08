<script lang="ts">
    import { onMount } from "svelte";
    import Sidebar from "$lib/components/Sidebar.svelte";
    import DetailPanel from "$lib/components/DetailPanel.svelte";
    import ZoomContainer from "$lib/components/shared/ZoomContainer.svelte";
    import Legend from "$lib/components/shared/Legend.svelte";

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
    } from "$lib/stores/viewSettings";
    import { filters } from "$lib/stores/filters";
    import { selection } from "$lib/stores/selection";

    export let data: any;

    let rawGraph: any = null;
    let loading = true;
    let errorMsg = "";

    onMount(async () => {
        try {
            const res = await fetch("/tasks.json");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            rawGraph = await res.json();
            recomputeGraph();
        } catch (e: any) {
            errorMsg = "Failed to load tasks.json: " + e.message;
            console.error(e);
        } finally {
            loading = false;
        }
    });

    $: if (rawGraph) {
        recomputeGraph();
    }

    function recomputeGraph() {
        if (!rawGraph) return;

        const prepared = prepareGraphData(rawGraph);
        let fNodes = [...prepared.nodes];
        let fLinks = [...prepared.links];
        const isForce =
            $viewSettings.viewMode === "Force Atlas 2" ||
            $viewSettings.viewMode === "SFDP";

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
                (n) => !["done", "completed", "cancelled"].includes(n.status),
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

        applyHighlightOpacity(fNodes, fLinks);
        $graphData = { ...prepared, nodes: fNodes, links: fLinks };
    }

    function applyHighlightOpacity(nodes: GraphNode[], links: GraphEdge[]) {
        const active = $selection.activeNodeId;
        const isFocus = $selection.focusNodeId !== null;
        const focusSet = $selection.focusNeighborSet;
        const layout = getLayoutFromViewSettings($viewSettings);

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
                if (n.parent === active) isHighLighted = true;

                const isActiveParentNode = nodes.find((act) => act.id === active)?.parent;
                if (isActiveParentNode && n.parent === isActiveParentNode && ["force", "arc"].includes(layout)) {
                    isHighLighted = true;
                }

                links.forEach((l) => {
                    const sid = typeof l.source === "object" ? l.source.id : l.source;
                    const tid = typeof l.target === "object" ? l.target.id : l.target;
                    if (l.type === "depends_on") {
                        if (sid === active && n.id === tid) isHighLighted = true;
                        if (tid === active && n.id === sid) isHighLighted = true;
                    }
                });

                if (!isHighLighted) n.opacity = 0.12;
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

    $: {
        if ($selection && rawGraph) {
            recomputeGraph();
        }
    }

    $: activeLayout = getLayoutFromViewSettings($viewSettings);
</script>

{#if loading}
    <div class="col-span-12 flex items-center justify-center h-full text-primary font-mono text-xl animate-pulse">
        Initializing Operator System...
    </div>
{:else if errorMsg}
    <div class="col-span-12 flex items-center justify-center h-full text-red-500 font-mono text-lg">
        {errorMsg}
    </div>
{:else}
    <!-- LEFT SIDEBAR: Navigation & Filters -->
    <aside class="col-span-3 border-r border-primary/30 bg-background-dark flex flex-col h-full overflow-y-auto custom-scrollbar">
        <Sidebar />
    </aside>

    {#if $viewSettings.mainTab === "Threaded Tasks"}
        <!-- THREADED TASKS & EDITOR OVERRIDE -->
        <section class="col-span-9 flex flex-col h-full bg-background-dark overflow-hidden">
            <ThreadedTasksView />
        </section>
    {:else}
        <!-- MAIN CONTENT: Graph or Dashboard -->
        <section class="col-span-6 relative bg-surface-dark flex flex-col h-full border-r border-primary/30 overflow-hidden">
            <div class="absolute inset-0 grid-bg opacity-30 pointer-events-none"></div>

            <!-- Focus banner (Absolute Over Graph) -->
            {#if $selection.focusNodeId}
                <div class="absolute top-4 left-4 z-20 flex items-center gap-3">
                    <button
                        class="px-3 py-1.5 bg-black/80 border border-primary/40 text-primary font-mono text-xs hover:bg-primary/20 transition-colors backdrop-blur-md cursor-pointer"
                        on:click={() =>
                            selection.update((s) => ({
                                ...s,
                                focusNodeId: null,
                                focusNeighborSet: null,
                            }))}>← FULL VIEW</button>
                    <span class="px-3 py-1.5 bg-black/60 border border-primary/20 text-primary/70 font-mono text-xs backdrop-blur-md">
                        FOCUS: {$selection.focusNodeId}
                    </span>
                </div>
            {/if}

            <!-- The Graph Area -->
            <div class="flex-1 relative z-0 h-full" class:blur-md={$viewSettings.mainTab === "Dashboard"} class:scale-105={$viewSettings.mainTab === "Dashboard"} style="transition: filter 0.5s ease, transform 0.5s ease;">
                <ZoomContainer let:containerGroup>
                    {#if containerGroup}
                        {#if activeLayout === "treemap" || activeLayout === "tree"}
                            <TreemapView {containerGroup} />
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

            <!-- Overlay Dashboard -->
            {#if $viewSettings.mainTab === "Dashboard"}
                <div class="absolute inset-0 z-50 bg-background-dark/90 backdrop-blur-lg overflow-y-auto custom-scrollbar">
                    <DashboardView {data} />
                </div>
            {/if}
        </section>

        <!-- RIGHT SIDEBAR: Details -->
        <aside class="col-span-3 bg-background-dark flex flex-col h-full overflow-y-auto custom-scrollbar">
            <DetailPanel />
        </aside>
    {/if}
{/if}

<style>
    :global(body) {
        margin: 0;
        padding: 0;
        overflow: hidden;
    }
</style>
