<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { graphData } from "../../stores/graph";
    import HierarchyTree from "./HierarchyTree.svelte";

    export let taskId: string | null = null;

    const dispatch = createEventDispatcher();

    $: task = taskId ? ($graphData?.nodes.find(n => n.id === taskId) || null) : null;
    $: title = task?.label || "Unknown Task";
    $: description = (task as any)?._raw?.body || ``;

    function close() {
        dispatch("close");
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
                <div class="space-y-1 max-w-xl">
                    <h1 class="text-2xl font-bold tracking-tight uppercase text-primary line-clamp-2">EDIT: {title}</h1>
                    <p class="text-primary/60 text-xs font-mono uppercase tracking-widest">
                        Type: {task.type} | Status:
                        <span class="text-primary {task.status === 'in_progress' ? 'animate-pulse' : ''}">
                            {task.status === 'in_progress' ? '● RUNNING' : task.status}
                        </span>
                    </p>
                </div>
                <div class="flex gap-3">
                    <button class="px-6 py-2 border border-primary bg-primary/10 text-primary hover:bg-primary hover:text-background-dark font-bold text-sm transition-all rounded">
                        [ SAVE ]
                    </button>
                    <button class="px-6 py-2 border border-primary/40 text-primary/70 hover:border-primary hover:text-primary font-bold text-sm transition-all rounded">
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
                        <textarea class="w-full flex-1 bg-transparent border-none focus:ring-0 text-sm font-mono leading-relaxed text-primary/90 resize-none outline-none" placeholder={description ? "" : "No description provided."} value={description}></textarea>
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
