<script lang="ts">
    import { graphData } from "../../stores/graph";
    import { selection } from "../../stores/selection";
    import TaskEditorView from "./TaskEditorView.svelte";

    let selectedTaskForEdit: string | null = null;
    let currentTab = "ACTIVE_TASKS";

    // Build the directory tree (Goals -> Projects -> Epics/Tasks)
    // For simplicity, we just extract projects and their tasks here based on current graph data.
    $: projects = $graphData ? Array.from(new Set($graphData.nodes.map(n => n.project).filter((p): p is string => !!p))).sort() : [];

    let expandedProjects: Record<string, boolean> = {};

    function toggleProject(p: string) {
        expandedProjects[p] = !expandedProjects[p];
    }

    $: activeTasks = $graphData ? $graphData.nodes.filter(n => !['done', 'completed', 'cancelled'].includes(n.status) && n.type === 'task') : [];
</script>

{#if selectedTaskForEdit}
    <TaskEditorView taskId={selectedTaskForEdit} on:close={() => selectedTaskForEdit = null} />
{:else}
    <div class="flex flex-1 overflow-hidden h-full">
        <!-- Directory Tree (TUI Style) -->
        <aside class="w-64 border-r border-primary/20 bg-background-dark flex flex-col shrink-0">
            <div class="p-4 border-b border-primary/10">
                <h3 class="text-xs font-bold text-primary/60 uppercase tracking-widest mb-1">Directory_Tree</h3>
                <p class="text-[10px] font-mono text-primary/40">WORKSPACE/PROJECTS</p>
            </div>
            <div class="flex-1 overflow-y-auto p-2 font-mono text-sm custom-scrollbar">
                <div class="mb-2">
                    <div class="flex items-center gap-2 p-2 text-primary hover:bg-primary/10 rounded cursor-pointer group">
                        <span class="material-symbols-outlined text-lg">target</span>
                        <span class="flex-1 font-bold">PROJECTS</span>
                    </div>
                    <div class="ml-4 border-l border-primary/20 pl-2 mt-1 space-y-1">
                        {#each projects as project}
                            <div>
                                <button class="flex items-center gap-2 p-1.5 w-full text-left {expandedProjects[project] ? 'text-primary/90 bg-primary/20 border-l-2 border-primary' : 'text-primary/80 hover:bg-primary/10'} rounded cursor-pointer" on:click={() => toggleProject(project)}>
                                    <span class="material-symbols-outlined text-base">{expandedProjects[project] ? 'folder_open' : 'folder'}</span>
                                    <span class="truncate">{project}</span>
                                </button>
                                {#if expandedProjects[project]}
                                    <div class="ml-4 border-l border-primary/20 pl-2 mt-1 space-y-1">
                                        {#each ($graphData?.nodes || []).filter(n => n.project === project && n.type === 'task').slice(0, 5) as task}
                                            <div class="flex items-center gap-2 p-1.5 text-primary/60 hover:text-primary hover:bg-primary/10 rounded cursor-pointer text-xs truncate">
                                                <span class="material-symbols-outlined text-sm">check_box_outline_blank</span>
                                                <span class="truncate">{task.label}</span>
                                            </div>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>

                <!-- Logs Section -->
                <div class="mt-4 pt-4 border-t border-primary/10">
                    <div class="flex items-center gap-2 p-2 text-primary/50 hover:text-primary hover:bg-primary/10 rounded cursor-pointer">
                        <span class="material-symbols-outlined text-lg">history</span>
                        <span>ARCHIVE_DUMP</span>
                    </div>
                </div>
            </div>

            <div class="p-4 bg-primary/5 text-[10px] font-mono border-t border-primary/20">
                <div class="flex justify-between items-center mb-1">
                    <span class="text-primary/60">TASKS_LOADED</span>
                    <span class="text-primary/60">{$graphData?.nodes.length || 0}</span>
                </div>
                <div class="w-full bg-primary/10 h-1 rounded-full overflow-hidden">
                    <div class="bg-primary h-full w-full"></div>
                </div>
            </div>
        </aside>

        <!-- Right Content: Breadcrumbs & Task List -->
        <section class="flex-1 flex flex-col bg-background-light dark:bg-background-dark relative">
            <!-- Breadcrumbs -->
            <div class="px-6 py-4 flex items-center gap-3 border-b border-primary/10 bg-primary/5">
                <div class="flex items-center gap-2 text-primary/60 text-sm font-mono">
                    <span class="hover:text-primary transition-colors cursor-pointer">WORKSPACE</span>
                    <span class="material-symbols-outlined text-xs">chevron_right</span>
                    <span class="text-primary font-bold">ALL_TASKS</span>
                </div>
                <div class="ml-auto flex gap-2">
                    <button class="bg-primary text-background-dark px-3 py-1 text-xs font-bold flex items-center gap-1 hover:brightness-110 font-mono transition-all">
                        <span class="material-symbols-outlined text-sm">add</span> NEW_TASK
                    </button>
                    <button class="bg-primary/10 border border-primary/30 text-primary px-3 py-1 text-xs font-bold hover:bg-primary/20 font-mono transition-all">
                        FILTER
                    </button>
                </div>
            </div>

            <!-- Tabs -->
            <div class="px-6 border-b border-primary/10 flex gap-8 font-mono">
                {#each ['ACTIVE_TASKS', 'COMPLETED', 'BACKLOG'] as tab}
                    <button
                        class="py-3 text-sm font-bold transition-colors {currentTab === tab ? 'text-primary border-b-2 border-primary' : 'text-primary/40 hover:text-primary'}"
                        on:click={() => currentTab = tab}
                    >
                        {tab} {tab === 'ACTIVE_TASKS' ? `[${activeTasks.length}]` : ''}
                    </button>
                {/each}
            </div>

            <!-- Task Table -->
            <div class="flex-1 overflow-auto p-6 custom-scrollbar">
                <div class="border border-primary/20 bg-background-dark shadow-xl">
                    <table class="w-full text-left border-collapse font-mono">
                        <thead>
                            <tr class="bg-primary/10 border-b border-primary/20">
                                <th class="px-4 py-3 text-[10px] font-bold text-primary/70 uppercase tracking-widest w-20">ID</th>
                                <th class="px-4 py-3 text-[10px] font-bold text-primary/70 uppercase tracking-widest w-32">Status</th>
                                <th class="px-4 py-3 text-[10px] font-bold text-primary/70 uppercase tracking-widest">Task_Name</th>
                                <th class="px-4 py-3 text-[10px] font-bold text-primary/70 uppercase tracking-widest w-32">Assignee</th>
                                <th class="px-4 py-3 text-[10px] font-bold text-primary/70 uppercase tracking-widest w-28">Priority</th>
                                <th class="px-4 py-3 text-[10px] font-bold text-primary/70 uppercase tracking-widest w-12"></th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-primary/10 text-sm">
                            {#each activeTasks as task}
                                <tr class="hover:bg-primary/5 group transition-colors cursor-pointer" on:click={() => selectedTaskForEdit = task.id}>
                                    <td class="px-4 py-4 text-primary/60">{task.id.substring(0, 8)}</td>
                                    <td class="px-4 py-4">
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border {task.status === 'in_progress' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-primary/5 text-primary/60 border-primary/20'} uppercase">
                                            {task.status}
                                        </span>
                                    </td>
                                    <td class="px-4 py-4">
                                        <div class="flex flex-col">
                                            <span class="text-primary font-medium">{task.label}</span>
                                            <span class="text-[10px] text-primary/40 mt-1 uppercase">Project: {task.project || 'None'}</span>
                                        </div>
                                    </td>
                                    <td class="px-4 py-4">
                                        <div class="flex items-center gap-2">
                                            {#if task.assignee}
                                                <div class="size-6 bg-primary/10 border border-primary/30 flex items-center justify-center text-[10px] text-primary font-bold">
                                                    {task.assignee.substring(0, 2).toUpperCase()}
                                                </div>
                                                <span class="text-primary/80 text-xs">{task.assignee}</span>
                                            {:else}
                                                <span class="text-primary/40 text-xs italic">Unassigned</span>
                                            {/if}
                                        </div>
                                    </td>
                                    <td class="px-4 py-4">
                                        <span class="inline-flex items-center gap-1.5 text-[10px] font-bold {task.priority === 0 ? 'text-red-500' : task.priority === 1 ? 'text-primary' : 'text-primary/60'}">
                                            <span class="size-1.5 rounded-full {task.priority === 0 ? 'bg-red-500' : task.priority === 1 ? 'bg-primary' : 'bg-primary/60'}"></span>
                                            {task.priority === 0 ? 'CRITICAL' : task.priority === 1 ? 'HIGH' : task.priority === 2 ? 'MED' : 'LOW'}
                                        </span>
                                    </td>
                                    <td class="px-4 py-4 text-right">
                                        <button class="opacity-0 group-hover:opacity-100 p-1 text-primary hover:bg-primary/20 transition-all" on:click|stopPropagation={() => selectedTaskForEdit = task.id}>
                                            <span class="material-symbols-outlined text-lg">edit</span>
                                        </button>
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>

                <!-- Density Controls Footer -->
                <div class="mt-4 flex items-center justify-between font-mono text-[10px] text-primary/40 uppercase">
                    <div class="flex gap-4">
                        <span>TOTAL_TASKS: {$graphData?.nodes.filter(n => n.type === 'task').length || 0}</span>
                        <span>FILTERED: {activeTasks.length}</span>
                    </div>
                </div>
            </div>
        </section>
    </div>
{/if}
