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

    // Re-run prepareGraphData when global filters change that affect the data shape.
    // Wait, D3 filtering works better if we just pass a pre-filtered shallow copy
    // to the graph store rather than fully recomputing prepareGraphData.
    $: if (rawGraph) {
        recomputeGraph();
    }

    function recomputeGraph() {
        if (!rawGraph) return;

        // First, standard preprocessing
        const prepared = prepareGraphData(rawGraph);

        // Then apply current sidebar filters
        let fNodes = [...prepared.nodes];
        let fLinks = [...prepared.links];
        const isForce =
            $viewSettings.viewMode === "Force Atlas 2" ||
            $viewSettings.viewMode === "SFDP";

        // 1. Status filters
        if (!$filters.showActive) {
            fNodes = fNodes.filter(
                (n) =>
                    ![
                        "active",
                        "inbox",
                        "todo",
                        "in_progress",
                        "review",
                    ].includes(n.status),
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

        // 2. Project filter
        if (isForce && $filters.project !== "ALL") {
            fNodes = fNodes.filter(
                (n) =>
                    n.project === $filters.project ||
                    n.type === "project" ||
                    n.type === "goal",
            );
        }

        // 3. Orphans filter
        if ($viewSettings.viewMode === "SFDP" && !$filters.showOrphans) {
            // Only keep nodes that have edges
            const nodesWithEdges = new Set<string>();
            fLinks.forEach((l) => {
                const sid =
                    typeof l.source === "object" ? l.source.id : l.source;
                const tid =
                    typeof l.target === "object" ? l.target.id : l.target;
                nodesWithEdges.add(sid);
                nodesWithEdges.add(tid);
            });
            fNodes = fNodes.filter(
                (n) => nodesWithEdges.has(n.id) || !n.isLeaf,
            );
        }

        // 4. Edge toggles
        if (!$filters.showDependencies) {
            fLinks = fLinks.filter((e) => e.type !== "depends_on");
        }
        if (!$filters.showReferences) {
            fLinks = fLinks.filter((e) => e.type !== "ref");
        }

        // 5. Trim Top N (leaves only for performance)
        if (isForce && $viewSettings.topNLeaves < fNodes.length) {
            // Keep all structural nodes (parents), but limit leaves by weight
            const parents = fNodes.filter((n) => !n.isLeaf);
            let leaves = fNodes
                .filter((n) => n.isLeaf)
                .sort((a, b) => b.dw - a.dw);
            leaves = leaves.slice(0, $viewSettings.topNLeaves);
            fNodes = [...parents, ...leaves];
        }

        // Filter broken edges
        const survivingNodeIds = new Set(fNodes.map((n) => n.id));
        fLinks = fLinks.filter((l) => {
            const sid = typeof l.source === "object" ? l.source.id : l.source;
            const tid = typeof l.target === "object" ? l.target.id : l.target;
            return survivingNodeIds.has(sid) && survivingNodeIds.has(tid);
        });

        // 6. Highlight logic via opacity mutation
        applyHighlightOpacity(fNodes, fLinks);

        $graphData = { ...prepared, nodes: fNodes, links: fLinks };
    }

    function getNeighbors(nodeId: string, hops: number, links: GraphEdge[]) {
        const result = new Set<string>([nodeId]);
        let frontier = new Set<string>([nodeId]);
        for (let h = 0; h < hops; h++) {
            const next = new Set<string>();
            links.forEach((l) => {
                const sid =
                    typeof l.source === "object" ? l.source.id : l.source;
                const tid =
                    typeof l.target === "object" ? l.target.id : l.target;
                if (frontier.has(sid) && !result.has(tid)) {
                    next.add(tid);
                    result.add(tid);
                }
                if (frontier.has(tid) && !result.has(sid)) {
                    next.add(sid);
                    result.add(sid);
                }
            });
            frontier = next;
            if (frontier.size === 0) break;
        }
        return result;
    }

    function applyHighlightOpacity(nodes: GraphNode[], links: GraphEdge[]) {
        const active = $selection.activeNodeId;
        const isFocus = $selection.focusNodeId !== null;
        const focusSet = $selection.focusNeighborSet;
        const layout = getLayoutFromViewSettings($viewSettings);

        nodes.forEach((n) => {
            // Reset to default
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
                // Build highlight set for active selection
                // Normal highlight logic mimics index.html
                // For tree/circle: only deps. For force/arc: parents, siblings, deps.
                // Here we just use a simplified 1-hop focus for now or if we implement the exact html logic:
                let isHighLighted = false;

                if (n.id === active) isHighLighted = true;
                if (n.parent === active) isHighLighted = true;

                const isActiveParentNode = nodes.find(
                    (act) => act.id === active,
                )?.parent;
                if (
                    isActiveParentNode &&
                    n.parent === isActiveParentNode &&
                    ["force", "arc"].includes(layout)
                ) {
                    isHighLighted = true;
                }

                // deps
                links.forEach((l) => {
                    const sid =
                        typeof l.source === "object" ? l.source.id : l.source;
                    const tid =
                        typeof l.target === "object" ? l.target.id : l.target;
                    if (l.type === "depends_on") {
                        if (sid === active && n.id === tid)
                            isHighLighted = true;
                        if (tid === active && n.id === sid)
                            isHighLighted = true;
                    }
                });

                if (!isHighLighted) n.opacity = 0.12;
            }
        });

        links.forEach((l) => {
            if (isFocus && focusSet) {
                const sid =
                    typeof l.source === "object" ? l.source.id : l.source;
                const tid =
                    typeof l.target === "object" ? l.target.id : l.target;
                l.color =
                    focusSet.has(sid) && focusSet.has(tid)
                        ? l.color
                        : "transparent";
            }
        });
    }

    // Watch for selection changes to mutate highlight colors without a full recompute if possible,
    // but a full recompute is fast enough for Top N leaves locally.
    $: {
        if ($selection && rawGraph) {
            recomputeGraph();
        }
    }

    $: activeLayout = getLayoutFromViewSettings($viewSettings);
</script>

<div class="app-container">
    <Sidebar />
    <div class="main-content">
        {#if loading}
            <div class="msg">Loading tasks.json...</div>
        {:else if errorMsg}
            <div class="msg error">{errorMsg}</div>
        {:else}
            <!-- THE VOID (Background Layer) -->
            <div
                class="void-layer"
                class:deep-blur-scale={$viewSettings.mainTab === "Dashboard"}
            >
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

            <!-- DEEP DIVE (Project Overlays) -->
            {#if $viewSettings.mainTab === "Dashboard"}
                <div class="deep-dive-overlay">
                    <DashboardView {data} />
                </div>
            {/if}

            <DetailPanel />
            <Legend />

            {#if $selection.focusNodeId}
                <div class="focus-banner">
                    <button
                        on:click={() =>
                            selection.update((s) => ({
                                ...s,
                                focusNodeId: null,
                                focusNeighborSet: null,
                            }))}>← Full view</button
                    >
                    <span>Focusing Ego Network: {$selection.focusNodeId}</span>
                </div>
            {/if}
        {/if}
    </div>
</div>

<style>
    :global(body) {
        margin: 0;
        padding: 0;
        overflow: hidden;
        background: #0f172a; /* Slate 900 background for visualization area */
    }

    .app-container {
        display: flex;
        width: 100vw;
        height: 100vh;
    }

    .main-content {
        flex: 1;
        position: relative;
        background: var(--color-background);
        overflow: hidden;
    }

    .void-layer {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        transition:
            filter 0.6s cubic-bezier(0.16, 1, 0.3, 1),
            transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .deep-blur-scale {
        filter: blur(20px);
        transform: scale(
            1.5
        ); /* 300% is too extreme for SVG performance, 150% feels deep */
    }

    .deep-dive-overlay {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        z-index: 50;
        overflow-y: auto;
        padding-left: 320px; /* Offset for floating sidebar */
    }

    .msg {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        color: white;
        font-family: sans-serif;
    }
    .error {
        color: #f87171;
    }

    .focus-banner {
        position: absolute;
        top: 16px;
        left: 16px;
        z-index: 10;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .focus-banner button {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 11px;
        cursor: pointer;
        color: #f8fafc;
        font-weight: 600;
        backdrop-filter: blur(8px);
    }

    .focus-banner span {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 11px;
        color: #94a3b8;
        backdrop-filter: blur(8px);
    }
</style>
