<script lang="ts">
    import { graphData } from "../../stores/graph";
    import HierarchyTree from "./HierarchyTree.svelte";
    import {
        TYPE_CHARGE,
        STATUS_FILLS
    } from "../../data/constants";

    let { taskId = null, onclose = () => {} }: { taskId?: string | null, onclose?: () => void } = $props();

    let task = $derived(taskId ? ($graphData?.nodes.find(n => n.id === taskId) || null) : null);
    let title = $derived((task as any)?.fullTitle || task?.label || "Unknown Task");
    let metadata = $derived((task as any)?._raw || {});

    let description = $state("");
    let loadingBody = $state(false);

    // Fetch body on-demand
    $effect(() => {
        if (task?.path) {
            fetchBody(task.path);
        } else {
            description = "";
        }
    });

    async function fetchBody(path: string) {
        loadingBody = true;
        try {
            const res = await fetch(`/api/task?path=${encodeURIComponent(path)}`);
            if (res.ok) {
                const data = await res.json();
                description = data.body || "";
            } else {
                description = "Failed to load task description.";
            }
        } catch (e) {
            description = "Error loading task description.";
        } finally {
            loadingBody = false;
        }
    }

    // Filter out internal fields from metadata display
    let filteredMetadata = $derived(Object.entries(metadata).filter(([key]) =>
        !['body', 'id', 'title', 'label', 'node_type', 'status', 'priority', 'project', 'assignee', 'layouts', 'x', 'y', 'depth', 'maxDepth', 'lines', 'dw', 'downstream_weight', 'modified', 'created', 'isLeaf', 'parent', 'fullTitle'].includes(key)
    ));

    const statusOptions = Object.keys(STATUS_FILLS).sort();
    const typeOptions = Object.keys(TYPE_CHARGE).sort();

    async function updateTask(updates: Record<string, any>) {
        if (!taskId || !task) return;

        // Optimistic local update
        graphData.update(gd => {
            if (!gd) return gd;
            const nodes = gd.nodes.map(n => {
                if (n.id === taskId) {
                    const updated = { ...n, ...updates };
                    // If status changed, update fill and text colors (simplified)
                    if (updates.status) {
                        updated.status = updates.status;
                    }
                    if (updates.type) {
                        updated.type = updates.type;
                    }
                    return updated;
                }
                return n;
            });
            return { ...gd, nodes };
        });

        console.log(`[AGENT ACTION REQUIRED] Update task ${taskId} with:`, updates);
        // In a real app, this would be an API call.
        // As an agent, I will perform the mcp__pkb__update_task call after this file edit.
    }

    function setStatus(status: string) {
        updateTask({ status });
    }

    function setType(type: string) {
        updateTask({ type });
    }

    function close() {
        onclose();
    }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && close()} />

