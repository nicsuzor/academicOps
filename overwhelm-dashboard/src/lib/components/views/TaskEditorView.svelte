<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { graphData } from "../../stores/graph";

    export let taskId: string;

    const dispatch = createEventDispatcher();

    $: task = $graphData?.nodes.find(n => n.id === taskId) || null;
    $: title = task?.label || "Unknown Task";
    $: description = (task as any)?._raw?.body || `No description provided for ${taskId}.`;

    function close() {
        dispatch("close");
    }
</script>

{#if task}
    <div class="flex flex-col h-full bg-background-light dark:bg-background-dark overflow-hidden font-mono">
        <!-- Breadcrumbs & Header -->
        <div class="flex flex-col gap-2 p-6 border-b border-primary/20 bg-background-dark shrink-0">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 text-xs font-mono opacity-60">
                    <button class="hover:text-primary transition-colors cursor-pointer uppercase" on:click={close}>WORKSPACE</button>
                    <span class="material-symbols-outlined text-[10px]">chevron_right</span>
                    <span class="uppercase">{task.project || 'UNASSIGNED'}</span>
                    <span class="material-symbols-outlined text-[10px]">chevron_right</span>
                    <span class="text-primary">{task.id.substring(0, 8)}</span>
                </div>
                <button class="text-primary hover:text-white transition-colors" on:click={close}>
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>

            <div class="flex flex-wrap justify-between items-end gap-4 mt-2">
                <div class="space-y-1 max-w-3xl">
                    <h1 class="text-2xl font-bold tracking-tight uppercase text-primary line-clamp-2">EDIT_TASK: {title}</h1>
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
                    <button class="px-6 py-2 border border-red-900 text-red-500 bg-red-900/10 hover:bg-red-900/30 font-bold text-sm transition-all rounded">
                        [ DELETE ]
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
                                <select class="w-full bg-background-dark border border-primary/30 rounded p-2 text-sm text-primary focus:ring-1 focus:ring-primary focus:border-primary outline-none">
                                    <option value="0" selected={task.priority === 0}>00_CRITICAL</option>
                                    <option value="1" selected={task.priority === 1}>01_HIGH</option>
                                    <option value="2" selected={task.priority === 2}>02_MEDIUM</option>
                                    <option value="3" selected={task.priority === 3}>03_LOW</option>
                                    <option value="4" selected={task.priority === 4}>04_BACKLOG</option>
                                </select>
                            </label>

                            <label class="block">
                                <span class="text-xs font-bold uppercase mb-2 block text-primary/70">Assignee</span>
                                <input class="w-full bg-background-dark border border-primary/30 rounded p-2 text-sm text-primary focus:ring-1 focus:ring-primary focus:border-primary outline-none placeholder:text-primary/30" placeholder="UNASSIGNED" type="text" value={task.assignee || ""}/>
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

                            <label class="block">
                                <span class="text-xs font-bold uppercase mb-2 block text-primary/70">Tags_Metadata</span>
                                <div class="flex flex-wrap gap-2">
                                    <span class="px-2 py-0.5 border border-primary bg-primary/10 text-[10px] font-bold text-primary">{task.type.toUpperCase()}</span>
                                    {#if task.structural}
                                        <span class="px-2 py-0.5 border border-primary bg-primary/10 text-[10px] font-bold text-primary">STRUCTURAL</span>
                                    {/if}
                                    <button class="px-2 py-0.5 border border-primary/30 text-[10px] font-bold text-primary/60 hover:text-primary hover:border-primary">+</button>
                                </div>
                            </label>
                        </div>
                    </div>

                    <!-- System Health Card / Task Metrics -->
                    <div class="border border-primary/30 p-4 bg-primary/5">
                        <span class="text-xs font-bold uppercase mb-3 block text-primary/70">Task_Metrics</span>
                        <div class="space-y-3">
                            <div>
                                <div class="flex justify-between text-[10px] font-mono mb-1 text-primary uppercase">
                                    <span>DOWNSTREAM_WEIGHT</span>
                                    <span>{task.dw.toFixed(1)}</span>
                                </div>
                                <div class="w-full bg-primary/10 h-1.5 rounded-full overflow-hidden">
                                    <div class="bg-primary h-full" style="width: {Math.min((task.dw / 50) * 100, 100)}%"></div>
                                </div>
                            </div>
                            <div>
                                <div class="flex justify-between text-[10px] font-mono mb-1 text-primary uppercase">
                                    <span>DEPTH_LEVEL</span>
                                    <span>{task.depth} / {task.maxDepth}</span>
                                </div>
                                <div class="w-full bg-primary/10 h-1.5 rounded-full overflow-hidden">
                                    <div class="bg-primary h-full" style="width: {(task.depth / Math.max(1, task.maxDepth)) * 100}%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Main Editor -->
                <div class="lg:col-span-2 flex flex-col h-full min-h-[500px]">
                    <div class="border border-primary/30 p-6 flex-1 bg-background-dark relative flex flex-col">
                        <div class="absolute top-0 right-0 p-2 text-[10px] font-mono text-primary/30 pointer-events-none">
                            ENCODING: UTF-8 | MARKDOWN
                        </div>
                        <div class="mb-4 flex items-center gap-4 border-b border-primary/20 pb-2">
                            <button class="text-xs font-bold text-primary border-b-2 border-primary pb-2 -mb-[9px]">DESCRIPTION</button>
                            <button class="text-xs font-bold text-primary/40 hover:text-primary transition-colors pb-2">SUB_TASKS</button>
                            <button class="text-xs font-bold text-primary/40 hover:text-primary transition-colors pb-2">HISTORY</button>
                        </div>
                        <textarea class="w-full flex-1 bg-transparent border-none focus:ring-0 text-sm font-mono leading-relaxed text-primary/90 resize-none outline-none" placeholder="[ENTER TECHNICAL SPECIFICATIONS HERE]">{description}</textarea>
                    </div>
                </div>
            </div>
        </div>
    </div>
{:else}
    <div class="flex items-center justify-center h-full text-red-500 font-mono">
        TASK_NOT_FOUND: {taskId}
    </div>
{/if}
