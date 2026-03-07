<script lang="ts">
    export let projectProjects: string[] = [];
    export let projectData: any = {};

    $: hasData = projectProjects && projectProjects.length > 0;
</script>

{#if hasData}
    <div class="flex flex-col gap-6 font-mono text-primary">
        {#each projectProjects as project}
            {@const meta = projectData.meta?.[project] || {}}
            {@const tasks = projectData.tasks?.[project] || []}
            {@const accomplishments =
                projectData.accomplishments?.[project] || []}
            {@const sessions = projectData.sessions?.[project] || []}

            {#if tasks.length > 0 || accomplishments.length > 0 || sessions.length > 0}
                <div class="flex flex-col gap-4">
                    <div class="flex justify-between items-center border-b border-primary/30 pb-2">
                        <h3 class="text-sm font-bold tracking-[0.2em] flex items-center gap-2">
                            <span class="material-symbols-outlined text-[16px]">folder_open</span>
                            {project.toUpperCase()}
                            {#if meta.is_spotlight}
                                <span class="bg-primary text-black text-[10px] px-2 py-0.5 ml-2 font-bold tracking-widest animate-pulse">
                                    SPOTLIGHT
                                </span>
                            {/if}
                        </h3>
                    </div>

                    <div class="flex flex-col gap-4">
                        {#if meta.epics && meta.epics.length > 0}
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {#each meta.epics as epic}
                                    <div class="bg-black/40 border border-primary/20 p-3 hover:border-primary transition-colors">
                                        <div class="flex justify-between items-center mb-2">
                                            <span class="text-xs font-bold truncate pr-2">{epic.title}</span>
                                            {#if epic.progress}
                                                <span class="text-[10px] text-primary/60 shrink-0"
                                                    >{epic.progress.completed}/{epic.progress.total}</span
                                                >
                                            {/if}
                                        </div>
                                        {#if epic.progress && epic.progress.total > 0}
                                            <div class="h-1 w-full bg-black border border-primary/30">
                                                <div
                                                    class="h-full bg-primary"
                                                    style="width: {(epic.progress.completed / epic.progress.total) * 100}%"
                                                ></div>
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        {/if}

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <!-- Active Tasks Column -->
                            <div class="flex flex-col gap-2">
                                <h4 class="text-[10px] font-bold tracking-widest text-primary/60 mb-1">ACTIVE TASKS</h4>
                                {#each tasks as task}
                                    <div class="flex items-start gap-2 p-2 bg-primary/5 border-l-2 {task.priority === 0 ? 'border-red-500' : task.priority === 1 ? 'border-orange-500' : 'border-primary/50'} hover:bg-primary/10 transition-colors">
                                        <span class="text-[10px] font-bold {task.priority === 0 ? 'text-red-500' : task.priority === 1 ? 'text-orange-500' : 'text-primary/70'}">P{task.priority}</span>
                                        <span class="text-xs text-primary/90 flex-1">{task.title}</span>
                                        {#if task.status === "in_progress"}
                                            <span class="text-[10px] bg-primary text-black px-1 font-bold animate-pulse">RUNNING</span>
                                        {/if}
                                    </div>
                                {:else}
                                    <div class="text-xs text-primary/40 italic">No active tasks.</div>
                                {/each}
                            </div>

                            <!-- Completed Column -->
                            <div class="flex flex-col gap-2">
                                <h4 class="text-[10px] font-bold tracking-widest text-primary/60 mb-1">RECENTLY COMPLETED</h4>
                                {#each accomplishments as acc}
                                    <div class="flex items-start gap-2 p-2 border border-primary/10 bg-black/30 hover:border-primary/30 transition-colors">
                                        <span class="material-symbols-outlined text-[14px] text-green-500">check</span>
                                        <span class="text-xs text-primary/70">{acc.description}</span>
                                    </div>
                                {:else}
                                    <div class="text-xs text-primary/40 italic">
                                        Nothing recently completed.
                                    </div>
                                {/each}
                            </div>
                        </div>
                    </div>
                </div>
            {/if}
        {/each}
    </div>
{/if}