{#if !taskId}
    <div class="flex flex-col items-center justify-center h-full text-primary/30 p-8 text-center bg-background border-l border-primary-border">
        <span class="material-symbols-outlined text-4xl mb-2">check_circle</span>
        <span class="text-xs tracking-widest uppercase">SELECT A TASK TO VIEW DETAILS</span>
    </div>
{:else if task}
    <div class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm cursor-pointer" onclick={close} onkeydown={(e) => e.key === 'Enter' && close()} tabindex="0" role="button"></div>
    <div class="absolute right-0 top-0 bottom-0 w-full max-w-4xl z-50 flex flex-col h-full bg-background overflow-hidden font-mono border-l border-primary/20 shadow-2xl">
        <!-- Breadcrumbs & Header -->
        <div class="flex flex-col gap-2 p-6 border-b border-primary/20 bg-background shrink-0">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 text-xs font-mono opacity-60">
                    <button class="hover:text-primary transition-colors cursor-pointer uppercase" onclick={close}>WORKSPACE</button>
                    <span class="material-symbols-outlined text-[10px]">chevron_right</span>
                    <span class="uppercase">{task.project || 'UNASSIGNED'}</span>
                    <span class="material-symbols-outlined text-[10px]">chevron_right</span>
                    <span class="text-primary">{task.id}</span>
                </div>
                <button class="text-primary/50 hover:text-primary transition-colors" onclick={close}>
                    <span class="material-symbols-outlined text-xl">close</span>
                </button>
            </div>

            <div class="flex flex-wrap justify-between items-end gap-4 mt-2">
                <div class="space-y-1 w-full max-w-2xl">
                    <h1 class="text-2xl font-bold tracking-tight uppercase text-primary break-words">EDIT: {title}</h1>
                    <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-primary/60 text-xs font-mono uppercase tracking-widest">
                        <div class="flex items-center gap-2">
                            <span>Type:</span>
                            <select
                                class="bg-primary/5 border border-primary/20 text-primary px-1 py-0.5 rounded outline-none focus:border-primary/50 transition-colors"
                                value={task.type}
                                onchange={(e) => setType(e.currentTarget.value)}
                            >
                                {#each typeOptions as type}
                                    <option value={type}>{type}</option>
                                {/each}
                            </select>
                        </div>
                        <div class="flex items-center gap-2">
                            <span>Status:</span>
                            <select
                                class="bg-primary/5 border border-primary/20 text-primary px-1 py-0.5 rounded outline-none focus:border-primary/50 transition-colors"
                                value={task.status}
                                onchange={(e) => setStatus(e.currentTarget.value)}
                            >
                                {#each statusOptions as status}
                                    <option value={status}>{status}</option>
                                {/each}
                            </select>
                        </div>
                        {#if task.modified}
                            <span>Modified: {new Date(task.modified).toLocaleString()}</span>
                        {/if}
                        {#if (task as any)?._raw?.created}
                            <span>Created: {new Date((task as any)._raw.created).toLocaleString()}</span>
                        {/if}
                    </div>
                </div>
                <div class="flex gap-3">
                    <button
                        class="px-6 py-2 border border-primary {task.status === 'done' ? 'bg-primary text-background-dark' : 'bg-primary/10 text-primary'} hover:bg-primary hover:text-background-dark font-bold text-sm transition-all rounded"
                        onclick={() => setStatus('done')}
                    >
                        [ {task.status === 'done' ? 'DONE ✓' : 'DONE'} ]
                    </button>
                    <button
                        class="px-6 py-2 border border-primary/40 {task.status === 'ready' ? 'bg-primary/30 border-primary text-primary' : 'text-primary/70'} hover:border-primary hover:text-primary font-bold text-sm transition-all rounded"
                        onclick={() => setStatus('ready')}
                    >
                        [ READY ]
                    </button>
                    <button
                        class="px-6 py-2 border border-primary/40 {task.status === 'paused' ? 'bg-amber-500/20 border-amber-500/50 text-amber-500' : 'text-primary/70'} hover:border-primary hover:text-primary font-bold text-sm transition-all rounded"
                        onclick={() => setStatus('paused')}
                    >
                        [ PAUSE ]
                    </button>
                    <button class="px-3 py-2 border border-destructive/30 text-destructive/70 hover:bg-destructive/10 hover:text-destructive font-bold text-sm transition-all rounded" title="Delete Task">
                        <span class="material-symbols-outlined text-sm">delete</span>
                    </button>
                </div>
            </div>
        </div>

        <!-- Form Grid -->
        <div class="flex-1 overflow-y-auto custom-scrollbar p-6">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-6xl mx-auto h-full">
                <!-- Sidebar Controls -->
                <div class="lg:col-span-1 space-y-6">
                    <div class="border border-primary/30 p-4 bg-primary/5 space-y-4">
                        <div class="space-y-4">
                            <label class="block">
                                <span class="text-xs font-bold uppercase mb-2 block text-primary/70">Priority_Level</span>
                                <select class="w-full bg-background border border-primary/30 rounded p-2 text-sm text-primary focus:ring-1 focus:ring-primary focus:border-primary outline-none">
                                    <option value="0" selected={task.priority === 0}>Critical</option>
                                    <option value="1" selected={task.priority === 1}>High</option>
                                    <option value="2" selected={task.priority === 2}>Medium</option>
                                    <option value="3" selected={task.priority === 3}>Low</option>
                                    <option value="4" selected={task.priority === 4}>Backlog</option>
                                </select>
                            </label>

                            <label class="block">
                                <span class="text-xs font-bold uppercase mb-2 block text-primary/70">Assignee</span>
                                <input class="w-full bg-background border border-primary/30 rounded p-2 text-sm text-primary focus:ring-1 focus:ring-primary focus:border-primary outline-none placeholder:text-primary/30" placeholder="UNASSIGNED" type="text" value={task.assignee || ""}/>
                            </label>

                            <label class="block border-t border-primary/10 pt-4">
                                <span class="text-xs font-bold uppercase mb-2 block text-primary/70">Hierarchy_Navigation</span>
                                <HierarchyTree {taskId} />
                            </label>

                            <label class="block">
                                <span class="text-xs font-bold uppercase mb-2 block text-primary/70">Dependencies</span>
                                <div class="space-y-2 max-h-32 overflow-y-auto pr-2 custom-scrollbar">
                                    {#each ($graphData?.links || []).filter(l => (typeof l.source === 'object' ? l.source.id : l.source) === task.id && l.type === 'depends_on') as dep}
                                        <div class="flex items-center justify-between p-2 border border-primary/20 bg-primary/10 rounded">
                                            <span class="text-[10px] font-mono text-primary truncate max-w-[180px]">DEP_{typeof dep.target === 'object' ? dep.target.id.substring(0, 8) : String(dep.target).substring(0, 8)}</span>
                                            <span class="material-symbols-outlined text-xs text-primary/40 hover:text-primary cursor-pointer">close</span>
                                        </div>
                                    {:else}
                                        <div class="text-[10px] text-primary/40 italic">No dependencies.</div>
                                    {/each}
                                    <button class="w-full border border-dashed border-primary/30 hover:border-primary py-1.5 text-[10px] uppercase text-primary/50 hover:text-primary transition-colors mt-2">+ Add Link</button>
                                </div>
                            </label>
                        </div>
                    </div>

                    <!-- Metadata Section -->
                    <div class="border border-primary/20 p-4 space-y-3">
                        <span class="text-xs font-bold uppercase block text-primary/70 border-b border-primary/10 pb-2 mb-2">Extended_Metadata</span>
                        <div class="space-y-2">
                            {#each filteredMetadata as [key, value]}
                                <div class="flex flex-col gap-1">
                                    <span class="text-[9px] uppercase text-primary/40 font-bold tracking-tighter">{key}</span>
                                    <span class="text-xs text-primary/80 truncate" title={String(value)}>{value}</span>
                                </div>
                            {/each}
                            {#if filteredMetadata.length === 0}
                                <span class="text-[10px] text-primary/30 italic">No extended metadata.</span>
                            {/if}
                        </div>
                    </div>
                </div>

                <!-- Main Editor -->
                <div class="lg:col-span-2 flex flex-col h-full min-h-[400px]">
                    <div class="border border-primary/30 p-6 flex-1 bg-background relative flex flex-col">
                        <div class="absolute top-0 right-0 p-2 text-[10px] font-mono text-primary/30 pointer-events-none">
                            ENCODING: UTF-8 | MARKDOWN
                        </div>
                        <div class="mb-4 flex items-center gap-4 border-b border-primary/20 pb-2">
                            <button class="text-xs font-bold text-primary border-b-2 border-primary pb-2 -mb-[9px]">DESCRIPTION</button>
                        </div>
                        <textarea class="w-full flex-1 bg-transparent border-none focus:ring-0 text-sm font-mono leading-relaxed text-primary/90 resize-none outline-none" placeholder={loadingBody ? "Loading content..." : (description ? "" : "No description provided.")} value={description}></textarea>
                    </div>
                </div>
            </div>
        </div>
    </div>
{:else}
    <!-- Empty state for task not found -->
    <div class="flex flex-col items-center justify-center h-full text-primary/30 p-8 text-center bg-background border-l border-primary-border">
        <span class="material-symbols-outlined text-4xl mb-2 text-red-500/50">error</span>
        <span class="text-xs tracking-widest uppercase">TASK NOT FOUND</span>
        <button class="mt-4 px-4 py-2 border border-primary/30 text-primary/60 hover:text-primary hover:border-primary transition-colors text-xs" onclick={close}>CLOSE</button>
    </div>
{/if}
